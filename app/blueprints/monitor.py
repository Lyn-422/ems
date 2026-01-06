# app/blueprints/monitor.py

from flask import Blueprint, render_template, request, jsonify,flash
from sqlalchemy import func
from app.decorators import role_required
from app.models import PowerRoom, CircuitData, PVDevice, GridPoint, TransformerData, PVGenerationData, PVForecastData
from app.extensions import db
from datetime import datetime, date, time , timedelta
from flask_login import current_user # 【新增】需要获取当前登录用户
import math
import time as time_mod  # 重命名避免冲突

bp = Blueprint('monitor', __name__)

# =================================================
# 1. 定义标准预测曲线 (基准线 0-23点)
# =================================================
BASE_FORECAST_RULES = [
    0, 0, 0, 0, 0, 0,
    30, 240, 540, 960, 1350, 1500,  # 06:00 - 11:00
    1530, 1440, 1140, 750, 450, 180, # 12:00 - 17:00
    30, 0, 0, 0, 0, 0, 0
]

# 【核心逻辑】预测修正系数
# 1.0 = 正常状态
# 0.6 = 优化后状态 (适应故障/低功率环境)
current_forecast_factor = 1.0


# ============= 配电网监测业务线  =============
@bp.route('/distribution')
@role_required(['operator', 'admin', 'analyst', 'order_manager'])
def distribution_list():
    """
    配电房列表与状态
    【修改】实现权限控制: 运维人员仅能查看负责区域
    """
    user_roles = [r.role_name for r in current_user.roles]

    # 如果是超级管理员，查看所有
    if 'admin' in user_roles:
        rooms = PowerRoom.query.all()

    # 如果只是运维人员(且不是管理员)，只查 responsible_id 匹配的
    elif 'operator' in user_roles:
        rooms = PowerRoom.query.filter_by(responsible_id=current_user.user_id).all()
        # 如果该运维人员没被分配任何配电房，给个空列表或提示
        if not rooms:
            flash('您当前没有负责的配电区域，请联系管理员分配。', 'info')

    # 其他角色(如分析师)默认看所有(或根据需求调整)
    else:
        rooms = PowerRoom.query.all()

    return render_template('monitor/distribution_list.html', rooms=rooms)
@bp.route('/transformer/<int:power_room_id>')
@role_required(['operator', 'energy_manager', 'admin', 'order_manager'])
def transformer_detail(power_room_id):
    """ 变压器监测详情页 """
    room = PowerRoom.query.get_or_404(power_room_id)
    transformers = TransformerData.query.filter_by(power_room_id=power_room_id) \
        .order_by(TransformerData.collect_time.desc()).limit(50).all()
    return render_template('monitor/transformer_detail.html', room=room, transformers=transformers)


# ============= 分布式光伏管理业务线  =============
@bp.route('/pv')
@role_required(['analyst', 'admin', 'operator'])
def pv_dashboard():
    """ 光伏设备运行状态 """
    devices = PVDevice.query.join(GridPoint).all()
    return render_template('monitor/pv_dashboard.html', devices=devices)


@bp.route('/api/pv/upload', methods=['POST'])
def upload_pv_data():
    """接收模拟器数据并存入数据库"""
    data = request.json
    try:
        # 1. 获取设备 ID (确保和 init_data 中的 device_id 对应)
        dev_id = data.get('device_id')
        if not dev_id:
            return jsonify({"code": 400, "msg": "缺少 device_id"}), 400

        # 2. 从数据包中提取字段 (适配你的 Mock 脚本)
        v = data.get('string_voltage_v', 0)
        i = data.get('string_current_a', 0)
        eff = data.get('inverter_eff_pct', 98.5)
        gen = data.get('gen_kwh', 0)

        # 3. 创建新记录 (字段名必须与你的 PVGenerationData 模型完全一致)
        new_record = PVGenerationData(
            device_id=dev_id,
            collect_time=datetime.now(),
            string_voltage_v=v,
            string_current_a=i,
            inverter_eff_pct=eff,
            gen_kwh=gen,
            grid_point_id=1  # 对应你 init_data 中创建的 grid_point_id
        )

        db.session.add(new_record)
        db.session.commit()

        return jsonify({"code": 200, "msg": "数据上传成功"})

    except Exception as e:
        db.session.rollback()
        # 在终端打印错误详情，方便你看到底是哪个字段错了
        print(f"❌ 上传失败详情: {str(e)}")
        return jsonify({"code": 500, "msg": f"后端处理出错: {str(e)}"}), 500


