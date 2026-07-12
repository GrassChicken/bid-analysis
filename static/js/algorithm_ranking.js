/**
 * 算法效能排名页面脚本
 */

class AlgorithmRanking {
    constructor() {
        this.currentFilters = {
            location: '',
            days: ''
        };
        this.init();
    }

    async init() {
        await this.loadLocations();
        await this.loadRankingData();
    }

    /**
     * 加载地点列表
     */
    async loadLocations() {
        try {
            const response = await fetch('/api/algorithm/ranking');
            const result = await response.json();
            
            if (!result.success) {
                console.error('加载地点列表失败');
                return;
            }

            const locations = result.data.locations || [];
            const select = document.getElementById('locationFilter');
            
            // 清空现有选项（保留"全部地点"）
            select.innerHTML = '<option value="">全部地点</option>';
            
            // 添加地点选项
            locations.forEach(location => {
                const option = document.createElement('option');
                option.value = location;
                option.textContent = location;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('加载地点列表失败:', error);
        }
    }

    /**
     * 加载排名数据
     */
    async loadRankingData() {
        try {
            const params = new URLSearchParams();
            if (this.currentFilters.location) {
                params.append('location', this.currentFilters.location);
            }
            if (this.currentFilters.days) {
                params.append('days', this.currentFilters.days);
            }

            const response = await fetch(`/api/algorithm/ranking?${params.toString()}`);
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || '加载数据失败');
            }

            // 检查是否有数据
            const hasK1 = result.data.k1_rankings && result.data.k1_rankings.length > 0;
            const hasQ1 = result.data.q1_rankings && result.data.q1_rankings.length > 0;
            
            if (!hasK1 && !hasQ1) {
                document.getElementById('emptyState').style.display = 'block';
                document.getElementById('statsGrid').style.display = 'none';
                document.getElementById('top3Panel').style.display = 'none';
                document.getElementById('rankingPanel').style.display = 'none';
                return;
            }

            // 显示数据
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('statsGrid').style.display = 'grid';
            document.getElementById('top3Panel').style.display = 'block';
            document.getElementById('rankingPanel').style.display = 'block';

            // 渲染数据
            this.renderStats(result.data.summary);
            this.renderTop3(result.data.k1_top3 || [], result.data.q1_top3 || []);
            this.renderRanking(result.data.k1_rankings || [], result.data.q1_rankings || []);
            
        } catch (error) {
            console.error('加载排名数据失败:', error);
            document.getElementById('emptyState').style.display = 'block';
            document.getElementById('emptyState__title').textContent = '加载失败';
            document.getElementById('emptyState__text').textContent = error.message;
        }
    }

    /**
     * 渲染汇总统计
     */
    renderStats(summary) {
        if (!summary) return;
        
        document.getElementById('statTotal').textContent = summary.total_predictions || 0;
        document.getElementById('statBest').textContent = summary.best_k1_algorithm || '-';
        document.getElementById('statBestRate').textContent = 
            (summary.best_k1_hit_rate || 0).toFixed(1) + '%';
        document.getElementById('statAvgRate').textContent = 
            (summary.avg_k1_hit_rate || 0).toFixed(1) + '%';
    }

