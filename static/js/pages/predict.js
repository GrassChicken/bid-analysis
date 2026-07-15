// V6.0 智能预测页面 JS

var allData = [];
var loadingProgressTimer = null;

// 页面加载
document.addEventListener('DOMContentLoaded', function() {
    loadLocations();
});

function loadLocations() {
    fetch('/api/data/list', { credentials: 'same-origin' })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                allData = data.records;
                const select = document.getElementById('locationFilter');
                select.innerHTML = '<option value="">不限地点</option>';
                data.locations.forEach(function(loc) {
                    const option = document.createElement('option');
                    option.value = loc;
                    option.textContent = loc;
                    select.appendChild(option);
                });
                updateDataCount();
            }
        });
}

function parseBidDateTime(bidDate, bidTime) {
    if (!bidDate) return '';
    const datePart = bidDate.replace(/\//g, '-');
    if (!bidTime) return datePart;
    return datePart + ' ' + bidTime;
}

function updateDataCount() {
    const location = document.getElementById('locationFilter').value;
    const method = document.getElementById('methodFilter').value;
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;

    let filtered = allData;
    if (location) filtered = filtered.filter(function(r) { return r.bid_location === location; });
    if (method) filtered = filtered.filter(function(r) { return r.method_category === method; });
    if (dateFrom) {
        const dtFrom = dateFrom.replace('T', ' ');
        filtered = filtered.filter(function(r) {
            return parseBidDateTime(r.bid_date, r.bid_time) >= dtFrom;
        });
    }
    if (dateTo) {
        const dtTo = dateTo.replace('T', ' ');
        filtered = filtered.filter(function(r) {
            return parseBidDateTime(r.bid_date, r.bid_time) <= dtTo;
        });
    }

    document.getElementById('dataCount').textContent = filtered.length;
    document.getElementById('k1Count').textContent = filtered.filter(function(r) { return r.k1_value; }).length;
    document.getElementById('q1Count').textContent = filtered.filter(function(r) { return r.q1_value; }).length;
}

function predict() {
    doPredict(null);
}

function doPredict(existingRecordId) {
    const projectName = document.getElementById('projectName').value.trim();
    const locationFilter = document.getElementById('locationFilter').value;
    const methodFilter = document.getElementById('methodFilter').value;
    const dateFromRaw = document.getElementById('dateFrom').value;
    const dateToRaw = document.getElementById('dateTo').value;
    // datetime-local 格式 "2025-01-01T09:30" -> 转换为 "2025-01-01 09:30" 发给后端
    const dateFrom = dateFromRaw ? dateFromRaw.replace('T', ' ') : '';
    const dateTo = dateToRaw ? dateToRaw.replace('T', ' ') : '';

    if (!projectName) {
        // 输入框抖动提示
        const input = document.getElementById('projectName');
        input.style.borderColor = '#e74c3c';
        input.style.animation = 'shake 0.4s ease';
        input.focus();
        setTimeout(function() {
            input.style.borderColor = '';
            input.style.animation = '';
        }, 600);
        return;
    }

    // 显示加载动画
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('resultSection').classList.add('hidden');

    // 进度条动画
    startLoadingProgress();

    // 加载文字动态变化
    var loadingText = document.getElementById('loadingText');
    var loadingStages = [
        '正在初始化预测引擎',
        '正在加载统计算法模块',
        '正在分析历史数据',
        '正在运行 20 种统计算法分析数据'
    ];
    var stageIndex = 0;
    loadingText.textContent = loadingStages[0];
    var stageTimer = setInterval(function() {
        stageIndex++;
        if (stageIndex < loadingStages.length) {
            loadingText.textContent = loadingStages[stageIndex];
        }
    }, 700);

    // 根据是否是覆盖模式选择 API
    var apiUrl = existingRecordId
        ? '/api/predict/update/' + existingRecordId
        : '/api/predict';

    // 延迟 3 秒后调用后台 API
    setTimeout(function() {
        clearInterval(stageTimer);
        loadingText.textContent = '正在生成预测结果';

        fetch(apiUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({
                project_name: projectName,
                location: locationFilter || null,
                method_category: methodFilter || null,
                datetime_from: dateFrom || null,
                datetime_to: dateTo || null
            })
        })
        .then(function(response) {
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    throw new Error('会话已过期');
                }
                return response.json().then(function(data) {
                    throw new Error(data.error || '服务器错误');
                });
            }
            return response.json();
        })
        .then(function(data) {
            stopLoadingProgress();
            document.getElementById('loading').classList.add('hidden');
            if (data.success) {
                // 检查是否重复项目
                if (data.duplicate && data.existing) {
                    showDuplicateConfirm(projectName, locationFilter, methodFilter, dateFrom, dateTo, data, data.existing);
                } else {
                    // 保存记录 ID 用于导出
                    currentPredictionRecordId = data.record_id || null;
                    displayResults(data);
                }
            } else {
                document.getElementById('resultSection').classList.add('hidden');
                alert('预测失败: ' + (data.error || '未知错误'));
            }
        })
        .catch(function(error) {
            stopLoadingProgress();
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('resultSection').classList.add('hidden');
            alert('请求失败: ' + error);
        });
    }, 3000);
}

