#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证控制器
处理用户认证相关请求
"""

from flask import Blueprint, request, jsonify, session
from backend.services.user_service import UserService
from backend.models.user import User
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def login_required(f):
    """登录验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录', 'require_login': True}), 401
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'})
    
    user_service = UserService()
    user = user_service.authenticate(username, password)
    
    if user == 'DISABLED':
        return jsonify({
            'success': False,
            'error': '您的账号已被禁用，请联系管理员处理',
            'error_code': 'ACCOUNT_DISABLED'
        })
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user.get('is_admin', False)
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'is_admin': user.get('is_admin', False)
            }
        })
    else:
        return jsonify({'success': False, 'error': '用户名或密码错误'})

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'success': True, 'message': '已登出'})

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'})
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码长度不能少于6位'})
    
    user_service = UserService()
    success = user_service.create_user(username, password, phone, email)
    
    if success:
        return jsonify({'success': True, 'message': '注册成功'})
    else:
        return jsonify({'success': False, 'error': '用户名已存在'})

@auth_bp.route('/check-login', methods=['GET'])
def check_login():
    """检查登录状态"""
    return jsonify({
        'logged_in': 'user_id' in session,
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    })

@auth_bp.route('/user/info', methods=['GET'])
@login_required
def user_info():
    """获取当前用户信息"""
    user_id = session.get('user_id')
    user_service = UserService()
    user = user_service.get_user_by_id(user_id)
    
    if user:
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'phone': user.get('phone'),
                'email': user.get('email'),
                'created_at': user.get('created_at')
            }
        })
    else:
        return jsonify({'success': False, 'error': '用户不存在'})