#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 app.py 文件
"""

import re

# Read the current app.py file
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the correct before_request function
correct_before_request = '''    # 全局请求前处理 - 检查登录状态
    @app.before_request
    def check_session():
        # 不需要登录验证的路由
        public_routes = [
            '/',  # 根路径会重定向
            '/login',
            '/register',
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/check-login',
            '/health'
        ]
        
        # 检查是否为公共路由
        if request.path in public_routes:
            return None
        
        # 检查是否为静态资源
        if request.path.startswith('/static/') or request.path.startswith('/uploads/'):
            return None
        
        # 对于需要登录的页面，如果没有登录则重定向到登录页
        if request.path.startswith('/') and 'user_id' not in session:
            if request.is_json or request.content_type == 'application/json':
                # API 请求返回 JSON 错误
                return jsonify({'error': '会话已过期，请重新登录', 'require_login': True}), 401
            else:
                # 页面请求重定向到登录页
                return redirect(url_for('auth.login_page'))
'''

# Replace the existing before_request function
content = re.sub(
    r'    # 全局请求前处理 - 检查登录状态.*?                return redirect\\(url_for\\(\'auth.login_page\'\\)\\)',
    correct_before_request,
    content,
    flags=re.DOTALL
)

# Write the fixed content back
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py 修复完成")