function startLoadingProgress() {
    const bar = document.getElementById('loadingProgressBar');
    if (bar) {
        bar.style.animation = 'none';
        // Force reflow
        void bar.offsetWidth;
        bar.style.animation = 'progressAnim 3s ease-in-out';
    }
}

function stopLoadingProgress() {
    const bar = document.getElementById('loadingProgressBar');
    if (bar) {
        bar.style.animation = 'none';
        bar.style.width = '100%';
    }
}

function displayResults(data) {
    const resultGrid = document.getElementById('resultGrid');
    let html = '';

    // 渲染雷达图
    renderRadarChart(data);

    // 获取预测的方法类别
    var predictedMethod = '';
    if (data.method_prediction) {
        predictedMethod = data.method_prediction.prediction;
    }

    // 1. 方法类别预测
    if (data.method_prediction) {
        html += createPredictionCard(
            '📋 方法类别',
            data.method_prediction.prediction == '1' ? '方法 1' : '方法 2',
            data.method_prediction.confidence,
            data.method_prediction.reasoning,
            data.method_prediction.method,
            '#e74c3c',
            data.method_all
        );
    }

    // 2. K1 值预测
    if (data.k1_prediction) {
        html += createPredictionCard(
            '🎯 K1 值',
            data.k1_prediction.prediction,
            data.k1_prediction.confidence,
            data.k1_prediction.reasoning,
            data.k1_prediction.method,
            '#3498db',
            data.k1_all
        );
    }

    // 3. Q1 值预测 - 方法类别为1时不显示
    if (data.q1_prediction && predictedMethod !== '1') {
        html += createPredictionCard(
            '⚙️ Q1 值',
            data.q1_prediction.prediction,
            data.q1_prediction.confidence,
            data.q1_prediction.reasoning,
            data.q1_prediction.method,
            '#9b59b6',
            data.q1_all
        );
    }

    if (!html) {
        html = '<div class="empty-prediction"><p>📭 数据不足,无法进行预测</p><p class="sub-text">至少需要 3 条有效数据</p></div>';
    }

    resultGrid.innerHTML = html;
    document.getElementById('resultSection').classList.remove('hidden');

    // 滚动到结果区域
    setTimeout(function() {
        document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

function createPredictionCard(title, value, confidence, reasoning, methodName, color, allPredictions) {
    const confPercent = (confidence * 100).toFixed(0);
    const confClass = confidence >= 0.8 ? 'high' : (confidence >= 0.5 ? 'medium' : 'low');

    // 置信度标签文字
    const confTagText = confidence >= 0.8 ? '✅ 高置信度' : (confidence >= 0.5 ? '⚠️ 中等置信度' : '❌ 低置信度');

    let otherMethodsHtml = '';
    if (allPredictions && allPredictions.length > 1) {
        otherMethodsHtml = '<div class="other-methods"><div class="other-methods-title">📈 其他方法结果</div>';
        for (var i = 1; i < allPredictions.length; i++) {
            const p = allPredictions[i];
            const pConf = (p.confidence * 100).toFixed(0);
            const pConfClass = p.confidence >= 0.8 ? 'high' : (p.confidence >= 0.5 ? 'medium' : 'low');
            otherMethodsHtml += '<div class="other-method-item">' +
                '<span class="method-name">' + p.method + '</span>' +
                '<span class="method-value">' + p.prediction + '</span>' +
                '<span class="method-conf ' + pConfClass + '">' + pConf + '%</span>' +
                '</div>';
        }
        otherMethodsHtml += '</div>';
    }

    return '<div class="result-card">' +
        '<div class="card-accent" style="background:linear-gradient(90deg,' + color + ',' + color + '80);"></div>' +
        '<div class="card-body">' +
        '<div class="card-header">' +
        '<h3>' + title + '</h3>' +
        '<span class="method-badge" style="background:' + color + '">' + methodName + '</span>' +
        '</div>' +
        '<div class="prediction-value" style="color:' + color + '">' + value + '</div>' +
        '<div class="confidence-bar-container">' +
        '<div class="confidence-bar-label">' +
        '<span>置信度</span>' +
        '<span style="color:' + color + '">' + confPercent + '%</span>' +
        '</div>' +
        '<div class="confidence-bar">' +
        '<div class="confidence-bar__fill ' + confClass + '" style="width:' + confPercent + '%"></div>' +
        '</div>' +
        '<div class="confidence-tag ' + confClass + '">' + confTagText + '</div>' +
        '</div>' +
        '<div class="reasoning">' +
        '<strong>📝 分析理由</strong>' +
        '<p>' + (reasoning || '暂无分析理由') + '</p>' +
        '</div>' +
        otherMethodsHtml +
        '</div>' +
        '</div>';
}


// ============================================================
// 导出功能
// ============================================================
var currentPredictionRecordId = null;

function exportCurrentPrediction(format) {
    if (!currentPredictionRecordId) {
        alert('无法导出:未找到预测记录 ID');
        return;
    }
    var url = '/api/prediction/export/' + currentPredictionRecordId + '/' + format;
    window.open(url, '_blank');
}


// ============================================================
// 重复项目检测 & 覆盖预测
// ============================================================

/**
 * 全局变量:存储覆盖确认回调参数
 */
var _overwritePendingRecordId = null;
var _overwritePendingProject = '';
var _overwritePendingPredictData = null;
var _overwritePendingParams = null;

/**
 * 显示重复项目确认模态框
 */
function showDuplicateConfirm(projectName, locationFilter, methodFilter, dateFrom, dateTo, predictData, existing) {
    // 暂存参数,供确认按钮回调使用
    _overwritePendingRecordId = existing.id;
    _overwritePendingProject = projectName;
    _overwritePendingPredictData = predictData;
    _overwritePendingParams = {
        locationFilter: locationFilter,
        methodFilter: methodFilter,
        dateFrom: dateFrom,
        dateTo: dateTo
    };

    // 上次预测信息
    var existingMethod = existing.method_prediction === '1' ? '方法1' : (existing.method_prediction === '2' ? '方法2' : (existing.method_prediction || '未预测'));
    var existingK1 = existing.k1_prediction || '无';
    var existingQ1 = existing.q1_prediction || '无';
    var existingTime = existing.prediction_time || '未知';

    // 本次预测信息
    var newMethod = predictData.method_prediction ? (predictData.method_prediction.prediction === '1' ? '方法1' : '方法2') : '未预测';
    var newK1 = predictData.k1_prediction ? predictData.k1_prediction.prediction : '无';
    var newQ1 = predictData.q1_prediction ? predictData.q1_prediction.prediction : '无';

    // 填充项目名称
    document.getElementById('modalProjectName').innerHTML = '项目名称:<strong>' + escapeHtml(projectName) + '</strong>';

    // 填充上次预测
    document.getElementById('modalOldTime').textContent = existingTime;
    document.getElementById('modalOldMethod').textContent = existingMethod;
    document.getElementById('modalOldK1').textContent = existingK1;
    document.getElementById('modalOldQ1').textContent = existingQ1;

    // 填充本次预测
    document.getElementById('modalNewMethod').textContent = newMethod;
    document.getElementById('modalNewK1').textContent = newK1;
    document.getElementById('modalNewQ1').textContent = newQ1;

    // 填充变化对比
    var changesHtml = '<div class="modal-changes-title">📊 变化对比</div>';
    var changes = [];
    var currentMethodPred = (predictData.method_prediction && predictData.method_prediction.prediction) ? predictData.method_prediction.prediction : null;
    if (existing.method_prediction !== currentMethodPred) {
        changes.push({ label: '方法类别', old: existingMethod, new: newMethod });
    }
    if (existing.k1_prediction !== newK1) {
        changes.push({ label: 'K1', old: existingK1, new: newK1 });
    }
    if (existing.q1_prediction !== newQ1) {
        changes.push({ label: 'Q1', old: existingQ1, new: newQ1 });
    }

    if (changes.length === 0) {
        changesHtml += '<div class="modal-change-item same">✅ 预测结果与上次一致</div>';
    } else {
        changes.forEach(function(c) {
            changesHtml += '<div class="modal-change-item">' +
                c.label + ': <span class="arrow">' + c.old + '</span> → <span class="arrow">' + c.new + '</span>' +
                '</div>';
        });
    }
    document.getElementById('modalChanges').innerHTML = changesHtml;

    // 显示模态框
    document.getElementById('duplicateModal').classList.add('show');
}

/**
 * 关闭重复确认模态框(取消操作,显示本次结果)
 */
function closeDuplicateModal() {
    document.getElementById('duplicateModal').classList.remove('show');
    // 显示本次预测结果供参考
    if (_overwritePendingPredictData) {
        currentPredictionRecordId = null;
        displayResults(_overwritePendingPredictData);
    }
    _overwritePendingRecordId = null;
    _overwritePendingProject = '';
    _overwritePendingPredictData = null;
    _overwritePendingParams = null;
}

/**
 * 点击模态框外部关闭
 */
document.addEventListener('click', function(e) {
    var modal = document.getElementById('duplicateModal');
    if (e.target === modal) {
        closeDuplicateModal();
    }
});

/**
 * 模态框中点击"确认覆盖"
 */
function modalOverwrite() {
    var recordId = _overwritePendingRecordId;
    if (recordId) {
        closeDuplicateModal();
        overwritePredict(recordId);
    }
}

/**
 * 执行覆盖预测（调用 update API）
 */
function overwritePredict(recordId) {
    // 优先使用已存储的参数（模态框流程），否则从表单读取
    var projectName, locationFilter, methodFilter, dateFrom, dateTo;
    if (_overwritePendingProject) {
        projectName = _overwritePendingProject;
        var params = _overwritePendingParams || {};
        locationFilter = params.locationFilter || '';
        methodFilter = params.methodFilter || '';
        dateFrom = params.dateFrom || '';
        dateTo = params.dateTo || '';
    } else {
        projectName = document.getElementById('projectName').value.trim();
        locationFilter = document.getElementById('locationFilter').value;
        methodFilter = document.getElementById('methodFilter').value;
        dateFrom = document.getElementById('dateFrom').value;
        dateTo = document.getElementById('dateTo').value;
    }

    // 重新显示加载动画
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('resultSection').classList.add('hidden');
    startLoadingProgress();

    var loadingText = document.getElementById('loadingText');
    loadingText.textContent = '正在更新预测记录...';

    fetch('/api/predict/update/' + recordId, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({
            project_name: projectName,
            location: locationFilter || null,
            method_category: methodFilter || null,
            date_from: dateFrom || null,
            date_to: dateTo || null
        })
    })
    .then(function(response) {
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/login';
                throw new Error('会话已过期');
            }
            return response.json().then(function(data) {
                throw new Error(data.error || '服务器错误');
            });
        }
        return response.json();
    })
    .then(function(data) {
        stopLoadingProgress();
        document.getElementById('loading').classList.add('hidden');
        if (data.success && data.updated) {
            currentPredictionRecordId = data.record_id || null;
            displayResults(data);
            // 提示更新成功
            showToast('✅ 预测记录已更新!');
        } else {
            document.getElementById('resultSection').classList.add('hidden');
            alert('更新失败: ' + (data.error || '未知错误'));
        }
    })
    .catch(function(error) {
        stopLoadingProgress();
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('resultSection').classList.add('hidden');
        alert('请求失败: ' + error);
    });
}

