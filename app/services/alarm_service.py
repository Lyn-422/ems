# app/services/alarm_service.py
from datetime import datetime
from app.extensions import db
from app.models import Alarm, WorkOrder, EquipmentLedger


class AlarmService:
    """
    告警全生命周期管理：生成 -> 派单 -> 结案
    对应业务线: 告警运维管理
    """

    @staticmethod
    def create_alarm(equipment_id, content, level='低', alarm_type='越限告警'):
        """
        创建新告警 (通常由监测数据自动触发)
        """
        try:
            # 校验设备是否存在于台账中
            equipment = EquipmentLedger.query.get(equipment_id)
            if not equipment:
                return None, "关联设备不存在"

            alarm = Alarm(
                equipment_id=equipment_id,
                alarm_level=level,
                alarm_content=content,
                occur_time=datetime.now(),
                handle_status='未处理',
                trigger_thresh=alarm_type  # 复用字段存储类型或阈值描述
            )
            db.session.add(alarm)
            db.session.commit()
            return alarm, "创建成功"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def dispatch_work_order(alarm_id, maintainer_id, instruction=None):
        """
        派发运维工单 (事务操作)
        """
        try:
            alarm = Alarm.query.get(alarm_id)
            if not alarm:
                return False, "告警不存在"

            if alarm.handle_status != '未处理':
                return False, "告警已在处理中"

            # 创建工单
            work_order = WorkOrder(
                alarm_id=alarm_id,
                maintainer_id=maintainer_id,
                dispatch_time=datetime.now(),
                review_status='待处理',
                result_desc=instruction  # 派单时可填写指导意见
            )

            # 更新告警状态
            alarm.handle_status = '处理中'

            db.session.add(work_order)
            db.session.commit()
            return True, work_order.work_order_id
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def close_work_order(work_order_id, result_desc, attachment_path=None):
        """
        完成工单并结案
        """
        try:
            order = WorkOrder.query.get(work_order_id)
            if not order:
                return False, "工单不存在"

            # 1. 更新工单信息
            order.finish_time = datetime.now()
            order.result_desc = result_desc
            order.attachment_path = attachment_path
            order.review_status = '已完成'

            # 2. 级联更新告警状态
            if order.alarm:
                order.alarm.handle_status = '已结案'

            db.session.commit()
            return True, "结案成功"
        except Exception as e:
            db.session.rollback()
            return False, str(e)