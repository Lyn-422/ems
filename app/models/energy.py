# app/models/energy.py
from app.extensions import db
from sqlalchemy.orm import relationship


# ---------------- 配电监测数据 ----------------
class CircuitData(db.Model):
    """ 回路监测数据 """
    __tablename__ = 'circuit_data'
    circuit_data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    power_room_id = db.Column(db.BigInteger, db.ForeignKey('power_room.power_room_id'))
    circuit_code = db.Column(db.String(50))
    collect_time = db.Column(db.DateTime, index=True)

    voltage_kv = db.Column(db.Numeric(10, 2))
    current_a = db.Column(db.Numeric(10, 2))
    active_power_kw = db.Column(db.Numeric(10, 2))
    reactive_power_kvar = db.Column(db.Numeric(10, 2))
    power_factor = db.Column(db.Numeric(4, 2))
    forward_kwh = db.Column(db.Numeric(12, 2))
    reverse_kwh = db.Column(db.Numeric(12, 2))
    switch_status = db.Column(db.String(10))
    cable_temp_c = db.Column(db.Numeric(5, 1))
    capacitor_temp_c = db.Column(db.Numeric(5, 1))
    is_abnormal = db.Column(db.SmallInteger, default=0)


class TransformerData(db.Model):
    """ 变压器监测数据 """
    __tablename__ = 'transformer_data'
    transformer_data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    power_room_id = db.Column(db.BigInteger, db.ForeignKey('power_room.power_room_id'))
    transformer_code = db.Column(db.String(50))
    collect_time = db.Column(db.DateTime, index=True)

    load_rate_percent = db.Column(db.Numeric(5, 2))
    winding_temp_c = db.Column(db.Numeric(5, 1))
    core_temp_c = db.Column(db.Numeric(5, 1))
    env_temp_c = db.Column(db.Numeric(5, 1))
    env_humidity = db.Column(db.Numeric(5, 2))
    run_status = db.Column(db.String(20))


# ---------------- 光伏数据 ----------------
class PVGenerationData(db.Model):
    """ 光伏发电数据 """
    __tablename__ = 'pv_generation_data'
    gen_data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.BigInteger, db.ForeignKey('pv_device.device_id'))
    grid_point_id = db.Column(db.BigInteger, db.ForeignKey('grid_point.grid_point_id'))
    collect_time = db.Column(db.DateTime, index=True)

    gen_kwh = db.Column(db.Numeric(12, 2))
    on_grid_kwh = db.Column(db.Numeric(12, 2))
    self_use_kwh = db.Column(db.Numeric(12, 2))
    inverter_eff_pct = db.Column(db.Numeric(5, 2))
    string_voltage_v = db.Column(db.Numeric(10, 2))
    string_current_a = db.Column(db.Numeric(10, 2))
    is_abnormal = db.Column(db.SmallInteger, default=0)


class PVForecastData(db.Model):
    """ 光伏预测数据 """
    __tablename__ = 'pv_forecast_data'
    forecast_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    grid_point_id = db.Column(db.BigInteger, db.ForeignKey('grid_point.grid_point_id'))
    forecast_date = db.Column(db.Date)
    forecast_period = db.Column(db.String(20))
    forecast_kwh = db.Column(db.Numeric(12, 2))
    actual_kwh = db.Column(db.Numeric(12, 2))
    deviation_pct = db.Column(db.Numeric(5, 2))
    model_version = db.Column(db.String(20))
    need_optimize = db.Column(db.SmallInteger, default=0)


# ---------------- 能耗与报表 ----------------
class EnergyData(db.Model):
    """ 能耗监测数据 """
    __tablename__ = 'energy_data'
    energy_data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    meter_id = db.Column(db.BigInteger, db.ForeignKey('energy_meter.meter_id'))
    plant_id = db.Column(db.BigInteger, db.ForeignKey('plant.plant_id'))
    collect_time = db.Column(db.DateTime, index=True)

    energy_value = db.Column(db.Numeric(12, 2))
    unit = db.Column(db.String(10))
    data_quality = db.Column(db.String(10))
    need_verify = db.Column(db.SmallInteger, default=0)

    meter = relationship('EnergyMeter', backref='energy_data')

class PeakValleyEnergy(db.Model):
    """ 峰谷能耗统计 """
    __tablename__ = 'peak_valley_energy'
    pv_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    energy_type = db.Column(db.String(20))  # 能源类型（水/蒸汽/天然气/电力等）
    plant_id = db.Column(db.BigInteger, db.ForeignKey('plant.plant_id'))
    stat_date = db.Column(db.Date)

    sharp_value = db.Column(db.Numeric(12, 2))
    peak_value = db.Column(db.Numeric(12, 2))
    flat_value = db.Column(db.Numeric(12, 2))
    valley_value = db.Column(db.Numeric(12, 2))
    total_value = db.Column(db.Numeric(12, 2))
    total_cost = db.Column(db.Numeric(12, 2))
    price_per_unit = db.Column(db.Numeric(10, 4))


