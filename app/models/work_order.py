# app/models/work_order.py
from app.extensions import db


class Alarm(db.Model):
    """ 告警表 [cite: 54] """
    __tablename__ = 'alarm'
    alarm_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    # 关联设备台账，实现统一的设备告警管理
    equipment_id = db.Column(db.BigInteger, db.ForeignKey('equipment_ledger.equipment_id'))

    occur_time = db.Column(db.DateTime, nullable=False)
    alarm_level = db.Column(db.String(10), comment='高/中/低')
    alarm_content = db.Column(db.String(255))
    handle_status = db.Column(db.String(20), default='未处理')
    trigger_thresh = db.Column(db.String(50))

    # 一对一关联工单
    work_order = db.relationship('WorkOrder', backref='alarm', uselist=False)


class WorkOrder(db.Model):
    """ 运维工单 [cite: 55] """
    __tablename__ = 'work_order'
    work_order_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    alarm_id = db.Column(db.BigInteger, db.ForeignKey('alarm.alarm_id'), nullable=False)

    # 关联运维人员 (User表)
    maintainer_id = db.Column(db.BigInteger, db.ForeignKey('sys_user.user_id'))

    dispatch_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)
    result_desc = db.Column(db.String(255))
    review_status = db.Column(db.String(20))
    attachment_path = db.Column(db.String(255))