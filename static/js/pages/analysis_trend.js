/**
 * 趋势分析功能 JavaScript
 */

// ==================== 初始化趋势图表 ====================

function initTrendCharts() {
    if (!trendInitialized) {
        const trendEl = document.getElementById('trendChart');
        const regionEl = document.getElementById('regionCompareChart');
        const methodEl = document.getElementById('methodTrendChart');
        
        if (trendEl) trendChart = echarts.init(trendEl);
        if (regionEl) regionCompareChart = echarts.init(regionEl);
        if (methodEl) methodTrendChart = echarts.init(methodEl);
        
        trendInitialized = true;
        
        window.addEventListener('resize', function() {
            if (trendChart) trendChart.resize();
            if (regionCompareChart) regionCompareChart.resize();
            if (methodTrendChart) methodTrendChart.resize();
        });
        
        // 加载地区和选项
        loadTrendLocations();
        loadTrendMethods();
    }
}

// ==================== 加载筛选选项 ====================

function loadTrendLocations() {
    fetch('/api/data/list')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.locations) {
                const select = document.getElementById('trendLocations');
                const regionSelect = document.getElementById('regionCompareLocations');
                
                if (select) {
                    select.innerHTML = '<option value="">全部地区</option>';
                    data.locations.forEach(location => {
                        const option = document.createElement('option');
                        option.value = location;
                        option.textContent = location;
                        select.appendChild(option);
                    });
                }
                
                if (regionSelect) {
                    regionSelect.innerHTML = '<option value="">全部地区</option>';
                    data.locations.forEach(location => {
                        const option = document.createElement('option');
                        option.value = location;
                        option.textContent = location;
                        regionSelect.appendChild(option);
                    });
                }
            }
        })
        .catch(error => console.error('加载地区列表失败:', error));
}

function loadTrendMethods() {
    // 从分布数据中获取方法类别
    fetch('/api/analysis/distribution?param_type=k1')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.methods) {
                const select = document.getElementById('trendMethods');
                if (select) {
                    select.innerHTML = '<option value="">全部方法</option>';
                    data.methods.forEach(method => {
                        const option = document.createElement('option');
                        option.value = method;
                        option.textContent = `方法 ${method}`;
                        select.appendChild(option);
                    });
                }
            }
        })
        .catch(error => console.error('加载方法列表失败:', error));
}

// ==================== 主趋势图加载 ====================

function loadTrendData() {
    // 收集选中的参数类型
    const paramTypes = [];
    if (document.getElementById('trendParamK1').checked) paramTypes.push('k1');
    if (document.getElementById('trendParamK2').checked) paramTypes.push('k2');
    if (document.getElementById('trendParamQ1').checked) paramTypes.push('q1');
    
    if (paramTypes.length === 0) {
        alert('请至少选择一个参数类型');
        return;
    }
    
    const granularity = document.getElementById('trendGranularity').value;
    const dateFrom = document.getElementById('trendDateFrom').value;
    const dateTo = document.getElementById('trendDateTo').value;
    const movingAvg = document.getElementById('trendMovingAvg').value;
    
    // 获取选中的地区
    const locationsSelect = document.getElementById('trendLocations');
    const selectedLocations = Array.from(locationsSelect.selectedOptions)
        .map(opt => opt.value).filter(v => v !== '');
    
    // 获取选中的方法
    const methodsSelect = document.getElementById('trendMethods');
    const selectedMethods = Array.from(methodsSelect.selectedOptions)
        .map(opt => opt.value).filter(v => v !== '');
    
    const params = new URLSearchParams({
        param_types: paramTypes.join(','),
        granularity: granularity
    });
    
    if (selectedLocations.length > 0) params.append('locations', selectedLocations.join(','));
    if (selectedMethods.length > 0) params.append('methods', selectedMethods.join(','));
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (movingAvg) params.append('moving_avg', movingAvg);
    
    fetch(`/api/analysis/trend?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderTrendChart(data);
                updateTrendStats(data);
            } else {
                console.error('加载趋势数据失败:', data.error);
            }
        })
        .catch(error => console.error('加载趋势数据失败:', error));
}

function renderTrendChart(data) {
    const { results, granularity } = data;
    const series = [];
    const colors = ['#5470c6', '#91cc75', '#fac858']; // K1, K2, Q1 颜色
    
    Object.keys(results).forEach((paramType, idx) => {
        const result = results[paramType];
        if (!result.data || result.data.length === 0) return;
        
        const paramLabels = { k1: 'K1', k2: 'K2', q1: 'Q1' };
        const label = paramLabels[paramType] || paramType;
        
        const periods = result.data.map(d => d.period);
        const avgValues = result.data.map(d => d.avg);
        
        // 基础系列
        series.push({
            name: `${label}`,
            type: 'line',
            data: avgValues,
            smooth: true,
            itemStyle: { color: colors[idx % colors.length] },
            lineStyle: { width: 3 }
        });
        
        // 移动平均系列（如果有）
        if (result.moving_avg && result.data[0].smoothed_avg !== undefined) {
            const smoothedValues = result.data.map(d => d.smoothed_avg);
            series.push({
                name: `${label} (${result.moving_avg}日移动平均)`,
                type: 'line',
                data: smoothedValues,
                smooth: true,
                itemStyle: { color: colors[idx % colors.length], opacity: 0.5 },
                lineStyle: { width: 2, type: 'dashed' }
            });
        }
    });
    
    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                let result = `<div style="font-weight:bold;">${params[0].name}</div>`;
                params.forEach(param => {
                    result += `<div>${param.seriesName}: <span style="color:${param.color};font-weight:bold;">${param.value !== null ? param.value.toFixed(4) : '-'}</span></div>`;
                });
                return result;
            }
        },
        legend: {
            data: series.map(s => s.name),
            top: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: Object.values(results)[0]?.data?.map(d => d.period) || [],
            axisLabel: { rotate: 45, fontSize: 11 }
        },
        yAxis: {
            type: 'value',
            name: '参数值'
        },
        series: series
    };
    
    trendChart.setOption(option, true);
}

function updateTrendStats(data) {
    const stats = data.overall_stats;
    if (!stats || Object.keys(stats).length === 0) return;
    
    // 使用第一个参数的统计数据
    const firstParam = Object.keys(stats)[0];
    const stat = stats[firstParam];
    
    document.getElementById('trendStatCount').textContent = stat.count || 0;
    document.getElementById('trendStatMean').textContent = stat.mean ? stat.mean.toFixed(4) : '-';
    document.getElementById('trendStatMax').textContent = stat.max ? stat.max.toFixed(4) : '-';
    document.getElementById('trendStatMin').textContent = stat.min ? stat.min.toFixed(4) : '-';
    document.getElementById('trendStatStd').textContent = stat.std ? stat.std.toFixed(4) : '-';
    document.getElementById('trendStatDirection').textContent = stat.trend_direction || '-';
    
    document.getElementById('trendStatsSummary').style.display = 'grid';
}

// ==================== 地区对比趋势图 ====================

function loadRegionCompare() {
    const paramType = document.getElementById('regionCompareParam').value;
    const granularity = document.getElementById('trendGranularity').value;
    const dateFrom = document.getElementById('trendDateFrom').value;
    const dateTo = document.getElementById('trendDateTo').value;
    
    const locationsSelect = document.getElementById('regionCompareLocations');
    const selectedLocations = Array.from(locationsSelect.selectedOptions)
        .map(opt => opt.value).filter(v => v !== '');
    
    const params = new URLSearchParams({
        param_type: paramType,
        group_by: 'location',
        granularity: granularity
    });
    
    if (selectedLocations.length > 0) params.append('items', selectedLocations.join(','));
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    fetch(`/api/analysis/trend_grouped?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderRegionCompareChart(data);
            }
        })
        .catch(error => console.error('加载地区对比数据失败:', error));
}

