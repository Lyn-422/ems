-- ========================================================
-- 数据库初始化脚本
-- 对应文档: 详细数据库关系图 (Image 1863d8)
-- ========================================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS energy_db DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE energy_db;

-- ==================== 权限与用户模块 ====================

-- 角色表
CREATE TABLE IF NOT EXISTS sys_role (
    role_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '角色ID',
    role_name VARCHAR(50) NOT NULL UNIQUE COMMENT '角色名称',
    description VARCHAR(200) COMMENT '角色描述'
) COMMENT='系统角色表';

-- 用户表
CREATE TABLE IF NOT EXISTS sys_user (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '加密密码',
    real_name VARCHAR(50) COMMENT '真实姓名',
    phone VARCHAR(20) COMMENT '手机号',
    email VARCHAR(100) COMMENT '电子邮件',
    status TINYINT DEFAULT 1 COMMENT '账号状态 1:正常 0:禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT='系统用户表';

-- 用户-角色关联表 (多对多)
CREATE TABLE IF NOT EXISTS sys_user_role (
    ur_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES sys_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE
) COMMENT='用户角色关联表';


-- ==================== 基础档案模块 ====================

-- 厂区表
CREATE TABLE IF NOT EXISTS plant (
    plant_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plant_code VARCHAR(50) UNIQUE COMMENT '厂区编号',
    plant_name VARCHAR(100) COMMENT '厂区名称',
    location_desc VARCHAR(200) COMMENT '位置描述'
) COMMENT='厂区信息表';

-- 设备台账总表
CREATE TABLE IF NOT EXISTS equipment_ledger (
    equipment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    equipment_code VARCHAR(50) UNIQUE COMMENT '设备编号',
    equipment_name VARCHAR(100) COMMENT '设备名称',
    equipment_type VARCHAR(50) COMMENT '设备类型',
    model VARCHAR(50) COMMENT '型号',
    install_time DATE COMMENT '安装时间',
    warranty_years INT COMMENT '质保年限',
    scrap_status VARCHAR(20) COMMENT '报废状态'
) COMMENT='设备台账表';


-- ==================== 配电网监测模块 ====================

-- 配电房表
CREATE TABLE IF NOT EXISTS power_room (
    power_room_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_code VARCHAR(50) UNIQUE COMMENT '配电房编号',
    room_name VARCHAR(100) COMMENT '配电房名称',
    location_desc VARCHAR(200) COMMENT '位置描述',
    voltage_level VARCHAR(20) COMMENT '电压等级',
    transformer_cnt INT COMMENT '变压器数量',
    start_time DATE COMMENT '投运时间',
    responsible_id BIGINT COMMENT '负责人ID',
    contact_phone VARCHAR(20) COMMENT '联系方式',
    FOREIGN KEY (responsible_id) REFERENCES sys_user(user_id)
) COMMENT='配电房信息表';

-- 变压器监测数据
CREATE TABLE IF NOT EXISTS transformer_data (
    transformer_data_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    power_room_id BIGINT NOT NULL,
    transformer_code VARCHAR(50) COMMENT '变压器编号',
    collect_time DATETIME NOT NULL COMMENT '采集时间',
    load_rate_percent DECIMAL(5, 2) COMMENT '负载率',
    winding_temp_c DECIMAL(5, 1) COMMENT '绕组温度',
    core_temp_c DECIMAL(5, 1) COMMENT '铁芯温度',
    env_temp_c DECIMAL(5, 1) COMMENT '环境温度',
    env_humidity DECIMAL(5, 2) COMMENT '环境湿度',
    run_status VARCHAR(20) COMMENT '运行状态',
    FOREIGN KEY (power_room_id) REFERENCES power_room(power_room_id)
) COMMENT='变压器监测数据表';

-- 回路监测数据
CREATE TABLE IF NOT EXISTS circuit_data (
    circuit_data_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    power_room_id BIGINT NOT NULL,
    circuit_code VARCHAR(50) COMMENT '回路编号',
    collect_time DATETIME NOT NULL COMMENT '采集时间',
    voltage_kv DECIMAL(10, 2) COMMENT '电压',
    current_a DECIMAL(10, 2) COMMENT '电流',
    active_power_kw DECIMAL(10, 2) COMMENT '有功功率',
    reactive_power_kvar DECIMAL(10, 2) COMMENT '无功功率',
    power_factor DECIMAL(4, 2) COMMENT '功率因数',
    forward_kwh DECIMAL(12, 2) COMMENT '正向有功电量',
    reverse_kwh DECIMAL(12, 2) COMMENT '反向有功电量',
    switch_status VARCHAR(10) COMMENT '开关状态',
    cable_temp_c DECIMAL(5, 1) COMMENT '电缆头温度',
    capacitor_temp_c DECIMAL(5, 1) COMMENT '电容器温度',
    is_abnormal TINYINT DEFAULT 0 COMMENT '是否异常',
    FOREIGN KEY (power_room_id) REFERENCES power_room(power_room_id)
) COMMENT='回路监测数据表';


-- ==================== 分布式光伏模块 ====================

-- 并网点
CREATE TABLE IF NOT EXISTS grid_point (
    grid_point_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plant_id BIGINT NOT NULL,
    grid_code VARCHAR(50) COMMENT '并网点编号',
    location_desc VARCHAR(200) COMMENT '并网点位置描述',
    FOREIGN KEY (plant_id) REFERENCES plant(plant_id)
) COMMENT='光伏并网点表';

-- 光伏设备表
CREATE TABLE IF NOT EXISTS pv_device (
    device_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    grid_point_id BIGINT NOT NULL,
    device_code VARCHAR(50) COMMENT '设备编号',
    device_type VARCHAR(20) COMMENT '设备类型',
    install_pos VARCHAR(100) COMMENT '安装位置',
    capacity_kwp DECIMAL(10, 2) COMMENT '装机容量',
    start_time DATE COMMENT '投运时间',
    calib_cycle_m INT COMMENT '校准周期(月)',
    run_status VARCHAR(20) COMMENT '运行状态',
    FOREIGN KEY (grid_point_id) REFERENCES grid_point(grid_point_id)
) COMMENT='光伏设备信息表';

-- 光伏发电数据
CREATE TABLE IF NOT EXISTS pv_generation_data (
    gen_data_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT NOT NULL,
    grid_point_id BIGINT,
    collect_time DATETIME NOT NULL,
    gen_kwh DECIMAL(12, 2) COMMENT '发电量',
    on_grid_kwh DECIMAL(12, 2) COMMENT '上网电量',
    self_use_kwh DECIMAL(12, 2) COMMENT '自用电量',
    inverter_eff_pct DECIMAL(5, 2) COMMENT '逆变器效率',
    string_voltage_v DECIMAL(10, 2) COMMENT '组串电压',
    string_current_a DECIMAL(10, 2) COMMENT '组串电流',
    is_abnormal TINYINT DEFAULT 0,
    FOREIGN KEY (device_id) REFERENCES pv_device(device_id),
    FOREIGN KEY (grid_point_id) REFERENCES grid_point(grid_point_id)
) COMMENT='光伏发电数据表';

-- 光伏预测数据
CREATE TABLE IF NOT EXISTS pv_forecast_data (
    forecast_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    grid_point_id BIGINT NOT NULL,
    forecast_date DATE NOT NULL,
    forecast_period VARCHAR(20) COMMENT '预测时段',
    forecast_kwh DECIMAL(12, 2) COMMENT '预测发电量',
    actual_kwh DECIMAL(12, 2) COMMENT '实际发电量',
    deviation_pct DECIMAL(5, 2) COMMENT '偏差率',
    model_version VARCHAR(20) COMMENT '预测模型版本',
    need_optimize TINYINT DEFAULT 0 COMMENT '是否需要优化',
    FOREIGN KEY (grid_point_id) REFERENCES grid_point(grid_point_id)
) COMMENT='光伏预测数据表';


-- ==================== 综合能耗模块 ====================

-- 能耗计量设备
CREATE TABLE IF NOT EXISTS energy_meter (
    meter_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plant_id BIGINT NOT NULL,
    energy_type VARCHAR(20) COMMENT '能源类型',
    install_pos VARCHAR(100) COMMENT '安装位置',
    pipe_spec VARCHAR(50) COMMENT '管道规格',
    protocol VARCHAR(20) COMMENT '通讯协议',
    run_status VARCHAR(20) COMMENT '运行状态',
    calib_cycle_m INT COMMENT '校准周期',
    manufacturer VARCHAR(100) COMMENT '生产厂家',
    FOREIGN KEY (plant_id) REFERENCES plant(plant_id)
) COMMENT='能耗计量设备表';

-- 能耗监测数据
CREATE TABLE IF NOT EXISTS energy_data (
    energy_data_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    meter_id BIGINT NOT NULL,
    plant_id BIGINT,
    collect_time DATETIME NOT NULL,
    energy_value DECIMAL(12, 2) COMMENT '能耗值',
    unit VARCHAR(10) COMMENT '单位',
    data_quality VARCHAR(10) COMMENT '数据质量',
    need_verify TINYINT DEFAULT 0 COMMENT '是否待核实',
    FOREIGN KEY (meter_id) REFERENCES energy_meter(meter_id),
    FOREIGN KEY (plant_id) REFERENCES plant(plant_id)
) COMMENT='能耗监测数据表';

-- 峰谷能耗数据
CREATE TABLE IF NOT EXISTS peak_valley_energy (
    pv_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plant_id BIGINT NOT NULL,
    energy_type VARCHAR(20) NOT NULL COMMENT '能源类型',
    stat_date DATE NOT NULL COMMENT '统计日期',
    sharp_value DECIMAL(12, 2) COMMENT '尖峰值',
    high_value DECIMAL(12, 2) COMMENT '高峰值',
    flat_value DECIMAL(12, 2) COMMENT '平段值',
    low_value DECIMAL(12, 2) COMMENT '低谷值',
    total_value DECIMAL(12, 2) COMMENT '总能耗',
    price_per_unit DECIMAL(10, 4) COMMENT '单位成本',
    total_cost DECIMAL(12, 2) COMMENT '总成本',
    FOREIGN KEY (plant_id) REFERENCES plant(plant_id)
) COMMENT='峰谷能耗统计表';


-- ==================== 告警与工单模块 ====================

-- 告警表
CREATE TABLE IF NOT EXISTS alarm (
    alarm_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    equipment_id BIGINT COMMENT '关联设备ID',
    occur_time DATETIME NOT NULL COMMENT '发生时间',
    alarm_level VARCHAR(10) COMMENT '告警级别',
    alarm_content VARCHAR(255) COMMENT '告警内容',
    handle_status VARCHAR(20) COMMENT '处理状态',
    trigger_thresh VARCHAR(50) COMMENT '触发阈值',
    FOREIGN KEY (equipment_id) REFERENCES equipment_ledger(equipment_id)
) COMMENT='系统告警表';

-- 运维工单表
CREATE TABLE IF NOT EXISTS work_order (
    work_order_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alarm_id BIGINT NOT NULL,
    maintainer_id BIGINT COMMENT '运维人员ID',
    dispatch_time DATETIME COMMENT '派单时间',
    response_time DATETIME COMMENT '响应时间',
    finish_time DATETIME COMMENT '完成时间',
    result_desc VARCHAR(255) COMMENT '处理结果',
    review_status VARCHAR(20) COMMENT '复查状态',
    attachment_path VARCHAR(255) COMMENT '附件路径',
    FOREIGN KEY (alarm_id) REFERENCES alarm(alarm_id),
    FOREIGN KEY (maintainer_id) REFERENCES sys_user(user_id)
) COMMENT='运维工单表';


-- ==================== 大屏配置模块 ====================

-- 大屏配置表
CREATE TABLE IF NOT EXISTS screen_config (
    config_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    module_name VARCHAR(50) COMMENT '模块名称',
    refresh_sec INT COMMENT '刷新间隔',
    display_fields VARCHAR(255) COMMENT '展示字段',
    order_rule VARCHAR(50) COMMENT '排序规则',
    perm_level VARCHAR(20) COMMENT '权限等级'
) COMMENT='大屏配置表';

-- 历史趋势数据
CREATE TABLE IF NOT EXISTS history_trend (
    trend_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    config_id BIGINT,
    energy_type VARCHAR(20) COMMENT '能源类型',
    stat_cycle VARCHAR(20) COMMENT '统计周期',
    stat_time DATE COMMENT '统计时间',
    value DECIMAL(12, 2) COMMENT '数值',
    yoy_pct DECIMAL(5, 2) COMMENT '同比增长率',
    mom_pct DECIMAL(5, 2) COMMENT '环比增长率',
    industry_avg DECIMAL(12, 2) COMMENT '行业均值',
    FOREIGN KEY (config_id) REFERENCES screen_config(config_id)
) COMMENT='历史趋势数据表';

-- 实时汇总数据
CREATE TABLE IF NOT EXISTS realtime_summary (
    summary_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    config_id BIGINT,
    stat_time DATETIME COMMENT '统计时间',
    total_power_kwh DECIMAL(12, 2) COMMENT '总用电量',
    total_water_m3 DECIMAL(12, 2) COMMENT '总用水量',
    total_steam_t DECIMAL(12, 2) COMMENT '总蒸汽',
    total_gas_m3 DECIMAL(12, 2) COMMENT '总天然气',
    pv_total_kwh DECIMAL(12, 2) COMMENT '光伏总发电',
    pv_self_use_kwh DECIMAL(12, 2) COMMENT '光伏自用',
    alarm_total_count INT COMMENT '总告警数',
    alarm_high_count INT COMMENT '高等告警数',
    alarm_mid_count INT COMMENT '中等告警数',
    alarm_low_count INT COMMENT '低等告警数',
    FOREIGN KEY (config_id) REFERENCES screen_config(config_id)
) COMMENT='实时汇总数据表';