#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法效能排名 API
提供算法统计、排名、详情等接口
"""

from flask import Blueprint, session, jsonify, request, render_template
from backend.services.algorithm_stats import AlgorithmStatsService
from routes.auth import login_required

algorithm_bp = Blueprint('algorithm', __name__)
stats_service = AlgorithmStatsService()


@algorithm_bp.route('/algorithm-ranking')
@login_required
def algorithm_ranking_page():
    """算法效能排名页面"""
    return render_template('algorithm_ranking.html')


@algorithm_bp.route('/api/algorithm/ranking')
@login_required
def get_ranking():
    """
    获取算法效能排名
    
    Query params:
        location: 地点筛选（可选）
        days: 时间范围（可选，30/90/180/365）
    """
    user_id = session.get('user_id')
    location = request.args.get('location', '').strip() or None
    days_str = request.args.get('days', '').strip()
    days = int(days_str) if days_str and days_str.isdigit() else None

    try:
        result = stats_service.calculate_stats(user_id, location, days)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@algorithm_bp.route('/api/algorithm/detail/<algorithm_name>')
@login_required
def get_detail(algorithm_name):
    """
    获取算法详细统计
    
    Query params:
        location: 地点筛选（可选）
    """
    user_id = session.get('user_id')
    location = request.args.get('location', '').strip() or None

    try:
        result = stats_service.get_algorithm_detail(user_id, algorithm_name, location)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
