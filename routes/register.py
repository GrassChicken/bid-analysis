#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册页面路由
处理用户注册页面的渲染
"""

from flask import Blueprint, render_template

register_bp = Blueprint('register', __name__)

@register_bp.route('/register')
def register_page():
    """注册页面"""
    return render_template('register.html')