#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6.0 配置管理
独立的配置文件，与 V5.0 隔离
"""

import os
from dotenv import load_dotenv

# 加载 V6.0 专用环境变量
load_dotenv('.env.v6')

class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'v6-dev-secret-key-change-in-production'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'v6_bid_database.db'
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT', 5001))  # V6.0 使用 5001 端口
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # AI 分析配置
    DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'qwen3.5-plus')
    
    # 上传文件配置
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # 静态文件配置
    STATIC_FOLDER = 'static'
    TEMPLATE_FOLDER = 'templates'
    
    # PWA 配置
    PWA_ENABLED = True
    PWA_NAME = '工程开标数据智能分析平台 V6.0'
    PWA_SHORT_NAME = 'BidAnalysis V6'
    PWA_THEME_COLOR = '#667eea'
    PWA_BACKGROUND_COLOR = '#ffffff'
    PWA_DISPLAY = 'standalone'
    PWA_START_URL = '/'
    
    # 推送通知配置
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', 'mailto:admin@example.com')

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    DATABASE_PATH = os.environ.get('DEV_DATABASE_PATH') or 'dev_v6_bid_database.db'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'prod-secret-key-required'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}