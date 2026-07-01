#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录路由模块
处理预测历史记录相关页面和API
"""

from flask import Blueprint, render_template, session, jsonify, request, send_file
from backend.models.prediction import Prediction
from backend.models.operation_log import OperationLog
from backend.config.config import Config
from backend.services.export_service import export_prediction_excel, export_prediction_pdf, get_prediction_details
from routes.auth import login_required
import os
import io
from datetime import datetime

history_bp = Blueprint('history', __name__)

# 初始化模型
db_path = Config.DATABASE_PATH
prediction_model = Prediction(db_path)
log_model = OperationLog()

@history_bp.route('/prediction/history')
@login_required
def history_page():
    """预测历史记录页面"""
    return render_template('history.html')

@history_bp.route('/api/prediction/history')
@login_required
def api_prediction_history():
    """获取预测历史记录，支持关键字搜索和时间筛选"""
    user_id = session.get('user_id')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    keyword = request.args.get('keyword', '').strip() or None
    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None

    records, total = prediction_model.get_predictions(
        user_id,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        limit=page_size,
        offset=(page-1)*page_size
    )

    history = []
    for r in records:
        history.append({
            'id': r['id'],
            'project_name': r['project_name'] or '',
            'prediction_time': r['prediction_time'],
            'location_filter': r['location_filter'],
            'method_filter': r['method_filter'],
            'date_from': r.get('date_from') or '',
            'date_to': r.get('date_to') or '',
            'data_count': r['data_count'],
            'method_prediction': r['method_prediction'],
            'method_confidence': r['method_confidence'],
            'k1_prediction': r['k1_prediction'],
            'k1_confidence': r['k1_confidence'],
            'k1_method': r['k1_method'],
            'q1_prediction': r['q1_prediction'],
            'q1_confidence': r['q1_confidence'],
            'q1_method': r['q1_method'],
            'used_ai': bool(r['used_ai'])
        })

    return jsonify({
        'success': True,
        'total': total,
        'page': page,
        'page_size': page_size,
        'history': history
    })

@history_bp.route('/api/prediction/delete', methods=['POST'])
@login_required
def api_delete_prediction():
    """删除单条预测记录"""
    user_id = session.get('user_id')
    data = request.get_json()
    record_id = data.get('id')

    if not record_id:
        return jsonify({'success': False, 'error': '记录 ID 不能为空'})

    success = prediction_model.delete_prediction(record_id, user_id)
    if success:
        log_model.log(
            user_id=user_id,
            username=session.get('username', 'unknown'),
            action='DELETE',
            module='预测历史',
            table_name='prediction_records',
            record_id=record_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )
        return jsonify({'success': True, 'message': '删除成功'})
    else:
        log_model.log(
            user_id=user_id,
            username=session.get('username', 'unknown'),
            action='DELETE',
            module='预测历史',
            table_name='prediction_records',
            record_id=record_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='failed',
            error_message='记录不存在或无权删除'
        )
        return jsonify({'success': False, 'error': '删除失败或记录不存在'})

@history_bp.route('/api/prediction/clear', methods=['POST'])
@login_required
def api_clear_predictions():
    """清空所有预测记录"""
    user_id = session.get('user_id')
    deleted_count = prediction_model.clear_all_predictions(user_id)
    
    log_model.log(
        user_id=user_id,
        username=session.get('username', 'unknown'),
        action='CLEAR',
        module='预测历史',
        table_name='prediction_records',
        new_value={'deleted_count': deleted_count},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', ''),
        status='success'
    )
    
    return jsonify({
        'success': True,
        'message': f'已清空 {deleted_count} 条预测记录',
        'deleted_count': deleted_count
    })

# ============================================================
# 导出 API
# ============================================================

@history_bp.route('/api/prediction/export/<int:record_id>/<format>')
@login_required
def api_export_prediction(record_id, format):
    """导出单条预测记录为 Excel 或 PDF"""
    user_id = session.get('user_id')
    
    record, k1_algorithms, q1_algorithms = get_prediction_details(record_id, user_id)
    if not record:
        return jsonify({'success': False, 'error': '记录不存在'}), 404
    
    project_name = (record.get('project_name') or '预测').replace('/', '_').replace('\\', '_')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        if format == 'excel':
            data = export_prediction_excel(record, k1_algorithms, q1_algorithms)
            filename = f"预测报告_{project_name}_{timestamp}.xlsx"
            return send_file(
                io.BytesIO(data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
        elif format == 'pdf':
            data = export_prediction_pdf(record, k1_algorithms, q1_algorithms)
            filename = f"预测报告_{project_name}_{timestamp}.pdf"
            return send_file(
                io.BytesIO(data),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({'success': False, 'error': '不支持的格式'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'导出失败: {str(e)}'}), 500