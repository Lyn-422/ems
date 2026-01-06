import json
import io
import time
import psutil  # 系统监控需要
from datetime import datetime, date
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from sqlalchemy import text
from app.decorators import role_required
from app.extensions import db
from app.models import (
    User, Role, Plant, GridPoint, PowerRoom, EquipmentLedger,
    TransformerData, CircuitData, Alarm, WorkOrder,
    PVDevice, EnergyMeter, ScreenConfig, SystemConfig
)

bp = Blueprint('admin', __name__)


# =======================================================
#  1. 用户权限管理
# =======================================================
@bp.route('/users')
@role_required(['admin'])
def user_management():
    """ 用户列表 """
    users = User.query.all()
    roles = Role.query.all()
    return render_template('admin/user_list.html', users=users, roles=roles)


@bp.route('/users/add', methods=['POST'])
@role_required(['admin'])
def add_user():
    """ 新增用户 """
    username = request.form.get('username')
    password = request.form.get('password')
    role_id = request.form.get('role_id')
    real_name = request.form.get('real_name')

    if User.query.filter_by(username=username).first():
        flash('用户名已存在', 'warning')
    else:
        new_user = User(username=username, real_name=real_name)
        new_user.set_password(password)
        if role_id:
            role = Role.query.get(role_id)
            if role:
                new_user.roles.append(role)
        db.session.add(new_user)
        db.session.commit()
        flash('用户创建成功', 'success')

    return redirect(url_for('admin.user_management'))


# =======================================================
#  2. 系统运行状态监控
# =======================================================
@bp.route('/system/monitor')
@role_required(['admin'])
def system_monitor():
    """ 监控数据库运行状态与服务器资源 """
    status = {}

    # 1. 数据库响应时间测试
    start_time = time.time()
    try:
        db.session.execute(text('SELECT 1'))
        duration = (time.time() - start_time) * 1000
        status['db_latency'] = f"{duration:.2f} ms"
        status['db_status'] = '正常'
    except Exception as e:
        status['db_latency'] = "超时"
        status['db_status'] = f"异常: {str(e)}"

    # 2. 服务器资源监控
    try:
        disk = psutil.disk_usage('/')
        status['disk_usage'] = f"{disk.percent}%"
        status['disk_free'] = f"{disk.free / (1024 ** 3):.2f} GB"

        mem = psutil.virtual_memory()
        status['mem_usage'] = f"{mem.percent}%"

        status['cpu_usage'] = f"{psutil.cpu_percent(interval=0.1)}%"
    except Exception as e:
        status['os_error'] = str(e)

    return render_template('admin/monitor.html', status=status)


# =======================================================
#  3. 告警规则与参数配置
# =======================================================
@bp.route('/system/config', methods=['GET', 'POST'])
@role_required(['admin'])
def config_management():
    """ 配置告警阈值与峰谷时段 """
    default_configs = [
        ('transformer_temp_high', '85', '变压器高温告警阈值 (℃)'),
        ('circuit_overload_amp', '400', '回路电流过载阈值 (A)'),
        ('peak_hours', '09:00-11:00,15:00-17:00', '峰段电价时间范围'),
        ('data_refresh_rate', '15', '采集终端数据刷新间隔 (秒)')
    ]

    if request.method == 'POST':
        for key, default_val, desc in default_configs:
            new_val = request.form.get(key)
            conf = SystemConfig.query.get(key)
            if conf:
                conf.config_value = new_val
            else:
                db.session.add(SystemConfig(config_key=key, config_value=new_val, description=desc))
        db.session.commit()
        flash('系统参数配置已更新', 'success')
        return redirect(url_for('admin.config_management'))

    configs = {}
    for key, default_val, desc in default_configs:
        conf = SystemConfig.query.get(key)
        if not conf:
            configs[key] = {'val': default_val, 'desc': desc}
        else:
            configs[key] = {'val': conf.config_value, 'desc': conf.description}

    return render_template('admin/config.html', configs=configs)


# =======================================================
#  4. 数据备份与恢复 (你报错缺失的部分)
# =======================================================
def model_to_dict(obj):
    """ 辅助函数：将数据库模型对象转为字典 """
    data = {}
    for column in obj.__table__.columns:
        val = getattr(obj, column.name)
        if isinstance(val, (datetime, date)):
            data[column.name] = val.isoformat()
        else:
            data[column.name] = val

    if isinstance(obj, User):
        data['role_names'] = [r.role_name for r in obj.roles]

    return data