/**
 * 简单的提示框
 */
function showToast(message) {
    var toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = 'position:fixed; top:20px; left:50%; transform:translateX(-50%); ' +
        'background:#27ae60; color:#fff; padding:12px 24px; border-radius:8px; ' +
        'font-size:14px; z-index:10000; box-shadow:0 4px 12px rgba(0,0,0,0.2); ' +
        'opacity:0; transition:opacity 0.3s ease;';
    document.body.appendChild(toast);
    setTimeout(function() { toast.style.opacity = '1'; }, 10);
    setTimeout(function() {
        toast.style.opacity = '0';
        setTimeout(function() { document.body.removeChild(toast); }, 300);
    }, 2500);
}

/**
 * HTML 转义
 */
function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str || ''));
    return div.innerHTML;
}

/**
 * 渲染算法置信度雷达图
 */
function renderRadarChart(data) {
    var radarContainer = document.getElementById('radarChart');
    if (!radarContainer) return;

    // 收集所有算法置信度
    var algorithmScores = [];
    
    // K1 算法
    if (data.k1_all && data.k1_all.length > 0) {
        data.k1_all.forEach(function(item) {
            algorithmScores.push({
                name: 'K1-' + item.method,
                confidence: item.confidence * 100
            });
        });
    }
    
    // Q1 算法
    if (data.q1_all && data.q1_all.length > 0) {
        data.q1_all.forEach(function(item) {
            algorithmScores.push({
                name: 'Q1-' + item.method,
                confidence: item.confidence * 100
            });
        });
    }
    
    // 方法预测
    if (data.method_all && data.method_all.length > 0) {
        data.method_all.forEach(function(item) {
            algorithmScores.push({
                name: '方法-' + item.method,
                confidence: item.confidence * 100
            });
        });
    }
    
    if (algorithmScores.length === 0) {
        radarContainer.style.display = 'none';
        return;
    }
    
    radarContainer.style.display = 'block';
    
    // 限制显示前 8 个算法，避免雷达图过于拥挤
    algorithmScores = algorithmScores.slice(0, 8);
    
    // 初始化 ECharts
    var chart = echarts.init(radarContainer);
    
    // 构建指标
    var indicator = algorithmScores.map(function(item) {
        return {
            name: item.name,
            max: 100
        };
    });
    
    // 构建数据
    var values = algorithmScores.map(function(item) {
        return item.confidence;
    });
    
    // 配置项
    var option = {
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                var html = '<div style="font-weight:bold;margin-bottom:8px;">' + params.name + '</div>';
                params.value.forEach(function(value, index) {
                    html += '<div>' + algorithmScores[index].name + ': ' + value.toFixed(1) + '%</div>';
                });
                return html;
            }
        },
        legend: {
            data: ['当前预测'],
            bottom: 0,
            textStyle: {
                fontSize: 12
            }
        },
        radar: {
            indicator: indicator,
            shape: 'polygon',
            splitNumber: 5,
            axisName: {
                color: '#999',
                fontSize: 11
            },
            splitLine: {
                lineStyle: {
                    color: ['rgba(255, 255, 255, 0.1)', 'rgba(255, 255, 255, 0.2)', 
                            'rgba(255, 255, 255, 0.3)', 'rgba(255, 255, 255, 0.4)', 'rgba(255, 255, 255, 0.5)']
                }
            },
            splitArea: {
                show: true,
                areaStyle: {
                    color: ['rgba(255, 255, 255, 0.02)', 'rgba(255, 255, 255, 0.05)']
                }
            },
            axisLine: {
                lineStyle: {
                    color: 'rgba(255, 255, 255, 0.3)'
                }
            }
        },
        series: [{
            name: '算法置信度',
            type: 'radar',
            data: [{
                value: values,
                name: '当前预测',
                symbol: 'circle',
                symbolSize: 6,
                lineStyle: {
                    color: '#5470c6',
                    width: 2
                },
                areaStyle: {
                    color: 'rgba(84, 112, 198, 0.3)'
                },
                itemStyle: {
                    color: '#5470c6'
                }
            }]
        }]
    };
    
    chart.setOption(option);
    
    // 响应式
    window.addEventListener('resize', function() {
        chart.resize();
    });
}
