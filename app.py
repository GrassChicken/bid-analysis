#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工程开标数据智能分析平台 V6.0
模块化重构版本 - 核心应用入口
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import os
import logging
from dotenv import load_dotenv

# 加载 V6.0 环境配置
load_dotenv('.env.v6')

from backend.config.config import Config
from backend.utils.logger import setup_logger

def create_app():
    """创建 Flask 应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    
    # 配置日志系统（输出到 log/ 目录）
    setup_logger(app)
    
    # 注册路由
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.data import data_bp
    from routes.predict import predict_bp
    from routes.history import history_bp
    from routes.user import user_bp
    from routes.register import register_bp
    from routes.operation_log import operation_log_bp
    from routes.accuracy import accuracy_bp
    from routes.user_admin import user_admin_bp
    from routes.algorithm_ranking import algorithm_bp
    from routes.diagnosis import diagnosis_bp
    from routes.backup import backup_bp
    from routes.analysis import analysis_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(operation_log_bp)
    app.register_blueprint(accuracy_bp)
    app.register_blueprint(user_admin_bp)
    app.register_blueprint(algorithm_bp)
    app.register_blueprint(diagnosis_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(analysis_bp)

    # 全局请求前处理 - 检查登录状态
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
            '/health',
            '/operation-logs',
            '/api/operation-logs',
            '/api/operation-logs/stats',
            '/api/operation-logs/users',
            '/api/operation-logs/clear',
            '/api/operation-logs/log'
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
    
    # 健康检查端点
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'service': 'V6.0'})
    
    # 首页重定向到仪表盘
    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard.dashboard_page'))
        return redirect(url_for('auth.login_page'))
    
    return app

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    host = app.config.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5001))  # Use environment variable or default to 5001
    
    logging.info("=" * 80)
    logging.info("🏗️ 工程开标数据智能分析平台 V6.0 启动中...")
    logging.info("=" * 80)
    logging.info(f"🌐 服务地址:http://{host}:{port}")
    logging.info(f"📊 数据库路径:{app.config.get('DATABASE_PATH', 'v6_bid_database.db')}")
    logging.info(f"📝 日志目录:{os.path.join(os.getcwd(), 'log')}")
    logging.info(f"🔐 默认管理员:admin / admin123")
    logging.info("=" * 80)
    
    app.run(host=host, port=port, debug=app.config.get('DEBUG', False))