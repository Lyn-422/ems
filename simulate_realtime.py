import time
import threading
import random
from datetime import datetime
from app import create_app
from app.extensions import db
from app.services.alarm_service import AlarmService
from app.models import TransformerData, CircuitData, PowerRoom, EquipmentLedger, Alarm

# 1. 【引入配置】
from app.configs import ROOM_CONFIGS

app = create_app()

INTERVAL_SECONDS = 15

# 2. 【自动展平列表】用于随机故障抽取
# 解释：遍历 ROOM_CONFIGS，拿出每个 transformers 元组的第一个元素(编号)
ALL_TRANSFORMERS = [t[0] for r in ROOM_CONFIGS for t in r['transformers']]
ALL_CIRCUITS = [c[0] for r in ROOM_CONFIGS for c in r['circuits']]

# 故障状态存储
fault_state = {
    'transformer_targets': [],
    'circuit_targets': []
}


# ================= 变压器生成逻辑 =================
def generate_transformer_task():
    with app.app_context():
        now = datetime.now()

        # 3. 【遍历配置】无需再手动定义 ROOM_MAPPING
        for room_conf in ROOM_CONFIGS:
            room_code = room_conf['code']  # 注意这里是 'code' 键
            room = PowerRoom.query.filter_by(room_code=room_code).first()
            if not room: continue

            # 遍历该房间下的变压器 (注意是元组解包)
            for t_code, _, _ in room_conf['transformers']:
                ledger = EquipmentLedger.query.filter_by(equipment_code=t_code).first()
                if not ledger: continue

                is_faulty = (t_code in fault_state['transformer_targets'])

                if not is_faulty:
                    base = 60 if '001' in t_code or '004' in t_code else 40
                    load_rate = base + random.uniform(-5, 5)
                    winding_temp = 40 + (load_rate * 0.4) + random.uniform(-1, 1)
                    core_temp = winding_temp + 2
                    run_status = '正常'

                    # 心跳日志
                    if t_code == 'TRANS_001' and not fault_state['transformer_targets']:
                        print(f"[{now.strftime('%H:%M:%S')}] 🔌 [变压器] 系统平稳")
                else:
                    load_rate = random.uniform(90, 98)
                    winding_temp = 90 + random.uniform(0, 5)
                    core_temp = winding_temp + 5
                    run_status = '超温告警'
                    print(f"[{now.strftime('%H:%M:%S')}] 🔥 [变压器] {t_code} 故障! 温度: {winding_temp:.1f}℃")

                td = TransformerData(
                    power_room_id=room.power_room_id, transformer_code=t_code, collect_time=now,
                    load_rate_percent=round(load_rate, 2), winding_temp_c=round(winding_temp, 1),
                    core_temp_c=round(core_temp, 1), env_temp_c=25.0, env_humidity=45.0, run_status=run_status
                )
                db.session.add(td)

                if winding_temp > 85.0:
                    trigger_alarm(ledger.equipment_id, f'{t_code} 绕组温度过高 ({round(winding_temp, 1)}℃)', '>85℃')

        db.session.commit()


