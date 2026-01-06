# app/services/energy_service.py
from sqlalchemy import func
from app.extensions import db
from app.models import  PeakValleyEnergy, EnergyData, EnergyMeter ,Plant
from decimal import Decimal


class AnalysisService:
    # 定义峰谷时段 (小时)
    SHARP_HOURS = [10, 11, 16, 17]
    PEAK_HOURS = [8, 9, 12, 13, 14, 15, 18, 19, 20, 21]
    FLAT_HOURS = [6, 7, 22, 23]
    VALLEY_HOURS = [0, 1, 2, 3, 4, 5]


    # 不同能源类型的模拟
    PRICE_MAP = {
        'electric': {'sharp': 1.5, 'peak': 1.2, 'flat': 0.8, 'valley': 0.4},  # 电力的单价
        'water': {'sharp': 0.8, 'peak': 0.7, 'flat': 0.5, 'valley': 0.3},  # 水的单价
        'gas': {'sharp': 2.0, 'peak': 1.8, 'flat': 1.0, 'valley': 0.5},  # 天然气的单价
        'steam': {'sharp': 2.5, 'peak': 2.2, 'flat': 1.5, 'valley': 1.0},  # 蒸汽的单价
    }

    @classmethod
    def calculate_daily_energy_cost(cls, plant_id, energy_type, stat_date):
        """
        计算指定日期和厂区的日能耗成本 (包含峰谷能耗统计)
        """

        try:
            print(f"Start calculating energy cost for plant {plant_id}, energy type {energy_type}, date {stat_date}")

            # 获取该厂区所有选中类型的能耗计量设备
            meters = EnergyMeter.query.filter_by(plant_id=plant_id, energy_type=energy_type).all()

            if not meters:
                print("No meters found for this plant and energy type")
                return None

            sharp, peak, flat, valley = 0.0, 0.0, 0.0, 0.0

            for meter in meters:
                records = db.session.query(EnergyData).filter(
                    func.date(EnergyData.collect_time) == stat_date,
                    EnergyData.plant_id == plant_id,
                    EnergyData.meter_id == meter.meter_id,
                    EnergyData.need_verify == 0 # 只统计已确认数据
                ).all()

                # 根据时段进行分类计算能耗
                for record in records:
                    hour = record.collect_time.hour
                    try:
                        energy_value = float(record.energy_value)
                    except ValueError:
                        print(
                            f"Invalid energy value: {record.energy_value} for meter {meter.meter_id} at {record.collect_time}")
                        continue  # 跳过无效记录

                    print(f"Record time: {record.collect_time}, hour: {hour}, energy value: {energy_value}")

                    # 根据时段进行分类计算能耗
                    if hour in cls.SHARP_HOURS:
                        print(f"  - Sharp hours: Adding {energy_value} to sharp.")
                        sharp += energy_value
                    elif hour in cls.PEAK_HOURS:
                        print(f"  - Peak hours: Adding {energy_value} to peak.")
                        peak += energy_value
                    elif hour in cls.FLAT_HOURS:
                        print(f"  - Flat hours: Adding {energy_value} to flat.")
                        flat += energy_value
                    else:
                        print(f"  - Valley hours: Adding {energy_value} to valley.")
                        valley += energy_value

            # 计算总能耗
            total_value = sharp + peak + flat + valley
            print(
                f"Total energy consumption: sharp={sharp}, peak={peak}, flat={flat}, valley={valley}, total={total_value}")

            # 使用对应能源类型的单价来计算总成本
            price_map = cls.PRICE_MAP.get(energy_type, {})
            total_cost = (sharp * price_map.get('sharp', 0) +
                          peak * price_map.get('peak', 0) +
                          flat * price_map.get('flat', 0) +
                          valley * price_map.get('valley', 0))
            avg_price = total_cost / total_value if total_value > 0 else 0

            print(f"Total cost: {total_cost}, Average price per unit: {avg_price}")

            # 存储或更新数据
            report = PeakValleyEnergy.query.filter_by(plant_id=plant_id, stat_date=stat_date,
                                                      energy_type=energy_type).first()
            if not report:
                print(f"Creating a new report for {plant_id} on {stat_date}")
                report = PeakValleyEnergy(plant_id=plant_id, stat_date=stat_date, energy_type=energy_type)

            report.sharp_value = round(sharp, 2)
            report.peak_value = round(peak, 2)
            report.flat_value = round(flat, 2)
            report.valley_value = round(valley, 2)
            report.total_value = round(total_value, 2)
            report.total_cost = round(total_cost, 2)
            report.price_per_unit = round(avg_price, 4)

            db.session.add(report)
            db.session.commit()
            print(f"Report created/updated successfully for {plant_id} on {stat_date}")

            return report

        except Exception as e:
            db.session.rollback()
            print(f"Error occurred while calculating energy cost: {str(e)}")
            raise e

    @classmethod
    def analyze_high_energy_plant(cls, stat_date, energy_type, threshold=0.3):
        # 修改点：使用 join 关联 Plant 表，查询出 (能耗记录对象, 厂区名称)
        records = (
            db.session.query(PeakValleyEnergy, Plant.plant_name)
            .join(Plant, PeakValleyEnergy.plant_id == Plant.plant_id)
            .filter(
                PeakValleyEnergy.stat_date == stat_date,
                PeakValleyEnergy.energy_type == energy_type
            ).all()
        )

        if not records:
            return None, []

        # 计算平均值
        total_sum = sum(r[0].total_value for r in records)
        avg_value = float(total_sum / len(records))

        threshold_dec = Decimal(str(threshold))
        limit = Decimal(str(avg_value)) * (Decimal('1') + threshold_dec)

        high_plants = []
        # r[0] 是 PeakValleyEnergy 对象，r[1] 是 plant_name 字符串
        for r, plant_name in records:
            if r.total_value > limit:
                high_plants.append({
                    'plant_id': r.plant_id,
                    'plant_name': plant_name,  # 新增：保存厂区名称
                    'total_value': float(r.total_value),
                    'avg_value': avg_value,
                    'exceed_pct': float(
                        (r.total_value - Decimal(str(avg_value))) / Decimal(str(avg_value)) * 100
                    )
                })

        return avg_value, high_plants