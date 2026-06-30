var allData = [];
        var filteredData = [];
        var displayedData = [];
        var charts = {};
        var currentPage = 1;
        var rowsPerPage = 50;
        var selectedIds = new Set();

        // 列过滤器状态
        var columnFilters = {};

        // 页面加载检查登录（统一入口）
        checkLoginStatus();

        function checkLoginStatus() {
            fetch('/api/auth/check-login')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (!data.logged_in) {
                        window.location.href = '/login';
                        return;
                    }
                    loadData();
                })
                .catch(function(error) {
                    console.error('检查登录状态失败:', error);
                    // 网络错误也可能是会话过期，跳转到登录页
                    window.location.href = '/login';
                });
        }

        // 带 401 处理的 fetch
        function fetchWithAuth(url, options) {
            return fetch(url, options)
                .then(function(response) {
                    if (response.status === 401) {
                        showModal('warning', '登录过期', '登录信息已过期，请重新登录', function() {
                            window.location.href = '/login';
                        });
                        return null;
                    }
                    return response.json();
                })
                .catch(function(error) {
                    console.error('API 请求失败:', error);
                    showModal('warning', '网络错误', '请刷新重试');
                    return null;
                });
        }

        // 加载数据
        function loadData() {
            fetchWithAuth('/api/data/list')
                .then(function(data) {
                    if (!data || !data.success) return;
                    allData = data.records;
                    filteredData = allData;
                    displayedData = allData;
                    updateStats();
                    initLocationSelect(data.locations);
                    renderPage();
                    renderPagination();
                    renderCharts();
                    if (allData.length > 0) {
                        document.getElementById('chartsSection').classList.remove('hidden');
                    }
                });
        }

        // 更新统计
        function updateStats() {
            document.getElementById('totalRecords').textContent = allData.length;
            var projects = {};
            var method1 = 0, method2 = 0;
            allData.forEach(function(r) {
                projects[r.project_name] = true;
                if (r.method_category == '1') method1++;
                else if (r.method_category == '2') method2++;
            });
            document.getElementById('totalProjects').textContent = Object.keys(projects).length;
            document.getElementById('method1Count').textContent = method1;
            document.getElementById('method2Count').textContent = method2;
        }

        // 初始化地点下拉
        function initLocationSelect(locations) {
            var select = document.getElementById('locationFilter');
            select.innerHTML = '<option value="">全部地点</option>';
            locations.forEach(function(loc) {
                var option = document.createElement('option');
                option.value = loc;
                option.textContent = loc;
                select.appendChild(option);
            });
        }

        // 应用所有过滤条件（顶部全局过滤器 + 列过滤器）
        function applyFilters() {
            var baseData = allData;

            // 顶部全局过滤：地点
            var locationValue = document.getElementById('locationFilter').value;
            if (locationValue) {
                baseData = baseData.filter(function(r) { return r.bid_location === locationValue; });
            }

            // 顶部全局过滤：方法类别
            var methodValue = document.getElementById('methodFilter').value;
            if (methodValue) {
                baseData = baseData.filter(function(r) { return r.method_category === methodValue; });
            }

            // 顶部全局过滤：日期范围
            var dateFrom = document.getElementById('dateFromFilter').value;
            var dateTo = document.getElementById('dateToFilter').value;
            if (dateFrom) {
                baseData = baseData.filter(function(r) { return r.bid_date >= dateFrom; });
            }
            if (dateTo) {
                baseData = baseData.filter(function(r) { return r.bid_date <= dateTo; });
            }

            // 列过滤器
            if (columnFilters.project) {
                baseData = baseData.filter(function(r) { return (r.project_name || '').toLowerCase().indexOf(columnFilters.project.toLowerCase()) !== -1; });
            }
            if (columnFilters.date) {
                baseData = baseData.filter(function(r) { return r.bid_date === columnFilters.date; });
            }
            if (columnFilters.time) {
                baseData = baseData.filter(function(r) { return (r.bid_time || '').indexOf(columnFilters.time) !== -1; });
            }
            if (columnFilters.location) {
                baseData = baseData.filter(function(r) { return (r.bid_location || '').toLowerCase().indexOf(columnFilters.location.toLowerCase()) !== -1; });
            }
            if (columnFilters.method) {
                baseData = baseData.filter(function(r) { return r.method_category === columnFilters.method; });
            }
            if (columnFilters.k2) {
                baseData = baseData.filter(function(r) { return (r.k2_value || '').indexOf(columnFilters.k2) !== -1; });
            }
            if (columnFilters.k1) {
                baseData = baseData.filter(function(r) { return (r.k1_value || '').indexOf(columnFilters.k1) !== -1; });
            }
            if (columnFilters.q1) {
                baseData = baseData.filter(function(r) { return (r.q1_value || '').indexOf(columnFilters.q1) !== -1; });
            }
            if (columnFilters.import) {
                baseData = baseData.filter(function(r) { return (r.import_time || '').toLowerCase().indexOf(columnFilters.import.toLowerCase()) !== -1; });
            }

            filteredData = baseData;
            displayedData = filteredData;
            currentPage = 1;
            renderPage();
            renderPagination();
            renderCharts();
            updateFilterIndicators();
        }

        // 应用列过滤器
        function applyColumnFilters() {
            columnFilters.project = document.getElementById('fProject').value;
            columnFilters.date = document.getElementById('fDate').value;
            columnFilters.time = document.getElementById('fTime').value;
            columnFilters.location = document.getElementById('fLocation').value;
            columnFilters.method = document.getElementById('fMethod').value;
            columnFilters.k2 = document.getElementById('fK2').value;
            columnFilters.k1 = document.getElementById('fK1').value;
            columnFilters.q1 = document.getElementById('fQ1').value;
            columnFilters.import = document.getElementById('fImport').value;

            // 清理空值
            for (var key in columnFilters) {
                if (columnFilters[key] === '' || columnFilters[key] === null) {
                    delete columnFilters[key];
                }
            }

            applyFilters();
        }

        // 重置所有过滤条件
        function resetAllFilters() {
            // 重置顶部全局过滤器
            document.getElementById('locationFilter').value = '';
            document.getElementById('methodFilter').value = '';
            document.getElementById('dateFromFilter').value = '';
            document.getElementById('dateToFilter').value = '';

            // 重置列过滤器
            document.getElementById('fProject').value = '';
            document.getElementById('fDate').value = '';
            document.getElementById('fTime').value = '';
            document.getElementById('fLocation').value = '';
            document.getElementById('fMethod').value = '';
            document.getElementById('fK2').value = '';
            document.getElementById('fK1').value = '';
            document.getElementById('fQ1').value = '';
            document.getElementById('fImport').value = '';

            columnFilters = {};
            applyFilters();
        }

        // 更新过滤指示器（高亮有过滤条件的列输入框）
        function updateFilterIndicators() {
            var filterIds = ['fProject', 'fDate', 'fTime', 'fLocation', 'fMethod', 'fK2', 'fK1', 'fQ1', 'fImport'];
            filterIds.forEach(function(id) {
                var el = document.getElementById(id);
                if (el) {
                    if (el.value) {
                        el.classList.add('active');
                    } else {
                        el.classList.remove('active');
                    }
                }
            });
        }

        // 渲染页面（统一使用表格显示，手机端横向滚动）
        function renderPage() {
            var tbody = document.getElementById('tableBody');
            var emptyState = document.getElementById('dataEmptyState');
            var tableWrapper = document.querySelector('.table-wrapper');

            // 空数据状态
            if (allData.length === 0) {
                if (tableWrapper) tableWrapper.style.display = 'none';
                emptyState.style.display = 'block';
                return;
            }

            if (tableWrapper) tableWrapper.style.display = 'block';
            emptyState.style.display = 'none';

            var start = (currentPage - 1) * rowsPerPage;
            var end = Math.min(start + rowsPerPage, displayedData.length);
            var pageRows = displayedData.slice(start, end);

            if (pageRows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="12" style="text-align:center;padding:40px;color:#999;">🔍 没有匹配的数据，请调整过滤条件</td></tr>';
            } else {
                tbody.innerHTML = pageRows.map(function(r, index) {
                    var actualIndex = start + index;
                    var isChecked = selectedIds.has(r.id) ? 'checked' : '';
                    var projectNameEsc = (r.project_name || '').replace(/'/g, "\\'");
                    return '<tr class="' + (isChecked ? 'selected' : '') + '" data-id="' + r.id + '">' +
                        '<td class="checkbox-cell"><input type="checkbox" class="row-checkbox" data-id="' + r.id + '" ' + isChecked + ' onchange="toggleSelection(' + r.id + ')"></td>' +
                        '<td>' + (actualIndex + 1) + '</td>' +
                        '<td title="' + (r.project_name || '') + '">' + (r.project_name || '') + '</td>' +
                        '<td>' + (r.bid_date || '') + '</td>' +
                        '<td>' + (r.bid_time || '') + '</td>' +
                        '<td>' + (r.bid_location || '') + '</td>' +
                        '<td>' + (r.method_category || '') + '</td>' +
                        '<td>' + (r.k2_value || '') + '</td>' +
                        '<td>' + (r.k1_value || '') + '</td>' +
                        '<td>' + (r.q1_value || '') + '</td>' +
                        '<td>' + (r.import_time || '') + '</td>' +
                        '<td class="action-cell"><button class="btn btn-danger btn-sm" onclick="deleteSingleRecord(' + r.id + ', \'' + projectNameEsc + '\')">🗑️ 删除</button></td>' +
                    '</tr>';
                }).join('');
            }

            updateBatchActions();
            updateDataInfo();
            syncSelectAllState();
        }

        function updateDataInfo() {
            var start = (currentPage - 1) * rowsPerPage + 1;
            var end = Math.min(currentPage * rowsPerPage, displayedData.length);
            var info = '共 ' + displayedData.length + ' 行数据';
            var locationValue = document.getElementById('locationFilter').value;
            var methodValue = document.getElementById('methodFilter').value;
            if (locationValue) info += '（已按地点过滤）';
            if (methodValue) info += '（已按方法过滤）';
            if (displayedData.length > 0) {
                info += '，显示第 ' + start + '-' + end + ' 行';
            }
            document.getElementById('dataInfo').textContent = info;
        }

        // 分页
        function renderPagination() {
            var totalPages = Math.ceil(displayedData.length / rowsPerPage);
            var pagination = document.getElementById('pagination');
            if (totalPages <= 1) { pagination.innerHTML = ''; return; }
            var html = '<button ' + (currentPage === 1 ? 'disabled' : '') + ' onclick="changePage(' + (currentPage - 1) + ')">⏮ 上一页</button>' +
                '<span>第 ' + currentPage + ' / ' + totalPages + ' 页</span>' +
                '<button ' + (currentPage === totalPages ? 'disabled' : '') + ' onclick="changePage(' + (currentPage + 1) + ')">下一页 ⏭</button>';
            pagination.innerHTML = html;
        }

        function changePage(page) {
            var totalPages = Math.ceil(displayedData.length / rowsPerPage);
            if (page < 1 || page > totalPages) return;
            currentPage = page;
            renderPage();
            renderPagination();
        }

        // 选择功能
        function toggleSelection(id) {
            if (selectedIds.has(id)) { selectedIds.delete(id); }
            else { selectedIds.add(id); }
            updateRowStyle(id);
            updateBatchActions();
            syncSelectAllState();
        }

        function updateRowStyle(id) {
            var row = document.querySelector('tr[data-id="' + id + '"]');
            if (row) {
                if (selectedIds.has(id)) {
                    row.classList.add('selected');
                    row.querySelector('.row-checkbox').checked = true;
                } else {
                    row.classList.remove('selected');
                    row.querySelector('.row-checkbox').checked = false;
                }
            }
        }

        function toggleSelectAll() {
            // 获取当前页所有行复选框
            var checkboxes = document.querySelectorAll('.row-checkbox');
            if (checkboxes.length === 0) return;
            
            // 判断当前页是否全部选中
            var allChecked = true;
            checkboxes.forEach(function(cb) {
                var id = parseInt(cb.getAttribute('data-id'));
                if (!selectedIds.has(id)) {
                    allChecked = false;
                }
            });
            
            // 如果全部选中，则取消；否则全选
            var shouldCheck = !allChecked;
            
            // 更新选中状态
            checkboxes.forEach(function(cb) {
                var id = parseInt(cb.getAttribute('data-id'));
                if (shouldCheck) {
                    selectedIds.add(id);
                } else {
                    selectedIds.delete(id);
                }
                cb.checked = shouldCheck;
            });
            
            // 更新全选复选框状态
            var selectAll = document.getElementById('selectAllCheckbox');
            if (selectAll) selectAll.checked = shouldCheck;
            
            // 更新行的选中样式
            var rows = document.querySelectorAll('#tableBody tr');
            rows.forEach(function(row) {
                var checkbox = row.querySelector('.row-checkbox');
                if (checkbox) {
                    var rowId = parseInt(checkbox.getAttribute('data-id'));
                    if (selectedIds.has(rowId)) {
                        row.classList.add('selected');
                    } else {
                        row.classList.remove('selected');
                    }
                }
            });
            
            updateBatchActions();
        }
        
        // 同步全选框状态（根据当前页选中情况）
        function syncSelectAllState() {
            var selectAll = document.getElementById('selectAllCheckbox');
            if (!selectAll) return;
            
            var checkboxes = document.querySelectorAll('.row-checkbox');
            if (checkboxes.length === 0) {
                selectAll.checked = false;
                return;
            }
            
            var allChecked = true;
            checkboxes.forEach(function(cb) {
                var id = parseInt(cb.getAttribute('data-id'));
                if (!selectedIds.has(id)) {
                    allChecked = false;
                }
            });
            
            selectAll.checked = allChecked;
        }

        function updateBatchActions() {
            // 删除按钮始终可用，点击时检查是否有选中
            var deleteBtn = document.getElementById('deleteSelectedBtn');
            if (deleteBtn) {
                deleteBtn.disabled = false;
            }
        }

        // 导出
        function exportData() {
            var dataToExport = filteredData.length > 0 ? filteredData : allData;
            if (dataToExport.length === 0) {
                showModal('warning', '暂无数据', '暂无数据可导出');
                return;
            }
            showModal('confirm', '📥 确认导出',
                '确定要导出 <strong>' + dataToExport.length + '</strong> 条记录吗？<br><br>' +
                (filteredData.length > 0 ? '<span style="color: #f39c12;">⚠️ 当前有过滤条件，仅导出过滤后的数据</span><br>' : '') +
                '<span style="color: #27ae60;">✅ 导出格式：Excel (.xlsx)</span>',
                function() {
                    var payload = {
                        exportFiltered: filteredData.length > 0,
                        filteredIds: filteredData.length > 0 ? filteredData.map(function(item) { return item.id; }) : []
                    };
                    fetchWithAuth('/api/data/export', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    })
                    .then(function(data) {
                        if (!data) return;
                        if (data.success) {
                            fetch('/api/data/download/' + encodeURIComponent(data.filename))
                                .then(function(response) { return response.blob(); })
                                .then(function(blob) {
                                    var url = URL.createObjectURL(blob);
                                    var a = document.createElement('a');
                                    a.href = url;
                                    a.download = data.filename;
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    URL.revokeObjectURL(url);
                                    showModal('success', '✅ 导出成功', '共导出 ' + data.count + ' 条记录<br>文件已自动下载');
                                });
                        } else {
                            showModal('error', '❌ 导出失败', data.error || '导出过程中发生错误');
                        }
                    });
                }
            );
        }

        // 模态框
        function showModal(type, title, content, onConfirm) {
            var modal = document.getElementById('confirmModal');
            var modalTitle = document.getElementById('modalTitle');
            var modalContent = document.getElementById('modalContent');
            var modalIcon = document.getElementById('modalIcon');
            var confirmBtn = document.getElementById('modalConfirmBtn');
            var cancelBtn = document.getElementById('modalCancelBtn');

            if (!modal) {
                console.error('模态框未找到');
                return;
            }

            confirmBtn.onclick = null;
            cancelBtn.onclick = null;

            modalTitle.textContent = title;
            modalContent.innerHTML = content;
            modalContent.classList.remove('multi-modal-content');

            var iconMap = { 'warning': '⚠️', 'error': '❌', 'success': '✅', 'confirm': '🔔', 'info': 'ℹ️' };
            modalIcon.textContent = iconMap[type] || 'ℹ️';

            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';

            switch(type) {
                case 'info': case 'success': case 'warning': case 'error':
                    cancelBtn.style.display = 'none';
                    confirmBtn.textContent = '确定';
                    confirmBtn.onclick = function() { hideModal(); };
                    break;
                case 'confirm':
                    cancelBtn.style.display = 'inline-block';
                    confirmBtn.textContent = '确定';
                    confirmBtn.onclick = function() {
                        if (onConfirm) onConfirm();
                        hideModal();
                    };
                    cancelBtn.onclick = function() { hideModal(); };
                    break;
            }
        }

        function hideModal() {
            var modal = document.getElementById('confirmModal');
            if (modal) {
                modal.style.display = 'none';
            }
            document.body.style.overflow = 'auto';
        }

        // 删除单条
        function deleteSingleRecord(id, projectName) {
            showModal('confirm', '⚠️ 删除确认',
                '确定要删除这条记录吗？<br><br>' +
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">' +
                '<strong>📋 项目：' + projectName + '</strong>' +
                '</div>' +
                '<span style="color: #e74c3c;">⚠️ 此操作不可恢复。</span>',
                function() {
                    fetchWithAuth('/api/data/delete', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({id: id})
                    })
                    .then(function(data) {
                        if (!data) return;
                        if (data.success) {
                            showModal('success', '✅ 删除成功', '记录已删除');
                            selectedIds.delete(id);
                            loadData();
                        } else {
                            showModal('error', '❌ 删除失败', '删除失败：' + (data.error || '未知错误'));
                        }
                    });
                }
            );
        }

        // 批量删除
        function deleteSelected() {
            if (selectedIds.size === 0) {
                showModal('warning', '提示', '请先选择要删除的记录');
                return;
            }
            showModal('confirm', '⚠️ 批量删除确认',
                '确定要删除选中的 <strong>' + selectedIds.size + '</strong> 条记录吗？<br><br>' +
                '<span style="color: #e74c3c;">⚠️ 此操作不可恢复。</span>',
                function() {
                    var ids = Array.from(selectedIds);
                    fetchWithAuth('/api/data/delete-batch', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ids: ids})
                    })
                    .then(function(data) {
                        if (!data) return;
                        if (data.success) {
                            showModal('success', '✅ 删除成功', '已删除 ' + data.deleted_count + ' 条记录');
                            selectedIds.clear();
                            loadData();
                        } else {
                            showModal('error', '❌ 删除失败', '删除失败：' + (data.error || '未知错误'));
                        }
                    });
                }
            );
        }

        // 清空全部（二次确认）
        function clearAllData() {
            if (allData.length === 0) {
                showModal('warning', '提示', '暂无数据');
                return;
            }
            showModal('confirm', '⚠️ 高危操作提示',
                '确定要清空 <strong>所有</strong> 数据记录吗？<br><br>' +
                '<div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 15px 0;">' +
                '<strong>📊 当前共有 ' + allData.length + ' 条记录</strong><br><br>' +
                '<span style="color: #e74c3c;">⚠️ 此操作不可恢复！</span>' +
                '</div>' +
                '请谨慎操作，建议先导出数据备份。',
                function() {
                    hideModal();
                    setTimeout(function() {
                        showModal('confirm', '⚠️ 再次确认',
                            '<div style="background: #f8d7da; padding: 15px; border-radius: 8px;">' +
                            '<strong>这是最后一次确认！</strong><br><br>' +
                            '你确定要删除所有 <strong style="color: #e74c3c; font-size: 1.2em;">' + allData.length + '</strong> 条数据记录吗？' +
                            '</div>',
                            function() {
                                fetchWithAuth('/api/data/clear', { method: 'POST' })
                                .then(function(data) {
                                    if (!data) return;
                                    if (data.success) {
                                        showModal('success', '✅ 清空成功', '已清空 ' + data.deleted_count + ' 条数据记录');
                                        selectedIds.clear();
                                        loadData();
                                    } else {
                                        showModal('error', '❌ 清空失败', '清空失败：' + (data.error || '未知错误'));
                                    }
                                });
                            }
                        );
                    }, 100);
                }
            );
        }

        // 刷新数据
        function refreshData() {
            // 保存当前过滤条件
            var savedFilters = {
                location: document.getElementById('locationFilter').value,
                method: document.getElementById('methodFilter').value,
                dateFrom: document.getElementById('dateFromFilter').value,
                dateTo: document.getElementById('dateToFilter').value,
                column: JSON.parse(JSON.stringify(columnFilters))
            };

            // 重新加载数据
            fetchWithAuth('/api/data/list')
                .then(function(data) {
                    if (!data || !data.success) return;
                    allData = data.records;
                    filteredData = allData;
                    displayedData = allData;
                    updateStats();
                    initLocationSelect(data.locations);
                    if (allData.length > 0) {
                        document.getElementById('chartsSection').classList.remove('hidden');
                    }

                    // 恢复过滤条件
                    document.getElementById('locationFilter').value = savedFilters.location;
                    document.getElementById('methodFilter').value = savedFilters.method;
                    document.getElementById('dateFromFilter').value = savedFilters.dateFrom;
                    document.getElementById('dateToFilter').value = savedFilters.dateTo;

                    // 恢复列过滤器
                    var fProject = document.getElementById('fProject');
                    var fDate = document.getElementById('fDate');
                    var fLocation = document.getElementById('fLocation');
                    var fMethod = document.getElementById('fMethod');
                    var fK2 = document.getElementById('fK2');
                    var fK1 = document.getElementById('fK1');
                    var fQ1 = document.getElementById('fQ1');
                    var fImport = document.getElementById('fImport');

                    if (fProject) fProject.value = savedFilters.column.project || '';
                    if (fDate) fDate.value = savedFilters.column.date || '';
                    if (fLocation) fLocation.value = savedFilters.column.location || '';
                    if (fMethod) fMethod.value = savedFilters.column.method || '';
                    if (fK2) fK2.value = savedFilters.column.k2 || '';
                    if (fK1) fK1.value = savedFilters.column.k1 || '';
                    if (fQ1) fQ1.value = savedFilters.column.q1 || '';
                    if (fImport) fImport.value = savedFilters.column.import || '';

                    columnFilters = savedFilters.column;
                    applyFilters();
                });
        }

        // 图表
        function renderCharts() {
            if (displayedData.length === 0) return;
            renderMethodChart();
            renderK2Chart();
            renderK1Chart();
            renderQ1Chart();
        }

        function renderMethodChart() {
            var ctx = document.getElementById('methodChart');
            if (!ctx) return;
            ctx = ctx.getContext('2d');
            if (charts.method) charts.method.destroy();
            var method1 = displayedData.filter(function(r) { return r.method_category == '1'; }).length;
            var method2 = displayedData.filter(function(r) { return r.method_category == '2'; }).length;
            var total = method1 + method2;
            charts.method = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['方法 1 类', '方法 2 类'],
                    datasets: [{ data: [method1, method2], backgroundColor: ['#3498db', '#e74c3c'] }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' },
                        title: { display: true, text: '方法类别分布' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    var label = context.label || '';
                                    var value = context.parsed || 0;
                                    var percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return label + ': ' + value + '条 (' + percentage + '%)';
                                }
                            }
                        }
                    }
                }
            });
        }

        function renderK2Chart() {
            var ctx = document.getElementById('k2Chart');
            if (!ctx) return;
            ctx = ctx.getContext('2d');
            if (charts.k2) charts.k2.destroy();
            var k2Values = displayedData.filter(function(r) { return r.k2_value; }).map(function(r) { return parseFloat(r.k2_value); });
            var totalCount = displayedData.length;
            var bins = {};
            k2Values.forEach(function(v) { var bin = v.toFixed(2); bins[bin] = (bins[bin] || 0) + 1; });
            var labels = Object.keys(bins).sort();
            var data = labels.map(function(l) { return bins[l]; });
            charts.k2 = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{ label: '出现次数', data: data, backgroundColor: '#3498db' }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        title: { display: true, text: 'K2 值分布' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    var value = context.parsed.y || 0;
                                    var percentage = totalCount > 0 ? ((value / totalCount) * 100).toFixed(1) : 0;
                                    return '数量: ' + value + '条 (占比: ' + percentage + '%)';
                                }
                            }
                        }
                    },
                    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
                }
            });
        }

        function renderK1Chart() {
            var ctx = document.getElementById('k1Chart');
            if (!ctx) return;
            ctx = ctx.getContext('2d');
            if (charts.k1) charts.k1.destroy();
            var k1Values = displayedData.filter(function(r) { return r.k1_value; }).map(function(r) { return parseFloat(r.k1_value); });
            var totalCount = displayedData.length;
            var bins = {};
            k1Values.forEach(function(v) { var bin = v.toFixed(3); bins[bin] = (bins[bin] || 0) + 1; });
            var labels = Object.keys(bins).sort();
            var data = labels.map(function(l) { return bins[l]; });
            charts.k1 = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{ label: '出现次数', data: data, backgroundColor: '#2ecc71' }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        title: { display: true, text: 'K1 值分布' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    var value = context.parsed.y || 0;
                                    var percentage = totalCount > 0 ? ((value / totalCount) * 100).toFixed(1) : 0;
                                    return '数量: ' + value + '条 (占比: ' + percentage + '%)';
                                }
                            }
                        }
                    },
                    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
                }
            });
        }

        function renderQ1Chart() {
            var ctx = document.getElementById('q1Chart');
            if (!ctx) return;
            ctx = ctx.getContext('2d');
            if (charts.q1) charts.q1.destroy();
            var q1Values = displayedData.filter(function(r) { return r.q1_value; }).map(function(r) { return parseFloat(r.q1_value); });
            var totalCount = displayedData.length;
            var bins = {};
            q1Values.forEach(function(v) { var bin = v.toFixed(2); bins[bin] = (bins[bin] || 0) + 1; });
            var labels = Object.keys(bins).sort();
            var data = labels.map(function(l) { return bins[l]; });
            charts.q1 = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{ label: '出现次数', data: data, backgroundColor: '#9b59b6' }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        title: { display: true, text: 'Q1 值分布' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    var value = context.parsed.y || 0;
                                    var percentage = totalCount > 0 ? ((value / totalCount) * 100).toFixed(1) : 0;
                                    return '数量: ' + value + '条 (占比: ' + percentage + '%)';
                                }
                            }
                        }
                    },
                    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
                }
            });
        }

        // 文件上传
        var uploadArea = document.getElementById('uploadArea');
        var fileInput = document.getElementById('fileInput');

        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
        });

        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) handleFile(e.target.files[0]);
        });

        function handleFile(file) {
            if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
                showModal('error', '文件格式错误', '请上传 Excel 文件（.xlsx 或 .xls）');
                return;
            }

            var formData = new FormData();
            formData.append('file', file);

            var progressSection = document.getElementById('progressSection');
            var progressBar = document.getElementById('progressBar');
            var progressPercent = document.getElementById('progressPercent');
            var progressStatus = document.getElementById('progressStatus');
            var progressText = document.getElementById('progressText');

            progressSection.classList.remove('hidden');
            progressBar.style.width = '0%';
            progressPercent.textContent = '0%';
            progressStatus.textContent = '📊 正在上传文件...';
            progressText.textContent = '文件大小：' + (file.size / 1024).toFixed(2) + ' KB';

            // 模拟进度
            var simulatedProgress = 0;
            var progressInterval = setInterval(function() {
                if (simulatedProgress < 80) {
                    simulatedProgress += 5;
                    progressBar.style.width = simulatedProgress + '%';
                    progressPercent.textContent = simulatedProgress + '%';
                    progressText.textContent = '正在上传并解析文件...';
                }
            }, 200);

            fetchWithAuth('/api/data/import', { method: 'POST', body: formData })
            .then(function(data) {
                clearInterval(progressInterval);
                if (!data) { progressSection.classList.add('hidden'); return; }

                if (data.success) {
                    progressBar.style.width = '100%';
                    progressPercent.textContent = '100%';
                    progressStatus.textContent = '✅ 导入完成！';
                    progressText.textContent = '共处理 ' + data.imported_count + ' 条记录';

                    setTimeout(function() {
                        progressSection.classList.add('hidden');
                        showImportResult(data);
                    }, 1000);

                    loadData();
                } else {
                    progressBar.style.width = '0%';
                    progressPercent.textContent = '0%';
                    progressStatus.textContent = '❌ 导入失败';
                    progressText.textContent = data.error || '导入过程中发生错误';
                    setTimeout(function() { progressSection.classList.add('hidden'); }, 2000);
                    showImportError(data.error || '导入过程中发生错误，请检查文件格式');
                }
            })
            .catch(function(error) {
                clearInterval(progressInterval);
                progressBar.style.width = '0%';
                progressPercent.textContent = '0%';
                progressStatus.textContent = '❌ 网络错误';
                progressText.textContent = '请稍后重试';
                setTimeout(function() { progressSection.classList.add('hidden'); }, 2000);
            });
        }

        // 显示导入结果（多模态框：成功 + 警告详情）
        function showImportResult(data) {
            var importCount = data.imported_count || 0;
            var updateCount = data.updated_count || 0;
            var insertCount = data.inserted_count || 0;
            var warningCount = data.warning_count || 0;
            var warnings = data.validation_warnings || [];

            // 构建导入概览
            var summaryHtml = '<div class="import-summary">';
            summaryHtml += '<div class="summary-item summary-success">';
            summaryHtml += '<span class="summary-icon">✅</span>';
            summaryHtml += '<span>成功导入 <strong>' + importCount + '</strong> 条记录</span>';
            summaryHtml += '</div>';
            if (insertCount > 0) {
                summaryHtml += '<div class="summary-item summary-info">';
                summaryHtml += '<span class="summary-icon">🆕</span>';
                summaryHtml += '<span>新增 <strong>' + insertCount + '</strong> 条</span>';
                summaryHtml += '</div>';
            }
            if (updateCount > 0) {
                summaryHtml += '<div class="summary-item summary-info">';
                summaryHtml += '<span class="summary-icon">🔄</span>';
                summaryHtml += '<span>更新 <strong>' + updateCount + '</strong> 条（项目名称已存在）</span>';
                summaryHtml += '</div>';
            }
            summaryHtml += '</div>';

            if (warningCount > 0) {
                // 有警告：显示多模态（概览 + 可展开的警告列表）
                var modalHtml = '<div class="import-result-modal">';
                modalHtml += summaryHtml;
                modalHtml += '<div class="warning-section">';
                modalHtml += '<div class="warning-header" onclick="toggleWarningList()">';
                modalHtml += '<span>⚠️ 发现 <strong>' + warningCount + '</strong> 条校验警告（不影响导入）</span>';
                modalHtml += '<span class="warning-arrow" id="warningArrow">▼</span>';
                modalHtml += '</div>';
                modalHtml += '<div class="warning-list" id="warningList">';
                warnings.forEach(function(w) {
                    modalHtml += '<div class="warning-item">' + w + '</div>';
                });
                modalHtml += '</div>';
                modalHtml += '<p class="warning-note">注：数据已正常导入，请检查上述参数值是否正确。</p>';
                modalHtml += '</div>';
                modalHtml += '</div>';

                showMultiModal('⚠️ 导入完成（含警告）', modalHtml, 'warning');
            } else {
                // 无警告：简单成功提示
                showMultiModal('✅ 导入成功', summaryHtml, 'success');
            }
        }

        // 显示导入错误
        function showImportError(errorMsg) {
            var errorHtml = '<div class="import-error">';
            errorHtml += '<div class="error-icon">❌</div>';
            errorHtml += '<div class="error-message">' + errorMsg + '</div>';
            errorHtml += '<p class="error-hint">请检查文件格式是否正确，或联系管理员。</p>';
            errorHtml += '</div>';
            showMultiModal('❌ 导入失败', errorHtml, 'error');
        }

        // 多模态框（移动端适配）
        function showMultiModal(title, contentHtml, type) {
            var modal = document.getElementById('confirmModal');
            var modalTitle = document.getElementById('modalTitle');
            var modalContent = document.getElementById('modalContent');
            var modalIcon = document.getElementById('modalIcon');
            var confirmBtn = document.getElementById('modalConfirmBtn');
            var cancelBtn = document.getElementById('modalCancelBtn');

            if (!modal) {
                console.error('模态框未找到');
                return;
            }

            var iconMap = { 'warning': '⚠️', 'error': '❌', 'success': '✅' };
            modalIcon.textContent = iconMap[type] || 'ℹ️';
            modalTitle.textContent = title;
            modalContent.innerHTML = contentHtml;
            modalContent.classList.add('multi-modal-content');

            cancelBtn.style.display = 'none';
            confirmBtn.textContent = '我知道了';
            confirmBtn.onclick = function() { hideModal(); };

            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }

        // 切换警告列表展开/折叠
        function toggleWarningList() {
            var list = document.getElementById('warningList');
            var arrow = document.getElementById('warningArrow');
            if (!list || !arrow) return;
            var currentDisplay = window.getComputedStyle(list).display;
            if (currentDisplay === 'none') {
                list.style.display = 'block';
                arrow.style.transform = 'rotate(0deg)';
            } else {
                list.style.display = 'none';
                arrow.style.transform = 'rotate(-90deg)';
            }
        }

        // 下载模板
        function downloadTemplate() {
            fetch('/api/data/template', {credentials: 'same-origin'})
                .then(function(response) {
                    if (response.status === 401 || response.status === 302) {
                        window.location.href = '/login';
                        return null;
                    }
                    return response.blob();
                })
                .then(function(blob) {
                    if (!blob) return;
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = '开标记录导入模板_V6.0.xlsx';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                })
                .catch(function(error) {
                    console.error('下载失败:', error);
                    window.location.href = '/api/data/template';
                });
        }

        // 查看样例
        function showExample() {
            var exampleSection = document.getElementById('exampleSection');
            exampleSection.classList.remove('hidden');
            var exampleData = {
                columns: ['开标日期', '开标时间', '项目名称', '开标地点', '方法类别', 'K2', 'K1', 'Q1'],
                rows: [
                    ['2026-01-05', '9:30', '江苏省建筑施工项目 -001', '南京市公共资源交易中心', '1', '0.92', '0.960', ''],
                    ['2026-01-12', '14:00', '江苏省市政工程项目 -002', '苏州市公共资源交易中心', '2', '0.88', '0.970', '0.80']
                ]
            };

            var table = '<thead><tr>' + exampleData.columns.map(function(col) {
                return '<th>' + col + '</th>';
            }).join('') + '</tr></thead><tbody>' + exampleData.rows.map(function(row) {
                return '<tr>' + row.map(function(cell) {
                    return '<td>' + cell + '</td>';
                }).join('') + '</tr>';
            }).join('') + '</tbody>';

            document.getElementById('exampleTable').innerHTML = table;
            // 滚动到样例区域
            exampleSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // 切换导入说明折叠/展开
        function toggleGuide() {
            var body = document.getElementById('guideBody');
            var arrow = document.getElementById('guideArrow');
            if (body.style.display === 'none') {
                body.style.display = 'block';
                arrow.classList.remove('collapsed');
            } else {
                body.style.display = 'none';
                arrow.classList.add('collapsed');
            }
        }

        // 退出登录
        function logout() {
            showModal('confirm', '确认退出', '确定要退出登录吗？', function() {
                fetch('/api/auth/logout', {method: 'POST'})
                    .then(function() { window.location.href = '/login'; })
                    .catch(function() { window.location.href = '/login'; });
            });
        }

        // 页面加载完成
        document.addEventListener('DOMContentLoaded', function() {
            console.log('📊 数据管理页面已加载');
        });