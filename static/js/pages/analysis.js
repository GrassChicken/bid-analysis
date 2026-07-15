/**
 * 数据分析页面 JavaScript
 */

// 全局变量
let histogramChart = null;
let boxplotChart = null;
let heatmapChart = null;
let heatmapInitialized = false;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    loadLocations();
    loadDistribution();
});

/**
 * 初始化 ECharts 实例
 */
function initCharts() {
    histogramChart = echarts.init(document.getElementById('histogramChart'));
    boxplotChart = echarts.init(document.getElementById('boxplotChart'));
    
    // 窗口大小改变时重新调整图表
    window.addEventListener('resize', function() {
        if (histogramChart) histogramChart.resize();
        if (boxplotChart) boxplotChart.resize();
    });
}

/**
 * 加载地区列表
 */
function loadLocations() {
    fetch('/api/data/list')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.locations) {
                const select = document.getElementById('locationFilter');
                select.innerHTML = '<option value="">全部地区</option>';
                data.locations.forEach(location => {
                    const option = document.createElement('option');
                    option.value = location;
                    option.textContent = location;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('加载地区列表失败:', error);
        });
}

/**
 * 切换 Tab
 */
function switchTab(tabName) {
    // 更新 Tab 按钮状态
    document.querySelectorAll('.analysis-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        }
    });
    
    // 切换内容区域
    document.getElementById('distributionContent').style.display = 
        tabName === 'distribution' ? 'block' : 'none';
    document.getElementById('heatmapContent').style.display = 
        tabName === 'heatmap' ? 'block' : 'none';
    document.getElementById('trendContent').style.display = 
        tabName === 'trend' ? 'block' : 'none';
    
    // 切换到热力图时初始化并加载数据
    if (tabName === 'heatmap') {
        setTimeout(() => {
            initHeatmap();
            loadHeatmap();
        }, 100);
    }
}

/**
 * 加载分布数据
 */
function loadDistribution() {
    const paramType = document.getElementById('paramType').value;
    const location = document.getElementById('locationFilter').value;
    const method = document.getElementById('methodFilter').value;
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    
    // 构建查询参数
    const params = new URLSearchParams({
        param_type: paramType
    });
    
    if (location) params.append('location', location);
    if (method) params.append('method', method);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    // 显示加载状态
    showLoading();
    
    fetch(`/api/analysis/distribution?${params}`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success && data.data && data.data.length > 0) {
                renderDistributionCharts(data.data, data.stats, data.location_stats);
            } else {
                showEmpty();
            }
        })
        .catch(error => {
            console.error('加载分布数据失败:', error);
            hideLoading();
            showEmpty('加载数据失败');
        });
}

/**
 * 渲染分布图表
 */
function renderDistributionCharts(values, stats, locationStats) {
    // 更新统计摘要
    updateStatsSummary(stats);
    
    // 渲染直方图
    renderHistogram(values, stats);
    
    // 渲染箱线图
    renderBoxplot(locationStats);
}

/**
 * 更新统计摘要
 */
function updateStatsSummary(stats) {
    if (!stats) return;
    
    document.getElementById('statCount').textContent = stats.count || 0;
    document.getElementById('statMean').textContent = 
        stats.mean ? stats.mean.toFixed(4) : '-';
    document.getElementById('statMedian').textContent = 
        stats.median ? stats.median.toFixed(4) : '-';
    document.getElementById('statStd').textContent = 
        stats.std ? stats.std.toFixed(4) : '-';
    document.getElementById('statSkewness').textContent = 
        stats.skewness ? stats.skewness.toFixed(4) : '-';
    document.getElementById('statKurtosis').textContent = 
        stats.kurtosis ? stats.kurtosis.toFixed(4) : '-';
    
    document.getElementById('statsSummary').style.display = 'grid';
}

/**
 * 渲染直方图
 */
function renderHistogram(values, stats) {
    // 计算直方图数据
    const binCount = 15;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const binSize = (max - min) / binCount;
    
    const bins = [];
    const counts = new Array(binCount).fill(0);
    
    for (let i = 0; i < binCount; i++) {
        const start = min + i * binSize;
        const end = start + binSize;
        bins.push(`${start.toFixed(3)} - ${end.toFixed(3)}`);
    }
    
    values.forEach(value => {
        let binIndex = Math.floor((value - min) / binSize);
        if (binIndex >= binCount) binIndex = binCount - 1;
        counts[binIndex]++;
    });
    
    // 配置 ECharts
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: bins,
            axisLabel: {
                rotate: 45,
                fontSize: 11
            }
        },
        yAxis: {
            type: 'value',
            name: '频次'
        },
        series: [
            {
                name: '频次',
                type: 'bar',
                data: counts,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#667eea' },
                        { offset: 1, color: '#764ba2' }
                    ])
                }
            }
        ]
    };
    
    histogramChart.setOption(option);
}

