#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能诊断引擎路由模块
"""

from flask import Blueprint, render_template, session, jsonify, request
from backend.services.diagnostic_engine import DiagnosticEngine
from routes.auth import login_required

diagnosis_bp = Blueprint('diagnosis', __name__)
diagnostic_engine = DiagnosticEngine()


@diagnosis_bp.route('/diagnosis')
@login_required
def diagnosis_page():
    """智能诊断页面"""
    return render_template('diagnosis.html')


@diagnosis_bp.route('/api/diagnosis/anomaly', methods=['POST'])
@login_required
def api_diagnosis_anomaly():
    """异常诊断 API"""
    user_id = session.get('user_id')
    data = request.get_json()

    result = diagnostic_engine.diagnose_anomaly(
        user_id=user_id,
        k1_pred=data.get('k1_pred'),
        q1_pred=data.get('q1_pred'),
        method_pred=data.get('method_pred'),
        location=data.get('location'),
        method_category=data.get('method_category'),
        date_from=data.get('date_from'),
        date_to=data.get('date_to'),
    )

    return jsonify({'success': True, **result})


@diagnosis_bp.route('/api/diagnosis/performance')
@login_required
def api_diagnosis_performance():
    """算法表现评估 API"""
    user_id = session.get('user_id')
    result = diagnostic_engine.evaluate_algorithm_performance(user_id)
    return jsonify({'success': True, **result})


@diagnosis_bp.route('/api/diagnosis/calibration')
@login_required
def api_diagnosis_calibration():
    """置信度校准 API"""
    user_id = session.get('user_id')
    result = diagnostic_engine.calibrate_confidence(user_id)
    return jsonify({'success': True, **result})
