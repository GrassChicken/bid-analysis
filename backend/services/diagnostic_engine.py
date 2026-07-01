#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能诊断引擎
对预测结果进行诊断分析，提供异常识别、算法表现评估、置信度校准等功能
"""

import sqlite3
from typing import Dict, List, Optional, Any
from backend.config.config import Config


class DiagnosticEngine:
    """智能诊断引擎"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH

    # ============================================================
    # 1. 预测异常自动识别
    # ============================================================

    def diagnose_anomaly(self, user_id: int, k1_pred: float = None,
                        q1_pred: float = None, method_pred: str = None,
                        location: str = None, method_category: str = None,
                        date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        """
        对一次新的预测结果进行异常诊断
        
        检测项：
        - K1 预测值是否偏离历史分布
        - Q1 预测值是否偏离历史分布
        - 方法类别预测置信度是否过低
        - 数据量是否不足
        """
        warnings = []
        suggestions = []

        # ---- K1 异常检测 ----
        if k1_pred is not None:
            k1_stats = self._get_k1_stats(user_id, location, method_category, date_from, date_to)
            if k1_stats and k1_stats['count'] >= 3:
                mean = k1_stats['mean']
                std = k1_stats['std']
                if std > 0:
                    z_score = abs(k1_pred - mean) / std
                    if z_score > 2.5:
                        warnings.append({
                            'type': 'k1_anomaly',
                            'level': 'high',
                            'title': '⚠️ K1 预测值显著偏离',
                            'message': f'预测值 {k1_pred:.3f} 偏离历史均值 {mean:.3f} ± {std:.3f}（Z={z_score:.1f}σ）',
                            'suggestion': '建议检查数据筛选范围，确认是否包含异常数据'
                        })
                    elif z_score > 1.8:
                        warnings.append({
                            'type': 'k1_anomaly',
                            'level': 'medium',
                            'title': '⚡ K1 预测值略有偏离',
                            'message': f'预测值 {k1_pred:.3f} 与历史均值 {mean:.3f} 偏差较大',
                            'suggestion': '属于正常波动范围，但建议关注'
                        })

                # 范围检查
                k1_range = self._get_k1_range(user_id, location, method_category, date_from, date_to)
                if k1_range and (k1_pred < k1_range['min'] or k1_pred > k1_range['max']):
                    warnings.append({
                        'type': 'k1_out_of_range',
                        'level': 'high',
                        'title': '⚠️ K1 预测值超出历史范围',
                        'message': f'预测值 {k1_pred:.3f} 不在历史数据范围 [{k1_range["min"]:.3f} ~ {k1_range["max"]:.3f}] 内',
                        'suggestion': '请确认预测是否合理，历史数据中从未出现此范围的值'
                    })

        # ---- Q1 异常检测 ----
        if q1_pred is not None:
            q1_stats = self._get_q1_stats(user_id, location, method_category, date_from, date_to)
            if q1_stats and q1_stats['count'] >= 3:
                mean = q1_stats['mean']
                std = q1_stats['std']
                if std > 0:
                    z_score = abs(q1_pred - mean) / std
                    if z_score > 2.5:
                        warnings.append({
                            'type': 'q1_anomaly',
                            'level': 'high',
                            'title': '⚠️ Q1 预测值显著偏离',
                            'message': f'预测值 {q1_pred:.2f} 偏离历史均值 {mean:.2f} ± {std:.2f}（Z={z_score:.1f}σ）',
                            'suggestion': '建议检查数据筛选范围'
                        })
                    elif z_score > 1.8:
                        warnings.append({
                            'type': 'q1_anomaly',
                            'level': 'medium',
                            'title': '⚡ Q1 预测值略有偏离',
                            'message': f'预测值 {q1_pred:.2f} 与历史均值 {mean:.2f} 偏差较大',
                            'suggestion': '属于正常波动范围，但建议关注'
                        })

        # ---- 方法类别置信度检查 ----
        if method_pred is not None:
            pass  # 方法类别本身置信度已在预测结果中体现

        # ---- 数据量检查 ----
        data_count = self._get_data_count(user_id, location, method_category, date_from, date_to)
        if data_count < 5:
            warnings.append({
                'type': 'low_data_count',
                'level': 'high',
                'title': '📊 数据量不足',
                'message': f'当前筛选条件仅获取到 {data_count} 条数据',
                'suggestion': '建议放宽筛选条件（如扩大日期范围或不限地点/方法），以获取更充足的样本'
            })
        elif data_count < 10:
            warnings.append({
                'type': 'low_data_count',
                'level': 'medium',
                'title': '📊 数据量偏少',
                'message': f'当前筛选条件获取到 {data_count} 条数据',
                'suggestion': '数据量偏少可能影响预测精度，建议适当放宽筛选条件'
            })

        return {
            'has_warnings': len(warnings) > 0,
            'warning_count': len(warnings),
            'warnings': warnings,
            'data_count': data_count,
            'diagnosis_summary': self._generate_summary(warnings, data_count)
        }

    # ============================================================
    # 2. 算法表现评估
    # ============================================================

    def evaluate_algorithm_performance(self, user_id: int) -> Dict[str, Any]:
        """
        评估各统计算法的实际表现
        
        基于已有真实值的预测记录，计算每个算法的准确率
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取所有已对比且有真实值的预测记录
        cursor.execute('''
            SELECT id, k1_prediction, k1_actual, q1_prediction, q1_actual,
                   k1_method, q1_method, method_prediction, method_actual,
                   prediction_time
            FROM prediction_records
            WHERE user_id = ? AND accuracy_checked = 1
              AND (k1_actual IS NOT NULL OR q1_actual IS NOT NULL)
            ORDER BY prediction_time DESC
        ''', (user_id,))
        records = cursor.fetchall()
        conn.close()

        if not records:
            return {
                'has_data': False,
                'message': '暂无已对比的预测数据，请先录入真实值',
                'k1_methods': [],
                'q1_methods': [],
                'overall_k1_accuracy': 0,
                'overall_q1_accuracy': 0,
            }

        # ---- K1 算法统计 ----
        k1_method_stats = {}
        k1_accurate = 0
        k1_total = 0

        for rec in records:
            k1_pred = rec[1]
            k1_act = rec[2]
            k1_method = rec[5]

            if k1_pred and k1_act and k1_method:
                k1_total += 1
                try:
                    deviation = abs(float(k1_pred) - float(k1_act))
                    is_accurate = deviation == 0
                    is_normal = deviation <= 0.01
                    if is_accurate:
                        k1_accurate += 1
                except (ValueError, TypeError):
                    pass

                if k1_method not in k1_method_stats:
                    k1_method_stats[k1_method] = {
                        'name': k1_method,
                        'total': 0,
                        'accurate': 0,
                        'normal': 0,
                        'avg_deviation': 0,
                        'deviations': []
                    }

                k1_method_stats[k1_method]['total'] += 1
                try:
                    dev = abs(float(k1_pred) - float(k1_act))
                    k1_method_stats[k1_method]['deviations'].append(dev)
                    if dev == 0:
                        k1_method_stats[k1_method]['accurate'] += 1
                    elif dev <= 0.01:
                        k1_method_stats[k1_method]['normal'] += 1
                except (ValueError, TypeError):
                    pass

        # 计算平均偏差
        for method, stats in k1_method_stats.items():
            if stats['deviations']:
                stats['avg_deviation'] = round(sum(stats['deviations']) / len(stats['deviations']), 4)
                stats['accuracy'] = round(
                    (stats['accurate'] + stats['normal']) / stats['total'] * 100, 1
                ) if stats['total'] > 0 else 0
            stats.pop('deviations')

        # ---- Q1 算法统计 ----
        q1_method_stats = {}
        q1_accurate = 0
        q1_total = 0

        for rec in records:
            q1_pred = rec[3]
            q1_act = rec[4]
            q1_method = rec[6]
            method_pred = rec[7]

            # 方法1 没有 Q1
            if method_pred == '1':
                continue

            if q1_pred and q1_act and q1_method:
                q1_total += 1
                try:
                    deviation = abs(float(q1_pred) - float(q1_act))
                    is_accurate = deviation == 0
                    is_normal = deviation <= 0.1
                    if is_accurate:
                        q1_accurate += 1
                except (ValueError, TypeError):
                    pass

                if q1_method not in q1_method_stats:
                    q1_method_stats[q1_method] = {
                        'name': q1_method,
                        'total': 0,
                        'accurate': 0,
                        'normal': 0,
                        'avg_deviation': 0,
                        'deviations': []
                    }

                q1_method_stats[q1_method]['total'] += 1
                try:
                    dev = abs(float(q1_pred) - float(q1_act))
                    q1_method_stats[q1_method]['deviations'].append(dev)
                    if dev == 0:
                        q1_method_stats[q1_method]['accurate'] += 1
                    elif dev <= 0.1:
                        q1_method_stats[q1_method]['normal'] += 1
                except (ValueError, TypeError):
                    pass

        for method, stats in q1_method_stats.items():
            if stats['deviations']:
                stats['avg_deviation'] = round(sum(stats['deviations']) / len(stats['deviations']), 4)
                stats['accuracy'] = round(
                    (stats['accurate'] + stats['normal']) / stats['total'] * 100, 1
                ) if stats['total'] > 0 else 0
            stats.pop('deviations')

        # 按准确率排序
        k1_methods = sorted(
            k1_method_stats.values(),
            key=lambda x: x.get('accuracy', 0),
            reverse=True
        )
        q1_methods = sorted(
            q1_method_stats.values(),
            key=lambda x: x.get('accuracy', 0),
            reverse=True
        )

        return {
            'has_data': True,
            'total_records': len(records),
            'k1_total': k1_total,
            'k1_accurate': k1_accurate,
            'overall_k1_accuracy': round((k1_accurate / k1_total * 100) if k1_total > 0 else 0, 1),
            'q1_total': q1_total,
            'q1_accurate': q1_accurate,
            'overall_q1_accuracy': round((q1_accurate / q1_total * 100) if q1_total > 0 else 0, 1),
            'k1_methods': k1_methods,
            'q1_methods': q1_methods,
        }

    # ============================================================
    # 3. 置信度校准
    # ============================================================

    def calibrate_confidence(self, user_id: int) -> Dict[str, Any]:
        """
        校准预测置信度
        
        对比历史预测中"标称置信度 vs 实际准确率"
        返回不同置信度区间的实际表现
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT k1_confidence, q1_confidence, k1_prediction, k1_actual,
                   q1_prediction, q1_actual, method_confidence, method_prediction, method_actual
            FROM prediction_records
            WHERE user_id = ? AND accuracy_checked = 1
        ''', (user_id,))
        records = cursor.fetchall()
        conn.close()

        if not records:
            return {
                'has_data': False,
                'message': '暂无已对比的预测数据',
                'confidence_buckets': []
            }

        # 按置信度区间分组：[0-50%), [50-70%), [70-85%), [85-95%), [95-100%]
        buckets = [
            {'range': '0-50%', 'min': 0, 'max': 0.5, 'count': 0, 'correct': 0},
            {'range': '50-70%', 'min': 0.5, 'max': 0.7, 'count': 0, 'correct': 0},
            {'range': '70-85%', 'min': 0.7, 'max': 0.85, 'count': 0, 'correct': 0},
            {'range': '85-95%', 'min': 0.85, 'max': 0.95, 'count': 0, 'correct': 0},
            {'range': '95-100%', 'min': 0.95, 'max': 1.0, 'count': 0, 'correct': 0},
        ]

        for rec in records:
            k1_conf = rec[0]
            k1_pred = rec[2]
            k1_act = rec[3]
            method_conf = rec[6]
            method_pred = rec[7]
            method_act = rec[8]

            # K1 置信度校准
            if k1_conf is not None and k1_pred and k1_act:
                try:
                    deviation = abs(float(k1_pred) - float(k1_act))
                    is_correct = deviation <= 0.01
                except (ValueError, TypeError):
                    is_correct = False

                for bucket in buckets:
                    if bucket['min'] <= k1_conf < bucket['max']:
                        bucket['count'] += 1
                        if is_correct:
                            bucket['correct'] += 1
                        break

        # 计算每个区间的实际准确率
        for bucket in buckets:
            bucket['actual_accuracy'] = round(
                bucket['correct'] / bucket['count'] * 100, 1
            ) if bucket['count'] > 0 else None

        # 找出过估/低估区间
        overconfident = []
        underconfident = []
        for bucket in buckets:
            if bucket['actual_accuracy'] is not None:
                avg_conf = (bucket['min'] + bucket['max']) / 2 * 100
                diff = bucket['actual_accuracy'] - avg_conf
                if diff < -15:  # 过估超过 15%
                    overconfident.append(bucket['range'])
                elif diff > 15:  # 低估超过 15%
                    underconfident.append(bucket['range'])

        return {
            'has_data': True,
            'total_records': len(records),
            'confidence_buckets': buckets,
            'overconfident_ranges': overconfident,
            'underconfident_ranges': underconfident,
            'calibration_summary': self._calibration_summary(overconfident, underconfident)
        }

    # ============================================================
    # 4. 算法排名评估（基于 Top5 算法详情）
    # ============================================================

    def get_algorithm_ranking(self, user_id: int) -> Dict[str, Any]:
        """
        算法排名评估
        
        基于已有真实值的预测记录，评估每个算法的预测值与真实值的偏差
        计算偏差平均值，偏差越小越准确
        按偏差值从小到大排序
        偏差最小的前5个算法标记为推荐算法
        
        Returns:
            {
                'has_data': bool,
                'k1_ranking': [...],  # K1算法排名列表
                'q1_ranking': [...],  # Q1算法排名列表（如所有预测都是方法1则为空）
                'k1_recommended': [...],  # K1推荐算法（前5）
                'q1_recommended': [...],  # Q1推荐算法（前5）
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取所有已对比且有真实值的预测记录
        cursor.execute('''
            SELECT pr.id, pr.k1_actual, pr.q1_actual, pr.method_prediction
            FROM prediction_records pr
            WHERE pr.user_id = ? AND pr.accuracy_checked = 1
        ''', (user_id,))
        predictions = cursor.fetchall()

        if not predictions:
            conn.close()
            return {
                'has_data': False,
                'message': '暂无已对比的预测数据，请先录入真实值',
                'k1_ranking': [],
                'q1_ranking': [],
                'k1_recommended': [],
                'q1_recommended': []
            }

        # 构建 prediction_id -> actual_values 映射
        actual_map = {}
        for pred_id, k1_actual, q1_actual, method_pred in predictions:
            # 安全转换：可能为 None、空字符串或 '--' 等无效值
            try:
                k1_val = float(k1_actual) if k1_actual and k1_actual not in ('--', '') else None
            except (ValueError, TypeError):
                k1_val = None
            try:
                q1_val = float(q1_actual) if q1_actual and q1_actual not in ('--', '') else None
            except (ValueError, TypeError):
                q1_val = None
            
            actual_map[pred_id] = {
                'k1_actual': k1_val,
                'q1_actual': q1_val,
                'method_prediction': method_pred
            }

        # 获取所有算法详情
        cursor.execute('''
            SELECT prediction_id, param_type, rank, algorithm_name, prediction_value, confidence
            FROM prediction_algorithm_details
            WHERE prediction_id IN ({})
            ORDER BY prediction_id, param_type, rank
        '''.format(','.join(str(pid) for pid in actual_map.keys())))
        algorithm_details = cursor.fetchall()
        conn.close()

        if not algorithm_details:
            return {
                'has_data': False,
                'message': '暂无算法详情数据',
                'k1_ranking': [],
                'q1_ranking': [],
                'k1_recommended': [],
                'q1_recommended': []
            }

        # 按算法分组统计偏差
        k1_stats = {}  # algorithm_name -> {'deviations': [], 'confidences': []}
        q1_stats = {}

        for pred_id, param_type, rank, algo_name, pred_value, confidence in algorithm_details:
            if pred_id not in actual_map:
                continue

            actual_data = actual_map[pred_id]

            try:
                pred_val = float(pred_value)
            except (ValueError, TypeError):
                continue

            # K1 统计
            if param_type == 'K1' and actual_data['k1_actual'] is not None:
                deviation = abs(pred_val - actual_data['k1_actual'])
                if algo_name not in k1_stats:
                    k1_stats[algo_name] = {'deviations': [], 'confidences': []}
                k1_stats[algo_name]['deviations'].append(deviation)
                k1_stats[algo_name]['confidences'].append(confidence)

            # Q1 统计（仅当 method_prediction != '1' 时）
            if param_type == 'Q1' and actual_data['method_prediction'] != '1' and actual_data['q1_actual'] is not None:
                deviation = abs(pred_val - actual_data['q1_actual'])
                if algo_name not in q1_stats:
                    q1_stats[algo_name] = {'deviations': [], 'confidences': []}
                q1_stats[algo_name]['deviations'].append(deviation)
                q1_stats[algo_name]['confidences'].append(confidence)

        # 计算平均偏差并排序
        def calculate_ranking(stats):
            ranking = []
            for algo_name, data in stats.items():
                if not data['deviations']:
                    continue
                avg_deviation = sum(data['deviations']) / len(data['deviations'])
                avg_confidence = sum(data['confidences']) / len(data['confidences'])
                sample_count = len(data['deviations'])
                
                ranking.append({
                    'algorithm_name': algo_name,
                    'avg_deviation': round(avg_deviation, 4),
                    'avg_confidence': round(avg_confidence, 3),
                    'sample_count': sample_count,
                    'evaluation_confidence': 0  # 稍后计算
                })
            
            # 按平均偏差从小到大排序
            ranking.sort(key=lambda x: x['avg_deviation'])
            return ranking

        k1_ranking = calculate_ranking(k1_stats)
        q1_ranking = calculate_ranking(q1_stats)

        # 计算评估置信度
        def calculate_evaluation_confidence(ranking):
            if not ranking:
                return
            
            for i, item in enumerate(ranking):
                # 评估置信度 = 历史置信度 * 样本量权重 * 排名权重
                # 样本量权重：样本越多越可靠，但设置上限
                sample_weight = min(1.0, item['sample_count'] / 10.0)
                
                # 排名权重：排名越靠前权重越高
                rank_weight = 1.0 - (i / len(ranking)) * 0.3  # 最多降低30%
                
                # 偏差权重：偏差越小权重越高
                deviation_weight = 1.0 / (1.0 + item['avg_deviation'] * 10)
                
                # 综合评估置信度
                evaluation_conf = (
                    item['avg_confidence'] * 0.4 +  # 历史置信度占40%
                    sample_weight * 0.3 +  # 样本量占30%
                    rank_weight * 0.15 +  # 排名占15%
                    deviation_weight * 0.15  # 偏差占15%
                )
                
                item['evaluation_confidence'] = round(min(1.0, evaluation_conf), 3)

        calculate_evaluation_confidence(k1_ranking)
        calculate_evaluation_confidence(q1_ranking)

        # 标记推荐算法（前5）
        k1_recommended = k1_ranking[:5]
        q1_recommended = q1_ranking[:5]

        return {
            'has_data': True,
            'k1_ranking': k1_ranking,
            'q1_ranking': q1_ranking,
            'k1_recommended': k1_recommended,
            'q1_recommended': q1_recommended
        }

    # ============================================================
    # 内部辅助方法
    # ============================================================

    def _get_k1_stats(self, user_id: int, location: str = None,
                     method_category: str = None, date_from: str = None,
                     date_to: str = None) -> Optional[Dict]:
        """获取 K1 值的统计信息"""
        query = 'SELECT k1_value FROM bid_records WHERE user_id = ? AND k1_value IS NOT NULL'
        params = [user_id]

        if location:
            query += ' AND bid_location = ?'
            params.append(location)
        if method_category:
            query += ' AND method_category = ?'
            params.append(method_category)
        if date_from:
            query += ' AND bid_date >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND bid_date <= ?'
            params.append(date_to)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        raw_values = [r[0] for r in cursor.fetchall() if r[0] is not None]
        values = []
        for v in raw_values:
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass
        conn.close()

        if len(values) < 2:
            return None

        import statistics
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'std': statistics.stdev(values),
            'min': min(values),
            'max': max(values),
        }

    def _get_q1_stats(self, user_id: int, location: str = None,
                     method_category: str = None, date_from: str = None,
                     date_to: str = None) -> Optional[Dict]:
        """获取 Q1 值的统计信息"""
        query = 'SELECT q1_value FROM bid_records WHERE user_id = ? AND q1_value IS NOT NULL'
        params = [user_id]

        if location:
            query += ' AND bid_location = ?'
            params.append(location)
        if method_category:
            query += ' AND method_category = ?'
            params.append(method_category)
        if date_from:
            query += ' AND bid_date >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND bid_date <= ?'
            params.append(date_to)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        raw_values = [r[0] for r in cursor.fetchall() if r[0] is not None]
        values = []
        for v in raw_values:
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass
        conn.close()

        if len(values) < 2:
            return None

        import statistics
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'std': statistics.stdev(values),
            'min': min(values),
            'max': max(values),
        }

    def _get_k1_range(self, user_id: int, location: str = None,
                     method_category: str = None, date_from: str = None,
                     date_to: str = None) -> Optional[Dict]:
        """获取 K1 值的范围"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = 'SELECT MIN(k1_value), MAX(k1_value) FROM bid_records WHERE user_id = ? AND k1_value IS NOT NULL'
        params = [user_id]

        if location:
            query += ' AND bid_location = ?'
            params.append(location)
        if method_category:
            query += ' AND method_category = ?'
            params.append(method_category)
        if date_from:
            query += ' AND bid_date >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND bid_date <= ?'
            params.append(date_to)

        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        if row and row[0] is not None and row[1] is not None:
            try:
                return {'min': float(row[0]), 'max': float(row[1])}
            except (ValueError, TypeError):
                return None
        return None

    def _get_data_count(self, user_id: int, location: str = None,
                       method_category: str = None, date_from: str = None,
                       date_to: str = None) -> int:
        """获取符合条件的数据条数"""
        query = 'SELECT COUNT(*) FROM bid_records WHERE user_id = ?'
        params = [user_id]

        if location:
            query += ' AND bid_location = ?'
            params.append(location)
        if method_category:
            query += ' AND method_category = ?'
            params.append(method_category)
        if date_from:
            query += ' AND bid_date >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND bid_date <= ?'
            params.append(date_to)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _generate_summary(self, warnings: List[Dict], data_count: int) -> str:
        """生成诊断摘要"""
        high_count = sum(1 for w in warnings if w['level'] == 'high')
        med_count = sum(1 for w in warnings if w['level'] == 'medium')

        if high_count == 0 and med_count == 0:
            return '✅ 预测结果正常，未发现明显异常'
        elif high_count > 0:
            return f'⚠️ 发现 {high_count} 个高风险项、{med_count} 个中风险项，建议检查后重新预测'
        else:
            return f'⚡ 发现 {med_count} 个中风险项，预测结果可参考，但建议关注'

    def _calibration_summary(self, overconfident: List, underconfident: List) -> str:
        """生成置信度校准摘要"""
        parts = []
        if overconfident:
            parts.append(f'系统在 {", ".join(overconfident)} 区间可能过于自信（标称置信度高于实际准确率）')
        if underconfident:
            parts.append(f'系统在 {", ".join(underconfident)} 区间可能过于保守（实际准确率高于标称置信度）')
        if not parts:
            return '✅ 置信度与实际准确率基本吻合，校准良好'
        return '；'.join(parts)
