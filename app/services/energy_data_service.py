# app/services/energy_data_service.py
from app.extensions import db
from app.models import EnergyData,Plant


class EnergyDataService:
    """
    能耗监测数据服务
    - 负责数据质量判定
    - 标记待核实数据
    """

    FLUCTUATION_THRESHOLD = 0.20  # 20%

    @classmethod
    def save_energy_data(
        cls,
        meter_id,
        plant_id,
        collect_time,
        energy_value,
        unit
    ):
        """
        保存能耗数据，并自动判定数据质量
        """

        # 1️ 查询该设备最近一条“可信数据”（Good / Fair）
        last_record = (
            EnergyData.query
            .filter(
                EnergyData.meter_id == meter_id,
                EnergyData.data_quality.in_(['Good', 'Fair'])
            )
            .order_by(EnergyData.collect_time.desc())
            .first()
        )

        # 默认值
        need_verify = 0
        data_quality = 'Good'

        # 2 计算波动率
        if last_record and last_record.energy_value and last_record.energy_value > 0:
            last_value = float(last_record.energy_value)
            current_value = float(energy_value)

            fluctuation = abs(current_value - last_value) / last_value

            if fluctuation <= 0.10:
                data_quality = 'Good'
            elif fluctuation <= 0.20:
                data_quality = 'Fair'
            elif fluctuation <= 0.50:
                data_quality = 'Medium'
                need_verify = 1
            else:
                data_quality = 'Bad'
                need_verify = 1

        # 3️ 构建 EnergyData 对象
        data = EnergyData(
            meter_id=meter_id,
            plant_id=plant_id,
            collect_time=collect_time,
            energy_value=energy_value,
            unit=unit,
            data_quality=data_quality,
            need_verify=need_verify
        )

        db.session.add(data)
        db.session.commit()

        return data

    @classmethod
    def confirm_energy_data(cls, data_id):
        data = EnergyData.query.get_or_404(data_id)
        data.need_verify = 0
        db.session.commit()

    @classmethod
    def update_energy_data(cls, data_id, new_value):
        data = EnergyData.query.get_or_404(data_id)

        data.energy_value = new_value
        data.need_verify = 0
        data.data_quality = 'Good'  # 或重新算一次

        db.session.commit()
