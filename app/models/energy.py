# app/models/energy.py
from app.extensions import db


# ---------------- 配电监测数据 ----------------
class CircuitData(db.Model):
    """ 回路监测数据 [cite: 15] """
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
    switch_status = db.Column(db.String(10))
    is_abnormal = db.Column(db.SmallInteger, default=0)


class TransformerData(db.Model):
    """ 变压器监测数据 [cite: 16] """
    __tablename__ = 'transformer_data'
    transformer_data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    power_room_id = db.Column(db.BigInteger, db.ForeignKey('power_room.power_room_id'))
    transformer_code = db.Column(db.String(50))
    collect_time = db.Column(db.DateTime, index=True)

    load_rate_percent = db.Column(db.Numeric(5, 2))
    winding_temp_c = db.Column(db.Numeric(5, 1))
    run_status = db.Column(db.String(20))


# ---------------- 光伏数据 ----------------
class PVGenerationData(db.Model):
    """ 光伏发电数据 [cite: 30] """
    __tablename__ = 'pv_generation_data'
    gen_data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.BigInteger, db.ForeignKey('pv_device.device_id'))
    grid_point_id = db.Column(db.BigInteger, db.ForeignKey('grid_point.grid_point_id'))
    collect_time = db.Column(db.DateTime, index=True)

    gen_kwh = db.Column(db.Numeric(12, 2))
    on_grid_kwh = db.Column(db.Numeric(12, 2))
    inverter_eff_pct = db.Column(db.Numeric(5, 2))
    is_abnormal = db.Column(db.SmallInteger, default=0)


class PVForecastData(db.Model):
    """ 光伏预测数据 [cite: 31] """
    __tablename__ = 'pv_forecast_data'
    forecast_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    grid_point_id = db.Column(db.BigInteger, db.ForeignKey('grid_point.grid_point_id'))
    forecast_date = db.Column(db.Date)
    forecast_period = db.Column(db.String(20))
    forecast_kwh = db.Column(db.Numeric(12, 2))
    actual_kwh = db.Column(db.Numeric(12, 2))
    deviation_pct = db.Column(db.Numeric(5, 2))


# ---------------- 能耗与报表 ----------------
class EnergyData(db.Model):
    """ 能耗监测数据 [cite: 41] """
    __tablename__ = 'energy_data'
    energy_data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    meter_id = db.Column(db.BigInteger, db.ForeignKey('energy_meter.meter_id'))
    plant_id = db.Column(db.BigInteger, db.ForeignKey('plant.plant_id'))
    collect_time = db.Column(db.DateTime, index=True)

    energy_value = db.Column(db.Numeric(12, 2))
    unit = db.Column(db.String(10))
    data_quality = db.Column(db.String(10))


class PeakValleyEnergy(db.Model):
    """ 峰谷能耗统计 [cite: 42] """
    __tablename__ = 'peak_valley_energy'
    pv_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    plant_id = db.Column(db.BigInteger, db.ForeignKey('plant.plant_id'))
    stat_date = db.Column(db.Date)

    sharp_value = db.Column(db.Numeric(12, 2))
    peak_value = db.Column(db.Numeric(12, 2))
    flat_value = db.Column(db.Numeric(12, 2))
    valley_value = db.Column(db.Numeric(12, 2))
    total_cost = db.Column(db.Numeric(12, 2))


# ---------------- 大屏配置与汇总 ----------------
class ScreenConfig(db.Model):
    __tablename__ = 'screen_config'
    config_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    module_name = db.Column(db.String(50))
    display_fields = db.Column(db.String(255))


class HistoryTrend(db.Model):
    __tablename__ = 'history_trend'
    trend_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    config_id = db.Column(db.BigInteger, db.ForeignKey('screen_config.config_id'))
    energy_type = db.Column(db.String(20))
    stat_time = db.Column(db.Date)
    value = db.Column(db.Numeric(12, 2))


class RealtimeSummary(db.Model):
    __tablename__ = 'realtime_summary'
    summary_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    config_id = db.Column(db.BigInteger, db.ForeignKey('screen_config.config_id'))
    stat_time = db.Column(db.DateTime)
    total_power_kwh = db.Column(db.Numeric(12, 2))
    alarm_high_count = db.Column(db.Integer)