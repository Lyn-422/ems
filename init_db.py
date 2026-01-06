# init_db.py
from app import create_app
from app.extensions import db
from app.models import User, Role, Plant, PowerRoom

app = create_app()

with app.app_context():
    # 1. 删除旧表并重置 (这是为了让新的 User 模型字段生效)
    db.drop_all()
    # print("已清理旧数据表...")

    # 2. 创建所有新表 (会自动包含 failed_login_count 和 locked_until 字段)
    db.create_all()
    print("数据库表结构创建成功！")

    # 3. 初始化角色 (RBAC 核心)
    roles = {
        'admin': '系统管理员',
        'operator': '运维人员',
        'energy_manager': '能源管理员',
        'analyst': '数据分析师',
        'order_manager': '工单管理员',
        'enterprise_admin': '企业管理员'  # 确保和 init_data 对应
    }

    db_roles = {}
    for code, desc in roles.items():
        role = Role.query.filter_by(role_name=code).first()
        if not role:
            role = Role(role_name=code, description=desc)
            db.session.add(role)
        db_roles[code] = role

    db.session.commit()
    print("系统角色初始化完成。")

    # 4. 创建默认管理员账号
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # 新字段 failed_login_count 默认为 0，locked_until 默认为 None，无需手动设置
        admin = User(username='admin', real_name='超级管理员')
        admin.set_password('123456')

        # 通过 append 添加角色对象
        admin.roles.append(db_roles['admin'])
        # 方便测试，给管理员赋予所有权限
        admin.roles.append(db_roles['operator'])
        admin.roles.append(db_roles['energy_manager'])

        db.session.add(admin)
        db.session.commit()
        print("管理员账号创建成功！(账号: admin / 密码: 123456)")
    else:
        print("管理员账号已存在。")