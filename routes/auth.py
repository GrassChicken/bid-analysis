#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证路由模块
处理用户登录、注册、登出等认证相关功能
"""

from flask import Blueprint, request, session, jsonify, render_template
from backend.models.user import User
from backend.models.operation_log import OperationLog
from backend.config.config import Config
from backend.services.user_service import UserService
import re
import os

auth_bp = Blueprint('auth', __name__)
log_model = OperationLog()

# 初始化用户模型
db_path = Config.DATABASE_PATH
user_model = User(db_path)

def login_required(f):
    """登录验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录', 'require_login': True}), 401
        return f(*args, **kwargs)
    return decorated_function

# 登录页面
@auth_bp.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')

# API 路由
@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """登录 API"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'})
        
        # 使用用户模型进行认证
        user_model = User()
        user = user_model.authenticate(username, password)
        
        if user == 'DISABLED':
            # 用户已禁用
            log_model.log(
                user_id=0, username=username,
                action='LOGIN_DISABLED', module='认证',
                new_value={'username': username},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                status='failure', error_message='账号已被禁用'
            )
            return jsonify({
                'success': False,
                'error': '您的账号已被禁用，请联系管理员处理',
                'error_code': 'ACCOUNT_DISABLED'
            })
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            
            log_model.log(
                user_id=user['id'], username=user['username'],
                action='LOGIN', module='认证',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            
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
            log_model.log(
                user_id=0, username=username,
                action='LOGIN_FAILURE', module='认证',
                new_value={'username': username},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                status='failure', error_message='用户名或密码错误'
            )
            return jsonify({'success': False, 'error': '用户名或密码错误'})
            
    except Exception as e:
        log_model.log(
            user_id=0, username=username,
            action='LOGIN_ERROR', module='认证',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='failure', error_message=str(e)
        )
        return jsonify({'success': False, 'error': f'登录失败: {str(e)}'})

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """登出 API"""
    user_id = session.get('user_id')
    username = session.get('username')
    if user_id:
        log_model.log(
            user_id=user_id, username=username or 'unknown',
            action='LOGOUT', module='认证',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
    session.clear()
    return jsonify({'success': True, 'message': '已登出'})

@auth_bp.route('/api/auth/verify-password', methods=['POST'])
@login_required
def api_verify_password():
    """验证当前用户密码"""
    try:
        data = request.get_json()
        password = data.get('password', '').strip()
        
        if not password:
            return jsonify({'success': False, 'error': '请输入密码'})
        
        # 使用 session 中的用户名直接验证
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': '未登录'})
        
        user_model = User()
        result = user_model.authenticate(username, password)
        
        if result == 'DISABLED':
            return jsonify({'success': False, 'error': '账号已被禁用'})
        
        if result:
            return jsonify({'success': True, 'message': '密码正确'})
        else:
            return jsonify({'success': False, 'error': '密码错误'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'验证失败: {str(e)}'})

@auth_bp.route('/api/auth/check-login')
def api_check_login():
    """检查登录状态"""
    return jsonify({
        'logged_in': 'user_id' in session,
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    })

@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    """注册 API"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'})
        
        if len(password) < 8:
            return jsonify({'success': False, 'error': '密码长度至少 8 位'})
        
        # 检查复杂度：必须包含字母、数字、特殊字符
        if not (re.search(r'[a-zA-Z]', password) and re.search(r'\d', password) and re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
            return jsonify({'success': False, 'error': '密码必须包含字母、数字和特殊字符'})
        
        # 使用用户模型创建用户
        user_model = User()
        success = user_model.create_user(username, password, phone, email)
        
        if success:
            log_model.log(
                user_id=session.get('user_id'),
                username=username,
                action='REGISTER', module='认证',
                new_value={'username': username, 'phone': phone, 'email': email},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            return jsonify({'success': True, 'message': '注册成功'})
        else:
            return jsonify({'success': False, 'error': '用户名已存在'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'注册失败: {str(e)}'})