#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6.0 日志配置模块
- 使用 RotatingFileHandler 实现单文件最大 10MB
- 日志全部输出到 log/ 目录
- 支持控制台和文件双输出
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


# 日志目录（相对于项目根目录）
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'log')
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件路径
LOG_FILE = os.path.join(LOG_DIR, 'bid-v6.log')

# 日志配置
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5              # 保留 5 个轮转文件


def setup_logger(app):
    """为 Flask 应用配置日志"""
    
    # 创建日志目录
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件 Handler - 轮转模式
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除旧 handler 避免重复
    root_logger.handlers.clear()
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Flask 应用日志
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    
    # 启动日志
    logging.info(f"📝 日志已配置: {LOG_FILE}")
    logging.info(f"📏 单文件最大: {LOG_MAX_BYTES / 1024 / 1024:.0f}MB, 保留 {LOG_BACKUP_COUNT} 个轮转文件")
    
    return root_logger


def get_log_dir():
    """返回日志目录路径"""
    return LOG_DIR


def get_log_file():
    """返回当前日志文件路径"""
    return LOG_FILE
