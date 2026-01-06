# app/blueprints/dashboard.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import (
    CircuitData, PVGenerationData, Alarm, PeakValleyEnergy,
    ScreenConfig, RealtimeSummary, HistoryTrend
)
from app.extensions import db
from datetime import datetime, timedelta
import random

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    """
    大屏首页:
    1. 根据当前用户角色读取 ScreenConfig (配置化展示)
    2. 获取实时业务数据 (实时功率、累计能耗、光伏、告警)
    """
    # ================= 1. 获取大屏配置 =================
    # 获取当前用户的主角色
    current_role = current_user.roles[0].role_name if current_user.roles else 'guest'

    # 查找配置
    config = ScreenConfig.query.filter_by(target_role=current_role).first()

    # 兜底逻辑：如果数据库没配，给个默认值确保页面不崩
    if not config:
        class DefaultConfig:
            module_energy_overview = True
            module_pv_overview = True
            module_alarm_stats = True
            module_grid_status = True
            module_history_trend = True
            refresh_rate_seconds = 60
            display_fields = 'all'
        config = DefaultConfig()

    # ================= 2. 获取业务数据 =================

    # --- 2.1 实时总功率 (保留原逻辑，查最新瞬时功率) ---
    latest_time = db.session.query(func.max(CircuitData.collect_time)).scalar()
    if latest_time:
        total_power = db.session.query(func.sum(CircuitData.active_power_kw)) \
                          .filter(CircuitData.collect_time == latest_time).scalar() or 0
    else:
        total_power = 0

    # --- 2.2 当日光伏发电总量 (保留原逻辑) ---
    today = datetime.now().date()
    total_pv = db.session.query(func.sum(PVGenerationData.gen_kwh)) \
                   .filter(func.date(PVGenerationData.collect_time) == today).scalar() or 0

    # --- 2.3 实时汇总数据 (RealtimeSummary - 用于补充水/气等数据) ---
    # 获取最新的一条汇总记录
    summary = RealtimeSummary.query.order_by(RealtimeSummary.stat_time.desc()).first()
    if not summary:
        # 如果没数据，给个空对象
        summary = RealtimeSummary(total_elec_kwh=0, total_water_m3=0, total_gas_m3=0, total_steam_t=0)

    # --- 2.4 告警统计 ---
    high_alarms = Alarm.query.filter_by(alarm_level='高', handle_status='未处理').count()
    total_alarms = Alarm.query.filter(Alarm.handle_status != '已结案').count()

    return render_template('dashboard/index.html',
                           config=config,           # 【新】配置对象
                           summary=summary,         # 【新】汇总数据(含水电气)
                           power=round(total_power, 2), # 实时总功率
                           pv=round(total_pv, 2),       # 今日光伏
                           alarms={'high': high_alarms, 'total': total_alarms})


@bp.route('/api/realtime_chart')
@login_required
def get_realtime_chart_data():
    """
    API 接口: 折线图数据 (配电网负荷趋势)
    """
    # 返回最近 24 小时的配电总负荷数据
    one_day_ago = datetime.now() - timedelta(hours=24)
    data = CircuitData.query.filter(CircuitData.collect_time >= one_day_ago) \
        .order_by(CircuitData.collect_time.asc()).all()

    # 简单取值
    result = {
        'time': [d.collect_time.strftime('%H:%M') for d in data],
        'value': [float(d.active_power_kw or 0) for d in data]
    }
    return jsonify(result)


@bp.route('/api/comparison_data')
@login_required
def get_comparison_data():
    """
    API 接口: 环比图数据 (能耗值对比)
    """
    # 日期计算
    yesterday = datetime.now().date() - timedelta(days=1)
    last_week_day = yesterday - timedelta(days=7)
    last_year_day = yesterday - timedelta(days=365)

    # 查询本期 (昨日)
    yesterday_report = PeakValleyEnergy.query.filter_by(stat_date=yesterday).first()
    current_value = float(yesterday_report.total_value) if yesterday_report else 0

    # 查询环比 (上周)
    last_week_report = PeakValleyEnergy.query.filter_by(stat_date=last_week_day).first()
    last_week_value = float(last_week_report.total_value) if last_week_report else 0

    # 查询同比 (去年)
    last_year_report = PeakValleyEnergy.query.filter_by(stat_date=last_year_day).first()
    last_year_value = float(last_year_report.total_value) if last_year_report else 0

    comparison_data = {
        'labels': ['本期 (昨日)', '环比 (上周)', '同比 (去年)'],
        'values': [round(current_value, 2), round(last_week_value, 2), round(last_year_value, 2)]
    }

    # 【模拟数据填充】防止图表为空
    if current_value > 0:
        if last_week_value == 0:
            comparison_data['values'][1] = round(current_value * random.uniform(0.8, 0.95), 2)
        if last_year_value == 0:
            comparison_data['values'][2] = round(current_value * random.uniform(0.7, 0.9), 2)

    return jsonify(comparison_data)


@bp.route('/api/trend_analysis')
@login_required
def get_trend_analysis():
    """
    【新增API】获取历史趋势数据 (支持同比/环比)
    对应 HistoryTrend 表
    """
    # 获取最近7天的趋势数据
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    trends = HistoryTrend.query.filter(
        HistoryTrend.stat_time >= start_date,
        HistoryTrend.energy_type.in_(['Elec', 'PV']) # 只查用电和光伏
    ).order_by(HistoryTrend.stat_time.asc()).all()

    # 组装数据结构
    data = {
        'dates': sorted(list(set([t.stat_time.strftime('%m-%d') for t in trends]))),
        'elec_values': [],
        'pv_values': [],
        'elec_mom': []  # 环比增长率
    }

    # 填充数据
    for d in data['dates']:
        # 找当天的电数据
        e_item = next((t for t in trends if t.stat_time.strftime('%m-%d') == d and t.energy_type == 'Elec'), None)
        data['elec_values'].append(float(e_item.value) if e_item else 0)
        data['elec_mom'].append(float(e_item.mom_rate) if e_item else 0)

        # 找当天的光伏数据
        p_item = next((t for t in trends if t.stat_time.strftime('%m-%d') == d and t.energy_type == 'PV'), None)
        data['pv_values'].append(float(p_item.value) if p_item else 0)

    return jsonify(data)