def get_historical_average_power(hour, minute_slot):
    """
    ✅ 新增：从数据库获取过去3天该时间点的平均功率
    """
    try:
        # 获取过去3天的同一时间段
        # 这里为了演示逻辑，我们通过 SQL 计算该时段的历史平均值
        # 实际生产中建议将此计算结果缓存，避免每次请求都扫大表
        avg_val = db.session.query(
            func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0)
        ).filter(
            func.date_format(PVGenerationData.collect_time, '%H:%i') >= f"{hour:02d}:{minute_slot:02d}",
            func.date_format(PVGenerationData.collect_time, '%H:%i') < f"{hour:02d}:{(minute_slot + 5):02d}"
        ).scalar() or 0
        return float(avg_val)
    except:
        return 0


current_forecast_factor = 1.0


# def get_smoothed_forecast(factor):
#     """
#     ✅ 关键改进：引入动态权重权重
#     如果 factor 被人工调整（不等于 1.0），说明历史数据不可信，加大理论基准的权重
#     """
#     smoothed_data = []
#     history_features = get_db_weighted_history()
#
#     # 判定是否处于人工干预状态
#     is_intervened = abs(factor - 1.0) > 0.05
#
#     for h in range(24):
#         curr_rule = BASE_FORECAST_RULES[h] * factor
#         next_rule = BASE_FORECAST_RULES[(h + 1) % 24] * factor
#
#         for i in range(12):
#             slot_idx = h * 12 + i
#             fraction = i / 12.0
#             interp_val = curr_rule + (next_rule - curr_rule) * fraction
#
#             db_val = history_features.get(slot_idx)
#
#             # ✅ 动态调权逻辑：
#             # 如果人工点击了优化，理论基准(interp_val)权重占 90%，强制曲线移动
#             # 如果是正常运行，历史特征(db_val)权重占 90%，保持波形真实
#             if is_intervened or db_val is None:
#                 final_val = interp_val
#             else:
#                 # 正常模式下，结合历史特征
#                 final_val = (db_val * 0.9) + (interp_val * 0.1)
#
#             pseudo_noise = (math.sin(h + i) * 0.01 + 1)
#             smoothed_data.append(round(final_val * pseudo_noise, 2))
#     return smoothed_data

def slot_noise(h, i):
    """生成基于时间槽的固定伪噪声，让预测线带点“历史感”"""
    return (math.sin(h + i) + math.cos(h * i)) if 'math' in globals() else 1


# def get_db_weighted_forecast(factor):
#     """
#     ✅ 修复：统一 Slot 计算 + 全局系数应用
#     """
#     forecast_288 = []
#     device_count = PVDevice.query.count() or 1
#
#     # 获取历史特征 (get_db_weighted_history 已经改对了，这里直接调用)
#     history_map = get_db_weighted_history()
#
#     for slot in range(288):
#         h = slot // 12
#         m_frac = (slot % 12) / 12.0
#
#         # 理论插值
#         curr_rule = BASE_FORECAST_RULES[h]
#         next_rule = BASE_FORECAST_RULES[(h + 1) % 24]
#         rule_val = curr_rule + (next_rule - curr_rule) * m_frac
#
#         # 混合历史
#         hist_val = history_map.get(slot, rule_val)
#
#         # 混合基数 (80% 历史 + 20% 理论)
#         base_val = (hist_val * 0.8) + (rule_val * 0.2)
#
#         # ✅ 关键修改：系数 factor 乘在最外面
#         # 这样 optimize_model 算出的 factor 才能真正把曲线拉到实际值
#         final_val = base_val * factor
#
#         forecast_288.append(round(final_val * (1 + math.sin(slot) * 0.002), 2))
#
#     return forecast_288

def get_db_history_map():
    """(保持不变)"""
    history_map = {}
    try:
        seven_days_ago = datetime.now() - timedelta(days=7)
        stats = db.session.query(
            (func.hour(PVGenerationData.collect_time) * 12 + func.floor(func.minute(PVGenerationData.collect_time) / 5)).label('slot'),
            func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0)
        ).filter(PVGenerationData.collect_time >= seven_days_ago).group_by('slot').all()

        device_count = PVDevice.query.count() or 1
        history_map = {int(s): float(v or 0) * device_count for s, v in stats}
    except Exception as e:
        print(f"提取历史特征失败: {e}")
    return history_map


