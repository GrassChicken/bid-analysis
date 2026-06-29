#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预测路由模块 - V6.0
20 种统计预测算法
"""

from flask import Blueprint, render_template, session, jsonify, request
from backend.models.bid_record import BidRecord
from backend.models.prediction import Prediction
from backend.models.operation_log import OperationLog
from backend.config.config import Config
from backend.analyzers.predictor import BidParameterAnalyzer
from routes.auth import login_required
import sqlite3
from datetime import datetime
import os

predict_bp = Blueprint('predict', __name__)

# 初始化模型
db_path = Config.DATABASE_PATH
bid_record_model = BidRecord(db_path)
prediction_model = Prediction(db_path)
analyzer = BidParameterAnalyzer()
log_model = OperationLog()

# 标准值集合
K2_STANDARD = [round(0.86 + i * 0.01, 2) for i in range(15)]
K1_STANDARD = [0.950, 0.955, 0.960, 0.965, 0.970, 0.975, 0.980]
Q1_STANDARD = [0.65, 0.70, 0.75, 0.80, 0.85]


@predict_bp.route('/predict')
@login_required
def predict_page():
    """预测页面"""
    return render_template('predict.html')


@predict_bp.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    """预测 API"""
    user_id = session.get('user_id')
    data = request.get_json()

    project_name = data.get('project_name', '').strip()
    location = data.get('location')
    method_category = data.get('method_category')
    date_from = data.get('date_from')
    date_to = data.get('date_to')

    if not project_name:
        return jsonify({'success': False, 'error': '请输入项目名称'})

    # 从数据库获取用户的数据
    records, _ = bid_record_model.get_records(
        user_id,
        filters={
            'location': location,
            'method': method_category,
            'date_from': date_from,
            'date_to': date_to
        },
        limit=10000,
        offset=0
    )

    if not records:
        return jsonify({'success': False, 'error': '没有足够的数据进行预测'})

    # 自动填充日期范围：如果用户没有设置开始/结束日期，则从过滤结果中取最早和最晚的开标日期
    if not date_from or not date_to:
        bid_dates = [r[3] for r in records if r[3]]
        if bid_dates:
            if not date_from:
                date_from = min(bid_dates)
            if not date_to:
                date_to = max(bid_dates)

    # 【修复】按开标日期正序排序，确保时间序列分析正确
    # 原始数据按 import_time DESC 排序，但预测算法需要按时间正序
    records = sorted(records, key=lambda r: r[3] or '')

    # 提取数据（records 是元组列表）
    # 列顺序: id(0), user_id(1), project_name(2), bid_date(3), bid_time(4),
    #         bid_location(5), method_category(6), k2_value(7), k1_value(8), q1_value(9), import_time(10)
    method_values = [r[6] for r in records if r[6]]
    k2_values = [float(r[7]) for r in records if r[7] and str(r[7]).replace('.', '').isdigit()]
    k1_values = [float(r[8]) for r in records if r[8] and str(r[8]).replace('.', '').isdigit()]
    q1_values = [float(r[9]) for r in records if r[9] and str(r[9]).replace('.', '').isdigit()]

    result = {
        'success': True,
        'data_count': len(records),
        'k2_count': len(k2_values),
        'k1_count': len(k1_values),
        'q1_count': len(q1_values),
        'method_count': len(method_values)
    }

    # 1. 预测方法类别
    if method_values:
        method_result = analyzer.predict_method_category(method_values)
        if method_result['success']:
            result['method_prediction'] = method_result['best_prediction']
            result['method_all'] = method_result.get('all_predictions', [])

    # 2. 预测 K1 值
    if len(k1_values) >= 3:
        k1_result = analyzer.analyze('k1', k1_values, K1_STANDARD)
        if k1_result['success']:
            result['k1_prediction'] = k1_result['best_prediction']
            result['k1_all'] = k1_result.get('all_predictions', [])

    # 3. 预测 Q1 值
    if len(q1_values) >= 3:
        q1_result = analyzer.analyze('q1', q1_values, Q1_STANDARD)
        if q1_result['success']:
            result['q1_prediction'] = q1_result['best_prediction']
            result['q1_all'] = q1_result.get('all_predictions', [])

    # 检查是否已有该项目的预测记录
    try:
        existing = prediction_model.get_prediction_by_project(user_id, project_name)
        if existing:
            result['existing'] = existing
            result['duplicate'] = True
            # 仍然计算预测结果供前端展示，但不保存
            # 保存逻辑移到 /api/predict/update
            return jsonify(result)
    except Exception as e:
        print(f"⚠️ 检查重复预测失败: {e}")

    # 保存预测记录
    try:
        method_pred = result.get('method_prediction', {}).get('prediction')
        
        prediction_data = {
            'project_name': project_name,
            'location_filter': location,
            'method_filter': method_category,
            'date_from': date_from,
            'date_to': date_to,
            'data_count': len(records),
            'method_prediction': result.get('method_prediction', {}).get('prediction'),
            'method_confidence': result.get('method_prediction', {}).get('confidence'),
            'k1_prediction': result.get('k1_prediction', {}).get('prediction'),
            'k1_confidence': result.get('k1_prediction', {}).get('confidence'),
            'k1_method': result.get('k1_prediction', {}).get('method'),
        }
        
        # 方法1 不存储 Q1 值（方法1 没有 Q1）
        if method_pred == '1':
            prediction_data['q1_prediction'] = None
            prediction_data['q1_confidence'] = None
            prediction_data['q1_method'] = None
            # 前端也清除 Q1 预测结果
            result['q1_prediction'] = None
            result['q1_confidence'] = None
            result['q1_method'] = None
        else:
            prediction_data['q1_prediction'] = result.get('q1_prediction', {}).get('prediction')
            prediction_data['q1_confidence'] = result.get('q1_prediction', {}).get('confidence')
            prediction_data['q1_method'] = result.get('q1_prediction', {}).get('method')
        
        record_id = prediction_model.create_prediction(user_id, prediction_data)
        if record_id > 0:
            result['record_id'] = record_id
            result['duplicate'] = False
            
            # 记录操作日志
            try:
                log_model.log(
                    user_id=user_id,
                    username=session.get('username', 'unknown'),
                    action='PREDICT_CREATE',
                    module='智能预测',
                    table_name='prediction_records',
                    new_value={
                        'project_name': project_name,
                        'method_prediction': prediction_data.get('method_prediction'),
                        'k1_prediction': prediction_data.get('k1_prediction'),
                        'q1_prediction': prediction_data.get('q1_prediction'),
                        'data_count': prediction_data.get('data_count'),
                    },
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', ''),
                    status='success'
                )
            except Exception as e:
                print(f"⚠️ 记录预测操作日志失败: {e}")
    except Exception as e:
        print(f"⚠️ 保存预测记录失败: {e}")
        # 记录失败日志
        try:
            log_model.log(
                user_id=user_id,
                username=session.get('username', 'unknown'),
                action='PREDICT_CREATE',
                module='智能预测',
                table_name='prediction_records',
                new_value={'project_name': project_name},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                status='failed',
                error_message=str(e)
            )
        except Exception:
            pass

    return jsonify(result)


@predict_bp.route('/api/predict/update/<int:record_id>', methods=['POST'])
@login_required
def api_predict_update(record_id):
    """更新已有项目的预测记录（覆盖模式）
    
    支持：方法变更（方法2→方法1时 Q1 置空）、置信度更新等
    同时重置准确率对比状态
    """
    user_id = session.get('user_id')
    data = request.get_json()

    project_name = data.get('project_name', '').strip()
    location = data.get('location')
    method_category = data.get('method_category')
    date_from = data.get('date_from')
    date_to = data.get('date_to')

    if not project_name:
        return jsonify({'success': False, 'error': '请输入项目名称'})

    # 验证 record_id 属于该用户
    existing = prediction_model.get_prediction_by_id(record_id, user_id)
    if not existing:
        return jsonify({'success': False, 'error': '预测记录不存在或无权操作'})

    # 从数据库获取用户的数据
    records, _ = bid_record_model.get_records(
        user_id,
        filters={
            'location': location,
            'method': method_category,
            'date_from': date_from,
            'date_to': date_to
        },
        limit=10000,
        offset=0
    )

    if not records:
        return jsonify({'success': False, 'error': '没有足够的数据进行预测'})

    # 自动填充日期范围
    if not date_from or not date_to:
        bid_dates = [r[3] for r in records if r[3]]
        if bid_dates:
            if not date_from:
                date_from = min(bid_dates)
            if not date_to:
                date_to = max(bid_dates)

    # 【修复】按开标日期正序排序，确保时间序列分析正确
    records = sorted(records, key=lambda r: r[3] or '')

    method_values = [r[6] for r in records if r[6]]
    k2_values = [float(r[7]) for r in records if r[7] and str(r[7]).replace('.', '').isdigit()]
    k1_values = [float(r[8]) for r in records if r[8] and str(r[8]).replace('.', '').isdigit()]
    q1_values = [float(r[9]) for r in records if r[9] and str(r[9]).replace('.', '').isdigit()]

    result = {
        'success': True,
        'data_count': len(records),
        'k2_count': len(k2_values),
        'k1_count': len(k1_values),
        'q1_count': len(q1_values),
        'method_count': len(method_values)
    }

    # 1. 预测方法类别
    if method_values:
        method_result = analyzer.predict_method_category(method_values)
        if method_result['success']:
            result['method_prediction'] = method_result['best_prediction']
            result['method_all'] = method_result.get('all_predictions', [])

    # 2. 预测 K1 值
    if len(k1_values) >= 3:
        k1_result = analyzer.analyze('k1', k1_values, K1_STANDARD)
        if k1_result['success']:
            result['k1_prediction'] = k1_result['best_prediction']
            result['k1_all'] = k1_result.get('all_predictions', [])

    # 3. 预测 Q1 值
    if len(q1_values) >= 3:
        q1_result = analyzer.analyze('q1', q1_values, Q1_STANDARD)
        if q1_result['success']:
            result['q1_prediction'] = q1_result['best_prediction']
            result['q1_all'] = q1_result.get('all_predictions', [])

    # 更新预测记录
    try:
        method_pred = result.get('method_prediction', {}).get('prediction')
        
        prediction_data = {
            'project_name': project_name,
            'location_filter': location,
            'method_filter': method_category,
            'date_from': date_from,
            'date_to': date_to,
            'data_count': len(records),
            'method_prediction': result.get('method_prediction', {}).get('prediction'),
            'method_confidence': result.get('method_prediction', {}).get('confidence'),
            'k1_prediction': result.get('k1_prediction', {}).get('prediction'),
            'k1_confidence': result.get('k1_prediction', {}).get('confidence'),
            'k1_method': result.get('k1_prediction', {}).get('method'),
        }
        
        # 方法1 不存储 Q1 值（方法1 没有 Q1）→ 支持将 Q1 置空
        if method_pred == '1':
            prediction_data['q1_prediction'] = None
            prediction_data['q1_confidence'] = None
            prediction_data['q1_method'] = None
            result['q1_prediction'] = None
            result['q1_confidence'] = None
            result['q1_method'] = None
        else:
            prediction_data['q1_prediction'] = result.get('q1_prediction', {}).get('prediction')
            prediction_data['q1_confidence'] = result.get('q1_prediction', {}).get('confidence')
            prediction_data['q1_method'] = result.get('q1_prediction', {}).get('method')
        
        success = prediction_model.update_prediction(record_id, user_id, prediction_data)
        if success:
            result['record_id'] = record_id
            result['updated'] = True
            
            # 记录操作日志
            try:
                log_model.log(
                    user_id=user_id,
                    username=session.get('username', 'unknown'),
                    action='PREDICT_UPDATE',
                    module='智能预测',
                    table_name='prediction_records',
                    record_id=record_id,
                    new_value={
                        'project_name': project_name,
                        'method_prediction': prediction_data.get('method_prediction'),
                        'k1_prediction': prediction_data.get('k1_prediction'),
                        'q1_prediction': prediction_data.get('q1_prediction'),
                    },
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', ''),
                    status='success'
                )
            except Exception as e:
                print(f"⚠️ 记录预测更新日志失败: {e}")
        else:
            result['success'] = False
            result['error'] = '更新失败'
            try:
                log_model.log(
                    user_id=user_id,
                    username=session.get('username', 'unknown'),
                    action='PREDICT_UPDATE',
                    module='智能预测',
                    table_name='prediction_records',
                    record_id=record_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', ''),
                    status='failed',
                    error_message='更新失败'
                )
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️ 更新预测记录失败: {e}")
        result['success'] = False
        result['error'] = str(e)
        try:
            log_model.log(
                user_id=user_id,
                username=session.get('username', 'unknown'),
                action='PREDICT_UPDATE',
                module='智能预测',
                table_name='prediction_records',
                record_id=record_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                status='failed',
                error_message=str(e)
            )
        except Exception:
            pass

    return jsonify(result)