function renderRegionCompareChart(data) {
    const { groups, time_periods, param_type } = data;
    const series = [];
    const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4'];
    
    Object.keys(groups).slice(0, 8).forEach((location, idx) => {
        const groupData = groups[location];
        const values = groupData.map(d => d.avg);
        
        series.push({
            name: location,
            type: 'line',
            data: values,
            smooth: true,
            itemStyle: { color: colors[idx % colors.length] },
            lineStyle: { width: 2 }
        });
    });
    
    const paramLabels = { k1: 'K1', k2: 'K2', q1: 'Q1' };
    
    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                let result = `<div style="font-weight:bold;">${params[0].name}</div>`;
                params.forEach(param => {
                    result += `<div>${param.seriesName}: <span style="color:${param.color};font-weight:bold;">${param.value !== null ? param.value.toFixed(4) : '-'}</span></div>`;
                });
                return result;
            }
        },
        legend: {
            data: series.map(s => s.name),
            top: 0,
            textStyle: { fontSize: 11 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: time_periods,
            axisLabel: { rotate: 45, fontSize: 10 }
        },
        yAxis: {
            type: 'value',
            name: `${paramLabels[param_type]} 值`
        },
        series: series
    };
    
    regionCompareChart.setOption(option, true);
}

// ==================== 方法类别趋势图 ====================

function loadMethodTrend() {
    const paramType = document.getElementById('methodTrendParam').value;
    const mode = document.getElementById('methodTrendMode').value;
    const granularity = document.getElementById('trendGranularity').value;
    const dateFrom = document.getElementById('trendDateFrom').value;
    const dateTo = document.getElementById('trendDateTo').value;
    
    const params = new URLSearchParams({
        param_type: paramType,
        group_by: 'method',
        granularity: granularity
    });
    
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    fetch(`/api/analysis/trend_grouped?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderMethodTrendChart(data, mode);
            }
        })
        .catch(error => console.error('加载方法趋势数据失败:', error));
}

function renderMethodTrendChart(data, mode) {
    const { groups, time_periods, param_type } = data;
    const series = [];
    const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'];
    
    Object.keys(groups).slice(0, 5).forEach((method, idx) => {
        const groupData = groups[method];
        const values = groupData.map(d => d.avg);
        
        series.push({
            name: `方法 ${method}`,
            type: mode === 'bar' ? 'bar' : 'line',
            data: values,
            smooth: mode === 'line',
            itemStyle: { color: colors[idx % colors.length] },
            barGap: '10%'
        });
    });
    
    const paramLabels = { k1: 'K1', k2: 'K2', q1: 'Q1' };
    
    const option = {
        tooltip: {
            trigger: mode === 'bar' ? 'axis' : 'item',
            formatter: function(params) {
                if (Array.isArray(params)) {
                    let result = `<div style="font-weight:bold;">${params[0].name}</div>`;
                    params.forEach(param => {
                        result += `<div>${param.seriesName}: <span style="color:${param.color};font-weight:bold;">${param.value !== null ? param.value.toFixed(4) : '-'}</span></div>`;
                    });
                    return result;
                } else {
                    return `${params.seriesName}<br/>${params.name}: ${params.value !== null ? params.value.toFixed(4) : '-'}`;
                }
            }
        },
        legend: {
            data: series.map(s => s.name),
            top: 0,
            textStyle: { fontSize: 11 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: time_periods,
            axisLabel: { rotate: 45, fontSize: 10 }
        },
        yAxis: {
            type: 'value',
            name: `${paramLabels[param_type]} 值`
        },
        series: series
    };
    
    methodTrendChart.setOption(option, true);
}
