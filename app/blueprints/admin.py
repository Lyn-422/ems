# app/blueprints/admin.py
import json
import io
import time
import psutil  # 系统监控需要
from sqlalchemy import text
from decimal import Decimal
from datetime import datetime, date
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from app.decorators import role_required
from app.extensions import db

# 引入所有需要备份的模型
from app.models import (
    User, Role,
    Plant, GridPoint, PowerRoom, EquipmentLedger, PVDevice, EnergyMeter,
    Alarm, WorkOrder,
    ScreenConfig, RealtimeSummary, TransformerData, CircuitData, SystemConfig
)

bp = Blueprint('admin', __name__)


# =======================================================
#  数据备份与恢复功能 (逻辑备份)
# =======================================================

def model_to_dict(obj):
    """
    辅助函数：将数据库模型对象转为字典
    自动处理 datetime 和 Decimal 序列化，以及 User-Role 多对多关系
    """
    data = {}
    # 1. 导出普通字段
    for column in obj.__table__.columns:
        val = getattr(obj, column.name)

        # 2. 【关键修复】处理特殊类型
        if isinstance(val, (datetime, date)):
            # 日期 -> ISO 字符串
            data[column.name] = val.isoformat()
        elif isinstance(val, Decimal):
            # Decimal -> float (为了让 JSON 能识别数字)
            data[column.name] = float(val)
        else:
            data[column.name] = val

    # 3. 如果是用户对象，额外导出它的角色列表
    if isinstance(obj, User):
        data['role_names'] = [r.role_name for r in obj.roles]

    return data


@bp.route('/users')
@role_required(['admin'])
def user_management():
    """ 用户权限管理 """
    users = User.query.all()
    roles = Role.query.all()
    return render_template('admin/user_list.html', users=users, roles=roles)


@bp.route('/users/add', methods=['POST'])
@role_required(['admin'])
def add_user():
    """ 新增用户并分配角色 """
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


# ============================================================
# 【新增】修改用户角色逻辑 (配合前端弹窗使用)
# ============================================================
@bp.route('/users/edit_roles/<int:user_id>', methods=['POST'])
@role_required(['admin'])
def edit_user_roles(user_id):
    """
    修改现有用户的角色 (实现增删/重新分配)
    接收参数: role_ids (列表)
    """
    # 1. 获取用户，如果不存在则返回404
    user = User.query.get_or_404(user_id)

    # 2. 获取表单提交的角色ID列表 (支持多选)
    # 前端 checkbox 的 name 属性必须是 'role_ids'
    new_role_ids = request.form.getlist('role_ids')

    try:
        # 3. 【核心逻辑】清空该用户当前所有角色
        # SQLAlchemy 会自动处理 sys_user_role 中间表的删除
        user.roles = []

        # 4. 【核心逻辑】重新添加选中的角色
        # 这一步实现了"增" (添加新勾选的) 和 "删" (没勾选的自然就没了)
        for r_id in new_role_ids:
            role = Role.query.get(int(r_id))
            if role:
                user.roles.append(role)

        db.session.commit()
        flash(f'用户 {user.real_name or user.username} 的角色分配已更新', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'角色修改失败: {str(e)}', 'danger')

    # 5. 处理完成后，重定向回用户列表页 (不新开页面)
    return redirect(url_for('admin.user_management'))

@bp.route('/system/backup')
@role_required(['admin'])
def backup_page():
    return render_template('admin/backup.html')


@bp.route('/system/backup/download')
@role_required(['admin'])
def download_backup():
    """ 执行备份：生成 JSON 文件并下载 """
    backup_data = {}

    # 定义需要备份的模型列表
    models_to_backup = {
        'roles': Role,
        'users': User,
        'plants': Plant,
        'grid_points': GridPoint,
        'power_rooms': PowerRoom,
        'equipment_ledger': EquipmentLedger,
        'pv_devices': PVDevice,
        'energy_meters': EnergyMeter,
        'alarms': Alarm,
        'work_orders': WorkOrder,
        'screen_configs': ScreenConfig,
        'realtime_summary': RealtimeSummary
    }

    try:
        for key, model in models_to_backup.items():
            records = model.query.all()
            # 这里会自动调用修改后的 model_to_dict，不会再报错了
            backup_data[key] = [model_to_dict(r) for r in records]

        json_str = json.dumps(backup_data, indent=4, ensure_ascii=False)

        mem_file = io.BytesIO()
        mem_file.write(json_str.encode('utf-8'))
        mem_file.seek(0)

        filename = f"ems_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return send_file(
            mem_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    except Exception as e:
        flash(f'备份生成失败: {str(e)}', 'danger')
        # 打印错误方便调试
        print(f"Backup Error: {e}")
        return redirect(url_for('admin.backup_page'))