    /**
     * 渲染 TOP 3 推荐（K1 和 Q1 分开）
     */
    renderTop3(k1Top3, q1Top3) {
        const container = document.getElementById('top3Container');
        
        const renderSection = (top3, paramType, icon) => {
            if (!top3 || top3.length === 0) {
                return `
                    <div class="top3-section">
                        <h4 class="top3-section-title">${icon} ${paramType} TOP 3 推荐</h4>
                        <div class="detail-empty">暂无推荐数据</div>
                    </div>
                `;
            }

            const medals = ['🥇', '🥈', '🥉'];
            const classes = ['gold', 'silver', 'bronze'];

            const cards = top3.map((item, index) => `
                <div class="top3-card top3-card--${classes[index] || 'bronze'}">
                    <div class="top3-badge top3-badge--${classes[index] || 'bronze'}">
                        ${medals[index] || '🏅'}
                    </div>
                    <h3 class="top3-name">${item.name}</h3>
                    <p class="top3-recommendation">${item.recommendation || ''}</p>
                    <div class="top3-stats">
                        <div class="top3-stat">
                            <div class="top3-stat-label">命中率</div>
                            <div class="top3-stat-value top3-stat-value--highlight">
                                ${item.hit_rate.toFixed(1)}%
                            </div>
                        </div>
                        <div class="top3-stat">
                            <div class="top3-stat-label">预测次数</div>
                            <div class="top3-stat-value top3-stat-value--normal">
                                ${item.total}
                            </div>
                        </div>
                        <div class="top3-stat">
                            <div class="top3-stat-label">平均偏差</div>
                            <div class="top3-stat-value">
                                ${item.avg_deviation.toFixed(4)}
                            </div>
                        </div>
                        <div class="top3-stat">
                            <div class="top3-stat-label">综合评分</div>
                            <div class="top3-stat-value">
                                ${item.combined_score.toFixed(1)}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

            return `
                <div class="top3-section">
                    <h4 class="top3-section-title">${icon} ${paramType} TOP 3 推荐算法</h4>
                    <div class="top3-grid">${cards}</div>
                </div>
            `;
        };

        container.innerHTML = renderSection(k1Top3, 'K1', '🎯') + renderSection(q1Top3, 'Q1', '⚙️');
    }

    /**
     * 渲染完整排名表格（K1 和 Q1 分开）
     */
    renderRanking(k1Rankings, q1Rankings) {
        const renderTable = (rankings, paramType, icon, emptyMsg) => {
            if (!rankings || rankings.length === 0) {
                return `
                    <div class="ranking-section">
                        <h4 class="ranking-section-title">${icon} ${paramType} 算法完整排名</h4>
                        <div class="detail-empty">${emptyMsg}</div>
                    </div>
                `;
            }

            const rows = rankings.map(item => {
                const rankClass = item.rank <= 3 ? item.rank : 'other';
                const scoreClass = item.combined_score >= 80 ? 'high' : 
                                  item.combined_score >= 60 ? 'medium' : 'low';
                
                return `
                    <tr>
                        <td>
                            <span class="rank-badge rank-badge--${rankClass}">
                                ${item.rank}
                            </span>
                        </td>
                        <td><strong>${item.name}</strong></td>
                        <td>${item.total}</td>
                        <td>${item.hits}</td>
                        <td>
                            <span class="hit-rate-badge hit-rate-badge--${scoreClass}">
                                ${item.hit_rate.toFixed(1)}%
                            </span>
                        </td>
                        <td>${item.avg_deviation.toFixed(4)}</td>
                        <td>${item.stability.toFixed(1)}%</td>
                        <td>
                            <span class="score-badge score-badge--${scoreClass}">
                                ${item.combined_score.toFixed(1)}
                            </span>
                        </td>
                        <td>
                            <button class="btn-detail" onclick="algorithmRanking.showDetail('${item.name}', '${paramType}')">
                                查看详情
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            return `
                <div class="ranking-section">
                    <h4 class="ranking-section-title">${icon} ${paramType} 算法完整排名</h4>
                    <div class="ranking-table-wrapper">
                        <table class="ranking-table">
                            <thead>
                                <tr>
                                    <th>排名</th>
                                    <th>算法名称</th>
                                    <th>预测次数</th>
                                    <th>命中次数</th>
                                    <th>命中率</th>
                                    <th>平均偏差</th>
                                    <th>稳定性</th>
                                    <th>综合评分</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>
            `;
        };

        const panel = document.getElementById('rankingPanel');
        panel.innerHTML = `
            <div class="ranking-panel__header">
                <div class="ranking-panel__icon">📋</div>
                <div>
                    <h3>完整排名</h3>
                    <p class="ranking-panel__desc">K1 和 Q1 算法分别统计的详细数据</p>
                </div>
            </div>
            <div class="ranking-panel__body">
                ${renderTable(k1Rankings, 'K1', '🎯', '暂无 K1 排名数据')}
                ${renderTable(q1Rankings, 'Q1', '⚙️', '暂无 Q1 排名数据')}
            </div>
        `;
    }

    /**
     * 显示算法详情
     */
    async showDetail(algorithmName, paramType = 'K1') {
        const modal = document.getElementById('algorithmDetailModal');
        const modalTitle = document.getElementById('detailModalTitle');
        const modalBody = document.getElementById('detailModalBody');
        
        modalTitle.textContent = `${algorithmName} - ${paramType} 详细分析`;
        modalBody.innerHTML = `
            <div class="loading">
                <div class="loading-spinner"></div>
                <p>正在加载详细数据...</p>
            </div>
        `;
        
        modal.style.display = 'flex';

        try {
            const params = new URLSearchParams();
            if (this.currentFilters.location) {
                params.append('location', this.currentFilters.location);
            }

            const response = await fetch(
                `/api/algorithm/detail/${encodeURIComponent(algorithmName)}?${params.toString()}`
            );
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || '加载详情失败');
            }

            this.renderDetailModal(result.data, paramType);
            
        } catch (error) {
            console.error('加载详情失败:', error);
            modalBody.innerHTML = `
                <div class="detail-empty">
                    <p>加载失败：${error.message}</p>
                </div>
            `;
        }
    }

    /**
     * 渲染详情模态框
     */
    renderDetailModal(data, paramType = 'K1') {
        const modalBody = document.getElementById('detailModalBody');
        
        const k1Monthly = data.k1_monthly || [];
        const q1Monthly = data.q1_monthly || [];
        const recentRecords = data.recent_records || [];

        // 根据 paramType 决定显示哪个趋势图
        const showK1 = paramType === 'K1' || k1Monthly.length > 0;
        const showQ1 = paramType === 'Q1' || q1Monthly.length > 0;

        modalBody.innerHTML = `
            ${paramType === 'K1' ? `
                <div class="detail-section">
                    <h4>🎯 K1 月度命中率趋势</h4>
                    ${k1Monthly.length > 0 ? this.renderMonthlyChart(k1Monthly, 'k1') : 
                      '<div class="detail-empty">暂无 K1 数据</div>'}
                </div>
            ` : ''}
            
            ${paramType === 'Q1' ? `
                <div class="detail-section">
                    <h4>⚙️ Q1 月度命中率趋势</h4>
                    ${q1Monthly.length > 0 ? this.renderMonthlyChart(q1Monthly, 'q1') : 
                      '<div class="detail-empty">暂无 Q1 数据</div>'}
                </div>
            ` : ''}
            
            <div class="detail-section">
                <h4>📋 最近预测记录（最多20条）</h4>
                ${recentRecords.length > 0 ? this.renderRecentRecords(recentRecords, paramType) : 
                  '<div class="detail-empty">暂无预测记录</div>'}
            </div>
        `;
    }

    /**
     * 渲染月度趋势图
     */
    renderMonthlyChart(monthlyData, type) {
        const maxHitRate = Math.max(...monthlyData.map(d => d.hit_rate));
        
        return `
            <div class="monthly-chart">
                ${monthlyData.map(item => {
                    const barHeight = (item.hit_rate / (maxHitRate || 1)) * 100;
                    const color = item.hit_rate >= 80 ? '#27ae60' : 
                                 item.hit_rate >= 60 ? '#f39c12' : '#e74c3c';
                    
                    return `
                        <div class="month-item">
                            <div class="month-label">${item.month}</div>
                            <div class="month-bar-wrapper">
                                <div class="month-value" style="color: ${color};">
                                    ${item.hit_rate.toFixed(1)}%
                                </div>
                                <div class="month-bar" style="height: ${barHeight}px; background: ${color};"></div>
                                <div class="month-count">${item.hits}/${item.total}</div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    /**
     * 渲染最近记录
     */
    renderRecentRecords(records, paramType = 'K1') {
        // 根据 paramType 决定显示哪列偏差
        const showK1 = paramType === 'K1';
        const deviationLabel = showK1 ? 'K1偏差' : 'Q1偏差';
        
        return `
            <table class="detail-table">
                <thead>
                    <tr>
                        <th>项目名称</th>
                        <th>预测时间</th>
                        <th>地点</th>
                        <th>${deviationLabel}</th>
                    </tr>
                </thead>
                <tbody>
                    ${records.map(record => {
                        const deviation = showK1 ? record.k1_deviation : record.q1_deviation;
                        const threshold = showK1 ? 0.005 : 0.05;
                        const warningThreshold = showK1 ? 0.01 : 0.1;
                        
                        const color = deviation === null ? '#999' :
                                     deviation <= threshold ? '#27ae60' : 
                                     deviation <= warningThreshold ? '#f39c12' : '#e74c3c';
                        
                        return `
                            <tr>
                                <td>${record.project_name || '-'}</td>
                                <td>${record.prediction_time || '-'}</td>
                                <td>${record.location || '-'}</td>
                                <td style="color: ${color};">
                                    ${deviation !== null ? deviation.toFixed(4) : '-'}
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;
    }
}

// 全局实例
let algorithmRanking;

// 筛选功能
function applyFilters() {
    const locationSelect = document.getElementById('locationFilter');
    const daysSelect = document.getElementById('timeRangeFilter');
    
    algorithmRanking.currentFilters.location = locationSelect.value;
    algorithmRanking.currentFilters.days = daysSelect.value;
    
    algorithmRanking.loadRankingData();
}

function resetFilters() {
    document.getElementById('locationFilter').value = '';
    document.getElementById('timeRangeFilter').value = '';
    
    algorithmRanking.currentFilters = { location: '', days: '' };
    
    algorithmRanking.loadRankingData();
}

function closeDetailModal() {
    document.getElementById('algorithmDetailModal').style.display = 'none';
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    algorithmRanking = new AlgorithmRanking();
    
    // 点击遮罩层关闭模态框
    document.getElementById('algorithmDetailModal').addEventListener('click', (e) => {
        if (e.target.id === 'algorithmDetailModal') {
            closeDetailModal();
        }
    });
});
