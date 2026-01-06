import sys
from datetime import datetime, timedelta
from app import create_app, db
from app.models import PVForecastData, GridPoint

app = create_app()


def force_inject_fault():
    with app.app_context():
        print("=" * 50)
        print("☢️  正在补全【历史故障数据】(昨天、前天)...")

        # 1. 先清空历史预测表 (防止重复)
        db.session.query(PVForecastData).delete()
        print("🧹 已清理旧历史数据")

        # 2. 确保有并网点
        if not GridPoint.query.get(1):
            db.session.add(GridPoint(grid_point_id=1, point_name="演示点", location="Sim", capacity_kw=1000))
            db.session.commit()

        # 3. 插入【昨天】和【前天】的数据 (严重故障)
        today = datetime.now().date()

        # 昨天
        d1 = today - timedelta(days=1)
        rec1 = PVForecastData(
            grid_point_id=1,
            forecast_date=d1,
            forecast_period='全天',
            forecast_kwh=1000.0,
            actual_kwh=550.0,
            deviation_pct=45.0,  # 异常
            model_version='v1.0',
            need_optimize=1
        )
        db.session.add(rec1)

        # 前天
        d2 = today - timedelta(days=2)
        rec2 = PVForecastData(
            grid_point_id=1,
            forecast_date=d2,
            forecast_period='全天',
            forecast_kwh=1000.0,
            actual_kwh=550.0,
            deviation_pct=45.0,  # 异常
            model_version='v1.0',
            need_optimize=1
        )
        db.session.add(rec2)

        # 注意：我们【不插入今天】的数据到这张表
        # 因为“今天”的数据由后端 monitor.py 实时计算，不需要查表

        db.session.commit()
        print(f"✅ 已补全: {d1} 和 {d2} 的故障记录")
        print("=" * 50)


if __name__ == '__main__':
    force_inject_fault()