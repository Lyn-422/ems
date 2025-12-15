1.项目结构解释
    SmartEnergySystem/
    ├── run.py                     # 项目启动入口
    ├── config.py                  # 配置文件 (数据库URL, 密钥, 告警阈值配置)
    ├── requirements.txt           # 依赖包列表
    ├── docs/                      # 文档存放 (对应 4.7 提交材料)
    │   ├── database_design.md     # 数据库设计文档
    │   ├── schema.sql             # DDL 建表语句 [cite: 116]
    │   └── test_data.sql          # 测试数据 [cite: 117]
    └── app/                       # 核心应用源码
        ├── __init__.py            # 工厂函数 (初始化APP, 注册蓝图)
        ├── extensions.py          # 扩展实例化 (SQLAlchemy, LoginManager)
        ├── decorators.py          # 权限控制装饰器 (实现 RBAC 机制 [cite: 130])
        │
        ├── models/                # 【持久层-实体定义】 (对应 3.1 概念/物理结构)
        │   ├── __init__.py
        │   ├── user.py            # 用户与角色表
        │   ├── device.py          # 配电房、光伏、计量设备表 [cite: 14, 29, 40]
        │   ├── energy.py          # 能耗监测与峰谷数据表 [cite: 41, 42]
        │   └── work_order.py      # 告警与工单表 [cite: 54, 55]
        │
        ├── services/              # 【持久层-业务逻辑封装】 (对应 3.3 持久层设计)
        │   # 将复杂的增删改查逻辑从路由中剥离，体现代码的高级封装
        │   ├── __init__.py
        │   ├── alarm_service.py   # 告警生成、状态更新、工单派发
        │   ├── analysis_service.py# 光伏预测优化、能耗报表计算 [cite: 37, 50]
        │   └── device_service.py  # 设备台账管理
        │
        ├── blueprints/            # 【控制层-路由】 (按业务线划分)
        │   ├── __init__.py
        │   ├── auth.py            # 登录/注销 (所有角色)
        │   ├── dashboard.py       # 大屏展示业务线 (企业管理层/所有角色) [cite: 65]
        │   ├── monitor.py         # 配电网 & 光伏业务线 (运维/数据分析师) [cite: 12, 27]
        │   ├── energy.py          # 综合能耗业务线 (能源管理员) [cite: 38]
        │   ├── maintenance.py     # 告警运维业务线 (运维人员/工单管理员) [cite: 52]
        │   └── admin.py           # 系统管理业务线 (系统管理员) 
        │
        ├── templates/             # 【视图层-页面】 (Jinja2 模板)
        │   ├── base.html          # 基础布局 (含动态侧边栏)
        │   ├── auth/              # 登录页
        │   ├── dashboard/         # 大屏可视化页面
        │   ├── monitor/           # 实时监测、光伏发电页面
        │   ├── energy/            # 能耗报表、成本分析页面
        │   ├── maintenance/       # 我的工单、设备台账、告警处理页面
        │   └── admin/             # 用户管理、日志监控页面
        │
        └── static/                # 静态资源
            ├── css/
            ├── js/                # ECharts 代码存放于此
            └── images/            # 故障现场照片上传目录 [cite: 55]

2.启动教程
    1）手动建立名为energy_db的数据库在本地
    2）修改根目录下config.py文件中的个人数据库密码
    3）运行init_db.py
    4）运行run.py
    