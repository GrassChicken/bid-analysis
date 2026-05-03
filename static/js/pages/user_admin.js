// ============================================================
// 用户管理页面 JavaScript - 响应式 + 多模态框
// ============================================================

var currentPage = 1;
var pageSize = 20;
var resetUserId = null;

// 页面加载
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
});

function checkLoginStatus() {
    fetch('/api/auth/check-login')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.logged_in) { window.location.href = '/login'; return; }
            loadStats();
            loadUsers();
        })
        .catch(function() { window.location.href = '/login'; });
}

// ============================================================
// 数据加载
// ============================================================
function loadStats() {
    fetch('/api/admin/users/stats')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                document.getElementById('totalUsers').textContent = data.stats.total;
                document.getElementById('activeUsers').textContent = data.stats.active;
                document.getElementById('disabledUsers').textContent = data.stats.disabled;
                document.getElementById('adminCount').textContent = data.stats.admin_count;
            }
        });
}

function loadUsers(page) {
    if (page) currentPage = page;
    
    var keyword = document.getElementById('searchInput').value;
    var status = document.getElementById('statusFilter').value;
    
    var url = '/api/admin/users/list?page=' + currentPage + '&page_size=' + pageSize;
    if (keyword) url += '&keyword=' + encodeURIComponent(keyword);
    if (status) url += '&status=' + encodeURIComponent(status);
    
    fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                renderPCView(data.users);
                renderMobileView(data.users);
                renderPagination(data.total, data.page, data.page_size);
                
                var empty = document.getElementById('emptyState');
                if (!data.users || data.users.length === 0) {
                    empty.style.display = 'block';
                    document.querySelector('.table-container, .card-list').style.display = 'none';
                    document.getElementById('pagination').innerHTML = '';
                } else {
                    empty.style.display = 'none';
                    document.querySelector('.table-container, .card-list').style.display = '';
                }
            }
        })
        .catch(function() { showToast('网络错误，请刷新重试', 'error'); });
}

// ============================================================
// PC 端表格渲染
// ============================================================
function renderPCView(users) {
    var tbody = document.getElementById('pcTableBody');
    if (!tbody) return;
    
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading-text">暂无数据</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(function(u) {
        var statusHtml = u.is_active 
            ? '<span class="status-badge status-active">● 活跃</span>'
            : '<span class="status-badge status-disabled">● 已禁用</span>';
        
        var roleHtml = u.is_admin
            ? '<span class="role-badge role-admin">👑 管理员</span>'
            : '<span class="role-badge role-user">用户</span>';
        
        var lastLogin = u.last_login ? u.last_login.substring(0, 16).replace('T', ' ') : '从未登录';
        var actions = buildActionButtons(u);
        
        return '<tr>' +
            '<td>' + u.id + '</td>' +
            '<td><strong>' + esc(u.username) + '</strong></td>' +
            '<td>' + esc(u.phone || '-') + '</td>' +
            '<td title="' + esc(u.email || '') + '">' + esc(u.email || '-') + '</td>' +
            '<td>' + roleHtml + '</td>' +
            '<td>' + statusHtml + '</td>' +
            '<td>' + lastLogin + '</td>' +
            '<td><div class="action-buttons">' + actions + '</div></td>' +
            '</tr>';
    }).join('');
}

// ============================================================
// 手机端卡片渲染
// ============================================================
function renderMobileView(users) {
    var container = document.getElementById('mobileCardList');
    if (!container) return;
    
    if (!users || users.length === 0) {
        container.innerHTML = '<div class="loading-text">暂无数据</div>';
        return;
    }
    
    container.innerHTML = users.map(function(u) {
        var statusHtml = u.is_active 
            ? '<span class="status-badge status-active">● 活跃</span>'
            : '<span class="status-badge status-disabled">● 已禁用</span>';
        
        var roleHtml = u.is_admin ? '👑 管理员' : '普通用户';
        var lastLogin = u.last_login ? u.last_login.substring(0, 16).replace('T', ' ') : '从未登录';
        var createdTime = u.created_at ? u.created_at.substring(0, 10) : '-';
        
        return '<div class="user-card">' +
            '<div class="user-card-header">' +
                '<span class="user-name">' + esc(u.username) + '</span>' +
                statusHtml +
            '</div>' +
            '<div class="user-card-body">' +
                '<div class="user-card-row"><span class="label">角色</span><span class="value">' + roleHtml + '</span></div>' +
                '<div class="user-card-row"><span class="label">手机</span><span class="value">' + esc(u.phone || '-') + '</span></div>' +
                '<div class="user-card-row"><span class="label">邮箱</span><span class="value">' + esc(u.email || '-') + '</span></div>' +
                '<div class="user-card-row"><span class="label">最后登录</span><span class="value">' + lastLogin + '</span></div>' +
                '<div class="user-card-row"><span class="label">注册时间</span><span class="value">' + createdTime + '</span></div>' +
            '</div>' +
            '<div class="user-card-footer">' + buildActionButtons(u) + '</div>' +
            '</div>';
    }).join('');
}

