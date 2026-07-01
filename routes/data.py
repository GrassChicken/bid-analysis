#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管理路由模块 - V6.0
处理数据导入、导出、查看、删除等操作
完整移植 V5.0 数据管理页面功能
"""

from flask import Blueprint, render_template, session, jsonify, request, send_file
from backend.models.bid_record import BidRecord
from backend.models.operation_log import OperationLog
from backend.config.config import Config
from routes.auth import login_required
import pandas as pd
import sqlite3
import os
import io
import json
import re
from datetime import datetime
import uuid
from pathlib import Path

data_bp = Blueprint('data', __name__)
db_path = Config.DATABASE_PATH
bid_record_model = BidRecord(db_path)
log_model = OperationLog(db_path)


# ============================================================
# 页面路由
# ============================================================

@data_bp.route('/data')
@login_required
def data_page():
    """数据管理页面"""
    return render_template('data.html')



# ============================================================
# API 路由
# ============================================================

@data_bp.route('/api/data/list')
@login_required
def api_data_list():
    """获取数据列表及统计信息"""
    user_id = session.get('user_id')

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 获取所有记录
        cursor.execute('''
            SELECT id, project_name, bid_date, bid_time, bid_location,
                   method_category, k2_value, k1_value, q1_value,
                   import_time
            FROM bid_records
            WHERE user_id = ?
            ORDER BY bid_date DESC, bid_time DESC
        ''', (user_id,))
        records = [dict(row) for row in cursor.fetchall()]

        # 获取开标地点列表
        cursor.execute('''
            SELECT DISTINCT bid_location FROM bid_records
            WHERE user_id = ? AND bid_location IS NOT NULL AND bid_location != ''
            ORDER BY bid_location
        ''', (user_id,))
        locations = [row['bid_location'] for row in cursor.fetchall() if row['bid_location']]

        return jsonify({
            'success': True,
            'records': records,
            'locations': locations
        })
    finally:
        conn.close()


@data_bp.route('/api/data/import', methods=['POST'])
@login_required
def api_data_import():
    """导入 Excel 数据（支持多 Sheet、多格式日期/时间、参数校验）"""
    user_id = session.get('user_id')

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未找到文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'})

    try:
        # 读取 Excel 文件的所有 sheet 页
        excel_file = pd.ExcelFile(file, engine='openpyxl')
        sheet_names = excel_file.sheet_names

        all_dfs = []

        for sheet_name in sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')

            # 验证必需列
            required_cols = ['开标日期', '开标时间', '项目名称', '开标地点', '方法类别', 'K2', 'K1', 'Q1']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return jsonify({
                    'success': False,
                    'error': f'Sheet "{sheet_name}" 缺少列: {", ".join(missing_cols)}'
                })

            # 处理日期
            def parse_date(val):
                if pd.isna(val):
                    return pd.NaT
                if isinstance(val, (pd.Timestamp, datetime)):
                    return val
                val_str = str(val).strip()
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y%m%d']:
                    try:
                        return datetime.strptime(val_str, fmt)
                    except Exception:
                        continue
                return pd.to_datetime(val_str, errors='coerce')

            df['开标日期'] = df['开标日期'].apply(parse_date)
            df = df.dropna(subset=['开标日期'])
            df['开标日期'] = df['开标日期'].dt.strftime('%Y-%m-%d')

            # 处理时间
            def parse_time(val):
                if pd.isna(val) or str(val).strip() == '':
                    return ''
                val_str = str(val).strip()
                if ':' in val_str:
                    parts = val_str.split(':')
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    return f"{hour:02d}:{minute:02d}"
                elif val_str.isdigit():
                    if len(val_str) == 3:
                        return f"0{val_str[0]}:{val_str[1:]}"
                    elif len(val_str) == 4:
                        return f"{val_str[:2]}:{val_str[2:]}"
                return val_str

            df['开标时间'] = df['开标时间'].apply(parse_time)
            all_dfs.append(df)

        df = pd.concat(all_dfs, ignore_index=True)

        # 验证项目名称唯一性
        duplicates = df[df['项目名称'].duplicated()]['项目名称'].tolist()
        if duplicates:
            return jsonify({
                'success': False,
                'error': f'项目名称必须唯一，发现重复: {duplicates[0]}'
            })

        # K2/K1/Q1 值范围校验
        validation_warnings = []

        for idx, row in df.iterrows():
            project_name = row['项目名称'] if pd.notna(row['项目名称']) else f'第{idx+1}行'

            # K2 校验
            if pd.notna(row['K2']) and str(row['K2']).strip() != '':
                try:
                    k2_val = float(row['K2'])
                    if k2_val < 0.86 or k2_val > 1.0:
                        validation_warnings.append(f'📍 {project_name}: K2 值 {k2_val} 超出范围 (0.86~1.0)')
                except (ValueError, TypeError):
                    validation_warnings.append(f'📍 {project_name}: K2 值 "{row["K2"]}" 不是有效数字')

            # K1 校验
            if pd.isna(row['K1']) or str(row['K1']).strip() == '':
                validation_warnings.append(f'📍 {project_name}: K1 值不能为空')
            else:
                try:
                    k1_val = float(row['K1'])
                    if k1_val < 0.95 or k1_val > 0.98:
                        validation_warnings.append(f'📍 {project_name}: K1 值 {k1_val} 超出范围 (0.95~0.98)')
                except (ValueError, TypeError):
                    validation_warnings.append(f'📍 {project_name}: K1 值 "{row["K1"]}" 不是有效数字')

            # Q1 校验
            method_val = ''
            if pd.notna(row['方法类别']):
                method_raw = row['方法类别']
                if isinstance(method_raw, (int, float)):
                    method_val = str(int(float(method_raw)))
                else:
                    method_val = str(method_raw).strip().replace('.0', '')

            if method_val == '1':
                if pd.notna(row['Q1']) and str(row['Q1']).strip() != '':
                    validation_warnings.append(f'📍 {project_name}: 方法类别为 1 时，Q1 值必须为空')
            elif method_val == '2':
                if pd.isna(row['Q1']) or str(row['Q1']).strip() == '':
                    validation_warnings.append(f'📍 {project_name}: 方法类别为 2 时，Q1 值不能为空')
                else:
                    try:
                        q1_val = float(row['Q1'])
                        if q1_val < 0.65 or q1_val > 0.85:
                            validation_warnings.append(f'📍 {project_name}: Q1 值 {q1_val} 超出范围 (0.65~0.85)')
                    except (ValueError, TypeError):
                        validation_warnings.append(f'📍 {project_name}: Q1 值 "{row["Q1"]}" 不是有效数字')

        # 限制警告数量
        if len(validation_warnings) > 50:
            validation_warnings = validation_warnings[:50]
            validation_warnings.append(f'... 还有更多警告未显示')

        # 导入数据库（项目名称为唯一 key，存在则更新，不存在则插入）
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        imported_count = 0
        inserted_count = 0
        updated_count = 0

        for _, row in df.iterrows():
            try:
                method_val = ''
                if pd.notna(row['方法类别']):
                    method_raw = row['方法类别']
                    if isinstance(method_raw, (int, float)):
                        method_val = str(int(float(method_raw)))
                    else:
                        method_val = str(method_raw).strip().replace('.0', '')

                # 先检查是否已存在（按 user_id + project_name）
                cursor.execute('''
                    SELECT id FROM bid_records
                    WHERE user_id = ? AND project_name = ?
                ''', (user_id, row['项目名称']))
                existing = cursor.fetchone()

                # 使用北京时间
                beijing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if existing:
                    # 存在则更新
                    cursor.execute('''
                        UPDATE bid_records
                        SET bid_date = ?, bid_time = ?, bid_location = ?,
                            method_category = ?, k2_value = ?, k1_value = ?, q1_value = ?,
                            import_time = ?
                        WHERE user_id = ? AND project_name = ?
                    ''', (
                        row['开标日期'],
                        str(row['开标时间']) if pd.notna(row['开标时间']) else '',
                        row['开标地点'],
                        method_val,
                        str(row['K2']) if pd.notna(row['K2']) else '',
                        str(row['K1']) if pd.notna(row['K1']) else '',
                        str(row['Q1']) if pd.notna(row['Q1']) else '',
                        beijing_time,
                        user_id,
                        row['项目名称']
                    ))
                    updated_count += 1
                else:
                    # 不存在则插入
                    cursor.execute('''
                        INSERT INTO bid_records
                        (user_id, project_name, bid_date, bid_time, bid_location,
                         method_category, k2_value, k1_value, q1_value, import_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        row['项目名称'],
                        row['开标日期'],
                        str(row['开标时间']) if pd.notna(row['开标时间']) else '',
                        row['开标地点'],
                        method_val,
                        str(row['K2']) if pd.notna(row['K2']) else '',
                        str(row['K1']) if pd.notna(row['K1']) else '',
                        str(row['Q1']) if pd.notna(row['Q1']) else '',
                        beijing_time
                    ))
                    inserted_count += 1

                imported_count += 1
            except Exception as e:
                print(f"导入单行失败: {e}")
                continue

        conn.commit()
        conn.close()

        # 记录操作日志
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='IMPORT',
            module='数据管理',
            table_name='bid_records',
            new_value={
                'filename': file.filename,
                'imported_count': imported_count,
                'inserted_count': inserted_count,
                'updated_count': updated_count,
                'sheets': len(sheet_names)
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )

        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'inserted_count': inserted_count,
            'updated_count': updated_count,
            'validation_warnings': validation_warnings,
            'warning_count': len(validation_warnings)
        })

    except Exception as e:
        log_model.log(
            user_id=session.get('user_id'),
            username=session.get('username'),
            action='IMPORT',
            module='数据管理',
            table_name='bid_records',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='failure',
            error_message=str(e)
        )
        return jsonify({'success': False, 'error': str(e)}), 500


@data_bp.route('/api/data/template')
@login_required
def api_data_template():
    """下载 Excel 模板（多 Sheet 页）"""

    def generate_sample_data(start_idx, count, locations, method):
        data = []
        from datetime import timedelta
        for i in range(count):
            idx = start_idx + i
            base_date = datetime(2025, 1, 1)
            date = base_date + timedelta(days=idx % 365)

            hour = 9 + (idx % 8)
            minute = 0 if idx % 2 == 0 else 30
            time_str = f"{hour:02d}:{minute:02d}"

            project_type = '建筑施工' if idx % 3 == 0 else ('市政工程' if idx % 3 == 1 else '设备采购')
            project_name = f"江苏省{project_type}项目-{idx:03d}"
            location = locations[idx % len(locations)]
            method_category = method

            k2 = 0.92 + (idx % 13) * 0.005
            k1 = 0.955 + (idx % 6) * 0.005
            q1 = '' if method == '1' else f"{0.80 + (idx % 6) * 0.01:.2f}"

            data.append({
                '开标日期': date.strftime('%Y-%m-%d'),
                '开标时间': time_str,
                '项目名称': project_name,
                '开标地点': location,
                '方法类别': method_category,
                'K2': f"{k2:.2f}",
                'K1': f"{k1:.3f}",
                'Q1': q1
            })
        return data

    nanjing_locations = ['南京市公共资源交易中心', '南京市江宁分中心', '南京市浦口分中心', '南京市六合分中心']
    suzhou_locations = ['苏州市公共资源交易中心', '苏州市昆山分中心', '苏州市常熟分中心', '苏州市太仓分中心']
    mixed_locations = nanjing_locations + suzhou_locations

    nanjing_data = generate_sample_data(0, 75, nanjing_locations, '1')
    suzhou_data = generate_sample_data(100, 75, suzhou_locations, '2')

    mixed_data = []
    from datetime import timedelta
    for i in range(75):
        idx = 200 + i
        base_date = datetime(2025, 1, 1)
        date = base_date + timedelta(days=idx % 365)
        hour = 9 + (idx % 8)
        minute = 0 if idx % 2 == 0 else 30
        time_str = f"{hour:02d}:{minute:02d}"
        project_type = '建筑施工' if idx % 3 == 0 else ('市政工程' if idx % 3 == 1 else '设备采购')
        project_name = f"江苏省{project_type}项目-{idx:03d}"
        location = mixed_locations[idx % len(mixed_locations)]
        method_category = '1' if idx % 2 == 0 else '2'
        k2 = 0.92 + (idx % 13) * 0.005
        k1 = 0.955 + (idx % 6) * 0.005
        q1 = '' if method_category == '1' else f"{0.80 + (idx % 6) * 0.01:.2f}"
        mixed_data.append({
            '开标日期': date.strftime('%Y-%m-%d'),
            '开标时间': time_str,
            '项目名称': project_name,
            '开标地点': location,
            '方法类别': method_category,
            'K2': f"{k2:.2f}",
            'K1': f"{k1:.3f}",
            'Q1': q1
        })

    df_nanjing = pd.DataFrame(nanjing_data)
    df_suzhou = pd.DataFrame(suzhou_data)
    df_mixed = pd.DataFrame(mixed_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_nanjing.to_excel(writer, index=False, sheet_name='南京地区')
        df_suzhou.to_excel(writer, index=False, sheet_name='苏州地区')
        df_mixed.to_excel(writer, index=False, sheet_name='混合地区')

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='开标记录导入模板_V6.0.xlsx'
    )


@data_bp.route('/api/data/delete', methods=['POST'])
@login_required
def api_data_delete():
    """删除单条开标记录"""
    user_id = session.get('user_id')
    data = request.get_json()
    record_id = data.get('id')

    if not record_id:
        return jsonify({'success': False, 'error': '记录 ID 不能为空'})

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 验证记录属于当前用户
        cursor.execute('SELECT id, project_name FROM bid_records WHERE id = ? AND user_id = ?', (record_id, user_id))
        record = cursor.fetchone()

        if not record:
            return jsonify({'success': False, 'error': '记录不存在或不属于当前用户'})

        # 删除记录
        cursor.execute('DELETE FROM bid_records WHERE id = ? AND user_id = ?', (record_id, user_id))
        conn.commit()

        # 记录操作日志
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='DELETE',
            module='数据管理',
            table_name='bid_records',
            record_id=record_id,
            old_value={'project_name': record['project_name']},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )

        return jsonify({'success': True})
    except Exception as e:
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='DELETE',
            module='数据管理',
            table_name='bid_records',
            record_id=record_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='failure',
            error_message=str(e)
        )
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@data_bp.route('/api/data/delete-batch', methods=['POST'])
@login_required
def api_data_delete_batch():
    """批量删除开标记录"""
    user_id = session.get('user_id')
    data = request.get_json()
    ids = data.get('ids', [])

    if not ids:
        return jsonify({'success': False, 'error': '请选择要删除的记录'})

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        placeholders = ','.join('?' for _ in ids)

        # 验证记录属于当前用户
        cursor.execute(
            f'SELECT id, project_name FROM bid_records WHERE id IN ({placeholders}) AND user_id = ?',
            ids + [user_id]
        )
        records = cursor.fetchall()

        if len(records) != len(ids):
            return jsonify({'success': False, 'error': '部分记录不属于当前用户或不存在'})

        # 删除记录
        cursor.execute(
            f'DELETE FROM bid_records WHERE id IN ({placeholders}) AND user_id = ?',
            ids + [user_id]
        )
        deleted_count = cursor.rowcount
        conn.commit()

        # 记录操作日志
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='DELETE',
            module='数据管理',
            table_name='bid_records',
            old_value={
                'deleted_count': deleted_count,
                'project_names': [r['project_name'] for r in records]
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )

        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='DELETE',
            module='数据管理',
            table_name='bid_records',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='failure',
            error_message=str(e)
        )
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@data_bp.route('/api/data/clear', methods=['POST'])
@login_required
def api_data_clear():
    """清空所有开标记录"""
    user_id = session.get('user_id')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM bid_records WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()

        # 记录操作日志
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='DELETE',
            module='数据管理',
            table_name='bid_records',
            new_value={'deleted_count': deleted_count},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )

        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='DELETE',
            module='数据管理',
            table_name='bid_records',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='failure',
            error_message=str(e)
        )
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@data_bp.route('/api/data/export', methods=['POST'])
@login_required
def api_data_export():
    """导出数据为 Excel 文件（支持过滤后导出）"""
    user_id = session.get('user_id')

    try:
        data = request.get_json()
        export_filtered = data.get('exportFiltered', False) if data else False
        filtered_ids = data.get('filteredIds', []) if data else []

        if filtered_ids and not isinstance(filtered_ids, list):
            try:
                filtered_ids = list(filtered_ids)
            except Exception:
                filtered_ids = []

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if export_filtered and filtered_ids:
            placeholders = ','.join('?' for _ in filtered_ids)
            sql = f'''
                SELECT id, project_name, bid_date, bid_time, bid_location,
                       method_category, k2_value, k1_value, q1_value
                FROM bid_records
                WHERE user_id = ? AND id IN ({placeholders})
                ORDER BY bid_date DESC, bid_time DESC
            '''
            cursor.execute(sql, [user_id] + filtered_ids)
        else:
            cursor.execute('''
                SELECT id, project_name, bid_date, bid_time, bid_location,
                       method_category, k2_value, k1_value, q1_value
                FROM bid_records
                WHERE user_id = ?
                ORDER BY bid_date DESC, bid_time DESC
            ''', (user_id,))

        records = cursor.fetchall()
        conn.close()

        if not records:
            return jsonify({'success': False, 'error': '没有数据可导出'})

        # 创建 DataFrame
        df_data = []
        for r in records:
            df_data.append({
                '开标日期': r['bid_date'],
                '开标时间': r['bid_time'],
                '项目名称': r['project_name'],
                '开标地点': r['bid_location'],
                '方法类别': r['method_category'],
                'K2': r['k2_value'],
                'K1': r['k1_value'],
                'Q1': r['q1_value']
            })

        df = pd.DataFrame(df_data)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'开标记录_{timestamp}.xlsx'

        # 保存到临时目录
        from backend.config.config import Config
        upload_folder = Config.UPLOAD_FOLDER
        temp_dir = Path(upload_folder) / 'exports'
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / filename

        df.to_excel(file_path, index=False, engine='openpyxl')

        # 记录操作日志
        log_model.log(
            user_id=user_id,
            username=session.get('username'),
            action='EXPORT',
            module='数据管理',
            table_name='bid_records',
            new_value={'count': len(records), 'filename': filename},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            status='success'
        )

        return jsonify({
            'success': True,
            'count': len(records),
            'filename': filename
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@data_bp.route('/api/data/download/<filename>')
@login_required
def api_data_download(filename):
    """下载导出的文件"""
    try:
        from backend.config.config import Config
        upload_folder = Config.UPLOAD_FOLDER
        file_path = Path(upload_folder) / 'exports' / filename

        if not file_path.exists():
            return jsonify({'success': False, 'error': '文件不存在'}), 404

        return send_file(
            str(file_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
