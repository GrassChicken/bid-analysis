// 仪表盘图表 - 通过 API 获取数据
(function() {
    'use strict';

    // 页面加载后获取数据并渲染图表
    document.addEventListener('DOMContentLoaded', function() {
        fetch('/api/dashboard/stats', { credentials: 'same-origin' })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (!data.success) return;

                var methodDist = data.bid_stats.method_distribution || {};
                var k1Dist = data.bid_stats.k1_distribution || {};

                // 方法类别分布图
                var ctx1 = document.getElementById('distributionChart');
                if (ctx1) {
                    new Chart(ctx1.getContext('2d'), {
                        type: 'bar',
                        data: {
                            labels: Object.keys(methodDist),
                            datasets: [{
                                label: '方法类别分布',
                                data: Object.values(methodDist),
                                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                                borderColor: 'rgba(102, 126, 234, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: { precision: 0 }
                                }
                            }
                        }
                    });
                }
            })
            .catch(function(err) {
                console.error('仪表盘数据加载失败:', err);
            });
    });
})();