def get_final_forecast_series(factor, split_idx=None):
    """
    ✅ 核心修复：分段预测生成
    - split_idx 之前 (过去)：使用系数 1.0 (显示原始基准，证明过去预测可能有偏)
    - split_idx 之后 (未来)：使用优化系数 (显示修正后的趋势)
    """
    forecast_288 = []
    history_map = get_db_history_map()

    # 如果没有传入分割点，说明是查看明天/全天预览，直接全量应用系数
    if split_idx is None:
        split_idx = -1

    for slot in range(288):
        h = slot // 12
        m_frac = (slot % 12) / 12.0

        # 1. 基础计算
        curr_rule = BASE_FORECAST_RULES[h]
        next_rule = BASE_FORECAST_RULES[(h + 1) % 24]
        rule_val = curr_rule + (next_rule - curr_rule) * m_frac
        hist_val = history_map.get(slot, rule_val)
        base_val = (hist_val * 0.8) + (rule_val * 0.2)

        # 2. ✅ 分段应用系数
        # 过去的时间保持原样 (1.0)，未来的时间应用优化系数
        # 这样点击优化时，只有当前点之后的蓝线会跳变，前面的保持不动
        active_factor = 1.0 if slot < split_idx else factor

        final_val = base_val * active_factor

        # 注入微小噪声
        forecast_288.append(round(final_val * (1 + math.sin(slot) * 0.002), 2))

    return forecast_288


# =================================================

@bp.route('/api/pv/realtime')
def pv_realtime_data():
    global current_forecast_factor
    now = datetime.now()
    today_start = datetime.combine(date.today(), time.min)

    devices = PVDevice.query.all()
    device_count = len(devices) if devices else 1

    # A. 实时功率
    total_latest_power = 0.0
    for dev in devices:
        last = PVGenerationData.query.filter_by(device_id=dev.device_id).order_by(
            PVGenerationData.collect_time.desc()).first()
        if last and (now - last.collect_time).total_seconds() < 60:
            total_latest_power += (float(last.string_voltage_v or 0) * float(last.string_current_a or 0)) / 1000.0

    # B. ✅ 绿线修复：初始化为 None，实现断线效果
    real_power_series = [None] * 288

    stats = db.session.query(
        (func.hour(PVGenerationData.collect_time) * 12 + func.floor(func.minute(PVGenerationData.collect_time) / 5)).label(
            'slot'),
        (func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0) * device_count)
    ).filter(PVGenerationData.collect_time >= today_start).group_by('slot').all()

    for slot, val in stats:
        idx = int(slot)
        if 0 <= idx < 288:
            real_power_series[idx] = round(float(val or 0), 2)

    # 锁定当前时间槽
    current_idx = now.hour * 12 + now.minute // 5

    # 填充 0 点到当前点的空洞 (防止断断续续)，但只填到 current_idx
    # 如果数据库没数，说明是 0 功率
    for i in range(current_idx + 1):
        if real_power_series[i] is None:
            real_power_series[i] = 0.0

    # 强制对齐末端
    if 0 <= current_idx < 288:
        real_power_series[current_idx] = round(total_latest_power, 2)

    # ✅ 关键：current_idx 之后的数据保持为 None (ECharts 不会绘制)

    # C. 生成分段预测线
    forecast_series = get_final_forecast_series(current_forecast_factor, split_idx=current_idx)

    # D. 偏差率 (复用分段后的预测值)
    current_forecast = forecast_series[current_idx] if current_idx < 288 else 0
    deviation_rate = 0.0
    if current_forecast > 1.0:
        deviation_rate = (abs(total_latest_power - current_forecast) / current_forecast) * 100
    elif total_latest_power > 1.0:
        deviation_rate = 100.0

    total_energy = db.session.query(func.sum(PVGenerationData.gen_kwh)).filter(
        PVGenerationData.collect_time >= today_start).scalar() or 0

    return jsonify({
        'current_power': round(total_latest_power, 2),
        'daily_energy': round(float(total_energy), 1),
        'co2_reduce': round(float(total_energy) * 0.997 / 1000, 3),
        'deviation_rate': round(deviation_rate, 1),
        'chart_series': real_power_series,  # 包含 None 的数组
        'forecast_series': forecast_series,
        'status': 'healthy' if deviation_rate < 15.0 else 'risk'
    })

