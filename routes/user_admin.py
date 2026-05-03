#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理路由模块（仅管理员可用）
处理用户列表、密码重置、启用/禁用、删除等操作
"""

from flask import Blueprint, render_template, session, jsonify, request
from backend.models.user import User
from backend.models.operation_log import OperationLog
from backend.config.config import Config
from routes.auth import login_required
import re

user_admin_bp = Blueprint('user_admin', __name__)

# 初始化模型
db_path = Config.DATABASE_PATH
user_model = User(db_path)
log_model = OperationLog(db_path)


def admin_required(f):
    """管理员权限验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


@user_admin_bp.route('/admin/users')
@admin_required
def user_admin_page():
    """用户管理页面"""
    return render_template('user_admin.html', username=session.get('username', '管理员'))


@user_admin_bp.route('/api/admin/users/list')
@admin_required
def api_users_list():
    """获取用户列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    keyword = request.args.get('keyword', '').strip() or None
    status = request.args.get('status', '').strip()  # all/active/disabled
    
    conn = user_model.db_path
    import sqlite3
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    
    # 构建查询条件
    conditions = []
    params = []
    
    if keyword:
        conditions.append('(username LIKE ? OR phone LIKE ? OR email LIKE ?)')
        kw = f'%{keyword}%'
        params.extend([kw, kw, kw])
    
    if status == 'active':
        conditions.append('is_active = 1')
    elif status == 'disabled':
        conditions.append('(is_active = 0 OR is_active IS NULL)')
    
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    # 获取总数
    cursor.execute(f'SELECT COUNT(*) FROM users WHERE {where_clause}', params)
    total = cursor.fetchone()[0]
    
    # 获取分页数据
    cursor.execute(f'''
        SELECT id, username, phone, email, created_at, is_admin, is_active, last_login
        FROM users WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ? OFFSET ?
    ''', params + [page_size, (page - 1) * page_size])
    
    rows = cursor.fetchall()
    db.close()
    
    users = []
    for row in rows:
        users.append({
            'id': row[0],
            'username': row[1],
            'phone': row[2] or '',
            'email': row[3] or '',
            'created_at': row[4],
            'is_admin': bool(row[5]),
            'is_active': bool(row[6]) if row[6] is not None else True,
            'last_login': row[7] or ''
        })
    
    return jsonify({
        'success': True,
        'total': total,
        'page': page,
        'page_size': page_size,
        'users': users
    })


@user_admin_bp.route('/api/admin/users/reset-password', methods=['POST'])
@admin_required
def api_reset_password():
    """重置用户密码"""
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password', '').strip()
    
    if not user_id:
        return jsonify({'success': False, 'error': '用户 ID 不能为空'})
    
    # 密码复杂度校验
    if len(new_password) < 8:
        return jsonify({'success': False, 'error': '密码长度至少 8 位'})
    if not (re.search(r'[a-zA-Z]', new_password) and re.search(r'\d', new_password) and re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password)):
        return jsonify({'success': False, 'error': '密码必须包含字母、数字和特殊字符'})
    
    # 不允许重置管理员密码（通过此接口）
    if user_id == 1:
        return jsonify({'success': False, 'error': '不允许重置管理员密码'})
    
    success = user_model.update_password(user_id, new_password)
    
    if success:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username'),
            action='RESET_PASSWORD',
            module='用户管理',
            table_name='users',
            record_id=user_id,
            new_value={'action': '重置密码'},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )
        return jsonify({'success': True, 'message': '密码重置成功'})
    else:
        return jsonify({'success': False, 'error': '密码重置失败'})


@user_admin_bp.route('/api/admin/users/toggle-status', methods=['POST'])
@admin_required
def api_toggle_status():
    """启用/禁用用户"""
    data = request.get_json()
    user_id = data.get('user_id')
    active = data.get('active', True)
    
    if not user_id:
        return jsonify({'success': False, 'error': '用户 ID 不能为空'})
    
    # 不允许禁用管理员
    if user_id == 1:
        return jsonify({'success': False, 'error': '不允许禁用管理员账号'})
    
    # 不能禁用自己
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'error': '不能禁用自己'})
    
    success = user_model.toggle_user_status(user_id, active)
    
    if success:
        action = '启用' if active else '禁用'
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username'),
            action='TOGGLE_STATUS',
            module='用户管理',
            table_name='users',
            record_id=user_id,
            new_value={'action': action, 'active': active},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )
        return jsonify({'success': True, 'message': f'已{action}用户'})
    else:
        return jsonify({'success': False, 'error': '操作失败'})


@user_admin_bp.route('/api/admin/users/delete', methods=['POST'])
@admin_required
def api_delete_user():
    """删除用户"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': '用户 ID 不能为空'})
    
    # 不允许删除管理员
    if user_id == 1:
        return jsonify({'success': False, 'error': '不允许删除管理员账号'})
    
    # 不能删除自己
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'error': '不能删除自己'})
    
    success = user_model.delete_user(user_id)
    
    if success:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username'),
            action='DELETE_USER',
            module='用户管理',
            table_name='users',
            record_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )
        return jsonify({'success': True, 'message': '用户已删除'})
    else:
        return jsonify({'success': False, 'error': '删除失败'})


@user_admin_bp.route('/api/admin/users/stats')
@admin_required
def api_users_stats():
    """获取用户统计信息"""
    import sqlite3
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    
    # 总用户数
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    
    # 活跃用户数
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    active = cursor.fetchone()[0]
    
    # 禁用用户数
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 0 OR is_active IS NULL')
    disabled = cursor.fetchone()[0]
    
    # 管理员数
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
    admin_count = cursor.fetchone()[0]
    
    # 今日新增
    cursor.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')")
    today_new = cursor.fetchone()[0]
    
    db.close()
    
    return jsonify({
        'success': True,
        'stats': {
            'total': total,
            'active': active,
            'disabled': disabled,
            'admin_count': admin_count,
            'today_new': today_new
        }
    })
