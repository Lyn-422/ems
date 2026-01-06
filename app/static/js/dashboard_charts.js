// app/static/js/dashboard_charts.js

document.addEventListener("DOMContentLoaded", function() {
    // 仅在存在对应 DOM 元素时初始化图表
    var mainChartDom = document.getElementById('mainChart');
    var pieChartDom = document.getElementById('pieChart');
    var comparisonChartDom = document.getElementById('comparisonChart'); // 【新增】获取环比图DOM

    if (mainChartDom) {
        initMainChart(mainChartDom);
    }
    if (pieChartDom) {
        initPieChart(pieChartDom);
    }
    // 【新增】初始化环比图
    if (comparisonChartDom) {
        initComparisonChart(comparisonChartDom);
    }
});

/**
 * 初始化主趋势图 (从后端 API 获取数据)
 */
function initMainChart(dom) {
    var myChart = echarts.init(dom);
    myChart.showLoading();

    fetch('/api/realtime_chart')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            myChart.hideLoading();

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
                    data: data.time,
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
                        data: data.value
                    }
                ]
            };
            myChart.setOption(option);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            myChart.hideLoading();
            dom.innerHTML = '<div class="text-center text-muted py-5">实时负荷数据加载失败</div>';
        });

    window.addEventListener('resize', function() {
        myChart.resize();
    });
}

/**
 * 初始化能耗构成饼图 (静态演示数据)
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
                radius: ['45%', '70%'],
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

/**
 * 【新增】初始化环比增长图 (从后端 API 获取数据)
 */
function initComparisonChart(dom) {
    var myChart = echarts.init(dom);
    myChart.showLoading();

    // 假设后端 API 接口为 /api/comparison_data
    fetch('/api/comparison_data')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            myChart.hideLoading();

            const current = data.values[0];
            const lastPeriod = data.values[1];
            const lastYear = data.values[2];

            // 计算环比增长率 (本期 vs 上期/上周)
            const periodGrowth = lastPeriod > 0 ? (((current - lastPeriod) / lastPeriod) * 100).toFixed(1) : 'N/A';
            // 计算同比增长率 (本期 vs 去年同期)
            const yearGrowth = lastYear > 0 ? (((current - lastYear) / lastYear) * 100).toFixed(1) : 'N/A';

            var option = {
                title: {
                    text: '能耗值对比',
                    left: 'center',
                    textStyle: { fontSize: 14 }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    formatter: function(params) {
                        const value = params[0].value;
                        const name = params[0].name;
                        let tooltip = `${name}<br/>能耗: ${value.toFixed(2)} kWh`;

                        if (name === data.labels[0]) {
                            tooltip += `<br/>环比(${data.labels[1]}): ${periodGrowth}%`;
                            tooltip += `<br/>同比(${data.labels[2]}): ${yearGrowth}%`;
                        }
                        return tooltip;
                    }
                },
                grid: {
                    left: '5%',
                    right: '5%',
                    bottom: '5%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: data.labels
                },
                yAxis: {
                    type: 'value',
                    name: '累计能耗 (kWh)',
                    axisLabel: {
                        formatter: '{value}'
                    }
                },
                series: [
                    {
                        name: '能耗值',
                        type: 'bar',
                        data: data.values,
                        barWidth: '30%',
                        itemStyle: {
                            borderRadius: [5, 5, 0, 0],
                            color: function(params) {
                                return params.dataIndex === 0 ? '#13ce66' : '#97c7e9'; // 本期绿色，对比期蓝色
                            }
                        },
                        markLine: {
                            symbol: 'none',
                            silent: true,
                            data: [
                                {
                                    xAxis: data.labels[0],
                                    lineStyle: { type: 'dashed', color: '#ff4949' },
                                    label: {
                                        formatter: `环比: ${periodGrowth}% | 同比: ${yearGrowth}%`,
                                        position: 'insideStartTop',
                                        fontSize: 12
                                    }
                                }
                            ]
                        }
                    }
                ]
            };
            myChart.setOption(option);
        })
        .catch(error => {
            console.error('Error fetching comparison data:', error);
            myChart.hideLoading();
            dom.innerHTML = '<div class="text-center text-muted py-5">环比数据加载失败</div>';
        });

    window.addEventListener('resize', function() {
        myChart.resize();
    });
}