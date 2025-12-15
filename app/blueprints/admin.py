# app/blueprints/admin.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.decorators import role_required
from app.models import User, Role
from app.extensions import db

bp = Blueprint('admin', __name__)


@bp.route('/users')
@role_required(['admin'])
def user_management():
    """ 用户权限管理 [cite: 93] """
    users = User.query.all()
    roles = Role.query.all()  # 供添加用户时选择
    return render_template('admin/user_list.html', users=users, roles=roles)


@bp.route('/users/add', methods=['POST'])
@role_required(['admin'])
def add_user():
    """ 新增用户并分配角色 """
    username = request.form.get('username')
    password = request.form.get('password')
    role_id = request.form.get('role_id')  # 获取选中的角色ID
    real_name = request.form.get('real_name')

    if User.query.filter_by(username=username).first():
        flash('用户名已存在', 'warning')
    else:
        # 1. 创建用户
        new_user = User(username=username, real_name=real_name)
        new_user.set_password(password)

        # 2. 关联角色
        if role_id:
            role = Role.query.get(role_id)
            if role:
                new_user.roles.append(role)

        db.session.add(new_user)
        db.session.commit()
        flash('用户创建成功', 'success')

    return redirect(url_for('admin.user_management'))