// ============================================================
// 操作按钮
// ============================================================
function buildActionButtons(user) {
    var btns = [];
    var isAdmin = user.is_admin;
    var isSelf = user.id === 1; // admin is ID 1
    
    if (!isAdmin) {
        btns.push('<button class="btn btn-sm btn-warning" onclick="openResetPassword(' + user.id + ',\'' + escJs(user.username) + '\')">🔑 重置密码</button>');
    }
    
    if (!isAdmin && !isSelf) {
        if (user.is_active) {
            btns.push('<button class="btn btn-sm btn-secondary" onclick="toggleUserStatus(' + user.id + ', false)">🚫 禁用</button>');
        } else {
            btns.push('<button class="btn btn-sm btn-success" onclick="toggleUserStatus(' + user.id + ', true)">✅ 启用</button>');
        }
    }
    
    if (!isAdmin && !isSelf) {
        btns.push('<button class="btn btn-sm btn-danger" onclick="deleteUser(' + user.id + ',\'' + escJs(user.username) + '\')">🗑️ 删除</button>');
    }
    
    return btns.join('');
}

// ============================================================
// 分页
// ============================================================
function renderPagination(total, page, pageSize) {
    var pagination = document.getElementById('pagination');
    var totalPages = Math.ceil(total / pageSize);
    
    if (totalPages <= 1) { pagination.innerHTML = ''; return; }
    
    var html = '';
    
    html += '<button ' + (page <= 1 ? 'disabled' : '') + ' onclick="loadUsers(' + (page - 1) + ')">«</button>';
    
    var startPage = Math.max(1, page - 2);
    var endPage = Math.min(totalPages, page + 2);
    
    if (startPage > 1) {
        html += '<button onclick="loadUsers(1)">1</button>';
        if (startPage > 2) html += '<button disabled>...</button>';
    }
    
    for (var i = startPage; i <= endPage; i++) {
        html += '<button class="' + (i === page ? 'active' : '') + '" onclick="loadUsers(' + i + ')">' + i + '</button>';
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += '<button disabled>...</button>';
        html += '<button onclick="loadUsers(' + totalPages + ')">' + totalPages + '</button>';
    }
    
    html += '<button ' + (page >= totalPages ? 'disabled' : '') + ' onclick="loadUsers(' + (page + 1) + ')">»</button>';
    
    pagination.innerHTML = html;
}

function applyFilters() { currentPage = 1; loadUsers(1); }
function refreshUsers() {
    document.getElementById('searchInput').value = '';
    document.getElementById('statusFilter').value = '';
    loadStats(); loadUsers(1);
}