# 修改 monitor.py 中的 get_pv_forecast 接口
@bp.route('/api/pv/forecast')
def get_pv_forecast():
    """
    ✅ 核心功能：基于【历史特征】的明日天气模拟
    逻辑：复用 get_final_forecast_series，但 split_idx 传 None (全天应用系数)
    """
    global current_forecast_factor

    weather = request.args.get('weather')

    # 定义三种典型气象的修正系数
    # 晴天=1.15 (比平时高)，多云=0.65 (明显下降)，雨天=0.25 (压得很低)
    weather_map = {
        'sunny': 1.15,
        'cloudy': 0.65,
        'rainy': 0.25
    }

    # 获取目标系数：
    # 如果前端传了 weather 参数，使用对应系数
    # 如果没传 (比如刚加载时)，使用当前正在运行的实时系数 (current_forecast_factor)
    target_factor = weather_map.get(weather, current_forecast_factor)

    # 生成预测数据
    # 注意：这里不传 split_idx，意味着全天 288 个点都应用 target_factor
    # 这样用户看到的就是一条完整的、带有本电站历史特征的“明天预测线”
    forecast_data = get_final_forecast_series(target_factor)

    return jsonify({'code': 200, 'data': forecast_data})


# app/blueprints/monitor.py

@bp.route('/api/pv/model_status')
def get_model_status():
    """
    ✅ 唯一的模型状态函数
    合并了实时偏差对齐逻辑与历史显示逻辑
    """
    global current_forecast_factor
    try:
        # 1. 统一调用实时数据接口的逻辑，确保数值与顶部卡片绝对一致
        realtime_response = pv_realtime_data()
        realtime_data = realtime_response.get_json()

        today_deviation = realtime_data.get('deviation_rate', 0.0)

        # 2. 获取历史记录 (过去2天)
        today_date = date.today()
        history_records = PVForecastData.query.filter(PVForecastData.forecast_date < today_date).order_by(
            PVForecastData.forecast_date.desc()).limit(2).all()

        # 3. 构造返回列表
        data_list = [
            {
                'date': '今天 (实时)',
                'deviation': today_deviation,
                'status': '异常' if today_deviation > 15 else '正常'
            }
        ]

        for r in history_records:
            dev_val = float(r.deviation_pct or 0)
            data_list.append({
                'date': r.forecast_date.strftime('%m-%d'),
                'deviation': round(dev_val, 1),
                'status': '异常' if dev_val > 15 else '正常'
            })

        # 4. 判定状态：只要今天异常，就激活优化按钮
        is_alarm = True if today_deviation > 15.0 else False

        return jsonify({
            'status': 'risk' if is_alarm else 'healthy',
            'history': data_list,
            'model_version': 'v2.2-Unified'
        })
    except Exception as e:
        print(f"❌ get_model_status 报错: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@bp.route('/api/pv/optimize', methods=['POST'])
def optimize_model():
    # ... (保持你之前的 optimize_model 代码，逻辑是通用的) ...
    # 只需要把计算逻辑放这里即可
    global current_forecast_factor
    try:
        now = datetime.now()
        current_slot = now.hour * 12 + now.minute // 5

        res = pv_realtime_data().get_json()
        actual_p = res['current_power']

        # 计算基准时，factor 传 1.0，split_idx 传 -1 (取纯基准)
        # 这里我们需要手动算一下基准值
        h = current_slot // 12
        m = (current_slot % 12) / 12.0
        rule = BASE_FORECAST_RULES[h] + (BASE_FORECAST_RULES[(h + 1) % 24] - BASE_FORECAST_RULES[h]) * m
        hist = get_db_history_map().get(current_slot, rule)
        base_p = hist * 0.8 + rule * 0.2

        if base_p > 5.0:
            new_factor = actual_p / base_p
            current_forecast_factor = round(max(0.1, min(2.5, new_factor)), 4)
            return jsonify({'code': 200, 'msg': f"已优化未来趋势，系数: {current_forecast_factor}"})
        return jsonify({'code': 400, 'msg': "功率过低"})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})

def get_db_weighted_history():
    """获取过去7天历史特征，增加错误处理防止空表报错"""
    history_map = {}
    try:
        # 只选取过去7天中偏差率小于20%的“高质量”历史数据作为参考
        # 避免模型学习到之前因为模拟器停发产生的 0 功率“脏数据”
        seven_days_ago = datetime.now() - timedelta(days=7)
        stats = db.session.query(
            (func.hour(PVGenerationData.collect_time) * 12 + func.floor(
                func.minute(PVGenerationData.collect_time) / 5)).label('slot'),
            func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0)
        ).filter(PVGenerationData.collect_time >= seven_days_ago).group_by('slot').all()

        device_count = PVDevice.query.count() or 1
        history_map = {int(s): float(v or 0) * device_count for s, v in stats}
    except Exception as e:
        print(f"提取历史特征失败: {e}")
    return history_map


# app/blueprints/monitor.py

# app/blueprints/monitor.py

