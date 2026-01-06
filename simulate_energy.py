# app/simulate_data.py
import time
import random
import threading
from datetime import datetime
from app import create_app
from app.services.energy_data_service import EnergyDataService
from app.models import EnergyMeter

# =====================================================
# 初始化 Flask 上下文
# =====================================================
app = create_app()

# =====================================================
# 全局配置
# =====================================================
INTERVAL_SECONDS = 15  # 采集间隔
running = True         # 程序运行开关
paused = False        # 暂停开关
error_mode = False     # 🚨 异常数据生成模式开关

# =====================================================
# 控制台输入监听线程
# =====================================================
def console_listener():
    """
    监听控制台输入，用于控制采集行为
    """
    global running, paused, error_mode

    print("\n" + "="*40)
    print("🎮 模拟器控制台已就绪")
    print("  - stop    : 暂停生成")
    print("  - continue: 恢复生成")
    print("  - error   : 开启【错误模式】(产生待核实数据)")
    print("  - normal  : 恢复【正常模式】")
    print("  - exit    : 退出程序")
    print("="*40 + "\n")

    while running:
        try:
            cmd = input().strip().lower()

            if cmd == 'stop':
                paused = True
                print("⏸ [系统] 已暂停生成能耗数据")

            elif cmd == 'continue':
                paused = False
                print("▶ [系统] 已恢复生成能耗数据")

            elif cmd == 'error':
                error_mode = True
                print("🚨 [警报] 错误模式已开启！即将生成大量异常数据以测试待核实功能...")

            elif cmd == 'normal':
                error_mode = False
                print("✅ [系统] 正常模式已恢复。")

            elif cmd in ('exit', 'quit'):
                running = False
                print("🛑 [系统] 正在停止模拟采集程序...")

            elif cmd == '':
                continue
            else:
                print(f"❓ 未知命令: {cmd}")
        except EOFError:
            break

# =====================================================
# 能耗数据模拟主逻辑
# =====================================================
def simulate_energy_collect():
    global running, paused, error_mode

    with app.app_context():
        meters = EnergyMeter.query.all()

        if not meters:
            print("❌ 错误: 数据库中未找到任何能耗计量设备 (EnergyMeter)，请先初始化基础档案。")
            return

        print(f"✅ 成功加载 {len(meters)} 个设备，开始循环采集...")

        while running:
            if paused:
                time.sleep(1)
                continue

            now = datetime.now()

            for meter in meters:
                # 1. 按能源类型决定基础参数
                if meter.energy_type == 'water':
                    base = 10; unit = 'm3'
                elif meter.energy_type == 'gas':
                    base = 8; unit = 'm3'
                elif meter.energy_type == 'steam':
                    base = 2; unit = 't'
                elif meter.energy_type == 'electric':
                    base = 50; unit = 'kWh'
                else:
                    continue

                # 2. 根据模式决定数值生成策略
                if error_mode:
                    # 💡 产生极大值，强制触发 EnergyDataService 的异常拦截逻辑
                    value = base * random.uniform(5.0, 10.0)
                    log_prefix = "⚠️ [异常触发]"
                else:
                    # 正常随机波动
                    value = base + random.uniform(-1.5, 1.5)
                    # 模拟 5% 的自发随机异常
                    if random.random() < 0.05:
                        value *= random.uniform(1.4, 2.0)
                    log_prefix = "📈 [正常采集]"

                value = round(value, 2)

                # 3. 统一通过 Service 入库 (Service 会自动判定 need_verify)
                try:
                    EnergyDataService.save_energy_data(
                        meter_id=meter.meter_id,
                        plant_id=meter.plant_id,
                        collect_time=now,
                        energy_value=value,
                        unit=unit
                    )

                    print(
                        f"[{now.strftime('%H:%M:%S')}] {log_prefix} "
                        f"{meter.energy_type.upper()}(ID:{meter.meter_id}) "
                        f"值: {value}{unit}"
                    )
                except Exception as e:
                    print(f"❌ 入库失败 (ID:{meter.meter_id}): {str(e)}")

            # 按照配置的间隔等待
            time.sleep(INTERVAL_SECONDS)

        print("👋 模拟程序已安全关闭。")

# =====================================================
# 程序入口
# =====================================================
if __name__ == '__main__':
    # 启动控制台监听线程 (daemon=True 保证主程序退出时它也退出)
    t = threading.Thread(target=console_listener, daemon=True)
    t.start()

    # 启动采集主循环
    simulate_energy_collect()