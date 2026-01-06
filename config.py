# configs.py
import os


class Config:
    # ================= 数据库配置 =================
    # 格式: mysql+pymysql://用户名:密码@主机地址:端口/数据库名
    # 请务必修改 'root:123456' 为你本地 MySQL 的真实账号密码
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:lyn041106@localhost/energy_db'

    # 关闭 SQLAlchemy 的事件追踪系统，节省内存
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ================= 安全配置 =================
    # 用于加密 Session 数据 (登录状态)，在生产环境中应使用随机强密码
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-for-course-design-2025'

    # ================= 业务阈值配置 (源自任务书) =================
    # [cite_start]1. 配电网业务 [cite: 19]
    # 35KV回路电压超 37KV 时标记异常
    VOLTAGE_LIMIT_35KV = 37.0

    # [cite_start]2. 光伏业务 [cite: 33]
    # 逆变器效率低于 85% 时标记设备异常
    INVERTER_EFFICIENCY_MIN = 85.0

    # 光伏预测偏差率超 15% 时触发模型优化提醒
    PV_PREDICTION_DEVIATION_MAX = 15.0

    # [cite_start]3. 告警业务 [cite: 58]
    # 高等级告警需在 15 分钟内响应
    ALARM_RESPONSE_TIME_LIMIT = 15  # 单位：分钟

    # [cite_start]4. 安全登录策略 [cite: 130]
    # 登录失败 5 次后锁定账号
    LOGIN_MAX_FAILURES = 5