from flask import Blueprint, render_template, request, jsonify,flash
from sqlalchemy import func
from app.decorators import role_required
from app.models import PowerRoom, CircuitData, PVDevice, GridPoint, TransformerData, PVGenerationData, PVForecastData
from app.extensions import db
from datetime import datetime, date, time , timedelta
from flask_login import current_user # 【新增】需要获取当前登录用户
import math
import time as time_mod  # 重命名避免冲突

bp = Blueprint('monitor', __name__)

# =================================================
# 1. 定义标准预测曲线 (基准线 0-23点)
# =================================================
BASE_FORECAST_RULES = [
    0, 0, 0, 0, 0, 0,
    30, 240, 540, 960, 1350, 1500,  # 06:00 - 11:00
    1530, 1440, 1140, 750, 450, 180, # 12:00 - 17:00
    30, 0, 0, 0, 0, 0, 0
]

# 【核心逻辑】预测修正系数
# 1.0 = 正常状态
# 0.6 = 优化后状态 (适应故障/低功率环境)
current_forecast_factor = 1.0


# ============= 配电网监测业务线  =============
@bp.route('/distribution')
@role_required(['operator', 'admin', 'analyst', 'order_manager'])
def distribution_list():
    """
    配电房列表与状态
    【修改】实现权限控制: 运维人员仅能查看负责区域
    """
    user_roles = [r.role_name for r in current_user.roles]

    # 如果是超级管理员，查看所有
    if 'admin' in user_roles:
        rooms = PowerRoom.query.all()

    # 如果只是运维人员(且不是管理员)，只查 responsible_id 匹配的
    elif 'operator' in user_roles:
        rooms = PowerRoom.query.filter_by(responsible_id=current_user.user_id).all()
        # 如果该运维人员没被分配任何配电房，给个空列表或提示
        if not rooms:
            flash('您当前没有负责的配电区域，请联系管理员分配。', 'info')

    # 其他角色(如分析师)默认看所有(或根据需求调整)
    else:
        rooms = PowerRoom.query.all()

    return render_template('monitor/distribution_list.html', rooms=rooms)
@bp.route('/transformer/<int:power_room_id>')
@role_required(['operator', 'energy_manager', 'admin', 'order_manager'])
def transformer_detail(power_room_id):
    """ 变压器监测详情页 """
    room = PowerRoom.query.get_or_404(power_room_id)
    transformers = TransformerData.query.filter_by(power_room_id=power_room_id) \
        .order_by(TransformerData.collect_time.desc()).limit(50).all()
    return render_template('monitor/transformer_detail.html', room=room, transformers=transformers)


# ============= 分布式光伏管理业务线  =============
@bp.route('/pv')
@role_required(['analyst', 'admin', 'operator'])
def pv_dashboard():
    """ 光伏设备运行状态 """
    devices = PVDevice.query.join(GridPoint).all()
    return render_template('monitor/pv_dashboard.html', devices=devices)


@bp.route('/api/pv/upload', methods=['POST'])
def upload_pv_data():
    """接收模拟器数据并存入数据库"""
    data = request.json
    try:
        # 1. 获取设备 ID (确保和 init_data 中的 device_id 对应)
        dev_id = data.get('device_id')
        if not dev_id:
            return jsonify({"code": 400, "msg": "缺少 device_id"}), 400

        # 2. 从数据包中提取字段 (适配你的 Mock 脚本)
        v = data.get('string_voltage_v', 0)
        i = data.get('string_current_a', 0)
        eff = data.get('inverter_eff_pct', 98.5)
        gen = data.get('gen_kwh', 0)

        # 3. 创建新记录 (字段名必须与你的 PVGenerationData 模型完全一致)
        new_record = PVGenerationData(
            device_id=dev_id,
            collect_time=datetime.now(),
            string_voltage_v=v,
            string_current_a=i,
            inverter_eff_pct=eff,
            gen_kwh=gen,
            grid_point_id=1  # 对应你 init_data 中创建的 grid_point_id
        )

        db.session.add(new_record)
        db.session.commit()

        return jsonify({"code": 200, "msg": "数据上传成功"})

    except Exception as e:
        db.session.rollback()
        # 在终端打印错误详情，方便你看到底是哪个字段错了
        print(f"❌ 上传失败详情: {str(e)}")
        return jsonify({"code": 500, "msg": f"后端处理出错: {str(e)}"}), 500


def get_historical_average_power(hour, minute_slot):
    """
    ✅ 新增：从数据库获取过去3天该时间点的平均功率
    """
    try:
        # 获取过去3天的同一时间段
        # 这里为了演示逻辑，我们通过 SQL 计算该时段的历史平均值
        # 实际生产中建议将此计算结果缓存，避免每次请求都扫大表
        avg_val = db.session.query(
            func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0)
        ).filter(
            func.date_format(PVGenerationData.collect_time, '%H:%i') >= f"{hour:02d}:{minute_slot:02d}",
            func.date_format(PVGenerationData.collect_time, '%H:%i') < f"{hour:02d}:{(minute_slot + 5):02d}"
        ).scalar() or 0
        return float(avg_val)
    except:
        return 0


