# app/blueprints/maintenance.py
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.decorators import role_required
from app.models import Alarm, WorkOrder, User, EquipmentLedger
from app.services.alarm_service import AlarmService

bp = Blueprint('maintenance', __name__)


@bp.route('/alarms')
@role_required(['operator', 'order_manager', 'admin'])
def alarm_list():
    """
    告警监控中心
    展示: 发生时间、等级、设备名称、内容、状态
    """
    # 关联设备台账查询，以便显示设备名称而不是 ID
    alarms = Alarm.query.join(EquipmentLedger).order_by(Alarm.occur_time.desc()).all()

    # 获取所有运维人员供派单选择 (role_id 需根据实际 ID 查询，此处简化为查所有用户)
    # 实际应查: User.query.join(User.roles).filter(Role.role_name=='operator').all()
    maintainers = User.query.all()

    return render_template('maintenance/alarm_list.html', alarms=alarms, maintainers=maintainers)


@bp.route('/dispatch/<int:alarm_id>', methods=['POST'])
@role_required(['order_manager', 'admin'])
def dispatch(alarm_id):
    """
    派单操作 [cite: 63]
    """
    maintainer_id = request.form.get('maintainer_id')
    instruction = request.form.get('instruction')

    success, msg = AlarmService.dispatch_work_order(alarm_id, maintainer_id, instruction)

    if success:
        flash(f'工单派发成功 (工单ID: {msg})', 'success')
    else:
        flash(f'派单失败: {msg}', 'danger')

    return redirect(url_for('maintenance.alarm_list'))


@bp.route('/my_tasks')
@role_required(['operator'])
def my_tasks():
    """
    我的运维工单 [cite: 85]
    """
    tasks = WorkOrder.query.filter_by(maintainer_id=current_user.user_id).all()
    return render_template('maintenance/my_tasks.html', tasks=tasks)


@bp.route('/close_task/<int:work_order_id>', methods=['POST'])
@role_required(['operator'])
def close_task(work_order_id):
    """
    工单结案 [cite: 64]
    上传处理结果与现场照片
    """
    desc = request.form.get('result_desc')
    file = request.files.get('attachment')

    filename = None
    if file:
        filename = secure_filename(file.filename)
        # 确保目录存在
        upload_dir = os.path.join(current_app.root_path, 'static/images')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file.save(os.path.join(upload_dir, filename))

    success, msg = AlarmService.close_work_order(work_order_id, desc, filename)

    if success:
        flash('工单处理完成，已自动结案', 'success')
    else:
        flash(f'提交失败: {msg}', 'danger')

    return redirect(url_for('maintenance.my_tasks'))