/**
 * 渲染箱线图
 */
function renderBoxplot(locationStats) {
    if (!locationStats || Object.keys(locationStats).length === 0) {
        // 如果没有地区数据，显示单个箱线图
        const option = {
            tooltip: {
                trigger: 'item'
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: ['全部数据']
            },
            yAxis: {
                type: 'value',
                name: '数值'
            },
            series: [
                {
                    name: 'boxplot',
                    type: 'boxplot',
                    data: []
                }
            ]
        };
        boxplotChart.setOption(option);
        return;
    }
    
    // 按地区排序
    const locations = Object.keys(locationStats).sort();
    const boxplotData = [];
    
    locations.forEach(location => {
        const stats = locationStats[location];
        if (stats && stats.q1 && stats.q3) {
            // boxplot 数据格式: [min, Q1, median, Q3, max]
            const min = stats.min || 0;
            const q1 = stats.q1;
            const median = stats.median;
            const q3 = stats.q3;
            const max = stats.max || 0;
            
            boxplotData.push([min, q1, median, q3, max]);
        }
    });
    
    const option = {
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                const location = locations[params.dataIndex];
                const data = params.data;
                return `
                    <div style="font-weight: bold; margin-bottom: 8px;">${location}</div>
                    <div>最小值: ${data[0].toFixed(4)}</div>
                    <div>Q1: ${data[1].toFixed(4)}</div>
                    <div>中位数: ${data[2].toFixed(4)}</div>
                    <div>Q3: ${data[3].toFixed(4)}</div>
                    <div>最大值: ${data[4].toFixed(4)}</div>
                `;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: locations,
            axisLabel: {
                rotate: 30,
                fontSize: 11
            }
        },
        yAxis: {
            type: 'value',
            name: '数值'
        },
        series: [
            {
                name: 'boxplot',
                type: 'boxplot',
                data: boxplotData,
                itemStyle: {
                    color: '#fff',
                    borderColor: '#667eea'
                }
            }
        ]
    };
    
    boxplotChart.setOption(option);
}

/**
 * 显示加载状态
 */
function showLoading() {
    document.getElementById('loadingState').style.display = 'flex';
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('statsSummary').style.display = 'none';
    if (histogramChart) histogramChart.clear();
    if (boxplotChart) boxplotChart.clear();
}

/**
 * 隐藏加载状态
 */
function hideLoading() {
    document.getElementById('loadingState').style.display = 'none';
}

/**
 * 显示空状态
 */
function showEmpty(message = '暂无数据') {
    document.getElementById('emptyState').style.display = 'flex';
    document.getElementById('emptyText').textContent = message;
    document.getElementById('statsSummary').style.display = 'none';
}

// ==================== 热力图功能 ====================

/**
 * 初始化热力图 ECharts 实例
 */
function initHeatmap() {
    if (!heatmapInitialized) {
        const chartEl = document.getElementById('heatmapChart');
        if (chartEl) {
            heatmapChart = echarts.init(chartEl);
            heatmapInitialized = true;
            
            window.addEventListener('resize', function() {
                if (heatmapChart) heatmapChart.resize();
            });
        }
    }
}

/**
 * 加载热力图数据
 */