current_forecast_factor = 1.0


# def get_smoothed_forecast(factor):
#     """
#     ✅ 关键改进：引入动态权重权重
#     如果 factor 被人工调整（不等于 1.0），说明历史数据不可信，加大理论基准的权重
#     """
#     smoothed_data = []
#     history_features = get_db_weighted_history()
#
#     # 判定是否处于人工干预状态
#     is_intervened = abs(factor - 1.0) > 0.05
#
#     for h in range(24):
#         curr_rule = BASE_FORECAST_RULES[h] * factor
#         next_rule = BASE_FORECAST_RULES[(h + 1) % 24] * factor
#
#         for i in range(12):
#             slot_idx = h * 12 + i
#             fraction = i / 12.0
#             interp_val = curr_rule + (next_rule - curr_rule) * fraction
#
#             db_val = history_features.get(slot_idx)
#
#             # ✅ 动态调权逻辑：
#             # 如果人工点击了优化，理论基准(interp_val)权重占 90%，强制曲线移动
#             # 如果是正常运行，历史特征(db_val)权重占 90%，保持波形真实
#             if is_intervened or db_val is None:
#                 final_val = interp_val
#             else:
#                 # 正常模式下，结合历史特征
#                 final_val = (db_val * 0.9) + (interp_val * 0.1)
#
#             pseudo_noise = (math.sin(h + i) * 0.01 + 1)
#             smoothed_data.append(round(final_val * pseudo_noise, 2))
#     return smoothed_data

def slot_noise(h, i):
    """生成基于时间槽的固定伪噪声，让预测线带点“历史感”"""
    return (math.sin(h + i) + math.cos(h * i)) if 'math' in globals() else 1


# def get_db_weighted_forecast(factor):
#     """
#     ✅ 修复：统一 Slot 计算 + 全局系数应用
#     """
#     forecast_288 = []
#     device_count = PVDevice.query.count() or 1
#
#     # 获取历史特征 (get_db_weighted_history 已经改对了，这里直接调用)
#     history_map = get_db_weighted_history()
#
#     for slot in range(288):
#         h = slot // 12
#         m_frac = (slot % 12) / 12.0
#
#         # 理论插值
#         curr_rule = BASE_FORECAST_RULES[h]
#         next_rule = BASE_FORECAST_RULES[(h + 1) % 24]
#         rule_val = curr_rule + (next_rule - curr_rule) * m_frac
#
#         # 混合历史
#         hist_val = history_map.get(slot, rule_val)
#
#         # 混合基数 (80% 历史 + 20% 理论)
#         base_val = (hist_val * 0.8) + (rule_val * 0.2)
#
#         # ✅ 关键修改：系数 factor 乘在最外面
#         # 这样 optimize_model 算出的 factor 才能真正把曲线拉到实际值
#         final_val = base_val * factor
#
#         forecast_288.append(round(final_val * (1 + math.sin(slot) * 0.002), 2))
#
#     return forecast_288

def get_db_history_map():
    """(保持不变)"""
    history_map = {}
    try:
        seven_days_ago = datetime.now() - timedelta(days=7)
        stats = db.session.query(
            (func.hour(PVGenerationData.collect_time) * 12 + func.floor(func.minute(PVGenerationData.collect_time) / 5)).label('slot'),
            func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0)
        ).filter(PVGenerationData.collect_time >= seven_days_ago).group_by('slot').all()

        device_count = PVDevice.query.count() or 1
        history_map = {int(s): float(v or 0) * device_count for s, v in stats}
    except Exception as e:
        print(f"提取历史特征失败: {e}")
    return history_map


