#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据备份与恢复路由模块
仅管理员可操作
"""

from flask import Blueprint, render_template, session, jsonify, request, send_file
from functools import wraps
from backend.services.backup_service import BackupService
from backend.models.operation_log import OperationLog
from routes.auth import login_required

backup_bp = Blueprint('backup', __name__)
backup_service = BackupService()
log_model = OperationLog()


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            return jsonify({'success': False, 'error': '仅管理员可操作', 'require_admin': True}), 403
        return f(*args, **kwargs)
    return decorated_function


# 备份管理页面
@backup_bp.route('/admin/backup')
@login_required
@admin_required
def backup_page():
    """数据备份管理页面"""
    return render_template('backup.html')


# API: 创建备份
@backup_bp.route('/api/backup/create', methods=['POST'])
@login_required
@admin_required
def api_create_backup():
    """手动创建备份"""
    result = backup_service.create_backup('manual')

    if result['success']:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username', 'unknown'),
            action='BACKUP_CREATE',
            module='数据备份',
            table_name='backups',
            new_value={
                'filename': result['filename'],
                'size': result['size'],
                'type': 'manual'
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )
        result['size_display'] = BackupService._format_size(result['size'])

    return jsonify(result)


# API: 备份列表
@backup_bp.route('/api/backup/list')
@login_required
@admin_required
def api_list_backups():
    """获取备份列表"""
    backups = backup_service.list_backups()
    return jsonify({'success': True, 'backups': backups})


# API: 恢复备份
@backup_bp.route('/api/backup/restore', methods=['POST'])
@login_required
@admin_required
def api_restore_backup():
    """恢复备份"""
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({'success': False, 'error': '请指定要恢复的备份文件'})

    result = backup_service.restore_backup(filename)

    if result['success']:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username', 'unknown'),
            action='BACKUP_RESTORE',
            module='数据备份',
            table_name='backups',
            new_value={
                'filename': filename,
                'pre_backup': result.get('pre_backup')
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )
    else:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username', 'unknown'),
            action='BACKUP_RESTORE',
            module='数据备份',
            table_name='backups',
            new_value={'filename': filename},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='failed',
            error_message=result.get('error')
        )

    return jsonify(result)


# API: 删除备份
@backup_bp.route('/api/backup/delete', methods=['POST'])
@login_required
@admin_required
def api_delete_backup():
    """删除备份"""
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({'success': False, 'error': '请指定要删除的备份文件'})

    result = backup_service.delete_backup(filename)

    if result['success']:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username', 'unknown'),
            action='BACKUP_DELETE',
            module='数据备份',
            table_name='backups',
            new_value={'filename': filename},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )

    return jsonify(result)


# API: 下载备份
@backup_bp.route('/api/backup/download')
@login_required
@admin_required
def api_download_backup():
    """下载备份文件"""
    filename = request.args.get('filename')

    if not filename:
        return jsonify({'success': False, 'error': '请指定要下载的备份文件'})

    filepath = backup_service.download_backup(filename)
    if not filepath:
        return jsonify({'success': False, 'error': '备份文件不存在'})

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/gzip'
    )


# API: 清理旧备份
@backup_bp.route('/api/backup/cleanup', methods=['POST'])
@login_required
@admin_required
def api_cleanup_backups():
    """清理旧备份"""
    data = request.get_json() or {}
    keep_days = data.get('keep_days', 7)
    keep_count = data.get('keep_count', 10)

    result = backup_service.cleanup_old_backups(keep_days, keep_count)

    if result['success'] and result['deleted'] > 0:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username', 'unknown'),
            action='BACKUP_CLEANUP',
            module='数据备份',
            table_name='backups',
            new_value={
                'keep_days': keep_days,
                'keep_count': keep_count,
                'deleted': result['deleted']
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )

    return jsonify(result)