// ============================================================
// 多模态框系统
// ============================================================
function showModal(options) {
    var modal = document.getElementById('globalModal');
    var container = document.getElementById('modalContainer');
    
    var type = options.type || 'info'; // info, success, warning, danger
    var iconMap = { info: 'ℹ️', success: '✅', warning: '⚠️', danger: '❌', key: '🔑' };
    var icon = options.icon || iconMap[type] || iconMap.info;
    
    var html = '';
    
    if (options.mode === 'confirm') {
        // 确认模态框
        html = '<div class="modal-confirm-body">' +
            '<div class="confirm-icon">' + icon + '</div>' +
            '<div class="confirm-title">' + esc(options.title || '确认操作') + '</div>' +
            '<div class="confirm-message">' + (options.message || '') + '</div>' +
            '</div>' +
            '<div class="modal-confirm-footer">' +
            '<button class="btn btn-secondary" onclick="hideModal()">取消</button>' +
            '<button class="btn btn-' + type + '" id="modalConfirmBtn">确认</button>' +
            '</div>';
    } else {
        // 普通模态框
        html = '<div class="modal-header">' +
            '<div class="modal-header-icon ' + type + '">' + icon + '</div>' +
            '<div class="modal-header-content">' +
            '<h3 class="modal-title">' + esc(options.title || '') + '</h3>' +
            (options.subtitle ? '<p class="modal-subtitle">' + options.subtitle + '</p>' : '') +
            '</div>' +
            '<button class="modal-close-btn" onclick="hideModal()">✕</button>' +
            '</div>';
        
        html += '<div class="modal-body">' + (options.body || '') + '</div>';
        
        if (options.buttons && options.buttons.length > 0) {
            html += '<div class="modal-footer">';
            options.buttons.forEach(function(btn) {
                html += '<button class="btn btn-' + (btn.style || 'secondary') + '" ' + (btn.id ? 'id="' + btn.id + '"' : '') + ' onclick="' + (btn.onclick || '') + '">' + esc(btn.text) + '</button>';
            });
            html += '</div>';
        }
    }
    
    container.innerHTML = html;
    modal.style.display = 'flex';
    
    // 绑定确认按钮事件
    if (options.mode === 'confirm' && options.onConfirm) {
        setTimeout(function() {
            var btn = document.getElementById('modalConfirmBtn');
            if (btn) {
                btn.onclick = function() { hideModal(); options.onConfirm(); };
            }
        }, 50);
    }
    
    // ESC 关闭
    document.onkeydown = function(e) {
        if (e.key === 'Escape') hideModal();
    };
}

function hideModal() {
    var modal = document.getElementById('globalModal');
    if (modal) modal.style.display = 'none';
    document.onkeydown = null;
}

// 点击遮罩关闭
document.addEventListener('click', function(e) {
    var modal = document.getElementById('globalModal');
    if (e.target === modal) hideModal();
});

// ============================================================
// 重置密码
// ============================================================
function openResetPassword(userId, username) {
    resetUserId = userId;
    
    showModal({
        type: 'key',
        title: '重置密码',
        subtitle: '为用户 <span class="highlight">' + esc(username) + '</span> 设置新密码',
        body: '<div class="form-group">' +
            '<label>新密码</label>' +
            '<input type="password" id="newPassword" placeholder="输入新密码" oninput="checkPasswordStrength()">' +
            '<div class="password-strength" id="passwordStrength">' +
            '<div class="strength-bar"><div class="strength-fill" id="strengthFill"></div></div>' +
            '<span class="strength-text" id="strengthText">请输入密码</span>' +
            '</div>' +
            '<p class="form-hint">需包含：字母 + 数字 + 特殊字符，至少 8 位</p>' +
            '</div>' +
            '<div class="form-group">' +
            '<label>确认密码</label>' +
            '<input type="password" id="confirmPassword" placeholder="再次输入新密码">' +
            '</div>' +
            '<div class="password-actions">' +
            '<button class="btn btn-sm btn-secondary" onclick="generateRandomPassword()">🎲 生成随机密码</button>' +
            '</div>',
        buttons: [
            { text: '取消', style: 'secondary', onclick: 'hideModal()' },
            { text: '确认重置', style: 'primary', onclick: 'confirmResetPassword()' }
        ]
    });
    
    // 自动聚焦
    setTimeout(function() {
        var input = document.getElementById('newPassword');
        if (input) input.focus();
    }, 100);
}

function checkPasswordStrength() {
    var password = document.getElementById('newPassword').value;
    var div = document.getElementById('passwordStrength');
    var fill = document.getElementById('strengthFill');
    var text = document.getElementById('strengthText');
    
    if (!password) {
        div.className = 'password-strength';
        fill.style.width = '0%';
        text.textContent = '请输入密码';
        return;
    }
    
    var score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
    
    if (score <= 2) { div.className = 'password-strength strength-weak'; text.textContent = '弱'; }
    else if (score <= 4) { div.className = 'password-strength strength-medium'; text.textContent = '中'; }
    else { div.className = 'password-strength strength-strong'; text.textContent = '强'; }
}