function loadHeatmap() {
    const paramType = document.getElementById('heatmapParamType').value;
    const dimension = document.getElementById('heatmapDimension').value;
    const metric = document.getElementById('heatmapMetric').value;
    const dateFrom = document.getElementById('heatmapDateFrom').value;
    const dateTo = document.getElementById('heatmapDateTo').value;
    
    const params = new URLSearchParams({
        param_type: paramType,
        dimension: dimension,
        metric: metric
    });
    
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    // 显示加载状态
    document.getElementById('heatmapLoading').style.display = 'flex';
    document.getElementById('heatmapEmpty').style.display = 'none';
    document.getElementById('heatmapStats').style.display = 'none';
    
    fetch(`/api/analysis/heatmap?${params}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('heatmapLoading').style.display = 'none';
            
            if (data.success && data.data && data.data.length > 0) {
                renderHeatmap(data);
            } else {
                document.getElementById('heatmapEmpty').style.display = 'flex';
                document.getElementById('heatmapEmptyText').textContent = 
                    data.message || '没有找到符合条件的数据';
                document.getElementById('heatmapStats').style.display = 'none';
                if (heatmapChart) heatmapChart.clear();
            }
        })
        .catch(error => {
            console.error('加载热力图数据失败:', error);
            document.getElementById('heatmapLoading').style.display = 'none';
            document.getElementById('heatmapEmpty').style.display = 'flex';
            document.getElementById('heatmapEmptyText').textContent = '加载数据失败';
        });
}

/**
 * 渲染热力图
 */
function renderHeatmap(result) {
    const { data, dimension, metric, locations } = result;
    
    // 确定轴标签
    let xLabels, xAxisName;
    if (dimension === 'location_time') {
        xLabels = result.time_labels;
        xAxisName = '月份';
    } else {
        xLabels = result.methods;
        xAxisName = '方法类别';
    }
    
    const yAxisName = '地区';
    const metricLabel = metric === 'mean' ? '均值' : '频次';
    
    // 更新标题
    const dimensionText = dimension === 'location_time' ? '地区 × 时间段' : '地区 × 方法类别';
    const paramText = { k1: 'K1', k2: 'K2', q1: 'Q1' }[document.getElementById('heatmapParamType').value];
    document.getElementById('heatmapTitle').textContent = 
        `🗺️ ${paramText} ${dimensionText}热力图（${metricLabel}）`;
    
    // 计算统计摘要
    const values = data.map(d => d[2]);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const avgVal = values.reduce((a, b) => a + b, 0) / values.length;
    
    // 更新统计摘要
    document.getElementById('heatmapCellCount').textContent = data.length;
    document.getElementById('heatmapMaxVal').textContent = maxVal.toFixed(4);
    document.getElementById('heatmapMinVal').textContent = minVal.toFixed(4);
    document.getElementById('heatmapAvgVal').textContent = avgVal.toFixed(4);
    document.getElementById('heatmapStats').style.display = 'grid';
    
    // 计算合适的单元格大小
    const cellSize = Math.min(60, Math.max(20, Math.floor(600 / Math.max(locations.length, xLabels.length))));
    
    // 根据维度选择颜色方案
    let colorRange;
    if (metric === 'mean') {
        // 均值：蓝-白-红渐变
        colorRange = ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027'];
    } else {
        // 频次：浅色到深色
        colorRange = ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'];
    }
    
    // ECharts 配置
    const option = {
        tooltip: {
            position: 'top',
            formatter: function(params) {
                const xLabel = xLabels[params.data[0]];
                const yLabel = locations[params.data[1]];
                const value = params.data[2];
                return `<div style="font-weight:bold;margin-bottom:4px;">${yLabel} · ${xLabel}</div>` +
                       `<div>${metricLabel}: <span style="color:#e74c3c;font-weight:bold;">${value.toFixed(4)}</span></div>`;
            }
        },
        grid: {
            top: '12%',
            left: '15%',
            right: '12%',
            bottom: '15%'
        },
        xAxis: {
            type: 'category',
            data: xLabels,
            name: xAxisName,
            nameLocation: 'middle',
            nameGap: 35,
            splitArea: { show: true },
            axisLabel: {
                rotate: dimension === 'location_time' ? 0 : 30,
                fontSize: 12,
                fontWeight: 'bold'
            }
        },
        yAxis: {
            type: 'category',
            data: locations,
            name: yAxisName,
            nameLocation: 'middle',
            nameGap: 80,
            splitArea: { show: true },
            axisLabel: {
                fontSize: 12,
                fontWeight: 'bold'
            }
        },
        visualMap: {
            min: minVal,
            max: maxVal,
            calculable: true,
            orient: 'vertical',
            right: 10,
            top: 'center',
            itemHeight: 300,
            inRange: {
                color: colorRange
            },
            text: ['高', '低'],
            textStyle: {
                fontSize: 12
            }
        },
        series: [{
            name: metricLabel,
            type: 'heatmap',
            data: data,
            label: {
                show: data.length <= 100,  // 数据格少时显示数值
                fontSize: 11,
                formatter: function(params) {
                    return params.data[2].toFixed(3);
                }
            },
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowColor: 'rgba(0, 0, 0, 0.5)',
                    borderColor: '#333',
                    borderWidth: 2
                }
            },
            itemStyle: {
                borderColor: '#fff',
                borderWidth: 2,
                borderRadius: 4
            }
        }]
    };
    
    heatmapChart.setOption(option, true);
    
    // 调整图表高度适应数据量
    const neededHeight = Math.max(400, locations.length * cellSize + 150);
    document.getElementById('heatmapChart').style.height = neededHeight + 'px';
    heatmapChart.resize();
}
