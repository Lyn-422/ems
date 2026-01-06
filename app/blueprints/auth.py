# app/blueprints/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models import User

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    系统登录
    安全策略: 密码加密校验 (SHA-256) [cite: 130]
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.status == 0:
                flash('账号已被禁用，请联系管理员', 'danger')
                return render_template('auth/login.html')

            login_user(user)
            flash(f'欢迎回来，{user.real_name or user.username}', 'success')

            # 根据角色跳转不同首页 (简单策略: 管理员去后台，其他人去大屏)
            # 注意: user.role 是我们在 User model 中写的兼容属性
            if 'admin' in [r.role_name for r in user.roles]:
                return redirect(url_for('admin.user_management'))
            return redirect(url_for('dashboard.index'))

        flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已安全退出', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/test_base')
def test_base():
    # 直接渲染 base.html，不走继承逻辑
    return render_template('base.html')