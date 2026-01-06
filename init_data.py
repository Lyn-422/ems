import random
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
# 【版本1特性】引入多配电房配置
from app.configs import ROOM_CONFIGS
from app.models import (
    User, Role, Plant, PowerRoom, GridPoint, EquipmentLedger,
    CircuitData, TransformerData,
    PVDevice, PVGenerationData, PVForecastData,
    EnergyMeter, EnergyData,
    PeakValleyEnergy,
    Alarm, WorkOrder,
    # 【版本2特性】引入大屏新表
    ScreenConfig, RealtimeSummary, HistoryTrend,
    # 【新增】系统配置表
    SystemConfig
)

app = create_app()


def init_mock_data():
    """
    全字段、全表模拟数据初始化 (完美融合版 + 系统配置)
    包含:
    1. 基础权限 (含企业管理员)
    2. 多配电房及设备 (基于 configs.py)
    3. 详细时序数据 (变压器+回路+光伏+水表)
    4. 大屏配置 (ScreenConfig)
    5. 实时汇总与历史趋势 (RealtimeSummary, HistoryTrend)
    6. 系统全局参数配置 (SystemConfig)
    """
    with app.app_context():
        print(">>> 正在清洗并初始化全量测试数据...")

        # ================= 1. 角色 (Role) =================
        roles = {
            'admin': '系统管理员',
            'operator': '运维人员',
            'energy_manager': '能源管理员',
            'analyst': '数据分析师',
            'order_manager': '工单管理员',
            'enterprise_admin': '企业管理员'  # 【版本2】新增
        }
        db_roles = {}
        for name, desc in roles.items():
            role = Role.query.filter_by(role_name=name).first()
            if not role:
                role = Role(role_name=name, description=desc)
                db.session.add(role)
            db_roles[name] = role
        db.session.commit()

        # ================= 2. 用户 (User) =================
        users_info = [
            ('operator1', '张运维', 'operator', '13800000001', 'zhang@ems.com'),
            ('manager1', '李能源', 'energy_manager', '13800000002', 'li@ems.com'),
            ('analyst1', '王分析', 'analyst', '13800000003', 'wang@ems.com'),
            ('order1', '孙工单', 'order_manager', '13800000004', 'sun@ems.com'),
            ('boss1', '赵总经理', 'enterprise_admin', '13800000005', 'boss@ems.com'),  # 【版本2】新增
            ('admin', '超级管理员', 'admin', '13800008888', 'admin@ems.com')
        ]

        db_users = {}
        for username, realname, role_key, phone, email in users_info:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    real_name=realname,
                    phone=phone,
                    email=email,
                    status=1
                )
                user.set_password('123456')
                user.roles.append(db_roles[role_key])
                if role_key == 'admin':
                    # 超管拥有所有权限
                    for r in ['order_manager', 'operator', 'energy_manager']:
                        user.roles.append(db_roles[r])
                db.session.add(user)
            db_users[username] = user
        db.session.commit()

        # ================= 3. 基础档案 (Plant, Grid) 批量生成 =================
        print(">>> 正在初始化多厂区、并网点及海量能耗数据...")

        # 厂区配置模板
        PLANTS_DATA = [
            {'code': 'PLANT_01', 'name': '第一生产基地', 'loc': '北区A栋'},
            {'code': 'PLANT_02', 'name': '第二生产基地', 'loc': '南区B栋'},
            {'code': 'PLANT_03', 'name': '第三生产基地', 'loc': '西区C栋'}
        ]

        METER_TEMPLATES = [
            {'type': 'electric', 'pos': '生产车间主回路', 'base': 150, 'peak': 1.8, 'unit': 'kWh'},
            {'type': 'electric', 'pos': '办公生活区', 'base': 40, 'peak': 2.2, 'unit': 'kWh'},
            {'type': 'water', 'pos': '工业用水总管', 'base': 20, 'peak': 1.3, 'unit': 'm3'},
            {'type': 'gas', 'pos': '动力站天然气', 'base': 60, 'peak': 1.5, 'unit': 'm3'},
            {'type': 'steam', 'pos': '锅炉房分汽柜', 'base': 35, 'peak': 1.2, 'unit': 't'}
        ]

        now = datetime.now()
        start_time = now - timedelta(hours=24)

        for p_info in PLANTS_DATA:
            # 1. 创建/获取厂区
            plant = Plant.query.filter_by(plant_code=p_info['code']).first()
            if not plant:
                plant = Plant(
                    plant_code=p_info['code'],
                    plant_name=p_info['name'],
                    location_desc=p_info['loc']
                )
                db.session.add(plant)
                db.session.flush()  # 关键：立即获取数据库生成的 plant_id 主键

            # 2. 为每个厂区创建并网点
            grid = GridPoint.query.filter_by(grid_code=f"GRID_{plant.plant_code}").first()
            if not grid:
                grid = GridPoint(
                    plant_id=plant.plant_id,  # 使用上面获取的主键
                    grid_code=f"GRID_{plant.plant_code}",
                    location_desc=f"{plant.plant_name}屋顶"
                )
                db.session.add(grid)

                # 3. 为每个厂区生成设备 (对应 energy_meter 表)
                for tpl in METER_TEMPLATES:
                    meter = EnergyMeter.query.filter_by(plant_id=plant.plant_id, install_pos=tpl['pos']).first()
                    if not meter:
                        meter = EnergyMeter(
                            plant_id=plant.plant_id,
                            energy_type=tpl['type'],
                            install_pos=tpl['pos'],
                            pipe_spec='DN50' if tpl['type'] != 'electric' else '400A',
                            protocol='Modbus-RTU',
                            run_status='正常',
                            calib_cycle_m=12,
                            manufacturer='Siemens'
                        )
                        db.session.add(meter)
                        db.session.flush()

                        # 4. 为设备生成 24 小时数据 (对应 energy_data 表)
                        curr_time = start_time
                        while curr_time <= now:
                            is_peak = 8 <= curr_time.hour <= 18

                            # --- 方案 A：针对不同厂区设置不同的能耗倍数 ---
                            base_val = tpl['base']

                            if p_info['code'] == 'PLANT_01':
                                multiplier = 4.5
                            elif p_info['code'] == 'PLANT_02':
                                multiplier = 3.8
                            else:
                                multiplier = 0.8

                            base_val = base_val * multiplier
                            # --------------------------------------------

                            # 计算最终值
                            val = (base_val * (tpl['peak'] if is_peak else 0.5)) + random.uniform(-5, 5)

                            # 模拟异常判定逻辑
                            need_verify = 0
                            data_quality = 'Good'
                            if random.random() < 0.05:  # 5% 概率模拟脏数据
                                val = val * random.uniform(2.5, 4.0)
                                need_verify = 1
                                data_quality = 'Bad'

                            # 插入明细表
                            db.session.add(EnergyData(
                                meter_id=meter.meter_id,
                                plant_id=plant.plant_id,
                                collect_time=curr_time,
                                energy_value=round(max(0, val), 2),
                                unit=tpl['unit'],
                                data_quality=data_quality,
                                need_verify=need_verify
                            ))
                            curr_time += timedelta(minutes=30)
        db.session.commit()
        print(">>> 多厂区及批量能耗设备初始化完成！")

        # ================= 4. 注册设备台账 (EquipmentLedger) =================
        print(">>> 正在注册配电房及设备台账...")
        room_objects = {}

        for conf in ROOM_CONFIGS:
            # 创建配电房
            r = PowerRoom.query.filter_by(room_code=conf['code']).first()
            if not r:
                r = PowerRoom(
                    room_code=conf['code'],
                    room_name=conf['name'],
                    voltage_level=conf['voltage'],
                    transformer_cnt=len(conf['transformers']),
                    start_time=datetime(2023, 1, 1).date(),
                    responsible_id=db_users['operator1'].user_id,
                    contact_phone='13800138000'
                )
                db.session.add(r)
                db.session.flush()
            room_objects[conf['code']] = r

            # 注册变压器
            for t_code, t_name, t_model in conf['transformers']:
                if not EquipmentLedger.query.filter_by(equipment_code=t_code).first():
                    eq = EquipmentLedger(
                        equipment_code=t_code, equipment_name=t_name, equipment_type='变压器',
                        model=t_model, specification='10kV/0.4kV',
                        install_time=datetime(2023, 1, 15).date(), warranty_years=5, scrap_status='正常',
                        last_calibration_time=datetime(2024, 1, 10).date(), last_calibration_person='张检测'
                    )
                    db.session.add(eq)

            # 注册回路
            for c_code, c_name, c_spec in conf['circuits']:
                if not EquipmentLedger.query.filter_by(equipment_code=c_code).first():
                    eq = EquipmentLedger(
                        equipment_code=c_code, equipment_name=c_name, equipment_type='配电回路',
                        model='GGD-01', specification=c_spec,
                        install_time=datetime(2023, 2, 1).date(), warranty_years=10, scrap_status='正常',
                        last_calibration_time=datetime(2024, 6, 1).date(), last_calibration_person='李测试'
                    )
                    db.session.add(eq)

        # 4.2 光伏与水表台账
        if not EquipmentLedger.query.filter_by(equipment_code='INV_001').first():
            db.session.add(EquipmentLedger(
                equipment_code='INV_001', equipment_name='1#逆变器', equipment_type='逆变器',
                model='HUAWEI-SUN2000', specification='50kW',
                install_time=datetime(2023, 6, 1).date(), warranty_years=10, scrap_status='正常',
                last_calibration_time=None, last_calibration_person=None
            ))

        if not EquipmentLedger.query.filter_by(equipment_code='METER_W_01').first():
            db.session.add(EquipmentLedger(
                equipment_code='METER_W_01', equipment_name='主进水管流量计', equipment_type='流量计',
                model='DN100', specification='DN100 PN16',
                install_time=datetime(2023, 3, 1).date(), warranty_years=3, scrap_status='正常',
                last_calibration_time=datetime(2024, 3, 1).date(), last_calibration_person='王计量'
            ))
        db.session.commit()

        # ================= 6. 业务设备实例 =================
        pv_dev = PVDevice.query.filter_by(device_code='PV_INV_01').first()
        if not pv_dev:
            pv_dev = PVDevice(
                grid_point_id=grid.grid_point_id, device_code='PV_INV_01', device_type='逆变器',
                install_pos='屋顶A区', capacity_kwp=50.0, start_time=datetime(2023, 6, 10).date(),
                run_status='正常', calib_cycle_m=12
            )
            db.session.add(pv_dev)

        meter_dev = EnergyMeter.query.filter_by(plant_id=plant.plant_id).first()
        if not meter_dev:
            meter_dev = EnergyMeter(
                plant_id=plant.plant_id, energy_type='water', install_pos='总进水管井',
                run_status='正常', pipe_spec='DN100', protocol='Modbus-RTU',
                calib_cycle_m=12, manufacturer='Siemens'
            )
            db.session.add(meter_dev)
        db.session.commit()

        # ================= 7. 时序数据生成 (24小时) =================
        print("正在生成24小时详细设备监测数据...")

        if CircuitData.query.count() < 50:
            now = datetime.now()
            start_time = now - timedelta(hours=24)
            curr = start_time

            cumulative_map = {}
            for conf in ROOM_CONFIGS:
                for c_code, _, _ in conf['circuits']:
                    cumulative_map[c_code] = 10000.0

            while curr <= now:
                is_peak = 8 <= curr.hour <= 18

                # --- A. 遍历所有配电房生成电力数据 ---
                for conf in ROOM_CONFIGS:
                    room_obj = room_objects[conf['code']]

                    # 1. 生成回路数据
                    for c_code, _, _ in conf['circuits']:
                        base_load = 200 if 'incoming' in c_code else 80
                        if is_peak: base_load *= 1.5

                        active_p = base_load + random.uniform(-10, 10)
                        pf = random.uniform(0.92, 0.98)
                        apparent_p = active_p / pf
                        voltage = 10.2 + random.uniform(-0.1, 0.1)
                        current = apparent_p / (voltage * 1.732)

                        cumulative_map[c_code] += active_p * 0.25

                        cd = CircuitData(
                            power_room_id=room_obj.power_room_id, circuit_code=c_code, collect_time=curr,
                            voltage_kv=round(voltage, 2), current_a=round(current, 2),
                            active_power_kw=round(active_p, 2),
                            reactive_power_kvar=round((apparent_p ** 2 - active_p ** 2) ** 0.5, 2),
                            power_factor=round(pf, 3), forward_kwh=round(cumulative_map[c_code], 2),
                            reverse_kwh=0, switch_status='合闸', is_abnormal=0,
                            cable_temp_c=round(30.0 + current / 20, 1), capacitor_temp_c=30.0
                        )
                        db.session.add(cd)

                    # 2. 生成变压器数据
                    for t_code, _, _ in conf['transformers']:
                        load_base = 50 + random.uniform(-10, 10)
                        temp = 40 + (load_base * 0.4) + random.uniform(-1, 1)

                        td = TransformerData(
                            power_room_id=room_obj.power_room_id, transformer_code=t_code, collect_time=curr,
                            load_rate_percent=round(load_base, 2), winding_temp_c=round(temp, 1),
                            core_temp_c=round(temp + 3, 1), env_temp_c=25.0, env_humidity=45.0, run_status='正常'
                        )
                        db.session.add(td)

                # --- B. 光伏 ---
                gen_p = 0
                if 6 <= curr.hour <= 18:
                    factor = 1 - abs(curr.hour - 12) / 6
                    gen_p = 45 * factor * random.uniform(0.8, 1.0)
                    if gen_p < 0: gen_p = 0

                pvd = PVGenerationData(
                    device_id=pv_dev.device_id, grid_point_id=grid.grid_point_id, collect_time=curr,
                    gen_kwh=round(gen_p * 0.25, 2), on_grid_kwh=round(gen_p * 0.25 * 0.9, 2),
                    inverter_eff_pct=98.50, is_abnormal=0, self_use_kwh=round(gen_p * 0.25 * 0.1, 2),
                    string_voltage_v=650.0 + random.uniform(-10, 10),
                    string_current_a=gen_p / 0.65 / 1000 if gen_p > 0 else 0
                )
                db.session.add(pvd)

                curr += timedelta(minutes=15)
            db.session.commit()

        # ================= 8. 预测/报表/告警 =================
        tomorrow = datetime.now().date() + timedelta(days=1)
        if not PVForecastData.query.filter_by(forecast_date=tomorrow).first():
            for h in range(6, 19):
                db.session.add(PVForecastData(
                    grid_point_id=grid.grid_point_id, forecast_date=tomorrow, forecast_period=f"{h:02d}:00",
                    forecast_kwh=round(10 + abs(h - 12) * 2, 2), model_version='v1.0'
                ))
            db.session.commit()

        # 9.2 历史告警 (Trans 001)
        trans_1 = EquipmentLedger.query.filter_by(equipment_code='TRANS_001').first()
        if trans_1 and not Alarm.query.filter_by(alarm_content='1#变压器油温过高').first():
            db.session.add(Alarm(
                equipment_id=trans_1.equipment_id, occur_time=datetime.now() - timedelta(hours=2),
                alarm_level='高', alarm_content='1#变压器油温过高', handle_status='未处理', trigger_thresh='>85℃'
            ))

        # 9.3 历史工单 (INV 001)
        inv_1 = EquipmentLedger.query.filter_by(equipment_code='INV_001').first()
        if inv_1 and not Alarm.query.filter_by(alarm_content='逆变器通讯中断').first():
            alarm_closed = Alarm(
                equipment_id=inv_1.equipment_id, occur_time=datetime.now() - timedelta(days=2),
                alarm_level='中', alarm_content='逆变器通讯中断', handle_status='已结案', trigger_thresh='Timeout'
            )
            db.session.add(alarm_closed)
            db.session.flush()
            if 'operator1' in db_users:
                db.session.add(WorkOrder(
                    alarm_id=alarm_closed.alarm_id, maintainer_id=db_users['operator1'].user_id,
                    dispatch_time=datetime.now() - timedelta(days=2, hours=1),
                    finish_time=datetime.now() - timedelta(days=2),
                    result_desc='重启通讯模块后恢复正常', review_status='已完成'
                ))

        db.session.commit()

        # ================= 10. 大屏配置 (ScreenConfig) =================
        configs = [
            {
                'role': 'admin', 'name': '全局监控视图',
                'modules': [True, True, True, True, True], 'refresh': 60, 'fields': 'all'
            },
            {
                'role': 'enterprise_admin', 'name': '企业经营看板',
                'modules': [True, True, False, True, True], 'refresh': 300, 'fields': 'total_cost,pv_income,yoy_rate'
            },
            {
                'role': 'operator', 'name': '运维实时大屏',
                'modules': [False, False, True, True, False], 'refresh': 10, 'fields': 'alarm_high,switch_status,temp'
            },
            {
                'role': 'energy_manager', 'name': '能源管理驾驶舱',
                'modules': [True, True, False, True, True], 'refresh': 60, 'fields': 'total_kwh,water_m3,gas_m3'
            }
        ]

        for cfg in configs:
            if not ScreenConfig.query.filter_by(target_role=cfg['role']).first():
                db.session.add(ScreenConfig(
                    config_name=cfg['name'], target_role=cfg['role'],
                    module_energy_overview=cfg['modules'][0], module_pv_overview=cfg['modules'][1],
                    module_grid_status=cfg['modules'][2], module_alarm_stats=cfg['modules'][3],
                    module_history_trend=cfg['modules'][4], refresh_rate_seconds=cfg['refresh'],
                    display_fields=cfg['fields']
                ))
        db.session.commit()

        # ================= 11. 实时汇总数据 (RealtimeSummary) =================
        print("正在生成大屏汇总数据...")
        now = datetime.now()
        start_time = now - timedelta(hours=1)
        curr = start_time
        cumulative_pv_today = 850.5

        while curr <= now:
            base_elec = 5000 + random.uniform(-200, 200)
            if 6 <= curr.hour <= 18:
                cumulative_pv_today += random.uniform(0.3, 0.8)

            rs = RealtimeSummary(
                stat_time=curr,
                total_elec_kwh=round(base_elec, 2),
                total_water_m3=round(200 + random.uniform(-10, 10), 2),
                total_steam_t=round(50 + random.uniform(-2, 2), 2),
                total_gas_m3=round(1000 + random.uniform(-50, 50), 2),
                pv_gen_kwh=round(cumulative_pv_today, 2),
                pv_self_use_kwh=round(cumulative_pv_today * 0.8, 2),
                alarm_total_count=random.randint(5, 15),
                alarm_high_count=random.randint(0, 2),
                alarm_mid_count=random.randint(1, 3),
                alarm_low_count=random.randint(3, 10)
            )
            db.session.add(rs)
            curr += timedelta(minutes=1)
        db.session.commit()

        # ================= 12. 历史趋势数据 (HistoryTrend) =================
        print("正在生成历史趋势分析数据...")
        trend_types = ['Elec', 'Water', 'Gas', 'PV']
        for day_offset in range(7):
            d = (now - timedelta(days=day_offset)).date()
            for etype in trend_types:
                yoy = random.uniform(-10, 20)
                mom = random.uniform(-5, 10)
                tag = 'up' if mom > 1.0 else ('down' if mom < -1.0 else 'flat')

                ht = HistoryTrend(
                    energy_type=etype, period_type='day', stat_time=d,
                    value=random.uniform(1000, 5000), yoy_rate=round(yoy, 2),
                    mom_rate=round(mom, 2), trend_tag=tag
                )
                db.session.add(ht)

        # 补一个企业级高危告警
        if trans_1:
            db.session.add(Alarm(
                equipment_id=trans_1.equipment_id, alarm_level='高',
                alarm_content='35KV配电房故障', handle_status='未处理', occur_time=datetime.now()
            ))

        db.session.commit()

        # ================= 13. 【新增】初始化系统配置 (SystemConfig) =================
        print("正在初始化系统全局配置参数...")
        default_configs = [
            ('transformer_temp_high', '85', '变压器高温告警阈值 (℃)'),
            ('circuit_overload_amp', '400', '回路电流过载阈值 (A)'),
            ('peak_hours', '09:00-11:00,15:00-17:00', '峰段电价时间范围'),
            ('data_refresh_rate', '15', '采集终端数据刷新间隔 (秒)')
        ]

        for key, val, desc in default_configs:
            if not SystemConfig.query.get(key):
                conf = SystemConfig(config_key=key, config_value=val, description=desc)
                db.session.add(conf)

        db.session.commit()

        print(">>> 融合版初始化完成！包含多配电房设备、时序数据、大屏配置及系统配置。")


if __name__ == '__main__':
    init_mock_data()