function generateRandomPassword() {
    var chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    var pwd = '';
    for (var i = 0; i < 12; i++) pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    
    var input1 = document.getElementById('newPassword');
    var input2 = document.getElementById('confirmPassword');
    if (input1) input1.value = pwd;
    if (input2) input2.value = pwd;
    checkPasswordStrength();
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(pwd).then(function() {
            showToast('密码已生成并复制到剪贴板', 'success');
        });
    }
}

function confirmResetPassword() {
    var newPwd = document.getElementById('newPassword').value;
    var confirmPwd = document.getElementById('confirmPassword').value;
    
    if (!newPwd) { showToast('请输入新密码', 'warning'); return; }
    if (newPwd !== confirmPwd) { showToast('两次输入的密码不一致', 'error'); return; }
    if (newPwd.length < 8) { showToast('密码长度至少 8 位', 'error'); return; }
    if (!(/[a-zA-Z]/.test(newPwd) && /\d/.test(newPwd) && /[!@#$%^&*(),.?":{}|<>]/.test(newPwd))) {
        showToast('密码必须包含字母、数字和特殊字符', 'error'); return;
    }
    
    fetch('/api/admin/users/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: resetUserId, new_password: newPwd })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            showToast(data.message || '密码重置成功', 'success');
            hideModal();
        } else {
            showToast(data.error || '密码重置失败', 'error');
        }
    })
    .catch(function() { showToast('网络错误', 'error'); });
}

// ============================================================
// 禁用/启用用户
// ============================================================
function toggleUserStatus(userId, active) {
    var action = active ? '启用' : '禁用';
    showModal({
        type: active ? 'success' : 'warning',
        mode: 'confirm',
        icon: active ? '✅' : '🚫',
        title: action + '用户',
        message: '确定要' + action + '该用户吗？' + (active ? '' : '禁用后该用户将无法登录系统。'),
        onConfirm: function() {
            doToggleStatus(userId, active);
        }
    });
}

function doToggleStatus(userId, active) {
    fetch('/api/admin/users/toggle-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, active: active })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            showToast(data.message || '操作成功', 'success');
            loadUsers(currentPage);
            loadStats();
        } else {
            showToast(data.error || '操作失败', 'error');
        }
    })
    .catch(function() { showToast('网络错误', 'error'); });
}

// ============================================================
// 删除用户
// ============================================================
function deleteUser(userId, username) {
    showModal({
        type: 'danger',
        mode: 'confirm',
        icon: '🗑️',
        title: '删除用户',
        message: '确定要删除用户 <strong>' + esc(username) + '</strong> 吗？<br>此操作不可恢复！',
        onConfirm: function() {
            doDeleteUser(userId);
        }
    });
}

function doDeleteUser(userId) {
    fetch('/api/admin/users/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            showToast(data.message || '用户已删除', 'success');
            loadUsers(currentPage);
            loadStats();
        } else {
            showToast(data.error || '删除失败', 'error');
        }
    })
    .catch(function() { showToast('网络错误', 'error'); });
}

// ============================================================
// Toast 提示
// ============================================================
function showToast(message, type) {
    type = type || 'info';
    var icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    
    var container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.innerHTML = '<span class="toast-icon">' + (icons[type] || 'ℹ️') + '</span>' +
        '<span class="toast-message">' + message + '</span>';
    
    container.appendChild(toast);
    
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s';
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}

// ============================================================
// 工具函数
// ============================================================
function esc(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

function escJs(str) {
    return (str || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function showLogoutConfirm() {
    showModal({
        type: 'warning',
        mode: 'confirm',
        icon: '👋',
        title: '退出登录',
        message: '确定要退出登录吗？',
        onConfirm: function() {
            fetch('/api/logout', { method: 'POST' })
                .then(function() { window.location.href = '/login'; })
                .catch(function() { window.location.href = '/login'; });
        }
    });
}

function handleLogout() {
    fetch('/api/logout', { method: 'POST' }).then(function() { window.location.href = '/login'; }).catch(function() { window.location.href = '/login'; });
}
