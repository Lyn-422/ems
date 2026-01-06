# app/blueprints/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required
from app.models import User
from app.extensions import db
from datetime import datetime, timedelta  # 【新增】引入时间处理

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    系统登录
    安全策略: 密码加密校验 (SHA-256)
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user:
            # 【新增】检查账号是否处于锁定状态
            if user.locked_until:
                if datetime.now() < user.locked_until:
                    # 如果当前时间还没到解锁时间
                    wait_minutes = int((user.locked_until - datetime.now()).total_seconds() / 60) + 1
                    flash(f'账号因多次尝试失败已被锁定，请 {wait_minutes} 分钟后再试', 'danger')
                    return render_template('auth/login.html')
                else:
                    # 锁定时间已过，自动解锁，重置计数
                    user.locked_until = None
                    user.failed_login_count = 0
                    db.session.commit()

            # 校验密码
            if user.check_password(password):
                if user.status == 0:
                    flash('账号已被禁用，请联系管理员', 'danger')
                    return render_template('auth/login.html')

                # 【新增】登录成功：清空失败计数，重置锁定时间
                user.failed_login_count = 0
                user.locked_until = None
                db.session.commit()

                # 【新增】启用会话超时控制 (配合 Config.PERMANENT_SESSION_LIFETIME)
                session.permanent = True

                login_user(user)
                flash(f'欢迎回来，{user.real_name or user.username}', 'success')

                # 根据角色跳转不同首页 (简单策略: 管理员去后台，其他人去大屏)
                if 'admin' in [r.role_name for r in user.roles]:
                    return redirect(url_for('admin.user_management'))
                return redirect(url_for('dashboard.index'))

            else:
                # 【新增】密码错误处理：增加失败计数
                user.failed_login_count = (user.failed_login_count or 0) + 1

                # 检查是否达到 5 次
                if user.failed_login_count >= 5:
                    # 锁定账号 30 分钟 (时间可按需调整)
                    user.locked_until = datetime.now() + timedelta(minutes=30)
                    db.session.commit()
                    flash('密码连续错误 5 次，账号已被锁定 30 分钟！', 'danger')
                else:
                    db.session.commit()
                    remaining = 5 - user.failed_login_count
                    flash(f'用户名或密码错误，还剩 {remaining} 次机会', 'danger')
        else:
            # 用户不存在时，为了安全通常提示通用错误
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