@bp.route('/system/backup')
@role_required(['admin'])
def backup_page():
    """ 备份恢复页面 """
    return render_template('admin/backup.html')


@bp.route('/system/backup/download')
@role_required(['admin'])
def download_backup():
    """ 执行备份 """
    backup_data = {}
    models_to_backup = {
        'roles': Role,
        'users': User,
        'plants': Plant,
        'grid_points': GridPoint,
        'power_rooms': PowerRoom,
        'equipment_ledger': EquipmentLedger,
        'alarms': Alarm,
        'work_orders': WorkOrder,
        # 'system_config': SystemConfig # 也可以加上配置表
    }

    try:
        for key, model in models_to_backup.items():
            records = model.query.all()
            backup_data[key] = [model_to_dict(r) for r in records]

        json_str = json.dumps(backup_data, indent=4, ensure_ascii=False)
        mem_file = io.BytesIO()
        mem_file.write(json_str.encode('utf-8'))
        mem_file.seek(0)

        filename = f"ems_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return send_file(mem_file, as_attachment=True, download_name=filename, mimetype='application/json')
    except Exception as e:
        flash(f'备份失败: {str(e)}', 'danger')
        return redirect(url_for('admin.backup_page'))


@bp.route('/system/backup/restore', methods=['POST'])
@role_required(['admin'])
def restore_backup():
    """ 执行恢复 """
    file = request.files.get('backup_file')
    if not file:
        flash('请选择文件', 'warning')
        return redirect(url_for('admin.backup_page'))

    try:
        data = json.load(file)

        # 1. 清空旧数据 (先删子表)
        db.session.query(WorkOrder).delete()
        db.session.query(Alarm).delete()
        db.session.query(EquipmentLedger).delete()
        db.session.query(TransformerData).delete()
        db.session.query(CircuitData).delete()
        db.session.query(PowerRoom).delete()
        db.session.query(GridPoint).delete()
        db.session.query(Plant).delete()
        db.session.query(User).delete()
        db.session.query(Role).delete()
        db.session.flush()

        # 2. 插入新数据
        role_map = {}
        if 'roles' in data:
            for item in data['roles']:
                r = Role(**item)
                db.session.add(r)
        db.session.flush()

        all_roles = {r.role_name: r for r in Role.query.all()}

        if 'users' in data:
            for item in data['users']:
                role_names = item.pop('role_names', [])
                if item.get('created_at'):
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                u = User(**item)
                for r_name in role_names:
                    if r_name in all_roles:
                        u.roles.append(all_roles[r_name])
                db.session.add(u)
        db.session.flush()

        # 恢复其他基础表 (此处简化，逻辑同前)
        if 'plants' in data:
            for item in data['plants']: db.session.add(Plant(**item))
        db.session.flush()

        if 'grid_points' in data:
            for item in data['grid_points']: db.session.add(GridPoint(**item))
        db.session.flush()

        if 'power_rooms' in data:
            for item in data['power_rooms']:
                if item.get('start_time'): item['start_time'] = date.fromisoformat(item['start_time'])
                db.session.add(PowerRoom(**item))
        db.session.flush()

        if 'equipment_ledger' in data:
            for item in data['equipment_ledger']:
                if item.get('install_time'): item['install_time'] = date.fromisoformat(item['install_time'])
                if item.get('last_calibration_time'): item['last_calibration_time'] = date.fromisoformat(
                    item['last_calibration_time'])
                db.session.add(EquipmentLedger(**item))
        db.session.flush()

        if 'alarms' in data:
            for item in data['alarms']:
                if item.get('occur_time'): item['occur_time'] = datetime.fromisoformat(item['occur_time'])
                db.session.add(Alarm(**item))

        if 'work_orders' in data:
            for item in data['work_orders']:
                if item.get('dispatch_time'): item['dispatch_time'] = datetime.fromisoformat(item['dispatch_time'])
                if item.get('finish_time'): item['finish_time'] = datetime.fromisoformat(item['finish_time'])
                db.session.add(WorkOrder(**item))

        db.session.commit()
        flash('全量数据恢复成功！', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'恢复失败: {str(e)}', 'danger')

    return redirect(url_for('admin.backup_page'))