# ---------------- 大屏配置与汇总 ----------------
class ScreenConfig(db.Model):
    """
    大屏展示配置表
    控制大屏的千人千面显示逻辑
    """
    __tablename__ = 'screen_config'
    config_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='配置编号')
    config_name = db.Column(db.String(50), comment='配置名称')

    # 1. 权限等级 (关联角色)
    # 通过这个字段判断该配置属于: admin(管理员) / energy_manager(能源管理员) / operator(运维人员)
    target_role = db.Column(db.String(50), unique=True, nullable=False, comment='权限等级/适用角色')

    # 2. 展示模块控制 (1=显示, 0=隐藏)
    module_energy_overview = db.Column(db.Boolean, default=True, comment='展示模块:能源总览')
    module_pv_overview = db.Column(db.Boolean, default=True, comment='展示模块:光伏总览')
    module_grid_status = db.Column(db.Boolean, default=True, comment='展示模块:配电网运行状态')
    module_alarm_stats = db.Column(db.Boolean, default=True, comment='展示模块:告警统计')
    module_history_trend = db.Column(db.Boolean, default=False, comment='展示模块:历史趋势')

    # 3. 数据刷新与展示细节
    refresh_rate_seconds = db.Column(db.Integer, default=60, comment='数据刷新频率(秒)')

    # 展示字段 (使用字符串存储，用逗号分隔，例如: "total_kwh,pv_kwh,high_alarm")
    display_fields = db.Column(db.String(255), default='all', comment='展示字段列表')

    # 排序规则 (time_desc:按时间降序 / energy_desc:按能耗降序)
    sort_rule = db.Column(db.String(20), default='time_desc', comment='排序规则')


class HistoryTrend(db.Model):
    """
    历史趋势数据表
    用于支持多周期查询、同比/环比分析
    """
    __tablename__ = 'history_trend'
    trend_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='趋势编号')
    # 虽然这里没有强制外键关联 ScreenConfig，但在业务逻辑中可用于特定配置下的展示数据缓存
    # config_id = db.Column(db.BigInteger, db.ForeignKey('screen_config.config_id'), nullable=True)

    # 1. 维度定义
    energy_type = db.Column(db.String(20), comment='能源类型: Elec/Water/Steam/Gas/PV')
    period_type = db.Column(db.String(20), comment='统计周期: day/week/month')
    stat_time = db.Column(db.DateTime, index=True, comment='统计时间')

    # 2. 核心数值
    value = db.Column(db.Numeric(14, 2), comment='能耗/发电量数值')

    # 3. 分析指标 (后端计算好存入)
    yoy_rate = db.Column(db.Numeric(8, 2), comment='同比增长率(%) - 较去年同期')
    mom_rate = db.Column(db.Numeric(8, 2), comment='环比增长率(%) - 较上个周期')

    # 辅助标记: 方便前端直接判断上升还是下降 (up/down/flat)
    trend_tag = db.Column(db.String(20), comment='趋势标记')


class RealtimeSummary(db.Model):
    """
    实时汇总数据表
    用于大屏顶部的数字看板，通常由定时任务每分钟生成一条最新记录
    """
    __tablename__ = 'realtime_summary'
    summary_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='汇总编号')
    # config_id = db.Column(db.BigInteger, db.ForeignKey('screen_config.config_id'), nullable=True)

    stat_time = db.Column(db.DateTime, index=True, comment='统计时间')

    # 1. 多能源消耗
    total_elec_kwh = db.Column(db.Numeric(12, 2), default=0, comment='总用电量(kWh)')
    total_water_m3 = db.Column(db.Numeric(12, 2), default=0, comment='总用水量(m³)')
    total_steam_t = db.Column(db.Numeric(12, 2), default=0, comment='总蒸汽消耗量(t)')
    total_gas_m3 = db.Column(db.Numeric(12, 2), default=0, comment='总天然气消耗量(m³)')

    # 2. 光伏数据
    pv_gen_kwh = db.Column(db.Numeric(12, 2), default=0, comment='光伏总发电量(kWh)')
    pv_self_use_kwh = db.Column(db.Numeric(12, 2), default=0, comment='光伏自用电量(kWh)')

    # 3. 告警统计
    alarm_total_count = db.Column(db.Integer, default=0, comment='总告警次数')
    alarm_high_count = db.Column(db.Integer, default=0, comment='高等级告警数')
    alarm_mid_count = db.Column(db.Integer, default=0, comment='中等级告警数')
    alarm_low_count = db.Column(db.Integer, default=0, comment='低等级告警数')


class SystemConfig(db.Model):
    """
    系统全局参数配置表
    存储如: 变压器高温阈值、峰谷电价时段、数据保留天数等
    """
    __tablename__ = 'system_config'
    config_key = db.Column(db.String(50), primary_key=True, comment='配置键 (如 transformer_temp_limit)')
    config_value = db.Column(db.String(255), nullable=False, comment='配置值')
    description = db.Column(db.String(200), comment='参数说明')
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())