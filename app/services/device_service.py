# app/services/device_service.py
from datetime import datetime, timedelta
from app.extensions import db
from app.models import EquipmentLedger, PVDevice, GridPoint, PowerRoom


class DeviceService:
    """
    设备全生命周期管理
    对应业务线: 设备台账与资产管理
    """

    @staticmethod
    def add_equipment_ledger(code, name, type_, model, install_date, warranty_years):
        """
        新增设备台账 (所有物理设备的父记录)
        """
        try:
            equipment = EquipmentLedger(
                equipment_code=code,
                equipment_name=name,
                equipment_type=type_,
                model=model,
                install_time=datetime.strptime(install_date, '%Y-%m-%d'),
                warranty_years=warranty_years,
                scrap_status='正常'
            )
            db.session.add(equipment)
            db.session.commit()
            return equipment
        except Exception as e:
            db.session.rollback()
            return None

    @staticmethod
    def get_devices_near_warranty(days_threshold=30):
        """
        查询即将过保的设备
        [cite_start]业务规则: 质保期到期前30天触发提醒 [cite: 60]
        """
        today = datetime.now().date()
        expiring_devices = []

        # 获取所有正常设备
        devices = EquipmentLedger.query.filter(
            EquipmentLedger.scrap_status != '已报废'
        ).all()

        for dev in devices:
            if dev.install_time and dev.warranty_years:
                # 计算到期日
                expire_date = dev.install_time.replace(year=dev.install_time.year + dev.warranty_years)
                # 计算剩余天数
                delta = (expire_date - today).days

                if 0 <= delta <= days_threshold:
                    expiring_devices.append({
                        'code': dev.equipment_code,
                        'name': dev.equipment_name,
                        'expire_date': expire_date,
                        'days_left': delta
                    })

        return expiring_devices

    @staticmethod
    def register_pv_device(grid_point_id, device_code, capacity):
        """
        注册光伏业务设备
        """
        device = PVDevice(
            grid_point_id=grid_point_id,
            device_code=device_code,
            device_type='逆变器',
            capacity_kwp=capacity,
            start_time=datetime.now(),
            run_status='正常'
        )
        db.session.add(device)
        db.session.commit()
        return device