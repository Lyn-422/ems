# app/blueprints/dashboard.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func
from app.models import CircuitData, PVGenerationData, Alarm
from app.extensions import db

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    """
    大屏首页: 实时汇总数据展示 [cite: 65, 68]
    业务数据: 总用电量、光伏发电量、告警统计
    """
    # 1. 实时总负荷 (模拟: 最新采集时间的总功率)
    # 实际场景可能需要查询 RealtimeSummary 表，这里演示实时聚合
    total_power = db.session.query(func.sum(CircuitData.active_power_kw)).scalar() or 0

    # 2. 当日光伏发电总量
    total_pv = db.session.query(func.sum(PVGenerationData.gen_kwh)).scalar() or 0

    # 3. 告警统计 (按等级)
    high_alarms = Alarm.query.filter_by(alarm_level='高', handle_status='未处理').count()
    total_alarms = Alarm.query.filter(Alarm.handle_status != '已结案').count()

    return render_template('dashboard/index.html',
                           power=round(total_power, 2),
                           pv=round(total_pv, 2),
                           alarms={'high': high_alarms, 'total': total_alarms})


@bp.route('/api/realtime_chart')
@login_required
def chart_data():
    """
    大屏图表接口: 历史趋势数据 [cite: 69]
    """
    # 示例: 返回最近 10 条配电总负荷数据
    # 实际应查询 HistoryTrend 表
    data = CircuitData.query.order_by(CircuitData.collect_time.desc()).limit(10).all()

    # 数据反转，按时间正序排列
    result = {
        'time': [d.collect_time.strftime('%H:%M') for d in reversed(data)],
        'value': [float(d.active_power_kw or 0) for d in reversed(data)]
    }
    return jsonify(result)