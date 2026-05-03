#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6.0 数据分析与预测模块
20 种统计预测算法 + 序列模式分析
用于预测方法类别、K1、Q1 值
"""

import numpy as np
from collections import Counter
from typing import Dict, List, Optional, Tuple
from scipy import stats


class BidParameterAnalyzer:
    """开标参数分析器（V6.0 - 20 种方法）"""
    
    def __init__(self):
        pass
    
    # ==================== 15 种基础预测算法（V5.0）====================
    
    def analyze_arithmetic(self, values: np.ndarray) -> Optional[Dict]:
        """1. 等差数列分析"""
        if len(values) < 3:
            return None
        diffs = np.diff(values)
        if np.allclose(diffs, diffs[0], atol=0.002):
            next_val = values[-1] + diffs[0]
            return {
                'method': '等差数列',
                'prediction': float(next_val),
                'confidence': 0.95,
                'reasoning': f'公差为{diffs[0]:.4f}的等差数列'
            }
        return None
    
    def analyze_geometric(self, values: np.ndarray) -> Optional[Dict]:
        """2. 等比数列分析"""
        if len(values) < 3 or 0 in values:
            return None
        ratios = values[1:] / values[:-1]
        if np.allclose(ratios, ratios[0], atol=0.01):
            next_val = values[-1] * ratios[0]
            return {
                'method': '等比数列',
                'prediction': float(next_val),
                'confidence': 0.95,
                'reasoning': f'公比为{ratios[0]:.4f}的等比数列'
            }
        return None
    
    def analyze_polynomial(self, values: np.ndarray, order: int = 2) -> Optional[Dict]:
        """3. 多项式拟合"""
        if len(values) < order + 2:
            return None
        try:
            x = np.arange(len(values))
            coeffs = np.polyfit(x, values, order)
            poly = np.poly1d(coeffs)
            predicted = poly(x)
            r_squared = 1 - np.sum((values - predicted)**2) / np.sum((values - np.mean(values))**2)
            if r_squared > 0.85:
                next_val = poly(len(values))
                return {
                    'method': f'{order}阶多项式',
                    'prediction': float(next_val),
                    'confidence': 0.80 * r_squared,
                    'reasoning': f'{order}阶多项式拟合 (R²={r_squared:.3f})'
                }
        except Exception:
            pass
        return None
    
    def analyze_moving_average(self, values: np.ndarray, window: int = 3) -> Optional[Dict]:
        """4. 移动平均"""
        if len(values) < window + 1:
            return None
        ma = np.convolve(values, np.ones(window)/window, mode='valid')
        if len(ma) >= 2:
            trend = ma[-1] - ma[-2]
            next_val = values[-1] + trend
            return {
                'method': f'{window}期移动平均',
                'prediction': float(next_val),
                'confidence': 0.65,
                'reasoning': f'基于{window}期移动平均趋势'
            }
        return None
    
    def analyze_exponential_smoothing(self, values: np.ndarray, alpha: float = 0.3) -> Optional[Dict]:
        """5. 指数平滑"""
        if len(values) < 3:
            return None
        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1-alpha) * smoothed[-1])
        trend = smoothed[-1] - smoothed[-2]
        next_val = values[-1] + alpha * trend
        return {
            'method': '指数平滑',
            'prediction': float(next_val),
            'confidence': 0.70,
            'reasoning': f'指数平滑 (α={alpha})'
        }
    
    def analyze_linear_regression(self, values: np.ndarray) -> Optional[Dict]:
        """6. 线性回归"""
        if len(values) < 3:
            return None
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        if r_value**2 > 0.6:
            next_val = slope * len(values) + intercept
            return {
                'method': '线性回归',
                'prediction': float(next_val),
                'confidence': 0.75 * r_value**2,
                'reasoning': f'线性回归 (R²={r_value**2:.3f}, 斜率={slope:.4f})'
            }
        return None
    
    def analyze_seasonal(self, values: np.ndarray, period: int = 4) -> Optional[Dict]:
        """7. 周期性分析"""
        if len(values) < period * 2:
            return None
        first_period = values[:period]
        second_period = values[period:2*period]
        if np.allclose(first_period, second_period, atol=0.005):
            next_idx = len(values) % period
            next_val = values[next_idx] if next_idx < len(values) else values[0]
            return {
                'method': f'周期性 (周期={period})',
                'prediction': float(next_val),
                'confidence': 0.90,
                'reasoning': f'发现{period}期循环规律'
            }
        return None
    
    def analyze_fibonacci(self, values: np.ndarray) -> Optional[Dict]:
        """8. 斐波那契数列"""
        if len(values) < 3:
            return None
        for i in range(2, len(values)):
            if not np.isclose(values[i], values[i-1] + values[i-2], atol=0.01):
                return None
        next_val = values[-1] + values[-2]
        return {
            'method': '斐波那契数列',
            'prediction': float(next_val),
            'confidence': 0.95,
            'reasoning': '满足斐波那契递推关系'
        }
    
    def analyze_power_law(self, values: np.ndarray) -> Optional[Dict]:
        """9. 幂律分布"""
        if len(values) < 4 or any(v <= 0 for v in values):
            return None
        try:
            log_x = np.log(np.arange(1, len(values)+1))
            log_y = np.log(values)
            slope, intercept, r_value, _, _ = stats.linregress(log_x, log_y)
            if r_value**2 > 0.85:
                next_val = np.exp(intercept) * (len(values)+1)**slope
                return {
                    'method': '幂律分布',
                    'prediction': float(next_val),
                    'confidence': 0.80 * r_value**2,
                    'reasoning': f'幂律分布 (R²={r_value**2:.3f})'
                }
        except Exception:
            pass
        return None
    
    def analyze_mean_reversion(self, values: np.ndarray) -> Optional[Dict]:
        """10. 均值回归"""
        if len(values) < 5:
            return None
        mean = np.mean(values)
        std = np.std(values)
        if std > 0 and abs(values[-1] - mean) > std:
            next_val = values[-1] + 0.5 * (mean - values[-1])
            return {
                'method': '均值回归',
                'prediction': float(next_val),
                'confidence': 0.60,
                'reasoning': f'偏离均值{((values[-1] - mean) / std):.2f}个标准差，预测回归'
            }
        return None
    
    def analyze_bollinger(self, values: np.ndarray, window: int = 5) -> Optional[Dict]:
        """11. 布林带"""
        if len(values) < window + 2:
            return None
        ma = np.mean(values[-window:])
        std = np.std(values[-window:])
        if std > 0:
            upper = ma + 2 * std
            lower = ma - 2 * std
            if values[-1] > upper:
                next_val = values[-1] - 0.3 * std
                return {
                    'method': '布林带',
                    'prediction': float(next_val),
                    'confidence': 0.65,
                    'reasoning': '突破上轨，预测回调'
                }
            elif values[-1] < lower:
                next_val = values[-1] + 0.3 * std
                return {
                    'method': '布林带',
                    'prediction': float(next_val),
                    'confidence': 0.65,
                    'reasoning': '突破下轨，预测反弹'
                }
        return None
    
    def analyze_momentum(self, values: np.ndarray) -> Optional[Dict]:
        """12. 动量分析"""
        if len(values) < 4:
            return None
        recent_momentum = values[-1] - values[-3]
        prev_momentum = values[-3] - values[-5] if len(values) >= 5 else recent_momentum
        if abs(prev_momentum) > 0.0001 and abs(recent_momentum) > abs(prev_momentum) * 1.2:
            next_val = values[-1] + recent_momentum * 0.5
            return {
                'method': '动量分析',
                'prediction': float(next_val),
                'confidence': 0.55,
                'reasoning': '动量增强，趋势延续'
            }
        return None
    
    def analyze_standard_values(self, values: np.ndarray, standard_set: List[float]) -> Optional[Dict]:
        """13. 标准值匹配"""
        if len(values) < 3 or not standard_set:
            return None
        recent = values[-3:]
        for std_val in standard_set:
            if all(np.isclose(v, std_val, atol=0.005) for v in recent):
                return {
                    'method': '标准值匹配',
                    'prediction': float(std_val),
                    'confidence': 0.90,
                    'reasoning': f'近期稳定在标准值{std_val:.3f}'
                }
        return None
    
    def analyze_markov(self, values: np.ndarray, states: int = 3) -> Optional[Dict]:
        """14. 马尔可夫链"""
        if len(values) < states * 2:
            return None
        low = np.percentile(values, 33)
        high = np.percentile(values, 67)
        def get_state(val):
            if val < low: return 0
            elif val < high: return 1
            else: return 2
        states_seq = [get_state(v) for v in values]
        transitions = {}
        for i in range(len(states_seq) - 1):
            curr = states_seq[i]
            next_s = states_seq[i + 1]
            if curr not in transitions: transitions[curr] = []
            transitions[curr].append(next_s)
        curr_state = states_seq[-1]
        if curr_state in transitions and transitions[curr_state]:
            next_state = max(set(transitions[curr_state]), key=transitions[curr_state].count)
            if next_state == 0: next_val = low * 0.95
            elif next_state == 1: next_val = (low + high) / 2
            else: next_val = high * 1.05
            return {
                'method': '马尔可夫链',
                'prediction': float(next_val),
                'confidence': 0.60,
                'reasoning': f'状态转移预测 (当前状态{curr_state}→{next_state})'
            }
        return None
    
    def analyze_weighted_average(self, values: np.ndarray) -> Optional[Dict]:
        """15. 加权平均"""
        if len(values) < 3:
            return None
        weights = np.arange(1, len(values) + 1)
        weighted_avg = np.average(values, weights=weights)
        recent_trend = values[-1] - values[-2] if len(values) >= 2 else 0
        next_val = weighted_avg + recent_trend * 0.3
        return {
            'method': '加权平均',
            'prediction': float(next_val),
            'confidence': 0.60,
            'reasoning': '近期值加权平均 (权重递增)'
        }
    
    # ==================== 5 种新增方法（V6.0）====================
    
    def analyze_ngram_pattern(self, values: np.ndarray, n: int = 2) -> Optional[Dict]:
        """16. N-gram 序列模式分析
        找出连续 n 个值组成的模式，预测下一个值"""
        if len(values) < n + 2:
            return None
        ngrams = {}
        for i in range(len(values) - n):
            key = tuple(round(v, 3) for v in values[i:i+n])
            next_val = values[i+n]
            if key not in ngrams: ngrams[key] = []
            ngrams[key].append(next_val)
        current = tuple(round(v, 3) for v in values[-n:])
        if current in ngrams:
            predicted = np.mean(ngrams[current])
            freq = len(ngrams[current])
            conf = min(0.90, 0.5 + freq * 0.1)
            return {
                'method': f'{n}-gram 模式',
                'prediction': float(predicted),
                'confidence': conf,
                'reasoning': f'历史出现{freq}次类似模式，预测下一值'
            }
        return None
    
    def analyze_transition_matrix(self, values: np.ndarray, standard_set: List[float]) -> Optional[Dict]:
        """17. 转移概率矩阵分析
        构建值之间的转移概率，预测最可能的下一个值"""
        if len(values) < 5 or not standard_set:
            return None
        # 将值映射到最近的标准值
        def to_std(v):
            return min(standard_set, key=lambda x: abs(x - v))
        mapped = [to_std(v) for v in values]
        # 构建转移矩阵
        trans = {}
        for i in range(len(mapped) - 1):
            curr, nxt = mapped[i], mapped[i+1]
            if curr not in trans: trans[curr] = Counter()
            trans[curr][nxt] += 1
        curr = mapped[-1]
        if curr in trans:
            most_likely = trans[curr].most_common(1)[0]
            next_val = most_likely[0]
            total = sum(trans[curr].values())
            prob = most_likely[1] / total
            return {
                'method': '转移概率矩阵',
                'prediction': float(next_val),
                'confidence': round(min(0.85, prob), 3),
                'reasoning': f'从当前值转移到{next_val:.3f}的概率为{prob*100:.1f}%'
            }
        return None
    
    def analyze_longest_repeat(self, values: np.ndarray, standard_set: List[float]) -> Optional[Dict]:
        """18. 最长重复子序列分析
        找出最长的重复模式，基于最后一次出现预测下一个值"""
        if len(values) < 6:
            return None
        def to_std(v):
            return min(standard_set, key=lambda x: abs(x - v))
        mapped = tuple(to_std(v) for v in values)
        best_len = 0
        best_pred = None
        for length in range(2, len(mapped) // 2 + 1):
            for i in range(len(mapped) - 2 * length + 1):
                seq = mapped[i:i+length]
                # 查找后续出现
                for j in range(i + length, len(mapped) - length + 1):
                    if mapped[j:j+length] == seq:
                        if j + length < len(mapped):
                            pred = mapped[j + length]
                            if length > best_len:
                                best_len = length
                                best_pred = pred
        if best_pred is not None and best_len >= 2:
            return {
                'method': '最长重复子序列',
                'prediction': float(best_pred),
                'confidence': round(min(0.88, 0.5 + best_len * 0.1), 3),
                'reasoning': f'发现长度为{best_len}的重复模式'
            }
        return None
    
    def analyze_autocorrelation(self, values: np.ndarray) -> Optional[Dict]:
        """19. 自相关性分析
        检测序列的自相关性，找出显著滞后并基于滞后预测"""
        if len(values) < 10:
            return None
        n = len(values)
        mean = np.mean(values)
        var = np.var(values)
        if var == 0:
            return None
        best_lag = None
        best_corr = 0
        for lag in range(1, n // 2):
            corr = sum((values[i] - mean) * (values[i + lag] - mean) for i in range(n - lag)) / ((n - lag) * var)
            if abs(corr) > abs(best_corr) and abs(corr) > 0.5:
                best_corr = corr
                best_lag = lag
        if best_lag and abs(best_corr) > 0.5:
            if best_lag < len(values):
                next_val = values[-1] + best_corr * (values[-1] - values[-best_lag - 1])
                return {
                    'method': '自相关性分析',
                    'prediction': float(next_val),
                    'confidence': round(min(0.80, abs(best_corr) * 0.8), 3),
                    'reasoning': f'滞后{best_lag}期自相关系数={best_corr:.3f}'
                }
        return None
    
    def analyze_frequency_heatmap(self, values: np.ndarray, standard_set: List[float]) -> Optional[Dict]:
        """20. 频次热区分析
        统计各标准值的出现频率，结合近期趋势预测"""
        if len(values) < 5 or not standard_set:
            return None
        # 统计全局频率
        def to_std(v):
            return min(standard_set, key=lambda x: abs(x - v))
        mapped = [to_std(v) for v in values]
        global_freq = Counter(mapped)
        # 统计近期频率（后 1/3）
        recent_len = max(3, len(values) // 3)
        recent = mapped[-recent_len:]
        recent_freq = Counter(recent)
        # 综合评分 = 全局频率 * 0.3 + 近期频率 * 0.7
        scores = {}
        for sv in standard_set:
            g = global_freq.get(sv, 0) / len(values)
            r = recent_freq.get(sv, 0) / len(recent)
            scores[sv] = 0.3 * g + 0.7 * r
        best_val = max(scores, key=scores.get)
        score = scores[best_val]
        return {
            'method': '频次热区分析',
            'prediction': float(best_val),
            'confidence': round(min(0.85, score * 2), 3),
            'reasoning': f'综合频率最高值，近期权重 70%'
        }
    
    # ==================== 综合分析 ====================
    
    def analyze_all_methods(self, values: np.ndarray, param_name: str,
                           standard_set: Optional[List[float]] = None) -> List[Dict]:
        """运行所有 20 种预测算法"""
        results = []
        
        # 1-15: V5.0 基础方法
        for method in [
            self.analyze_arithmetic, self.analyze_geometric,
            lambda v: self.analyze_polynomial(v, 2),
            lambda v: self.analyze_moving_average(v, 3),
            lambda v: self.analyze_exponential_smoothing(v, 0.3),
            self.analyze_linear_regression,
            lambda v: self.analyze_seasonal(v, 4),
            self.analyze_fibonacci, self.analyze_power_law,
            self.analyze_mean_reversion,
            lambda v: self.analyze_bollinger(v, 5),
            self.analyze_momentum,
            lambda v: self.analyze_standard_values(v, standard_set) if standard_set else None,
            self.analyze_markov,
            self.analyze_weighted_average
        ]:
            result = method(values)
            if result: results.append(result)
        
        # 16-20: V6.0 新增方法
        # 16. N-gram
        result = self.analyze_ngram_pattern(values, 2)
        if result: results.append(result)
        
        # 17. 转移概率矩阵
        if standard_set:
            result = self.analyze_transition_matrix(values, standard_set)
            if result: results.append(result)
        
        # 18. 最长重复子序列
        if standard_set:
            result = self.analyze_longest_repeat(values, standard_set)
            if result: results.append(result)
        
        # 19. 自相关性分析
        result = self.analyze_autocorrelation(values)
        if result: results.append(result)
        
        # 20. 频次热区分析
        if standard_set:
            result = self.analyze_frequency_heatmap(values, standard_set)
            if result: results.append(result)
        
        # 按置信度排序
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results
    
    def standardize_k1(self, value: float) -> float:
        """标准化 K1 值（0.950-0.980，间隔 0.005）"""
        standard_values = [0.950, 0.955, 0.960, 0.965, 0.970, 0.975, 0.980]
        value = max(0.950, min(0.980, value))
        return min(standard_values, key=lambda x: abs(x - value))
    
    def standardize_k2(self, value: float) -> float:
        """标准化 K2 值（0.86-1.00，间隔 0.01）"""
        standard_values = [round(0.86 + i * 0.01, 2) for i in range(15)]
        value = max(0.86, min(1.00, value))
        return min(standard_values, key=lambda x: abs(x - value))
    
    def standardize_q1(self, value: float) -> float:
        """标准化 Q1 值（0.65-0.85，间隔 0.05）"""
        standard_values = [0.65, 0.70, 0.75, 0.80, 0.85]
        value = max(0.65, min(0.85, value))
        return min(standard_values, key=lambda x: abs(x - value))
    
    def analyze(self, param_name: str, values: List[float],
                standard_set: Optional[List[float]] = None) -> Dict:
        """综合分析入口"""
        if not values or len(values) < 3:
            return {
                'success': False,
                'error': '数据量不足，至少需要 3 条数据',
                'predictions': []
            }
        
        np_values = np.array(values)
        results = self.analyze_all_methods(np_values, param_name, standard_set)
        
        if results:
            best = results[0]
            
            # 标准化预测结果
            if param_name.lower() == 'k1' and 'prediction' in best:
                best['original_prediction'] = best['prediction']
                best['prediction'] = self.standardize_k1(best['prediction'])
                best['reasoning'] += f'（已标准化为{best["prediction"]:.3f}）'
            elif param_name.lower() == 'k2' and 'prediction' in best:
                best['original_prediction'] = best['prediction']
                best['prediction'] = self.standardize_k2(best['prediction'])
                best['reasoning'] += f'（已标准化为{best["prediction"]:.2f}）'
            elif param_name.lower() == 'q1' and 'prediction' in best:
                best['original_prediction'] = best['prediction']
                best['prediction'] = self.standardize_q1(best['prediction'])
                best['reasoning'] += f'（已标准化为{best["prediction"]:.2f}）'
            
            # 标准化前 5 个预测结果
            for pred in results[:5]:
                if 'prediction' in pred:
                    if param_name.lower() == 'k1':
                        pred['original_prediction'] = pred['prediction']
                        pred['prediction'] = self.standardize_k1(pred['prediction'])
                    elif param_name.lower() == 'k2':
                        pred['original_prediction'] = pred['prediction']
                        pred['prediction'] = self.standardize_k2(pred['prediction'])
                    elif param_name.lower() == 'q1':
                        pred['original_prediction'] = pred['prediction']
                        pred['prediction'] = self.standardize_q1(pred['prediction'])
            
            return {
                'success': True,
                'best_prediction': best,
                'all_predictions': results[:5],
                'data_count': len(values),
                'param_name': param_name,
                'total_methods': len(results)
            }
        else:
            return {
                'success': False,
                'error': '未发现明显规律',
                'predictions': [],
                'total_methods': 0
            }
    
    def predict_method_category(self, method_values: List[str]) -> Dict:
        """预测方法类别（基于众数和马尔可夫链）"""
        if not method_values:
            return {'success': False, 'error': '无方法类别数据'}
        
        # 方法 1: 众数
        counter = Counter(method_values)
        most_common = counter.most_common(1)[0]
        mode_result = {
            'method': '统计分析（众数）',
            'prediction': most_common[0],
            'confidence': round(most_common[1] / len(method_values), 3),
            'reasoning': f'历史出现{most_common[1]}次, 占比{most_common[1]/len(method_values)*100:.1f}%'
        }
        
        # 方法 2: 马尔可夫链（类别转移）
        if len(method_values) >= 5:
            transitions = {}
            for i in range(len(method_values) - 1):
                curr, nxt = method_values[i], method_values[i+1]
                if curr not in transitions: transitions[curr] = Counter()
                transitions[curr][nxt] += 1
            curr = method_values[-1]
            if curr in transitions:
                most_likely = transitions[curr].most_common(1)[0]
                total = sum(transitions[curr].values())
                prob = most_likely[1] / total
                markov_result = {
                    'method': '马尔可夫链（类别转移）',
                    'prediction': most_likely[0],
                    'confidence': round(prob, 3),
                    'reasoning': f'方法{curr}→方法{most_likely[0]}的概率{prob*100:.1f}%'
                }
                results = [markov_result, mode_result]
                results.sort(key=lambda x: x['confidence'], reverse=True)
                return {
                    'success': True,
                    'best_prediction': results[0],
                    'all_predictions': results,
                    'data_count': len(method_values)
                }
        
        return {
            'success': True,
            'best_prediction': mode_result,
            'all_predictions': [mode_result],
            'data_count': len(method_values)
        }
