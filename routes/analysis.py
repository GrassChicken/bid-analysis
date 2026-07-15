"""
数据分析路由
"""
from flask import Blueprint, render_template, jsonify, request, session
from routes.auth import login_required
from backend.config.config import Config
import sqlite3

analysis_bp = Blueprint('analysis', __name__)

db_path = Config.DATABASE_PATH


@analysis_bp.route('/analysis/')
@login_required
def index():
    """数据分析主页"""
    return render_template('analysis.html')


@analysis_bp.route('/api/analysis/distribution')
@login_required
def get_distribution_data():
    """
    获取参数分布数据
    参数:
        param_type: k1/k2/q1
        location: 地区筛选（可选）
        method: 方法筛选（可选）
        date_from: 开始日期（可选）
        date_to: 结束日期（可选）
    """
    param_type = request.args.get('param_type', 'k1')
    location = request.args.get('location')
    method = request.args.get('method')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # 验证参数
    if param_type not in ['k1', 'k2', 'q1']:
        return jsonify({'success': False, 'error': '参数类型无效'}), 400
    
    db = sqlite3.connect(db_path)
    user_id = session.get('user_id')
    
    try:
        # 构建查询
        param_column = f'{param_type}_value'
        query = f"""
            SELECT {param_column}, bid_date, bid_time, bid_location, method_category
            FROM bid_records
            WHERE user_id = ? AND {param_column} IS NOT NULL
        """
        params = [user_id]
        
        # 添加筛选条件
        if location:
            query += " AND bid_location = ?"
            params.append(location)
        
        if method:
            query += " AND method_category = ?"
            params.append(method)
        
        if date_from:
            query += " AND (bid_date || ' ' || COALESCE(bid_time, '00:00')) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND (bid_date || ' ' || COALESCE(bid_time, '00:00')) <= ?"
            params.append(date_to)
        
        query += " ORDER BY bid_date, bid_time"
        
        cursor = db.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({
                'success': True,
                'data': [],
                'stats': None,
                'message': '没有找到符合条件的数据'
            })
        
        # 提取数值
        values = []
        locations = set()
        methods = set()
        
        for row in rows:
            value = row[0]
            if value is not None:
                try:
                    value = float(value)
                    values.append(value)
                    locations.add(row[3])
                    methods.add(row[4])
                except (ValueError, TypeError):
                    pass
        
        if not values:
            return jsonify({
                'success': True,
                'data': [],
                'stats': None,
                'message': '没有有效的数值数据'
            })
        
        # 计算统计信息
        import statistics
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        stats = {
            'count': n,
            'mean': round(statistics.mean(values), 4),
            'std': round(statistics.stdev(values), 4) if n > 1 else 0,
            'min': round(min(values), 4),
            'max': round(max(values), 4),
            'median': round(statistics.median(values), 4),
        }
        
        # 计算四分位数
        if n >= 4:
            q1_idx = n // 4
            q3_idx = (3 * n) // 4
            stats['q1'] = round(sorted_values[q1_idx], 4)
            stats['q3'] = round(sorted_values[q3_idx], 4)
            stats['iqr'] = round(stats['q3'] - stats['q1'], 4)
        
        # 计算偏度和峰度
        if n >= 3:
            mean = stats['mean']
            std = stats['std']
            if std > 0:
                skewness = sum((x - mean) ** 3 for x in values) / (n * std ** 3)
                kurtosis = sum((x - mean) ** 4 for x in values) / (n * std ** 4) - 3
                stats['skewness'] = round(skewness, 4)
                stats['kurtosis'] = round(kurtosis, 4)
        
        # 按地区分组计算统计（用于箱线图）
        location_stats = {}
        location_values = {}
        
        for row in rows:
            value = row[0]
            location = row[3]
            if value is not None:
                try:
                    value = float(value)
                    if location not in location_values:
                        location_values[location] = []
                    location_values[location].append(value)
                except (ValueError, TypeError):
                    pass
        
        # 计算每个地区的统计
        for loc, vals in location_values.items():
            if len(vals) >= 2:
                sorted_vals = sorted(vals)
                n_loc = len(sorted_vals)
                loc_stats = {
                    'location': loc,
                    'count': n_loc,
                    'mean': round(statistics.mean(vals), 4),
                    'min': round(min(vals), 4),
                    'max': round(max(vals), 4),
                    'median': round(statistics.median(vals), 4),
                }
                if n_loc >= 4:
                    q1_idx = n_loc // 4
                    q3_idx = (3 * n_loc) // 4
                    loc_stats['q1'] = round(sorted_vals[q1_idx], 4)
                    loc_stats['q3'] = round(sorted_vals[q3_idx], 4)
                
                # 检测异常值（1.5倍IQR规则）
                if 'q1' in loc_stats and 'q3' in loc_stats:
                    iqr = loc_stats['q3'] - loc_stats['q1']
                    lower_bound = loc_stats['q1'] - 1.5 * iqr
                    upper_bound = loc_stats['q3'] + 1.5 * iqr
                    outliers = [v for v in vals if v < lower_bound or v > upper_bound]
                    loc_stats['outliers'] = [round(v, 4) for v in outliers]
                
                location_stats[loc] = loc_stats
        
        return jsonify({
            'success': True,
            'data': values,
            'stats': stats,
            'location_stats': location_stats,
            'locations': list(locations),
            'methods': list(methods)
        })
        
    except Exception as e:
        print(f"获取分布数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/heatmap')
@login_required
def get_heatmap_data():
    """
    获取热力图数据
    参数:
        dimension: 分析维度 - 'location_time'（地区×月份）或 'location_method'（地区×方法）
        param_type: k1/k2/q1
        metric: 指标 - 'mean'（均值）或 'count'（频次）
        date_from/date_to: 日期范围（可选）
    返回:
        热力图矩阵数据
    """
    dimension = request.args.get('dimension', 'location_time')
    param_type = request.args.get('param_type', 'k1')
    metric = request.args.get('metric', 'mean')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # 验证参数
    if dimension not in ['location_time', 'location_method']:
        return jsonify({'success': False, 'error': '分析维度无效'}), 400
    if param_type not in ['k1', 'k2', 'q1']:
        return jsonify({'success': False, 'error': '参数类型无效'}), 400
    if metric not in ['mean', 'count']:
        return jsonify({'success': False, 'error': '指标类型无效'}), 400
    
    db = sqlite3.connect(db_path)
    user_id = session.get('user_id')
    
    try:
        param_column = f'{param_type}_value'
        
        # 根据维度构建不同的查询
        if dimension == 'location_time':
            # 地区 × 月份
            query = f"""
                SELECT {param_column}, bid_location, 
                       strftime('%Y-%m', bid_date) as month
                FROM bid_records
                WHERE user_id = ? AND {param_column} IS NOT NULL
            """
            params = [user_id]
            
            if date_from:
                query += " AND bid_date >= ?"
                params.append(date_from)
            if date_to:
                query += " AND bid_date <= ?"
                params.append(date_to)
            
            cursor = db.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return jsonify({
                    'success': True,
                    'data': [],
                    'locations': [],
                    'time_labels': [],
                    'message': '没有找到符合条件的数据'
                })
            
            # 整理数据：地区×月份矩阵
            location_month_data = {}  # {location: {month: [values]}}
            all_locations = set()
            all_months = set()
            
            for row in rows:
                value, location, month = row
                if value is not None and location and month:
                    try:
                        value = float(value)
                        all_locations.add(location)
                        all_months.add(month)
                        
                        if location not in location_month_data:
                            location_month_data[location] = {}
                        if month not in location_month_data[location]:
                            location_month_data[location][month] = []
                        location_month_data[location][month].append(value)
                    except (ValueError, TypeError):
                        pass
            
            # 排序
            locations = sorted(all_locations)
            time_labels = sorted(all_months)
            
            # 构建热力图数据 [x_index, y_index, value]
            heatmap_data = []
            
            for loc_idx, location in enumerate(locations):
                for time_idx, month in enumerate(time_labels):
                    if location in location_month_data and month in location_month_data[location]:
                        values = location_month_data[location][month]
                        if metric == 'mean':
                            cell_value = round(sum(values) / len(values), 4)
                        else:  # count
                            cell_value = len(values)
                        heatmap_data.append([time_idx, loc_idx, cell_value])
            
            return jsonify({
                'success': True,
                'data': heatmap_data,
                'locations': locations,
                'time_labels': time_labels,
                'dimension': dimension,
                'metric': metric
            })
            
        else:  # location_method
            # 地区 × 方法类别
            query = f"""
                SELECT {param_column}, bid_location, method_category
                FROM bid_records
                WHERE user_id = ? AND {param_column} IS NOT NULL
            """
            params = [user_id]
            
            if date_from:
                query += " AND bid_date >= ?"
                params.append(date_from)
            if date_to:
                query += " AND bid_date <= ?"
                params.append(date_to)
            
            cursor = db.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return jsonify({
                    'success': True,
                    'data': [],
                    'locations': [],
                    'methods': [],
                    'message': '没有找到符合条件的数据'
                })
            
            # 整理数据：地区×方法矩阵
            location_method_data = {}  # {location: {method: [values]}}
            all_locations = set()
            all_methods = set()
            
            for row in rows:
                value, location, method = row
                if value is not None and location and method:
                    try:
                        value = float(value)
                        all_locations.add(location)
                        all_methods.add(str(method))
                        
                        if location not in location_method_data:
                            location_method_data[location] = {}
                        if method not in location_method_data[location]:
                            location_method_data[location][method] = []
                        location_method_data[location][method].append(value)
                    except (ValueError, TypeError):
                        pass
            
            # 排序
            locations = sorted(all_locations)
            methods = sorted(all_methods)
            
            # 构建热力图数据
            heatmap_data = []
            
            for loc_idx, location in enumerate(locations):
                for method_idx, method in enumerate(methods):
                    if location in location_method_data and method in location_method_data[location]:
                        values = location_method_data[location][method]
                        if metric == 'mean':
                            cell_value = round(sum(values) / len(values), 4)
                        else:  # count
                            cell_value = len(values)
                        heatmap_data.append([method_idx, loc_idx, cell_value])
            
            return jsonify({
                'success': True,
                'data': heatmap_data,
                'locations': locations,
                'methods': methods,
                'dimension': dimension,
                'metric': metric
            })
    
    except Exception as e:
        print(f"获取热力图数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@analysis_bp.route('/api/analysis/trend')
@login_required
def get_trend_data():
    """
    获取趋势分析数据
    参数:
        param_types: 参数类型列表（逗号分隔），如 k1,k2,q1
        granularity: 时间粒度 - day/week/month/quarter
        locations: 地区列表（逗号分隔，可选）
        methods: 方法类别列表（逗号分隔，可选）
        date_from/date_to: 日期范围
        moving_avg: 移动平均天数（7或30，可选）
    """
    param_types = request.args.get('param_types', 'k1').split(',')
    granularity = request.args.get('granularity', 'month')
    locations = request.args.get('locations', '').split(',') if request.args.get('locations') else []
    methods = request.args.get('methods', '').split(',') if request.args.get('methods') else []
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    moving_avg_days = request.args.get('moving_avg', type=int)
    
    # 验证参数
    valid_params = ['k1', 'k2', 'q1']
    for pt in param_types:
        if pt not in valid_params:
            return jsonify({'success': False, 'error': f'无效的参数类型: {pt}'}), 400
    
    if granularity not in ['day', 'week', 'month', 'quarter']:
        return jsonify({'success': False, 'error': '无效的时间粒度'}), 400
    
    if moving_avg_days and moving_avg_days not in [7, 30]:
        return jsonify({'success': False, 'error': '移动平均只支持7或30天'}), 400
    
    db = sqlite3.connect(db_path)
    user_id = session.get('user_id')
    
    try:
        # 根据粒度构建时间分组表达式
        if granularity == 'day':
            time_expr = 'bid_date'
        elif granularity == 'week':
            time_expr = "strftime('%Y-W%W', bid_date)"
        elif granularity == 'month':
            time_expr = "strftime('%Y-%m', bid_date)"
        else:  # quarter
            time_expr = "strftime('%Y-Q', strftime('%m', bid_date)) || CAST((CAST(strftime('%m', bid_date) AS INTEGER) + 2) / 3 AS TEXT)"
        
        results = {}
        overall_stats = {}
        
        for param_type in param_types:
            param_column = f'{param_type}_value'
            
            query = f"""
                SELECT {time_expr} as time_period,
                       {param_column},
                       bid_location,
                       method_category
                FROM bid_records
                WHERE user_id = ? AND {param_column} IS NOT NULL
            """
            params = [user_id]
            
            # 添加筛选条件
            if locations and locations != ['']:
                placeholders = ','.join(['?' for _ in locations])
                query += f" AND bid_location IN ({placeholders})"
                params.extend(locations)
            
            if methods and methods != ['']:
                placeholders = ','.join(['?' for _ in methods])
                query += f" AND method_category IN ({placeholders})"
                params.extend(methods)
            
            if date_from:
                query += " AND bid_date >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND bid_date <= ?"
                params.append(date_to)
            
            query += f" ORDER BY {time_expr}"
            
            cursor = db.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                results[param_type] = {'data': [], 'stats': None}
                continue
            
            # 按时间周期聚合
            period_data = {}  # {time_period: [values]}
            all_values = []
            
            for row in rows:
                time_period, value, location, method = row
                if value is not None:
                    try:
                        value = float(value)
                        all_values.append(value)
                        
                        if time_period not in period_data:
                            period_data[time_period] = []
                        period_data[time_period].append(value)
                    except (ValueError, TypeError):
                        pass
            
            if not period_data:
                results[param_type] = {'data': [], 'stats': None}
                continue
            
            # 计算每个周期的平均值
            trend_data = []
            sorted_periods = sorted(period_data.keys())
            
            for period in sorted_periods:
                values = period_data[period]
                avg_value = sum(values) / len(values)
                trend_data.append({
                    'period': period,
                    'avg': round(avg_value, 4),
                    'count': len(values),
                    'min': round(min(values), 4),
                    'max': round(max(values), 4)
                })
            
            # 计算整体统计
            import statistics
            stats = {
                'count': len(all_values),
                'mean': round(statistics.mean(all_values), 4),
                'std': round(statistics.stdev(all_values), 4) if len(all_values) > 1 else 0,
                'min': round(min(all_values), 4),
                'max': round(max(all_values), 4),
                'median': round(statistics.median(all_values), 4)
            }
            
            # 计算趋势方向
            if len(trend_data) >= 2:
                first_half = trend_data[:len(trend_data)//2]
                second_half = trend_data[len(trend_data)//2:]
                first_avg = sum(d['avg'] for d in first_half) / len(first_half)
                second_avg = sum(d['avg'] for d in second_half) / len(second_half)
                
                change_pct = ((second_avg - first_avg) / first_avg * 100) if first_avg != 0 else 0
                
                if abs(change_pct) < 1:
                    trend_direction = '→平稳'
                elif change_pct > 0:
                    trend_direction = '↑上升'
                else:
                    trend_direction = '↓下降'
                
                stats['trend_direction'] = trend_direction
                stats['change_pct'] = round(change_pct, 2)
            
            # 应用移动平均
            if moving_avg_days and len(trend_data) > moving_avg_days:
                window_size = moving_avg_days
                smoothed_data = []
                
                for i in range(len(trend_data)):
                    if i < window_size - 1:
                        # 窗口不足，使用当前值
                        smoothed_data.append(trend_data[i])
                    else:
                        # 计算移动平均
                        window = trend_data[i-window_size+1:i+1]
                        avg_val = sum(d['avg'] for d in window) / len(window)
                        smoothed_point = dict(trend_data[i])
                        smoothed_point['smoothed_avg'] = round(avg_val, 4)
                        smoothed_data.append(smoothed_point)
                
                results[param_type] = {
                    'data': smoothed_data,
                    'stats': stats,
                    'moving_avg': moving_avg_days
                }
            else:
                results[param_type] = {
                    'data': trend_data,
                    'stats': stats
                }
            
            overall_stats[param_type] = stats
        
        return jsonify({
            'success': True,
            'results': results,
            'overall_stats': overall_stats,
            'granularity': granularity,
            'param_count': len([r for r in results.values() if r['data']])
        })
    
    except Exception as e:
        print(f"获取趋势数据失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@analysis_bp.route('/api/analysis/trend_grouped')
@login_required
def get_trend_grouped_data():
    """
    按分组获取趋势数据（用于地区对比、方法对比）
    参数:
        param_type: k1/k2/q1
        group_by: location 或 method
        granularity: day/week/month/quarter
        date_from/date_to: 日期范围
        items: 具体分组项列表（逗号分隔，可选）
    """
    param_type = request.args.get('param_type', 'k1')
    group_by = request.args.get('group_by', 'location')
    granularity = request.args.get('granularity', 'month')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    items = request.args.get('items', '').split(',') if request.args.get('items') else []
    
    if param_type not in ['k1', 'k2', 'q1']:
        return jsonify({'success': False, 'error': '无效的参数类型'}), 400
    if group_by not in ['location', 'method']:
        return jsonify({'success': False, 'error': '无效的分组维度'}), 400
    if granularity not in ['day', 'week', 'month', 'quarter']:
        return jsonify({'success': False, 'error': '无效的时间粒度'}), 400
    
    db = sqlite3.connect(db_path)
    user_id = session.get('user_id')
    
    try:
        param_column = f'{param_type}_value'
        group_column = 'bid_location' if group_by == 'location' else 'method_category'
        
        if granularity == 'day':
            time_expr = 'bid_date'
        elif granularity == 'week':
            time_expr = "strftime('%Y-W%W', bid_date)"
        elif granularity == 'month':
            time_expr = "strftime('%Y-%m', bid_date)"
        else:  # quarter
            time_expr = "strftime('%Y-Q', CAST((CAST(strftime('%m', bid_date) AS INTEGER) + 2) / 3 AS TEXT))"
        
        query = f"""
            SELECT {time_expr} as time_period,
                   {group_column} as group_val,
                   {param_column}
            FROM bid_records
            WHERE user_id = ? AND {param_column} IS NOT NULL
        """
        params = [user_id]
        
        if date_from:
            query += " AND bid_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND bid_date <= ?"
            params.append(date_to)
        
        query += f" ORDER BY {time_expr}"
        
        cursor = db.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({'success': True, 'groups': {}, 'time_periods': []})
        
        # 整理数据: {group_value: {time_period: [values]}}
        grouped = {}
        all_periods = set()
        
        for row in rows:
            time_period, group_val, value = row
            if value is None or not group_val:
                continue
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            
            if group_val not in grouped:
                grouped[group_val] = {}
            if time_period not in grouped[group_val]:
                grouped[group_val][time_period] = []
            grouped[group_val][time_period].append(value)
            all_periods.add(time_period)
        
        # 如果指定了 items，只返回指定的分组
        if items and items != ['']:
            grouped = {k: v for k, v in grouped.items() if k in items}
        
        # 构建返回数据
        time_periods = sorted(all_periods)
        result = {}
        
        for group_val, periods in grouped.items():
            series = []
            for period in time_periods:
                if period in periods:
                    values = periods[period]
                    series.append({
                        'period': period,
                        'avg': round(sum(values) / len(values), 4),
                        'count': len(values)
                    })
                else:
                    series.append({
                        'period': period,
                        'avg': None,
                        'count': 0
                    })
            result[group_val] = series
        
        return jsonify({
            'success': True,
            'groups': result,
            'time_periods': time_periods,
            'param_type': param_type,
            'group_by': group_by,
            'granularity': granularity
        })
    
    except Exception as e:
        print(f"获取分组趋势数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
