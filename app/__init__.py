# app/__init__.py
from flask import Flask
from app.extensions import db, login_manager


def create_app():
    app = Flask(__name__)

    # 1. 加载配置
    app.config.from_object('config.Config')

    # 2. 初始化插件
    db.init_app(app)
    login_manager.init_app(app)

    # 3. 【修复点】显式导入 models，触发 user_loader 注册
    # 必须放在 db.init_app 之后，注册蓝图之前
    from app import models

    # 4. 注册蓝图
    from app.blueprints import auth, dashboard, monitor, energy, maintenance, admin

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(monitor.bp, url_prefix='/monitor')
    app.register_blueprint(energy.bp, url_prefix='/energy')
    app.register_blueprint(maintenance.bp, url_prefix='/maintenance')
    app.register_blueprint(admin.bp, url_prefix='/admin')

    return app