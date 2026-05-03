let currentPage = 1;
        let searchTimer;

        document.addEventListener('DOMContentLoaded', function() {
            loadStats();
            loadUsers();
            loadLogs(1);
            updateClearHint();
            document.getElementById('clearDays').addEventListener('change', updateClearHint);
        });

        function updateClearHint() {
            var days = document.getElementById('clearDays').value;
            document.getElementById('clearHint').textContent = '将删除 ' + days + ' 天之前的所有操作日志记录';
        }

        function loadStats() {
            fetch('/api/operation-logs/stats')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        document.getElementById('totalCount').textContent = data.stats.total_count;
                        document.getElementById('successCount').textContent = data.stats.success_count;
                        document.getElementById('failureCount').textContent = data.stats.failure_count;
                    }
                });
        }

        function loadUsers() {
            fetch('/api/operation-logs/users')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        var select = document.getElementById('filterUsername');
                        data.users.forEach(function(u) {
                            var opt = document.createElement('option');
                            opt.value = u; opt.textContent = u;
                            select.appendChild(opt);
                        });
                    }
                });
        }

        function loadLogs(page) {
            var params = new URLSearchParams({
                page: page,
                page_size: 20,
                username: document.getElementById('filterUsername').value,
                module: document.getElementById('filterModule').value,
                status: document.getElementById('filterStatus').value,
                keyword: document.getElementById('filterKeyword').value
            });
            fetch('/api/operation-logs?' + params.toString())
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        displayLogs(data.logs);
                        updatePagination(data.total, data.page, data.page_size);
                    }
                });
        }

        function displayLogs(logs) {
            var tbody = document.getElementById('logBody');
            var empty = document.getElementById('emptyState');
            var table = document.getElementById('logTable');
            if (logs.length === 0) {
                table.style.display = 'none';
                empty.style.display = 'block';
                return;
            }
            table.style.display = 'table';
            empty.style.display = 'none';
            tbody.innerHTML = logs.map(function(log) {
                var badgeClass = log.status === 'success' ? 'badge-success' : 'badge-danger';
                var statusText = log.status === 'success' ? '✅ 成功' : '❌ 失败';
                var time = (log.created_at || '').substring(0, 19);
                return '<tr>' +
                    '<td>' + time + '</td>' +
                    '<td>' + (log.username || '--') + '</td>' +
                    '<td><strong>' + (log.action || '--') + '</strong></td>' +
                    '<td>' + (log.module || '--') + '</td>' +
                    '<td><span class="badge ' + badgeClass + '">' + statusText + '</span></td>' +
                    '<td>' + (log.ip_address || '--') + '</td>' +
                    '</tr>';
            }).join('');
        }

        function updatePagination(total, currentPage, pageSize) {
            var totalPages = Math.ceil(total / pageSize);
            var pagination = document.getElementById('pagination');
            if (totalPages <= 1) { pagination.innerHTML = ''; return; }
            var buttons = '';
            buttons += '<button onclick="loadLogs(' + Math.max(1, currentPage - 1) + ')" ' + (currentPage <= 1 ? 'disabled' : '') + '>上一页</button>';
            var start = Math.max(1, currentPage - 2);
            var end = Math.min(totalPages, currentPage + 2);
            if (start > 1) buttons += '<button onclick="loadLogs(1)">1</button>';
            if (start > 2) buttons += '<span>...</span>';
            for (var i = start; i <= end; i++) {
                buttons += '<button onclick="loadLogs(' + i + ')" ' + (i === currentPage ? 'class="active"' : '') + '>' + i + '</button>';
            }
            if (end < totalPages - 1) buttons += '<span>...</span>';
            if (end < totalPages) buttons += '<button onclick="loadLogs(' + totalPages + ')">' + totalPages + '</button>';
            buttons += '<button onclick="loadLogs(' + Math.min(totalPages, currentPage + 1) + ')" ' + (currentPage >= totalPages ? 'disabled' : '') + '>下一页</button>';
            pagination.innerHTML = buttons;
        }

        function applyFilters() { currentPage = 1; loadLogs(1); }
        function resetFilters() {
            document.getElementById('filterUsername').value = '';
            document.getElementById('filterModule').value = '';
            document.getElementById('filterStatus').value = '';
            document.getElementById('filterKeyword').value = '';
            applyFilters();
        }
        function debounceSearch() {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(function() { applyFilters(); }, 500);
        }

        function showClearModal() { document.getElementById('clearModal').style.display = 'flex'; }
        function hideClearModal() { document.getElementById('clearModal').style.display = 'none'; }
        function performClear() {
            var days = parseInt(document.getElementById('clearDays').value);
            fetch('/api/operation-logs/clear', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({days: days})
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        alert('✅ 已清理 ' + data.deleted_count + ' 条旧日志');
                        hideClearModal();
                        loadStats();
                        loadLogs(currentPage);
                    } else {
                        alert('❌ 清理失败: ' + data.error);
                    }
                });
        }