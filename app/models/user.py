# app/models/user.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.extensions import login_manager

# 多对多关联表: 用户-角色
sys_user_role = db.Table('sys_user_role',
                         db.Column('ur_id', db.BigInteger, primary_key=True, autoincrement=True),
                         db.Column('user_id', db.BigInteger, db.ForeignKey('sys_user.user_id', ondelete='CASCADE')),
                         db.Column('role_id', db.BigInteger, db.ForeignKey('sys_role.role_id', ondelete='CASCADE'))
                         )


class Role(db.Model):
    """
    角色表 (RBAC核心)
    """
    __tablename__ = 'sys_role'
    role_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False, comment='角色名称')
    description = db.Column(db.String(200), comment='角色描述')

    def __repr__(self):
        return f'<Role {self.role_name}>'


class User(UserMixin, db.Model):
    """
    用户表
    """
    __tablename__ = 'sys_user'

    user_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    password_hash = db.Column(db.String(255), nullable=False, comment='加密密码')
    real_name = db.Column(db.String(50), comment='真实姓名')
    phone = db.Column(db.String(20), comment='手机号')
    email = db.Column(db.String(100), comment='电子邮件')
    status = db.Column(db.SmallInteger, default=1, comment='状态 1:正常 0:禁用')
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # 关联关系: 多对多角色
    roles = db.relationship('Role', secondary=sys_user_role, backref=db.backref('users', lazy='dynamic'))

    # 关联关系: 负责的配电房 (一对多)
    power_rooms = db.relationship('PowerRoom', backref='manager', lazy='dynamic')

    # 关联关系: 处理的工单 (一对多)
    work_orders = db.relationship('WorkOrder', backref='maintainer', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 兼容性属性: 获取第一个角色名称 (用于旧代码逻辑)
    @property
    def role(self):
        return self.roles[0].role_name if self.roles else 'user'

    def get_id(self):
        return str(self.user_id)

    @login_manager.user_loader
    def load_user(user_id):
        """
        Flask-Login 需要此函数来根据 Session 中的 ID 获取用户对象
        """
        if user_id is None or user_id == 'None':
            return None
        return User.query.get(int(user_id))