# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# 初始化数据库插件
# 在这里创建实例，但在 app/__init__.py 中通过 db.init_app(app) 进行绑定
db = SQLAlchemy()

# 初始化登录管理插件 (用于处理用户 Session)
login_manager = LoginManager()

# 配置未登录时的跳转页面
# 当未登录用户尝试访问受保护页面时，会自动跳转到 'auth.login' (登录页)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'warning'