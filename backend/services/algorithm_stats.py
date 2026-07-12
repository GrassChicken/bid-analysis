#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法效能统计服务
基于历史预测数据，统计各算法的命中率、平均偏差、稳定性
"""

import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from backend.config.config import Config


class AlgorithmStatsService:
    """算法效能统计服务"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH

    def calculate_stats(self, user_id: int, location: str = None,
                        days: int = None) -> Dict[str, Any]:
        """
        计算算法效能排名（包含 Top5 候选算法统计）
        
        Args:
            user_id: 用户 ID
            location: 地点筛选（None=全部）
            days: 时间范围（None=全部，30/90/180/365）
        
        Returns:
            {
                'rankings': [...],       # 算法排名列表
                'top3': [...],           # TOP 3 推荐
                'summary': {...},        # 汇总信息
                'locations': [...]       # 可用地点列表
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 构建查询条件
        conditions = ['user_id = ?', 'accuracy_checked = 1']
        params = [user_id]

        if location:
            conditions.append('location_filter = ?')
            params.append(location)

        if days:
            date_threshold = (datetime.now() - __import__('datetime').timedelta(days=days)).strftime('%Y-%m-%d')
            conditions.append('prediction_time >= ?')
            params.append(date_threshold)

        where_clause = ' AND '.join(conditions)

        # 获取有真实值的预测记录 ID 列表
        cursor.execute(f'''
            SELECT id, location_filter, prediction_time
            FROM prediction_records
            WHERE {where_clause}
              AND k1_actual IS NOT NULL
        ''', params)
        record_ids = cursor.fetchall()

        # 获取可用地点列表
        cursor.execute(f'''
            SELECT DISTINCT location_filter
            FROM prediction_records
            WHERE user_id = ? AND location_filter IS NOT NULL AND location_filter != ''
            ORDER BY location_filter
        ''', [user_id])
        locations = [row[0] for row in cursor.fetchall()]

        conn.close()

        # 按算法名分组统计
        # 数据结构: { algorithm_name: { total, hits, deviations: [], is_candidate: bool } }
        k1_stats = defaultdict(lambda: {
            'total': 0, 'hits': 0, 'deviations': [],
            'recent_hits': 0, 'recent_total': 0,
            'param_type': 'K1'
        })
        q1_stats = defaultdict(lambda: {
            'total': 0, 'hits': 0, 'deviations': [],
            'recent_hits': 0, 'recent_total': 0,
            'param_type': 'Q1'
        })

        # 遍历每条预测记录，统计采用算法和 Top5 候选算法
        from backend.models.prediction import Prediction
        pred_model = Prediction(self.db_path)

        for record_id, loc, pred_time in record_ids:
            # 获取该记录的 Top5 算法详情
            k1_algorithms = pred_model.get_algorithm_details(record_id, 'K1')
            q1_algorithms = pred_model.get_algorithm_details(record_id, 'Q1')
            
            # 获取该记录的真实值和已采用算法
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT k1_actual, q1_actual, k1_method, k1_prediction, q1_method, q1_prediction, method_prediction
                FROM prediction_records WHERE id = ?
            ''', [record_id])
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                continue
            
            k1_actual, q1_actual, k1_method, k1_prediction, q1_method, q1_prediction, method_prediction = row
            
            # 已采用的算法名称集合（用于避免重复统计）
            k1_adopted = set()
            q1_adopted = set()

            # 1. 统计已采用算法（从 prediction_records 直接读取）
            if k1_method and k1_actual and k1_prediction:
                try:
                    actual_val = float(k1_actual)
                    pred_val = float(k1_prediction)
                    deviation = abs(pred_val - actual_val)
                    is_hit = deviation <= 0.005

                    stats = k1_stats[k1_method]
                    stats['total'] += 1
                    if is_hit:
                        stats['hits'] += 1
                    stats['deviations'].append(deviation)
                    stats['recent_total'] += 1
                    if is_hit:
                        stats['recent_hits'] += 1
                    k1_adopted.add(k1_method)
                except (ValueError, TypeError):
                    pass

            if q1_method and q1_actual and q1_prediction and method_prediction != '1':
                try:
                    actual_val = float(q1_actual)
                    pred_val = float(q1_prediction)
                    deviation = abs(pred_val - actual_val)
                    is_hit = deviation <= 0.05

                    stats = q1_stats[q1_method]
                    stats['total'] += 1
                    if is_hit:
                        stats['hits'] += 1
                    stats['deviations'].append(deviation)
                    stats['recent_total'] += 1
                    if is_hit:
                        stats['recent_hits'] += 1
                    q1_adopted.add(q1_method)
                except (ValueError, TypeError):
                    pass

            # 2. 统计 Top5 候选算法（排除已统计的采用算法）
            if k1_algorithms and k1_actual:
                try:
                    actual_val = float(k1_actual)
                    for algo in k1_algorithms:
                        algo_name = algo['algorithm_name']
                        if algo_name in k1_adopted:
                            continue  # 已统计，跳过
                        pred_val = float(algo['prediction_value'])
                        deviation = abs(pred_val - actual_val)
                        is_hit = deviation <= 0.005

                        stats = k1_stats[algo_name]
                        stats['total'] += 1
                        if is_hit:
                            stats['hits'] += 1
                        stats['deviations'].append(deviation)
                        stats['recent_total'] += 1
                        if is_hit:
                            stats['recent_hits'] += 1
                except (ValueError, TypeError):
                    pass

            if q1_algorithms and q1_actual and method_prediction != '1':
                try:
                    actual_val = float(q1_actual)
                    for algo in q1_algorithms:
                        algo_name = algo['algorithm_name']
                        if algo_name in q1_adopted:
                            continue  # 已统计，跳过
                        pred_val = float(algo['prediction_value'])
                        deviation = abs(pred_val - actual_val)
                        is_hit = deviation <= 0.05

                        stats = q1_stats[algo_name]
                        stats['total'] += 1
                        if is_hit:
                            stats['hits'] += 1
                        stats['deviations'].append(deviation)
                        stats['recent_total'] += 1
                        if is_hit:
                            stats['recent_hits'] += 1
                except (ValueError, TypeError):
                    pass

        # 分别构建 K1 排名和 Q1 排名
        def build_ranking(stats_dict, param_type):
            """构建单维度（K1或Q1）排名"""
            items = []
            for algo_name, s in stats_dict.items():
                if s['total'] == 0:
                    continue
                hit_rate = s['hits'] / s['total'] * 100
                deviations = s['deviations']
                avg_dev = sum(deviations) / len(deviations) if deviations else 0
                max_dev = max(deviations) if deviations else 0
                if len(deviations) > 1:
                    import numpy as np
                    std_dev = np.std(deviations)
                    stability = max(0, 100 - std_dev * 1000)
                else:
                    stability = hit_rate
                sample_score = min(100, s['total'] * 10)
                combined_score = hit_rate * 0.5 + stability * 0.3 + sample_score * 0.2
                items.append({
                    'name': algo_name,
                    'total': s['total'],
                    'hits': s['hits'],
                    'hit_rate': round(hit_rate, 1),
                    'avg_deviation': round(avg_dev, 4),
                    'max_deviation': round(max_dev, 4),
                    'stability': round(stability, 1),
                    'combined_score': round(combined_score, 1),
                    'param_type': param_type,
                })
            items.sort(key=lambda x: x['combined_score'], reverse=True)
            for i, item in enumerate(items, 1):
                item['rank'] = i
                item['recommendation'] = self._generate_recommendation(item)
            return items

        k1_rankings = build_ranking(dict(k1_stats), 'K1')
        q1_rankings = build_ranking(dict(q1_stats), 'Q1')

        # K1/Q1 各自的 TOP 3（至少 3 次预测）
        def get_top3(rankings):
            qualified = [r for r in rankings if r['total'] >= 3]
            return qualified[:3] if qualified else rankings[:3]

        k1_top3 = get_top3(k1_rankings)
        q1_top3 = get_top3(q1_rankings)

        # 汇总
        all_total = sum(s['total'] for s in k1_rankings) + sum(s['total'] for s in q1_rankings)
        best_k1 = k1_rankings[0] if k1_rankings else None
        best_q1 = q1_rankings[0] if q1_rankings else None

        summary = {
            'total_evaluated': len(k1_rankings) + len(q1_rankings),
            'total_predictions': all_total,
            'best_k1_algorithm': best_k1['name'] if best_k1 else '-',
            'best_k1_hit_rate': best_k1['hit_rate'] if best_k1 else 0,
            'best_q1_algorithm': best_q1['name'] if best_q1 else '-',
            'best_q1_hit_rate': best_q1['hit_rate'] if best_q1 else 0,
            'avg_k1_hit_rate': round(sum(s['hit_rate'] for s in k1_rankings) / len(k1_rankings), 1) if k1_rankings else 0,
            'avg_q1_hit_rate': round(sum(s['hit_rate'] for s in q1_rankings) / len(q1_rankings), 1) if q1_rankings else 0,
        }

        return {
            'k1_rankings': k1_rankings,
            'q1_rankings': q1_rankings,
            'k1_top3': k1_top3,
            'q1_top3': q1_top3,
            'summary': summary,
            'locations': locations
        }

    def _generate_recommendation(self, stats: Dict) -> str:
        """为算法生成推荐理由"""
        name = stats['name']
        hit_rate = stats['hit_rate']
        total = stats['total']
        stability = stats['stability']
        param_type = stats.get('param_type', '')

        reasons = []
        if hit_rate >= 80:
            reasons.append(f'{param_type}命中率高达{hit_rate}%')
        elif hit_rate >= 60:
            reasons.append(f'{param_type}命中率{hit_rate}%，表现稳健')

        if stability >= 70:
            reasons.append('表现稳定')

        if total >= 10:
            reasons.append(f'样本充足({total}次)')

        if not reasons:
            reasons.append(f'基于{total}次{param_type}预测的综合评估')

        return '；'.join(reasons)

    def get_algorithm_detail(self, user_id: int, algorithm_name: str,
                             location: str = None) -> Dict[str, Any]:
        """
        获取单个算法的详细统计（按月份的命中率趋势）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        conditions = ['user_id = ?', 'accuracy_checked = 1']
        params = [user_id]

        if location:
            conditions.append('location_filter = ?')
            params.append(location)

        where_clause = ' AND '.join(conditions)

        # K1 月度统计
        cursor.execute(f'''
            SELECT strftime('%Y-%m', prediction_time) as month,
                   COUNT(*) as total,
                   SUM(CASE WHEN ABS(CAST(k1_prediction AS REAL) - CAST(k1_actual AS REAL)) <= 0.005 THEN 1 ELSE 0 END) as hits
            FROM prediction_records
            WHERE {where_clause}
              AND k1_method = ?
              AND k1_actual IS NOT NULL AND k1_prediction IS NOT NULL
            GROUP BY month
            ORDER BY month
        ''', params + [algorithm_name])
        k1_monthly = [{'month': r[0], 'total': r[1], 'hits': r[2],
                       'hit_rate': round(r[2]/r[1]*100, 1) if r[1] > 0 else 0}
                      for r in cursor.fetchall()]

        # Q1 月度统计
        cursor.execute(f'''
            SELECT strftime('%Y-%m', prediction_time) as month,
                   COUNT(*) as total,
                   SUM(CASE WHEN ABS(CAST(q1_prediction AS REAL) - CAST(q1_actual AS REAL)) <= 0.05 THEN 1 ELSE 0 END) as hits
            FROM prediction_records
            WHERE {where_clause}
              AND q1_method = ?
              AND q1_actual IS NOT NULL AND q1_prediction IS NOT NULL
              AND method_prediction != '1'
            GROUP BY month
            ORDER BY month
        ''', params + [algorithm_name])
        q1_monthly = [{'month': r[0], 'total': r[1], 'hits': r[2],
                       'hit_rate': round(r[2]/r[1]*100, 1) if r[1] > 0 else 0}
                      for r in cursor.fetchall()]

        # 相关预测记录列表（最近 20 条）
        cursor.execute(f'''
            SELECT id, project_name, prediction_time, location_filter,
                   k1_prediction, k1_actual, k1_method,
                   q1_prediction, q1_actual, q1_method
            FROM prediction_records
            WHERE user_id = ? AND accuracy_checked = 1
              AND (k1_method = ? OR q1_method = ?)
            ORDER BY prediction_time DESC
            LIMIT 20
        ''', [user_id, algorithm_name, algorithm_name])
        records = []
        for row in cursor.fetchall():
            k1_dev = None
            if row[4] and row[5]:
                try:
                    k1_dev = round(abs(float(row[4]) - float(row[5])), 4)
                except:
                    pass
            q1_dev = None
            if row[7] and row[8]:
                try:
                    q1_dev = round(abs(float(row[7]) - float(row[8])), 4)
                except:
                    pass
            records.append({
                'id': row[0],
                'project_name': row[1],
                'prediction_time': row[2],
                'location': row[3],
                'k1_prediction': row[4],
                'k1_actual': row[5],
                'k1_method': row[6],
                'q1_prediction': row[7],
                'q1_actual': row[8],
                'q1_method': row[9],
                'k1_deviation': k1_dev,
                'q1_deviation': q1_dev,
            })

        conn.close()

        return {
            'algorithm_name': algorithm_name,
            'k1_monthly': k1_monthly,
            'q1_monthly': q1_monthly,
            'recent_records': records
        }
