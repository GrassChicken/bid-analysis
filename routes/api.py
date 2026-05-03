#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 路由模块
处理通用API请求
"""

from flask import Blueprint, jsonify, request, session
from routes.auth import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/check-login')
def api_check_login():
    """检查登录状态"""
    return jsonify({
        'logged_in': 'user_id' in session,
        'username': session.get('username')
    })

@api_bp.route('/api/user/info')
@login_required
def api_user_info():
    """获取当前用户信息"""
    return jsonify({
        'success': True,
        'user': {
            'id': session.get('user_id'),
            'username': session.get('username')
        }
    })

@api_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """登出 API"""
    session.clear()
    return jsonify({'success': True, 'message': '已登出'})