#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作日志路由
处理操作日志页面和API
"""

from flask import Blueprint, render_template, session, jsonify, request
from backend.models.operation_log import OperationLog

operation_log_bp = Blueprint('operation_log', __name__)
log_model = OperationLog()

@operation_log_bp.route('/operation-logs')
def operation_logs_page():
    """操作日志页面"""
    if 'user_id' not in session:
        return '''<script>window.location.href = '/login';</script>'''
    
    return render_template('operation_log.html', is_admin=session.get('is_admin', False))


# ========== API 路由 ==========

@operation_log_bp.route('/api/operation-logs')
def api_get_logs():
    """获取操作日志列表"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    
    result = log_model.get_logs(
        page=page, page_size=page_size,
        username=request.args.get('username'),
        module=request.args.get('module'),
        status=request.args.get('status'),
        keyword=request.args.get('keyword')
    )
    return jsonify({'success': True, **result})


@operation_log_bp.route('/api/operation-logs/stats')
def api_get_stats():
    """获取统计信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    stats = log_model.get_statistics(days=7)
    return jsonify({'success': True, 'stats': stats})


@operation_log_bp.route('/api/operation-logs/users')
def api_get_users():
    """获取所有操作过的用户"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    return jsonify({'success': True, 'users': log_model.get_all_users()})


@operation_log_bp.route('/api/operation-logs/clear', methods=['POST'])
def api_clear_old_logs():
    """清理旧日志（仅管理员）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'error': '权限不足，仅管理员可操作'}), 403
    
    data = request.get_json() or {}
    days = int(data.get('days', 90))
    if days not in [30, 60, 90]:
        days = 90
    
    deleted_count = log_model.delete_old_logs(days=days)
    
    log_model.log(
        user_id=session['user_id'],
        username=session['username'],
        action='CLEAN',
        module='操作日志',
        new_value={'days': days},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')
    )
    
    return jsonify({'success': True, 'deleted_count': deleted_count})


@operation_log_bp.route('/api/operation-logs/log', methods=['POST'])
def api_create_log():
    """创建操作日志记录（供其他模块调用）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    data = request.get_json()
    success = log_model.log(
        user_id=session['user_id'],
        username=session['username'],
        action=data.get('action', 'UNKNOWN'),
        module=data.get('module', '未知'),
        table_name=data.get('table_name'),
        record_id=data.get('record_id'),
        old_value=data.get('old_value'),
        new_value=data.get('new_value'),
        ip_address=data.get('ip_address', request.remote_addr),
        user_agent=data.get('user_agent', request.headers.get('User-Agent', '')),
        status=data.get('status', 'success'),
        error_message=data.get('error_message')
    )
    return jsonify({'success': success})