#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仪表盘路由模块
处理仪表盘页面和相关API
"""

from flask import Blueprint, render_template, session, jsonify, request
from backend.models.bid_record import BidRecord
from backend.models.prediction import Prediction
from backend.config.config import Config
from routes.auth import login_required
import os

dashboard_bp = Blueprint('dashboard', __name__)

# 初始化模型
db_path = Config.DATABASE_PATH
bid_record_model = BidRecord(db_path)
prediction_model = Prediction(db_path)


@dashboard_bp.route('/dashboard')
@login_required
def dashboard_page():
    """仪表盘页面"""
    user_id = session.get('user_id')
    
    # 获取统计信息
    bid_stats = bid_record_model.get_statistics(user_id)
    pred_stats = prediction_model.get_statistics(user_id)
    
    # 获取最近一次预测记录
    recent_predictions, _ = prediction_model.get_predictions(
        user_id, limit=1, offset=0
    )
    latest_prediction = recent_predictions[0] if recent_predictions else None
    
    # 获取近 7 天预测准确率（如果有真实值数据）
    accuracy_data = prediction_model.get_recent_accuracy(user_id, days=7)
    
    return render_template(
        'dashboard.html',
        username=session.get('username', '用户'),
        is_admin=session.get('is_admin', False),
        total_count=bid_stats['total_count'],
        today_count=bid_stats['today_count'],
        month_predictions=pred_stats['month_predictions'],
        ai_used_count=pred_stats['ai_used_count'],
        method_distribution=str(bid_stats['method_distribution']),
        k1_distribution=str(bid_stats['k1_distribution']),
        q1_distribution=str(bid_stats.get('q1_distribution', {})),
        location_distribution=str(bid_stats.get('location_distribution', {})),
        latest_prediction=latest_prediction,
        recent_accuracy=accuracy_data
    )
