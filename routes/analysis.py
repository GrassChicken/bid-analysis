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
