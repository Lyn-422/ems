# app/models/device.py
from app.extensions import db


# ---------------- 基础地理/组织架构 ----------------
class Plant(db.Model):
    """ 厂区信息 """
    __tablename__ = 'plant'
    plant_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    plant_code = db.Column(db.String(50), unique=True)
    plant_name = db.Column(db.String(100))
    location_desc = db.Column(db.String(200))

    # 关联: 厂区包含多个并网点、计量设备
    grid_points = db.relationship('GridPoint', backref='plant', lazy='dynamic')
    energy_meters = db.relationship('EnergyMeter', backref='plant', lazy='dynamic')


class GridPoint(db.Model):
    """ 并网点 (光伏相关) """
    __tablename__ = 'grid_point'
    grid_point_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    plant_id = db.Column(db.BigInteger, db.ForeignKey('plant.plant_id'), nullable=False)
    grid_code = db.Column(db.String(50), comment='并网点编号')
    location_desc = db.Column(db.String(200))

    pv_devices = db.relationship('PVDevice', backref='grid_point', lazy='dynamic')


# ---------------- 设备台账 (资产管理) ----------------
class EquipmentLedger(db.Model):
    """ 设备台账总表 (所有物理设备都在此注册，用于告警关联) """
    __tablename__ = 'equipment_ledger'
    equipment_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    equipment_code = db.Column(db.String(50), unique=True, comment='设备编号')
    equipment_name = db.Column(db.String(100))
    equipment_type = db.Column(db.String(50), comment='变压器/逆变器/水表等')
    model = db.Column(db.String(50))
    install_time = db.Column(db.Date)
    warranty_years = db.Column(db.Integer)
    scrap_status = db.Column(db.String(20))

    # 关联: 设备产生的告警
    alarms = db.relationship('Alarm', backref='equipment', lazy='dynamic')


# ---------------- 具体业务设备表 ----------------
class PowerRoom(db.Model):
    """ 配电房 [cite: 14] """
    __tablename__ = 'power_room'
    power_room_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    room_code = db.Column(db.String(50), unique=True)
    room_name = db.Column(db.String(100))
    location_desc = db.Column(db.String(200))
    voltage_level = db.Column(db.String(20), comment='35KV/0.4KV')
    transformer_cnt = db.Column(db.Integer)
    start_time = db.Column(db.Date)
    contact_phone = db.Column(db.String(20))

    responsible_id = db.Column(db.BigInteger, db.ForeignKey('sys_user.user_id'))

    circuits = db.relationship('CircuitData', backref='power_room', lazy='dynamic')
    transformers = db.relationship('TransformerData', backref='power_room', lazy='dynamic')


class PVDevice(db.Model):
    """ 光伏设备 (逆变器等) [cite: 29] """
    __tablename__ = 'pv_device'
    device_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    grid_point_id = db.Column(db.BigInteger, db.ForeignKey('grid_point.grid_point_id'))
    device_code = db.Column(db.String(50))
    device_type = db.Column(db.String(20))
    install_pos = db.Column(db.String(100))
    capacity_kwp = db.Column(db.Numeric(10, 2))
    start_time = db.Column(db.Date)
    run_status = db.Column(db.String(20))


class EnergyMeter(db.Model):
    """ 能耗计量设备 [cite: 40] """
    __tablename__ = 'energy_meter'
    meter_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    plant_id = db.Column(db.BigInteger, db.ForeignKey('plant.plant_id'))
    energy_type = db.Column(db.String(20), comment='水/蒸汽/气')
    install_pos = db.Column(db.String(100))
    run_status = db.Column(db.String(20))