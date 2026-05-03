#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态文件路由模块
处理静态资源请求
"""

from flask import Blueprint, send_from_directory, jsonify
import os

static_bp = Blueprint('static_files', __name__)

@static_bp.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件服务"""
    return send_from_directory('static', filename)

@static_bp.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """提供上传文件服务"""
    return send_from_directory('uploads', filename)