@bp.route('/system/backup/restore', methods=['POST'])
@role_required(['admin'])
def restore_backup():
    """ 执行恢复：读取 JSON 并覆盖数据库 """
    file = request.files.get('backup_file')
    if not file:
        flash('请选择上传的文件', 'warning')
        return redirect(url_for('admin.backup_page'))

    try:
        data = json.load(file)

        # 1. 清空旧数据 (遵循外键顺序)
        db.session.query(WorkOrder).delete()
        db.session.query(Alarm).delete()
        db.session.query(PVDevice).delete()
        db.session.query(EnergyMeter).delete()
        db.session.query(EquipmentLedger).delete()
        db.session.query(TransformerData).delete()
        db.session.query(CircuitData).delete()
        db.session.query(PowerRoom).delete()
        db.session.query(GridPoint).delete()
        db.session.query(Plant).delete()
        db.session.query(RealtimeSummary).delete()
        db.session.query(ScreenConfig).delete()
        db.session.query(User).delete()
        db.session.query(Role).delete()

        db.session.flush()

        # 2. 插入新数据

        # 2.1 角色
        if 'roles' in data:
            for item in data['roles']:
                db.session.add(Role(**item))
        db.session.flush()
        all_roles = {r.role_name: r for r in Role.query.all()}

        # 2.2 用户
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

        # 2.3 基础档案
        if 'plants' in data:
            for item in data['plants']:
                db.session.add(Plant(**item))
        if 'grid_points' in data:
            for item in data['grid_points']:
                db.session.add(GridPoint(**item))
        if 'power_rooms' in data:
            for item in data['power_rooms']:
                if item.get('start_time'):
                    item['start_time'] = date.fromisoformat(item['start_time'])
                db.session.add(PowerRoom(**item))
        db.session.flush()

        # 2.4 设备台账
        if 'equipment_ledger' in data:
            for item in data['equipment_ledger']:
                if item.get('install_time'):
                    item['install_time'] = date.fromisoformat(item['install_time'])
                if item.get('last_calibration_time'):
                    item['last_calibration_time'] = date.fromisoformat(item['last_calibration_time'])
                db.session.add(EquipmentLedger(**item))
        db.session.flush()

        # 2.5 业务设备
        if 'pv_devices' in data:
            for item in data['pv_devices']:
                if item.get('start_time'):
                    item['start_time'] = date.fromisoformat(item['start_time'])
                db.session.add(PVDevice(**item))
        if 'energy_meters' in data:
            for item in data['energy_meters']:
                db.session.add(EnergyMeter(**item))
        db.session.flush()

        # 2.6 告警与工单
        if 'alarms' in data:
            for item in data['alarms']:
                if item.get('occur_time'):
                    item['occur_time'] = datetime.fromisoformat(item['occur_time'])
                db.session.add(Alarm(**item))
        db.session.flush()

        if 'work_orders' in data:
            for item in data['work_orders']:
                if item.get('dispatch_time'):
                    item['dispatch_time'] = datetime.fromisoformat(item['dispatch_time'])
                if item.get('response_time'):
                    item['response_time'] = datetime.fromisoformat(item['response_time'])
                if item.get('finish_time'):
                    item['finish_time'] = datetime.fromisoformat(item['finish_time'])
                db.session.add(WorkOrder(**item))

        # 2.7 其它
        if 'screen_configs' in data:
            for item in data['screen_configs']:
                db.session.add(ScreenConfig(**item))
        if 'realtime_summary' in data:
            for item in data['realtime_summary']:
                if item.get('stat_time'):
                    item['stat_time'] = datetime.fromisoformat(item['stat_time'])
                db.session.add(RealtimeSummary(**item))

        db.session.commit()
        flash('全量数据恢复成功！', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"Restore Error: {e}")
        flash(f'恢复失败: {str(e)}', 'danger')

    return redirect(url_for('admin.backup_page'))

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
