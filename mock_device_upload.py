import time
import threading
import random
import requests
from datetime import datetime

# ================= 配置 =================
API_URL = "http://127.0.0.1:5000/monitor/api/pv/upload"
INTERVAL_SECONDS = 5

# 标准功率曲线 (基准：单台峰值约 500kW)
FORECAST_RULES = [
    0, 0, 0, 0, 0, 0,
    10, 80, 180, 320, 450, 500,
    510, 480, 380, 250, 150, 60,
    10, 0, 0, 0, 0, 0, 0
]

current_sim_factor = 1.1
current_weather_name = "晴天"


def get_base_power():
    """
    ✅ 核心改进：线性插值平滑功率
    根据当前 小时+分钟，在两个整点功率之间进行平滑过渡
    """
    now = datetime.now()
    h = now.hour
    m = now.minute

    # 获取当前小时和下一小时的基准
    curr_rule = FORECAST_RULES[h] if h < 24 else 0
    next_rule = FORECAST_RULES[(h + 1) % 24]

    # 计算当前分钟在整点间的比例 (0.0 到 1.0)
    # 比如 10:30，就是 10:00 和 11:00 的中间点
    weight = m / 60.0

    # 线性插值公式
    smooth_base = curr_rule + (next_rule - curr_rule) * weight

    return smooth_base * current_sim_factor


def upload_loop():
    device_ids = [1, 2, 3]

    while True:
        try:
            # 获取平滑后的基准值
            base_p = get_base_power()

            for dev_id in device_ids:
                # 1. 差异化各设备功率 (ID 2 略低, ID 3 略高)
                if dev_id == 2:
                    p = base_p * 0.85
                elif dev_id == 3:
                    p = base_p * 1.15
                else:
                    p = base_p

                # ✅ 2. 增强随机起伏逻辑 (模拟真实波动)
                # 叠加一个 -2% 到 +2% 的比例抖动
                noise_factor = random.uniform(0.98, 1.02)
                # 再叠加一个微小的绝对功率波动 (±2kW)
                jitter = random.uniform(-2, 2)

                # 计算最终实时功率
                p = max(0, (p * noise_factor) + jitter)

                # 3. 模拟电压和电流 (电压也加入微弱抖动)
                volts = 650.0 + random.uniform(-5, 5)
                amps = (p * 1000.0) / volts if volts > 0 else 0

                # 4. 构造 Payload
                payload = {
                    "device_id": dev_id,
                    "string_voltage_v": round(volts, 2),
                    "string_current_a": round(amps, 2),
                    "inverter_eff_pct": round(98.2 + random.uniform(0, 1.0), 2),
                    "gen_kwh": round(p * (INTERVAL_SECONDS / 3600), 4)
                }

                requests.post(API_URL, json=payload, timeout=2)

            # print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌤️ 发送功率: {round(base_p * 3, 2)} kW")

        except Exception as e:
            print(f"❌ 上传异常: {e}")

        time.sleep(INTERVAL_SECONDS)


# main 函数保持不变 ...
def main():
    global current_sim_factor, current_weather_name
    t = threading.Thread(target=upload_loop, daemon=True)
    t.start()
    print("=" * 60)
    print("   分布式光伏多设备集群模拟器 - 丝滑平滑版")
    print("   特性：整点线性插值 + 5s随机扰动")
    print("=" * 60)

    while True:
        cmd = input("切换天气模式 > ").strip().lower()
        if cmd == 'sunny':
            current_sim_factor = 1.1
            current_weather_name = "晴天"
            print(">>> ☀️ 切换至晴天")
        elif cmd == 'cloudy':
            current_sim_factor = 0.6
            current_weather_name = "多云"
            print(">>> ☁️ 切换至多云")
        elif cmd == 'rainy':
            current_sim_factor = 0.2
            current_weather_name = "雨天"
            print(">>> 🌧️ 切换至雨天")
        else:
            print("无效指令")


if __name__ == '__main__':
    main()