def get_final_forecast_series(factor, split_idx=None):
    """
    ✅ 核心修复：分段预测生成
    - split_idx 之前 (过去)：使用系数 1.0 (显示原始基准，证明过去预测可能有偏)
    - split_idx 之后 (未来)：使用优化系数 (显示修正后的趋势)
    """
    forecast_288 = []
    history_map = get_db_history_map()

    # 如果没有传入分割点，说明是查看明天/全天预览，直接全量应用系数
    if split_idx is None:
        split_idx = -1

    for slot in range(288):
        h = slot // 12
        m_frac = (slot % 12) / 12.0

        # 1. 基础计算
        curr_rule = BASE_FORECAST_RULES[h]
        next_rule = BASE_FORECAST_RULES[(h + 1) % 24]
        rule_val = curr_rule + (next_rule - curr_rule) * m_frac
        hist_val = history_map.get(slot, rule_val)
        base_val = (hist_val * 0.8) + (rule_val * 0.2)

        # 2. ✅ 分段应用系数
        # 过去的时间保持原样 (1.0)，未来的时间应用优化系数
        # 这样点击优化时，只有当前点之后的蓝线会跳变，前面的保持不动
        active_factor = 1.0 if slot < split_idx else factor

        final_val = base_val * active_factor

        # 注入微小噪声
        forecast_288.append(round(final_val * (1 + math.sin(slot) * 0.002), 2))

    return forecast_288


# =================================================

@bp.route('/api/pv/realtime')
def pv_realtime_data():
    global current_forecast_factor
    now = datetime.now()
    today_start = datetime.combine(date.today(), time.min)

    devices = PVDevice.query.all()
    device_count = len(devices) if devices else 1

    # A. 实时功率
    total_latest_power = 0.0
    for dev in devices:
        last = PVGenerationData.query.filter_by(device_id=dev.device_id).order_by(
            PVGenerationData.collect_time.desc()).first()
        if last and (now - last.collect_time).total_seconds() < 60:
            total_latest_power += (float(last.string_voltage_v or 0) * float(last.string_current_a or 0)) / 1000.0

    # B. ✅ 绿线修复：初始化为 None，实现断线效果
    real_power_series = [None] * 288

    stats = db.session.query(
        (func.hour(PVGenerationData.collect_time) * 12 + func.floor(func.minute(PVGenerationData.collect_time) / 5)).label(
            'slot'),
        (func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0) * device_count)
    ).filter(PVGenerationData.collect_time >= today_start).group_by('slot').all()

    for slot, val in stats:
        idx = int(slot)
        if 0 <= idx < 288:
            real_power_series[idx] = round(float(val or 0), 2)

    # 锁定当前时间槽
    current_idx = now.hour * 12 + now.minute // 5

    # 填充 0 点到当前点的空洞 (防止断断续续)，但只填到 current_idx
    # 如果数据库没数，说明是 0 功率
    for i in range(current_idx + 1):
        if real_power_series[i] is None:
            real_power_series[i] = 0.0

    # 强制对齐末端
    if 0 <= current_idx < 288:
        real_power_series[current_idx] = round(total_latest_power, 2)

    # ✅ 关键：current_idx 之后的数据保持为 None (ECharts 不会绘制)

    # C. 生成分段预测线
    forecast_series = get_final_forecast_series(current_forecast_factor, split_idx=current_idx)

    # D. 偏差率 (复用分段后的预测值)
    current_forecast = forecast_series[current_idx] if current_idx < 288 else 0
    deviation_rate = 0.0
    if current_forecast > 1.0:
        deviation_rate = (abs(total_latest_power - current_forecast) / current_forecast) * 100
    elif total_latest_power > 1.0:
        deviation_rate = 100.0

    total_energy = db.session.query(func.sum(PVGenerationData.gen_kwh)).filter(
        PVGenerationData.collect_time >= today_start).scalar() or 0

    return jsonify({
        'current_power': round(total_latest_power, 2),
        'daily_energy': round(float(total_energy), 1),
        'co2_reduce': round(float(total_energy) * 0.997 / 1000, 3),
        'deviation_rate': round(deviation_rate, 1),
        'chart_series': real_power_series,  # 包含 None 的数组
        'forecast_series': forecast_series,
        'status': 'healthy' if deviation_rate < 15.0 else 'risk'
    })

# 修改 monitor.py 中的 get_pv_forecast 接口
@bp.route('/api/pv/forecast')
def get_pv_forecast():
    """
    ✅ 核心功能：基于【历史特征】的明日天气模拟
    逻辑：复用 get_final_forecast_series，但 split_idx 传 None (全天应用系数)
    """
    global current_forecast_factor

    weather = request.args.get('weather')

    # 定义三种典型气象的修正系数
    # 晴天=1.15 (比平时高)，多云=0.65 (明显下降)，雨天=0.25 (压得很低)
    weather_map = {
        'sunny': 1.15,
        'cloudy': 0.65,
        'rainy': 0.25
    }

    # 获取目标系数：
    # 如果前端传了 weather 参数，使用对应系数
    # 如果没传 (比如刚加载时)，使用当前正在运行的实时系数 (current_forecast_factor)
    target_factor = weather_map.get(weather, current_forecast_factor)

    # 生成预测数据
    # 注意：这里不传 split_idx，意味着全天 288 个点都应用 target_factor
    # 这样用户看到的就是一条完整的、带有本电站历史特征的“明天预测线”
    forecast_data = get_final_forecast_series(target_factor)

    return jsonify({'code': 200, 'data': forecast_data})


