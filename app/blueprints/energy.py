from datetime import datetime

from flask import Blueprint, render_template, request, flash, redirect, url_for

from io import BytesIO
from flask import send_file
from app.decorators import role_required
from app.services.energy_data_service import EnergyDataService
from app.services.energy_service import AnalysisService
from app.models import PeakValleyEnergy, Plant, EnergyMeter, EnergyData

bp = Blueprint('energy', __name__)

@bp.route('/report')
@role_required(['energy_manager', 'admin'])
def cost_report():
    date_str = request.args.get('date')
    plant_id = request.args.get('plant_id')
    energy_type = request.args.get('energy_type', 'electric')

    plants = Plant.query.all()
    report = None

    # 👇 用户点了查询，但没选日期
    if request.args and not date_str:
        flash('请选择查询日期', 'warning')

    elif request.args and not plant_id:
        flash('请选择厂区', 'warning')

    elif date_str and plant_id:
        try:
            plant_id = int(plant_id)
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            report = AnalysisService.calculate_daily_energy_cost(
                plant_id=plant_id,
                energy_type=energy_type,
                stat_date=date_obj.date()
            )

            if report and report.total_value > 0:
                flash('报表已生成', 'success')
            else:
                flash('当前条件下暂无能耗数据', 'info')

        except Exception as e:
            flash(f'计算失败: {str(e)}', 'danger')

    return render_template(
        'energy/report.html',
        report=report,
        plants=plants
    )


# ===================== 待核实数据 =====================
@bp.route('/verify')
@role_required(['energy_manager', 'admin'])
def verify_energy_data():
    records = (
        EnergyData.query
        .filter(
            EnergyData.need_verify == 1,
            EnergyData.data_quality.in_(['Medium', 'Bad'])
        )
        .order_by(EnergyData.collect_time.desc())
        .all()
    )
    return render_template('energy/verify.html', records=records)


@bp.route('/verify/<int:data_id>/confirm', methods=['POST'])
@role_required(['energy_manager', 'admin'])
def confirm_data(data_id):
    EnergyDataService.confirm_energy_data(data_id)
    flash('数据已确认', 'success')
    return redirect(url_for('energy.verify_energy_data'))


@bp.route('/verify/<int:data_id>/edit', methods=['POST'])
@role_required(['energy_manager', 'admin'])
def edit_data(data_id):
    try:
        new_value = float(request.form.get('energy_value'))
        if new_value <= 0:
            raise ValueError
    except:
        flash('请输入合法的能耗值', 'warning')
        return redirect(url_for('energy.verify_energy_data'))

    EnergyDataService.update_energy_data(data_id, new_value)
    flash('数据已修正并确认', 'success')
    return redirect(url_for('energy.verify_energy_data'))

# ===================== 高能耗厂区 =====================
@bp.route('/high-energy')
@role_required(['energy_manager', 'admin'])
def high_energy_analysis():
    date_str = request.args.get('date')
    energy_type = request.args.get('energy_type', 'gas')

    avg_value = None
    high_plants = []

    if date_str:
        stat_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        avg_value, high_plants = AnalysisService.analyze_high_energy_plant(
            stat_date=stat_date,
            energy_type=energy_type
        )

    return render_template(
        'energy/high_energy.html',
        avg_value=avg_value,
        high_plants=high_plants
    )
# ===================== 月度报表即查即看 =====================
@bp.route('/period-report')
@role_required(['admin',  'analyst','energy_manager'])
def period_report():
    year = request.args.get('year', datetime.now().year, type=int)
    period_type = request.args.get('period_type', 'month') # month 或 quarter
    period_value = request.args.get('period_value', type=int)
    plant_id = request.args.get('plant_id', type=int)
    energy_type = request.args.get('energy_type', 'electric')

    plants = Plant.query.all()
    report = None

    if plant_id and period_value:
        report = AnalysisService.get_period_energy_report(
            plant_id=plant_id,
            energy_type=energy_type,
            year=year,
            period_value=period_value,
            period_type=period_type
        )
        if not report:
            flash(f'暂无该{ "月份" if period_type=="month" else "季度" }的统计数据', 'info')

    return render_template(
        'energy/period_report.html',
        report=report,
        plants=plants,
        year=year,
        period_type=period_type,
        period_value=period_value
    )


@bp.route('/analysis/comprehensive')
@role_required(['admin',  'analyst', 'enterprise_admin'])
def comprehensive_analysis():
    # 获取参数，默认显示 2026年 第1季度
    year = request.args.get('year', 2026, type=int)
    period_type = request.args.get('period_type', 'quarter')
    period_value = request.args.get('period_value', 1, type=int)

    # 获取多维聚合数据
    chart_data, table_results = AnalysisService.get_period_comprehensive_analysis(year, period_type, period_value)

    # 获取厂区列表（用于筛选下拉框）
    plants = Plant.query.all()

    return render_template('energy/comprehensive.html',
                           chart_data=chart_data,
                           results=table_results,
                           year=year,
                           period_type=period_type,
                           period_value=period_value,
                           plants=plants)


