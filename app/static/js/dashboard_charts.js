// app/static/js/dashboard_charts.js

document.addEventListener("DOMContentLoaded", function() {
    // 仅在存在对应 DOM 元素时初始化图表
    var mainChartDom = document.getElementById('mainChart');
    var pieChartDom = document.getElementById('pieChart');

    if (mainChartDom) {
        initMainChart(mainChartDom);
    }
    if (pieChartDom) {
        initPieChart(pieChartDom);
    }
});

/**
 * 初始化主趋势图 (从后端 API 获取数据)
 */
function initMainChart(dom) {
    var myChart = echarts.init(dom);

    // 显示加载动画
    myChart.showLoading();

    // 调用后端接口
    fetch('/api/realtime_chart')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            myChart.hideLoading();

            // 配置项
            var option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'cross' }
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: false,
                    data: data.time, // 后端返回的时间数组
                    axisLine: { lineStyle: { color: '#999' } }
                },
                yAxis: {
                    type: 'value',
                    name: '功率 (kW)',
                    axisLine: { show: false },
                    axisTick: { show: false },
                    splitLine: { lineStyle: { type: 'dashed' } }
                },
                series: [
                    {
                        name: '实时负荷',
                        type: 'line',
                        smooth: true,
                        symbol: 'none',
                        sampling: 'lttb',
                        itemStyle: { color: '#3498db' },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(52, 152, 219, 0.5)' },
                                { offset: 1, color: 'rgba(52, 152, 219, 0.05)' }
                            ])
                        },
                        data: data.value // 后端返回的数值数组
                    }
                ]
            };
            myChart.setOption(option);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            myChart.hideLoading();
            // 可以显示一个错误提示
            dom.innerHTML = '<div class="text-center text-muted py-5">暂无数据或加载失败</div>';
        });

    // 响应式调整
    window.addEventListener('resize', function() {
        myChart.resize();
    });
}

/**
 * 初始化能耗构成饼图 (静态演示数据)
 * 实际项目中也可改为从后端获取
 */
function initPieChart(dom) {
    var myChart = echarts.init(dom);

    var option = {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            bottom: '0%',
            left: 'center'
        },
        series: [
            {
                name: '能耗分布',
                type: 'pie',
                radius: ['45%', '70%'], // 环形图
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 5,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: '18',
                        fontWeight: 'bold'
                    }
                },
                labelLine: { show: false },
                data: [
                    { value: 1048, name: '生产设备', itemStyle: { color: '#3498db' } },
                    { value: 735, name: '暖通空调', itemStyle: { color: '#1abc9c' } },
                    { value: 580, name: '照明系统', itemStyle: { color: '#f1c40f' } },
                    { value: 484, name: '其他用电', itemStyle: { color: '#95a5a6' } }
                ]
            }
        ]
    };

    myChart.setOption(option);

    window.addEventListener('resize', function() {
        myChart.resize();
    });
}