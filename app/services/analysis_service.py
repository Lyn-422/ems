# app/services/analysis_service.py
from sqlalchemy import func
from app.extensions import db
from app.models import CircuitData, PeakValleyEnergy, PVForecastData, Plant


class AnalysisService:
    
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