import random
from datetime import datetime, timedelta, time
from app import create_app, db
from app.models import PVGenerationData, PVDevice, GridPoint

app = create_app()

# 与 monitor.py 保持一致的基准规则
BASE_FORECAST_RULES = [
    0, 0, 0, 0, 0, 0,
    30, 240, 540, 960, 1350, 1500,
    1530, 1440, 1140, 750, 450, 180,
    30, 0, 0, 0, 0, 0
]


def seed_7day_history():
    with app.app_context():
        print("=" * 60)
        print("🚀 正在注入过去 7 天的平滑+波动历史采集数据...")

        # 1. 基础检查
        if not GridPoint.query.get(1):
            db.session.add(GridPoint(grid_point_id=1, point_name="主并网点", capacity_kw=1500))

        devices = PVDevice.query.all()
        if not devices:
            print("❌ 错误：数据库中没有 PVDevice，请先初始化设备表")
            return

        # 2. 清理旧的采集数据 (可选，建议只清理历史时段的)
        seven_days_ago = datetime.now() - timedelta(days=7)
        db.session.query(PVGenerationData).filter(PVGenerationData.collect_time >= seven_days_ago).delete()
        print("🧹 已清理旧的 7 天采集数据")

        # 3. 循环生成 7 天数据
        now_dt = datetime.now()
        for day_offset in range(1, 8):
            # ✅ 修复：直接计算 Unix 时间戳基准，避免时区干扰
            target_date = (now_dt - timedelta(days=day_offset)).date()
            # 构造当天凌晨 00:00:00 的 datetime
            base_dt = datetime.combine(target_date, time.min)

            for hour in range(24):
                curr_base = BASE_FORECAST_RULES[hour]
                next_base = BASE_FORECAST_RULES[(hour + 1) % 24]

                for m in range(0, 60, 5):
                    weight = m / 60.0
                    interp_p = curr_base + (next_base - curr_base) * weight

                    if interp_p <= 0:
                        continue

                    # ✅ 修复：显式构造完整的时间戳
                    # 确保生成的点位严格对应 0, 5, 10 ... 分钟
                    precise_collect_time = base_dt + timedelta(hours=hour, minutes=m)

                    for dev in devices:
                        noise = random.uniform(0.95, 1.05)
                        if hour == 14:  # 模拟 14 点下跌规律
                            noise *= random.uniform(0.6, 0.8)

                        actual_p = interp_p * noise * (0.85 if dev.device_id == 2 else 1.0)
                        volts = 650.0 + random.uniform(-10, 10)
                        amps = (actual_p * 1000.0 / volts) / len(devices)

                        rec = PVGenerationData(
                            device_id=dev.device_id,
                            grid_point_id=1,
                            collect_time=precise_collect_time,  # ✅ 使用对齐后的时间
                            string_voltage_v=round(volts, 2),
                            string_current_a=round(amps, 2),
                            inverter_eff_pct=round(98.0 + random.uniform(-0.5, 0.5), 2),
                            gen_kwh=round(actual_p / 12, 4)
                        )
                        db.session.add(rec)
            db.session.commit()

        print("✅ 历史数据注入完成！模型现在可以‘学习’到 14:00 的下跌规律了。")
        print("=" * 60)


if __name__ == '__main__':
    seed_7day_history()