# ================= 回路生成逻辑 =================
def generate_circuit_task():
    with app.app_context():
        now = datetime.now()

        for room_conf in ROOM_CONFIGS:
            room = PowerRoom.query.filter_by(room_code=room_conf['code']).first()
            if not room: continue

            for c_code, _, _ in room_conf['circuits']:
                ledger = EquipmentLedger.query.filter_by(equipment_code=c_code).first()

                is_faulty = (c_code in fault_state['circuit_targets'])
                voltage = 10.2 + random.uniform(-0.1, 0.1)

                if not is_faulty:
                    base = 200 if 'incoming' in c_code else 50
                    current = base + random.uniform(-5, 5)
                    active_power = current * voltage * 1.732 * 0.95
                    is_abnormal = 0
                    cable_temp = 30 + (current / 20)

                    if c_code == 'AL1_incoming' and not fault_state['circuit_targets']:
                        print(f"[{now.strftime('%H:%M:%S')}] ⚡ [回  路] 系统平稳")
                else:
                    current = 600 + random.uniform(0, 50)
                    active_power = current * voltage * 1.732 * 0.6
                    is_abnormal = 1
                    cable_temp = 85.0
                    print(f"[{now.strftime('%H:%M:%S')}] 💥 [回  路] {c_code} 过载! 电流: {current:.1f}A")

                cd = CircuitData(
                    power_room_id=room.power_room_id, circuit_code=c_code, collect_time=now,
                    voltage_kv=round(voltage, 2), current_a=round(current, 2), active_power_kw=round(active_power, 2),
                    reactive_power_kvar=round(active_power * 0.3, 2), power_factor=0.95, forward_kwh=10000.0,
                    reverse_kwh=0, switch_status='合闸', cable_temp_c=round(cable_temp, 1),
                    capacitor_temp_c=30.0, is_abnormal=is_abnormal
                )
                db.session.add(cd)

                if current > 400.0 and ledger:
                    trigger_alarm(ledger.equipment_id, f'{c_code} 回路电流过载 ({round(current, 1)}A)', '>400A')

        db.session.commit()


# ================= 通用辅助 =================
def trigger_alarm(equipment_id, content, threshold_desc):
    search_key = content.split(' ')[0]
    existing_alarm = Alarm.query.filter(
        Alarm.equipment_id == equipment_id, Alarm.alarm_content.like(f'%{search_key}%'),
        Alarm.handle_status.in_(['未处理', '处理中'])
    ).first()
    if not existing_alarm:
        print(f"   >>> 🚨 [自动告警] 已为 {search_key} 创建告警单！")
        AlarmService.create_alarm(equipment_id=equipment_id, content=content, level='高', alarm_type=threshold_desc)


def auto_generator_loop():
    while True:
        time.sleep(INTERVAL_SECONDS)
        generate_transformer_task()
        generate_circuit_task()


def main_controller():
    print("=" * 60)
    print("🚀 智能仿真终端 (配置驱动版 - 动态适配 configs.py)")
    print(f"   刷新频率: {INTERVAL_SECONDS} 秒")
    print("-" * 60)
    print("   [error_t] : 随机让 1~3 台变压器故障")
    print("   [fix_t]   : 修复变压器")
    print("-" * 60)
    print("   [error_c] : 随机让 1~3 条回路故障")
    print("   [fix_c]   : 修复回路")
    print("-" * 60)
    print("   [q]       : 退出")
    print("=" * 60)

    t = threading.Thread(target=auto_generator_loop, daemon=True)
    t.start()

    while True:
        cmd = input(">>> ").strip().lower()
        if cmd == 'q':
            break

        elif cmd == 'error_t':
            count = random.randint(1, min(3, len(ALL_TRANSFORMERS)))
            targets = random.sample(ALL_TRANSFORMERS, count)
            fault_state['transformer_targets'] = targets
            print(f"\n🎲 命中 {count} 个目标: {', '.join(targets)}")
            print(f"🔥 故障注入成功！")
            generate_transformer_task()

        elif cmd == 'fix_t':
            fault_state['transformer_targets'] = []
            print("\n💚 变压器已修复。")
            generate_transformer_task()

        elif cmd == 'error_c':
            count = random.randint(1, min(3, len(ALL_CIRCUITS)))
            targets = random.sample(ALL_CIRCUITS, count)
            fault_state['circuit_targets'] = targets
            print(f"\n🎲 命中 {count} 个目标: {', '.join(targets)}")
            print(f"💥 故障注入成功！")
            generate_circuit_task()

        elif cmd == 'fix_c':
            fault_state['circuit_targets'] = []
            print("\n💚 回路已修复。")
            generate_circuit_task()
        else:
            print("❌ 无效指令")


if __name__ == '__main__':
    main_controller()