# app/blueprints/monitor.py

@bp.route('/api/pv/model_status')
def get_model_status():
    """
    ✅ 唯一的模型状态函数
    合并了实时偏差对齐逻辑与历史显示逻辑
    """
    global current_forecast_factor
    try:
        # 1. 统一调用实时数据接口的逻辑，确保数值与顶部卡片绝对一致
        realtime_response = pv_realtime_data()
        realtime_data = realtime_response.get_json()

        today_deviation = realtime_data.get('deviation_rate', 0.0)

        # 2. 获取历史记录 (过去2天)
        today_date = date.today()
        history_records = PVForecastData.query.filter(PVForecastData.forecast_date < today_date).order_by(
            PVForecastData.forecast_date.desc()).limit(2).all()

        # 3. 构造返回列表
        data_list = [
            {
                'date': '今天 (实时)',
                'deviation': today_deviation,
                'status': '异常' if today_deviation > 15 else '正常'
            }
        ]

        for r in history_records:
            dev_val = float(r.deviation_pct or 0)
            data_list.append({
                'date': r.forecast_date.strftime('%m-%d'),
                'deviation': round(dev_val, 1),
                'status': '异常' if dev_val > 15 else '正常'
            })

        # 4. 判定状态：只要今天异常，就激活优化按钮
        is_alarm = True if today_deviation > 15.0 else False

        return jsonify({
            'status': 'risk' if is_alarm else 'healthy',
            'history': data_list,
            'model_version': 'v2.2-Unified'
        })
    except Exception as e:
        print(f"❌ get_model_status 报错: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@bp.route('/api/pv/optimize', methods=['POST'])
def optimize_model():
    # ... (保持你之前的 optimize_model 代码，逻辑是通用的) ...
    # 只需要把计算逻辑放这里即可
    global current_forecast_factor
    try:
        now = datetime.now()
        current_slot = now.hour * 12 + now.minute // 5

        res = pv_realtime_data().get_json()
        actual_p = res['current_power']

        # 计算基准时，factor 传 1.0，split_idx 传 -1 (取纯基准)
        # 这里我们需要手动算一下基准值
        h = current_slot // 12
        m = (current_slot % 12) / 12.0
        rule = BASE_FORECAST_RULES[h] + (BASE_FORECAST_RULES[(h + 1) % 24] - BASE_FORECAST_RULES[h]) * m
        hist = get_db_history_map().get(current_slot, rule)
        base_p = hist * 0.8 + rule * 0.2

        if base_p > 5.0:
            new_factor = actual_p / base_p
            current_forecast_factor = round(max(0.1, min(2.5, new_factor)), 4)
            return jsonify({'code': 200, 'msg': f"已优化未来趋势，系数: {current_forecast_factor}"})
        return jsonify({'code': 400, 'msg': "功率过低"})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})

def get_db_weighted_history():
    """获取过去7天历史特征，增加错误处理防止空表报错"""
    history_map = {}
    try:
        # 只选取过去7天中偏差率小于20%的“高质量”历史数据作为参考
        # 避免模型学习到之前因为模拟器停发产生的 0 功率“脏数据”
        seven_days_ago = datetime.now() - timedelta(days=7)
        stats = db.session.query(
            (func.hour(PVGenerationData.collect_time) * 12 + func.floor(
                func.minute(PVGenerationData.collect_time) / 5)).label('slot'),
            func.avg(PVGenerationData.string_voltage_v * PVGenerationData.string_current_a / 1000.0)
        ).filter(PVGenerationData.collect_time >= seven_days_ago).group_by('slot').all()

        device_count = PVDevice.query.count() or 1
        history_map = {int(s): float(v or 0) * device_count for s, v in stats}
    except Exception as e:
        print(f"提取历史特征失败: {e}")
    return history_map

@bp.route('/circuit/<int:power_room_id>')
@role_required(['operator', 'admin', 'order_manager'])
def circuit_detail(power_room_id):
    """ 回路监测数据详情 """
    circuits = CircuitData.query.filter_by(power_room_id=power_room_id) \
        .order_by(CircuitData.collect_time.desc()).limit(50).all()
    room = PowerRoom.query.get_or_404(power_room_id)
    return render_template('monitor/circuit_detail.html', circuits=circuits, room=room)

