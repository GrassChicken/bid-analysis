#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户中心路由
处理用户个人信息修改、密码修改、退出登录等
"""

from flask import Blueprint, render_template, session, jsonify, request
from backend.models.user import User
from backend.services.user_service import UserService
from werkzeug.security import check_password_hash, generate_password_hash
import re

user_bp = Blueprint('user', __name__)

@user_bp.route('/user-center')
def user_center_page():
    """用户中心页面"""
    if 'user_id' not in session:
        return '<script>window.location.href = '/';</script>'
    
    user_id = session['user_id']
    from backend.config.config import Config
    user_service = UserService(db_path=Config.DATABASE_PATH)
    user_info = user_service.get_user_by_id(user_id)
    
    if not user_info:
        return '<script>window.location.href = '/';</script>'

    return render_template('user.html', user_info=user_info)

@user_bp.route('/api/user/update-info', methods=['POST'])
def api_update_info():
    """更新用户基本信息"""
    from backend.config.config import Config
    import sqlite3
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'})
        
    data = request.get_json()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({'success': False, 'error': '手机号码格式不正确'})
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'success': False, 'error': '邮箱格式不正确'})
    
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone=?, email=? WHERE id=?", (phone, email, session['user_id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@user_bp.route('/api/user/change-password', methods=['POST'])
def api_change_password():
    """修改密码"""
    from backend.config.config import Config
    import sqlite3
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'})
        
    data = request.get_json()
    old_pass = data.get('old_password', '')
    new_pass = data.get('new_password', '')
    
    user_service = UserService(db_path=Config.DATABASE_PATH)
    user = user_service.get_user_by_id(session['user_id'])
    
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'})
    
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id=?", (session['user_id'],))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not check_password_hash(row[0], old_pass):
            return jsonify({'success': False, 'error': '当前密码不正确'})
            
        # 验证新密码复杂度
        if len(new_pass) < 8:
            return jsonify({'success': False, 'error': '新密码长度至少 8 位'})
        if not (re.search(r'[a-zA-Z]', new_pass) and re.search(r'\d', new_pass) and re.search(r'[!@#$%^&*(),.?":{}|<>]', new_pass)):
            return jsonify({'success': False, 'error': '密码必须包含字母、数字和特殊字符'})
            
        # 更新密码
        new_hash = generate_password_hash(new_pass)
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, session['user_id']))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '修改成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})