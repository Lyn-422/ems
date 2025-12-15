# app/blueprints/energy.py
from flask import Blueprint, render_template, request, flash
from app.decorators import role_required
from app.services.analysis_service import AnalysisService
from app.models import PeakValleyEnergy, Plant

bp = Blueprint('energy', __name__)


@bp.route('/report')
@role_required(['energy_manager', 'admin'])
def cost_report():
    """
    日能耗成本报表 (峰谷电价) [cite: 42, 50]
    业务活动: 查看尖峰平谷能耗及成本
    """
    date_str = request.args.get('date')
    plant_id = request.args.get('plant_id')

    reports = []
    plants = Plant.query.all()  # 供下拉框选择

    if date_str and plant_id:
        # 1. 尝试查询现有报表
        reports = PeakValleyEnergy.query.filter_by(
            stat_date=date_str,
            plant_id=plant_id
        ).all()

        # 2. 如果无数据，调用服务层实时计算 (演示用)
        if not reports:
            try:
                new_report = AnalysisService.calculate_plant_daily_cost(plant_id, date_str)
                reports = [new_report]
                flash('报表已实时生成', 'success')
            except Exception as e:
                flash(f'计算失败: {str(e)}', 'warning')

    return render_template('energy/report.html', reports=reports, plants=plants)