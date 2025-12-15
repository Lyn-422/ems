# app/decorators.py
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(allowed_roles):
    """
    RBAC 权限控制装饰器 (升级版: 支持多对多角色)

    :param allowed_roles: 允许访问该路由的角色列表 (List[str])
                          例如: ['admin', 'operator']
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. 检查用户是否已登录
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            # 2. 获取当前用户拥有的所有角色名 (提取成列表)
            # 例如: user_roles = ['operator', 'admin', 'energy_manager']
            user_roles = [r.role_name for r in current_user.roles]

            # 3. 核心检查逻辑: 求交集
            # 只要用户的角色里，包含了 allowed_roles 中的任意一个，就放行
            # set(user_roles) & set(allowed_roles) 判断是否有交集
            is_authorized = False

            # 如果是超级管理员 'admin'，通常拥有所有权限 (直接放行)
            if 'admin' in user_roles:
                is_authorized = True
            else:
                # 检查是否有权限交集
                for role in allowed_roles:
                    if role in user_roles:
                        is_authorized = True
                        break

            if not is_authorized:
                # 权限不足处理
                flash('您没有权限执行此操作', 'danger')
                return abort(403)  # 返回 403 Forbidden

            # 4. 验证通过
            return f(*args, **kwargs)

        return decorated_function

    return decorator