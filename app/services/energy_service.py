# app/services/energy_service.py
from sqlalchemy import func, extract
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


  #==========月度报表===========
    @classmethod
    def get_period_energy_report(cls, plant_id, energy_type, year, period_value, period_type='month'):
        from datetime import date, timedelta
        import calendar

        # 1. 确定时间范围
        if period_type == 'month':
            start_date = date(year, period_value, 1)
            _, last_day = calendar.monthrange(year, period_value)
            end_date = date(year, period_value, last_day)
        else:  # quarter
            start_month = (period_value - 1) * 3 + 1
            start_date = date(year, start_month, 1)
            _, last_day = calendar.monthrange(year, start_month + 2)
            end_date = date(year, start_month + 2, last_day)

        # 2. 【核心】自动补偿缺失的日数据
        # 检查从 start_date 到 end_date 每一天是否有数据，没有就算一遍
        curr = start_date
        while curr <= end_date:
            exists = PeakValleyEnergy.query.filter_by(
                plant_id=plant_id, energy_type=energy_type, stat_date=curr
            ).first()
            if not exists:
                # 发现日能耗没更新，立即触发计算
                cls.calculate_daily_energy_cost(plant_id, energy_type, curr)
            curr += timedelta(days=1)

        # 3. 聚合查询（求和）
        report = db.session.query(
            func.sum(PeakValleyEnergy.sharp_value).label('sharp'),
            func.sum(PeakValleyEnergy.peak_value).label('peak'),
            func.sum(PeakValleyEnergy.flat_value).label('flat'),
            func.sum(PeakValleyEnergy.valley_value).label('valley'),
            func.sum(PeakValleyEnergy.total_value).label('total'),
            func.sum(PeakValleyEnergy.total_cost).label('cost')
        ).filter(
            PeakValleyEnergy.plant_id == plant_id,
            PeakValleyEnergy.energy_type == energy_type,
            PeakValleyEnergy.stat_date.between(start_date, end_date)
        ).first()

        return report

    #=======综合分析=========


    @classmethod
    def get_period_comprehensive_analysis(cls, year, period_type, period_value):
        """
        [多维度经营分析核心]
        修正版：增加 plant_costs 字段并保证厂区数据顺序一致
        """


        # 1. 基础聚合查询：关联厂区表和日统计表
        query = db.session.query(
            Plant.plant_name,
            PeakValleyEnergy.energy_type,
            func.sum(PeakValleyEnergy.total_value).label('total_val'),
            func.sum(PeakValleyEnergy.total_cost).label('total_cost')
        ).join(PeakValleyEnergy, Plant.plant_id == Plant.plant_id)

        # 2. 时间维度过滤
        query = query.filter(extract('year', PeakValleyEnergy.stat_date) == year)
        if period_type == 'month':
            query = query.filter(extract('month', PeakValleyEnergy.stat_date) == period_value)
        else:  # quarter
            start_month = (int(period_value) - 1) * 3 + 1
            query = query.filter(extract('month', PeakValleyEnergy.stat_date).between(start_month, start_month + 2))

        # 3. 按厂区和能源类型交叉分组
        results = query.group_by(Plant.plant_name, PeakValleyEnergy.energy_type).all()

        # 4. 结构化处理
        report_data = {
            "plants": [],  # 柱状图 X 轴：厂区名称列表
            "plant_costs": [],  # 柱状图 Y 轴：厂区总成本列表
            "cost_pie": []  # 饼图数据
        }

        # 临时字典用于聚合
        energy_costs_map = {}  # 能源类型 -> 总成本
        plant_costs_map = {}  # 厂区名称 -> 总成本

        for r in results:
            p_name = r[0]
            e_type = r[1]
            cost = float(r[3] or 0)

            # 汇总各能源成本 (用于饼图)
            energy_costs_map[e_type] = energy_costs_map.get(e_type, 0) + cost
            # 汇总各厂区成本 (用于柱状图)
            plant_costs_map[p_name] = plant_costs_map.get(p_name, 0) + cost

        # 整理饼图数据
        name_map = {'electric': '电力', 'water': '水', 'gas': '天然气', 'steam': '蒸汽'}
        for e_key, e_name in name_map.items():
            if e_key in energy_costs_map:
                report_data["cost_pie"].append({
                    "name": e_name,
                    "value": round(energy_costs_map[e_key], 2)
                })

        # 整理柱状图数据 (确保 plants 和 plant_costs 索引一一对应)
        for p_name, p_total_cost in plant_costs_map.items():
            report_data["plants"].append(p_name)
            report_data["plant_costs"].append(round(p_total_cost, 2))

        return report_data, results