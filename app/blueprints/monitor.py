# app/blueprints/monitor.py
from flask import Blueprint, render_template
from app.decorators import role_required
from app.models import PowerRoom, CircuitData, PVDevice, GridPoint

bp = Blueprint('monitor', __name__)


# ============= 配电网监测业务线  =============
@bp.route('/distribution')
@role_required(['operator', 'admin', 'analyst'])
def distribution_list():
    """ 配电房列表与状态 """
    # 关联查询负责人信息
    rooms = PowerRoom.query.all()
    return render_template('monitor/distribution_list.html', rooms=rooms)


@bp.route('/circuit/<int:power_room_id>')
@role_required(['operator', 'admin'])
def circuit_detail(power_room_id):
    """
    回路监测数据详情
    展示: 电压、电流、有功功率、开关状态 [cite: 15]
    """
    # 获取该配电房最新的回路数据 (限制 50 条演示)
    circuits = CircuitData.query.filter_by(power_room_id=power_room_id) \
        .order_by(CircuitData.collect_time.desc()).limit(50).all()

    room = PowerRoom.query.get(power_room_id)
    return render_template('monitor/circuit_detail.html', circuits=circuits, room=room)


# ============= 分布式光伏管理业务线  =============
@bp.route('/pv')
@role_required(['analyst', 'admin', 'operator'])
def pv_dashboard():
    """
    光伏设备运行状态
    展示: 逆变器状态、装机容量、归属并网点 [cite: 29]
    """
    # 关联并网点查询
    devices = PVDevice.query.join(GridPoint).all()
    return render_template('monitor/pv_dashboard.html', devices=devices)