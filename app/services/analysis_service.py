# app/services/analysis_service.py
from sqlalchemy import func
from app.extensions import db
from app.models import CircuitData, PeakValleyEnergy, PVForecastData, Plant


class AnalysisService:
    """
    数据分析服务
    [cite_start]对应业务线: 综合能耗管理 [cite: 41, 42][cite_start], 光伏预测优化 [cite: 31, 37]
    """

    # 定义峰谷时段 (小时)
    SHARP_HOURS = [10, 11, 16, 17]
    PEAK_HOURS = [8, 9, 12, 13, 14, 15, 18, 19, 20, 21]
    FLAT_HOURS = [6, 7, 22, 23]
    VALLEY_HOURS = [0, 1, 2, 3, 4, 5]

    # 模拟电价 (元/kWh)
    PRICE_MAP = {'sharp': 1.5, 'peak': 1.2, 'flat': 0.8, 'valley': 0.4}

    @classmethod
    def calculate_plant_daily_cost(cls, plant_id, stat_date):
        """
        计算厂区日能耗成本 (聚合该厂区下所有配电房数据)
        注意：实际业务中需建立 Plant -> PowerRoom 的关联，此处简化为查询所有数据演示
        """
        try:
            # 1. 获取当天的监测数据
            # 实际 SQL 应关联查询: CircuitData JOIN PowerRoom (where responsible_id...)
            records = CircuitData.query.filter(
                func.date(CircuitData.collect_time) == stat_date
            ).all()

            sharp, peak, flat, valley = 0.0, 0.0, 0.0, 0.0

            for r in records:
                hour = r.collect_time.hour
                # 假设采集频率为15分钟 (0.25h)，功率(kW) * 时间(h) = 电量(kWh)
                # 如果是分钟级采集，系数为 1/60
                kwh = float(r.active_power_kw or 0) * (15 / 60)

                if hour in cls.SHARP_HOURS:
                    sharp += kwh
                elif hour in cls.PEAK_HOURS:
                    peak += kwh
                elif hour in cls.FLAT_HOURS:
                    flat += kwh
                else:
                    valley += kwh

            total_kwh = sharp + peak + flat + valley
            total_cost = (sharp * cls.PRICE_MAP['sharp'] +
                          peak * cls.PRICE_MAP['peak'] +
                          flat * cls.PRICE_MAP['flat'] +
                          valley * cls.PRICE_MAP['valley'])

            avg_price = total_cost / total_kwh if total_kwh > 0 else 0

            # 2. 持久化存储结果
            # 检查是否已存在记录
            report = PeakValleyEnergy.query.filter_by(plant_id=plant_id, stat_date=stat_date).first()
            if not report:
                report = PeakValleyEnergy(plant_id=plant_id, stat_date=stat_date)

            report.sharp_value = round(sharp, 2)
            report.peak_value = round(peak, 2)
            report.flat_value = round(flat, 2)
            report.valley_value = round(valley, 2)
            report.total_value = round(total_kwh, 2)
            report.total_cost = round(total_cost, 2)
            report.price_per_unit = round(avg_price, 4)

            db.session.add(report)
            db.session.commit()
            return report

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def analyze_pv_forecast(grid_point_id, check_date):
        """
        [cite_start]分析光伏预测偏差 [cite: 37]
        """
        forecasts = PVForecastData.query.filter_by(
            grid_point_id=grid_point_id,
            forecast_date=check_date
        ).all()

        warnings = []
        for f in forecasts:
            if f.actual_kwh and f.forecast_kwh and f.forecast_kwh > 0:
                # 计算偏差率
                deviation = abs(float(f.actual_kwh - f.forecast_kwh)) / float(f.forecast_kwh)
                f.deviation_pct = round(deviation * 100, 2)

                # 偏差率超 15% 触发逻辑
                if f.deviation_pct > 15.0:
                    warnings.append(f"时段 {f.forecast_period} 偏差过大 ({f.deviation_pct}%)，建议优化模型")

        db.session.commit()
        return warnings