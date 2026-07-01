#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预测记录数据模型
处理预测记录的数据库操作
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any


class Prediction:
    """预测记录模型"""

    def __init__(self, db_path: str = "bid_database.db"):
        """初始化模型"""
        self.db_path = db_path
        self.init_table()
        self.init_algorithm_details_table()

    def init_table(self):
        """初始化预测记录表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建预测记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                project_name TEXT,
                location_filter TEXT,
                method_filter TEXT,
                date_from TEXT,
                date_to TEXT,
                data_count INTEGER,
                method_prediction TEXT,
                method_confidence REAL,
                k1_prediction TEXT,
                k1_confidence REAL,
                k1_method TEXT,
                q1_prediction TEXT,
                q1_confidence REAL,
                q1_method TEXT,
                used_ai INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # 添加准确率相关字段（如果不存在）
        try:
            cursor.execute('ALTER TABLE prediction_records ADD COLUMN k1_actual TEXT')
        except Exception:
            pass  # 字段已存在
        try:
            cursor.execute('ALTER TABLE prediction_records ADD COLUMN q1_actual TEXT')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE prediction_records ADD COLUMN method_actual TEXT')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE prediction_records ADD COLUMN accuracy_checked INTEGER DEFAULT 0')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE prediction_records ADD COLUMN checked_time TIMESTAMP')
        except Exception:
            pass

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prediction_user ON prediction_records(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prediction_time ON prediction_records(prediction_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prediction_project ON prediction_records(project_name)')

        # 添加唯一约束（用户 + 项目名称）- 防止同一项目重复预测
        try:
            # 如果存在重复数据，先保留每个项目 id 最大的记录，删除其余
            cursor.execute('''
                DELETE FROM prediction_records
                WHERE id NOT IN (
                    SELECT MAX(id) FROM prediction_records GROUP BY user_id, COALESCE(project_name, '')
                )
            ''')
            cleaned = cursor.rowcount
            if cleaned > 0:
                print(f"🧹 清理了 {cleaned} 条重复预测记录，准备创建唯一索引")
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_prediction_user_project ON prediction_records(user_id, COALESCE(project_name, ""))')
            print("✅ 已创建预测记录唯一索引：user_id + project_name")
        except Exception as e:
            print(f"⚠️ 创建预测唯一索引失败: {e}")

        conn.commit()
        conn.close()

    def init_algorithm_details_table(self):
        """初始化算法详情表（存储每次预测的 Top5 算法数据）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_algorithm_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER NOT NULL,
                param_type TEXT NOT NULL,
                rank INTEGER NOT NULL,
                algorithm_name TEXT NOT NULL,
                prediction_value TEXT NOT NULL,
                confidence REAL NOT NULL,
                FOREIGN KEY (prediction_id) REFERENCES prediction_records(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_algo_detail_prediction ON prediction_algorithm_details(prediction_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_algo_detail_param ON prediction_algorithm_details(param_type)')

        conn.commit()
        conn.close()

    def save_algorithm_details(self, prediction_id: int, param_type: str, algorithms: List[Dict]) -> bool:
        """保存 Top5 算法详情
        
        Args:
            prediction_id: 预测记录 ID
            param_type: 参数类型 ('K1' 或 'Q1')
            algorithms: 算法列表，每项包含 method, prediction, confidence
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 先删除该预测记录对应参数类型的旧数据（支持覆盖）
            cursor.execute('DELETE FROM prediction_algorithm_details WHERE prediction_id = ? AND param_type = ?',
                           (prediction_id, param_type))

            # 插入新的 Top5 算法数据
            for rank, algo in enumerate(algorithms[:5], start=1):
                cursor.execute('''
                    INSERT INTO prediction_algorithm_details
                    (prediction_id, param_type, rank, algorithm_name, prediction_value, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    prediction_id,
                    param_type,
                    rank,
                    algo.get('method', ''),
                    str(algo.get('prediction', '')),
                    algo.get('confidence', 0)
                ))

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"❌ 保存算法详情失败: {e}")
            return False
        finally:
            conn.close()

    def get_algorithm_details(self, prediction_id: int, param_type: str = None) -> List[Dict]:
        """获取预测记录的算法详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if param_type:
            cursor.execute('''
                SELECT rank, algorithm_name, prediction_value, confidence
                FROM prediction_algorithm_details
                WHERE prediction_id = ? AND param_type = ?
                ORDER BY rank
            ''', (prediction_id, param_type))
        else:
            cursor.execute('''
                SELECT param_type, rank, algorithm_name, prediction_value, confidence
                FROM prediction_algorithm_details
                WHERE prediction_id = ?
                ORDER BY param_type, rank
            ''', (prediction_id,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            if param_type:
                results.append({
                    'rank': row[0],
                    'algorithm_name': row[1],
                    'prediction_value': row[2],
                    'confidence': row[3]
                })
            else:
                results.append({
                    'param_type': row[0],
                    'rank': row[1],
                    'algorithm_name': row[2],
                    'prediction_value': row[3],
                    'confidence': row[4]
                })
        return results

    def create_prediction(self, user_id: int, prediction_data: Dict[str, Any]) -> int:
        """创建预测记录（使用北京时间）
        Returns: 新记录 ID，失败返回 -1
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 使用北京时间
        beijing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            cursor.execute('''
                INSERT INTO prediction_records
                (user_id, prediction_time, project_name, location_filter, method_filter, date_from, date_to,
                 data_count, method_prediction, method_confidence,
                 k1_prediction, k1_confidence, k1_method,
                 q1_prediction, q1_confidence, q1_method, used_ai)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                beijing_time,
                prediction_data.get('project_name'),
                prediction_data.get('location_filter'),
                prediction_data.get('method_filter'),
                prediction_data.get('date_from'),
                prediction_data.get('date_to'),
                prediction_data.get('data_count', 0),
                prediction_data.get('method_prediction'),
                prediction_data.get('method_confidence'),
                prediction_data.get('k1_prediction'),
                prediction_data.get('k1_confidence'),
                prediction_data.get('k1_method'),
                prediction_data.get('q1_prediction'),
                prediction_data.get('q1_confidence'),
                prediction_data.get('q1_method'),
                int(prediction_data.get('used_ai', False))
            ))

            record_id = cursor.lastrowid
            conn.commit()
            return record_id
        except sqlite3.Error as e:
            print(f"❌ 创建预测记录失败: {e}")
            return -1
        finally:
            conn.close()

    def get_prediction_by_project(self, user_id: int, project_name: str) -> Optional[Dict[str, Any]]:
        """根据项目名称查询用户已有的预测记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, project_name, prediction_time, method_prediction, method_confidence,
                   k1_prediction, k1_confidence, k1_method,
                   q1_prediction, q1_confidence, q1_method, data_count
            FROM prediction_records
            WHERE user_id = ? AND project_name = ?
            ORDER BY prediction_time DESC
            LIMIT 1
        ''', (user_id, project_name))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'project_name': row[1],
                'prediction_time': row[2],
                'method_prediction': row[3],
                'method_confidence': row[4],
                'k1_prediction': row[5],
                'k1_confidence': row[6],
                'k1_method': row[7],
                'q1_prediction': row[8],
                'q1_confidence': row[9],
                'q1_method': row[10],
                'data_count': row[11]
            }
        return None

    def update_prediction(self, record_id: int, user_id: int, prediction_data: Dict[str, Any]) -> bool:
        """更新预测记录（支持覆盖，包括将字段设为 NULL）
        
        当 method_prediction 变为方法1时，q1_prediction/q1_confidence/q1_method 会被置为 NULL
        Returns: 是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 使用北京时间
        beijing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建 SET 子句 - 所有字段都允许更新为 NULL
        fields = [
            'prediction_time', 'project_name', 'location_filter', 'method_filter',
            'date_from', 'date_to', 'data_count',
            'method_prediction', 'method_confidence',
            'k1_prediction', 'k1_confidence', 'k1_method',
            'q1_prediction', 'q1_confidence', 'q1_method', 'used_ai'
        ]
        set_clauses = [f'{f} = ?' for f in fields]
        params = [
            beijing_time,
            prediction_data.get('project_name'),
            prediction_data.get('location_filter'),
            prediction_data.get('method_filter'),
            prediction_data.get('date_from'),
            prediction_data.get('date_to'),
            prediction_data.get('data_count', 0),
            prediction_data.get('method_prediction'),
            prediction_data.get('method_confidence'),
            prediction_data.get('k1_prediction'),
            prediction_data.get('k1_confidence'),
            prediction_data.get('k1_method'),
            prediction_data.get('q1_prediction'),  # 可以为 None → NULL
            prediction_data.get('q1_confidence'),  # 可以为 None → NULL
            prediction_data.get('q1_method'),      # 可以为 None → NULL
            int(prediction_data.get('used_ai', False))
        ]
        
        # 如果方法变为方法1，确保 Q1 字段被清除
        if prediction_data.get('method_prediction') == '1':
            # q1_prediction 等已经是 None，SQL 会写入 NULL
            pass
        
        set_clauses.append('accuracy_checked = 0')
        set_clauses.append('checked_time = NULL')
        set_clauses.append('k1_actual = NULL')
        set_clauses.append('q1_actual = NULL')
        set_clauses.append('method_actual = NULL')
        
        params.extend([record_id, user_id])
        
        sql = f"UPDATE prediction_records SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?"
        
        try:
            cursor.execute(sql, params)
            success = cursor.rowcount > 0
            conn.commit()
            if success:
                print(f"✅ 预测记录已更新: id={record_id}, project={prediction_data.get('project_name')}")
            return success
        except sqlite3.Error as e:
            print(f"❌ 更新预测记录失败: {e}")
            return False
        finally:
            conn.close()

    def get_predictions(self, user_id: int, limit: int = 50,
                      offset: int = 0, keyword: str = None,
                      date_from: str = None, date_to: str = None) -> tuple:
        """获取预测记录（分页），支持关键字搜索和时间筛选"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = ['user_id = ?']
        params = [user_id]
        
        if keyword:
            conditions.append('(project_name LIKE ? OR method_prediction LIKE ? OR k1_prediction LIKE ? OR q1_prediction LIKE ?)')
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw, kw])
        
        if date_from:
            conditions.append('prediction_time >= ?')
            params.append(date_from + ' 00:00:00')
        
        if date_to:
            conditions.append('prediction_time <= ?')
            params.append(date_to + ' 23:59:59')
        
        where_clause = ' AND '.join(conditions)
        
        # 获取总数
        cursor.execute(f'SELECT COUNT(*) FROM prediction_records WHERE {where_clause}', params)
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        cursor.execute(f'''
            SELECT * FROM prediction_records
            WHERE {where_clause}
            ORDER BY prediction_time DESC
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])

        records = cursor.fetchall()
        conn.close()

        predictions = []
        for row in records:
            predictions.append({
                'id': row[0],
                'user_id': row[1],
                'prediction_time': row[2],
                'project_name': row[3],
                'location_filter': row[4],
                'method_filter': row[5],
                'date_from': row[6],
                'date_to': row[7],
                'data_count': row[8],
                'method_prediction': row[9],
                'method_confidence': row[10],
                'k1_prediction': row[11],
                'k1_confidence': row[12],
                'k1_method': row[13],
                'q1_prediction': row[14],
                'q1_confidence': row[15],
                'q1_method': row[16],
                'used_ai': bool(row[17])
            })

        return predictions, total

    def get_prediction_by_id(self, prediction_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取预测记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM prediction_records
            WHERE id = ? AND user_id = ?
        ''', (prediction_id, user_id))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'prediction_time': row[2],
                'project_name': row[3],
                'location_filter': row[4],
                'method_filter': row[5],
                'date_from': row[6],
                'date_to': row[7],
                'data_count': row[8],
                'method_prediction': row[9],
                'method_confidence': row[10],
                'k1_prediction': row[11],
                'k1_confidence': row[12],
                'k1_method': row[13],
                'q1_prediction': row[14],
                'q1_confidence': row[15],
                'q1_method': row[16],
                'used_ai': bool(row[17])
            }
        return None

    def delete_prediction(self, prediction_id: int, user_id: int) -> bool:
        """删除预测记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM prediction_records
            WHERE id = ? AND user_id = ?
        ''', (prediction_id, user_id))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def clear_all_predictions(self, user_id: int) -> int:
        """清空用户的所有预测记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM prediction_records WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()
        return deleted_count

    def auto_match_actual_values(self, user_id: int) -> Dict[str, Any]:
        """从开标记录中自动匹配真实值回填到预测记录
        
        匹配规则：按项目名称精确匹配
        回填字段：k1_actual, q1_actual, method_actual
        仅回填尚未录入真实值的记录
        
        Returns:
            Dict with matched_count, skipped_count, error_count
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 查询所有预测记录（项目名称不为空）
            cursor.execute('''
                SELECT id, project_name, k1_actual, q1_actual, method_actual
                FROM prediction_records
                WHERE user_id = ? AND project_name IS NOT NULL AND project_name != ''
            ''', (user_id,))
            predictions = cursor.fetchall()

            # 查询所有开标记录，按项目名称建立索引
            cursor.execute('''
                SELECT project_name, k1_value, q1_value, method_category
                FROM bid_records
                WHERE user_id = ?
            ''', (user_id,))
            bid_records = cursor.fetchall()

            # 建立项目名称 → 真实值 的映射（去除前后空格）
            bid_map = {}
            for project_name, k1, q1, method in bid_records:
                if project_name:
                    # 去除前后空格，取最新的一条记录（后面导入的会覆盖前面的）
                    normalized_name = project_name.strip()
                    bid_map[normalized_name] = {
                        'k1': k1,
                        'q1': q1,
                        'method': method
                    }

            matched_count = 0
            skipped_count = 0

            for pred_id, project_name, k1_act, q1_act, method_act in predictions:
                # 跳过已录入真实值的记录
                if k1_act or q1_act or method_act:
                    skipped_count += 1
                    continue

                # 精确匹配项目名称（去除前后空格）
                normalized_pred_name = project_name.strip()
                if normalized_pred_name in bid_map:
                    bid = bid_map[normalized_pred_name]
                    
                    updates = []
                    params = []
                    
                    if bid['k1'] is not None:
                        updates.append('k1_actual = ?')
                        params.append(bid['k1'])
                    if bid['q1'] is not None:
                        updates.append('q1_actual = ?')
                        params.append(bid['q1'])
                    if bid['method'] is not None:
                        updates.append('method_actual = ?')
                        params.append(bid['method'])
                    
                    if updates:
                        updates.append('accuracy_checked = 1')
                        # 使用北京时间
                        beijing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        updates.append("checked_time = '" + beijing_time + "'")
                        params.extend([pred_id, user_id])
                        
                        cursor.execute(f'''
                            UPDATE prediction_records
                            SET {', '.join(updates)}
                            WHERE id = ? AND user_id = ?
                        ''', params)
                        matched_count += 1

            conn.commit()
            return {
                'success': True,
                'matched_count': matched_count,
                'skipped_count': skipped_count,
                'total_predictions': len(predictions)
            }
        except sqlite3.Error as e:
            conn.rollback()
            print(f"❌ 自动匹配真实值失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()

    def get_statistics(self, user_id: int) -> Dict[str, Any]:
        """获取预测统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总预测次数
        cursor.execute('SELECT COUNT(*) FROM prediction_records WHERE user_id = ?', (user_id,))
        total_predictions = cursor.fetchone()[0]

        # 本月预测次数
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('''
            SELECT COUNT(*) FROM prediction_records
            WHERE user_id = ? AND strftime('%Y-%m', prediction_time) = ?
        ''', (user_id, current_month))
        month_predictions = cursor.fetchone()[0]

        # AI 使用统计
        cursor.execute('''
            SELECT COUNT(*) FROM prediction_records
            WHERE user_id = ? AND used_ai = 1
        ''', (user_id,))
        ai_used_count = cursor.fetchone()[0]

        # 预测方法统计
        cursor.execute('''
            SELECT k1_method, COUNT(*)
            FROM prediction_records
            WHERE user_id = ? AND k1_method IS NOT NULL
            GROUP BY k1_method
            ORDER BY COUNT(*) DESC
            LIMIT 5
        ''', (user_id,))
        method_stats = dict(cursor.fetchall())

        conn.close()

        return {
            'total_predictions': total_predictions,
            'month_predictions': month_predictions,
            'ai_used_count': ai_used_count,
            'method_stats': method_stats
        }

    def get_recent_accuracy(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """
        获取近 N 天的预测准确率统计
        Returns: {
            'total_checked': 已对比总数,
            'method_correct': 方法类别正确数,
            'method_accuracy': 方法准确率,
            'k1_accurate': K1 精准数（偏差=0）,
            'k1_normal': K1 一般数（偏差≤0.01）,
            'k1_accuracy': K1 精准率,
            'q1_accurate': Q1 精准数（偏差=0）,
            'q1_normal': Q1 一般数（偏差≤0.1）,
            'q1_accuracy': Q1 精准率,
        }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 查询近 N 天已对比的预测记录
        date_threshold = (datetime.now() - __import__('datetime').timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM prediction_records
            WHERE user_id = ? AND accuracy_checked = 1 AND prediction_time >= ?
        ''', (user_id, date_threshold))
        total_checked = cursor.fetchone()[0]

        if total_checked == 0:
            conn.close()
            return {
                'total_checked': 0,
                'method_correct': 0,
                'method_accuracy': 0,
                'k1_accurate': 0,
                'k1_normal': 0,
                'k1_accuracy': 0,
                'q1_accurate': 0,
                'q1_normal': 0,
                'q1_accuracy': 0,
            }

        # 方法类别正确数
        cursor.execute('''
            SELECT COUNT(*) FROM prediction_records
            WHERE user_id = ? AND accuracy_checked = 1 AND prediction_time >= ?
              AND method_actual IS NOT NULL AND method_prediction IS NOT NULL
              AND TRIM(method_prediction) = TRIM(method_actual)
        ''', (user_id, date_threshold))
        method_correct = cursor.fetchone()[0]

        # K1 精准/一般数
        cursor.execute('''
            SELECT k1_prediction, k1_actual FROM prediction_records
            WHERE user_id = ? AND accuracy_checked = 1 AND prediction_time >= ?
              AND k1_actual IS NOT NULL AND k1_prediction IS NOT NULL
        ''', (user_id, date_threshold))
        k1_rows = cursor.fetchall()
        k1_accurate = 0
        k1_normal = 0
        for pred, actual in k1_rows:
            try:
                deviation = abs(float(pred) - float(actual))
                if deviation == 0:
                    k1_accurate += 1
                elif deviation <= 0.01:
                    k1_normal += 1
            except (ValueError, TypeError):
                pass

        # Q1 精准/一般数
        cursor.execute('''
            SELECT q1_prediction, q1_actual FROM prediction_records
            WHERE user_id = ? AND accuracy_checked = 1 AND prediction_time >= ?
              AND q1_actual IS NOT NULL AND q1_prediction IS NOT NULL
              AND method_prediction != '1'
        ''', (user_id, date_threshold))
        q1_rows = cursor.fetchall()
        q1_accurate = 0
        q1_normal = 0
        for pred, actual in q1_rows:
            try:
                deviation = abs(float(pred) - float(actual))
                if deviation == 0:
                    q1_accurate += 1
                elif deviation <= 0.1:
                    q1_normal += 1
            except (ValueError, TypeError):
                pass

        conn.close()

        return {
            'total_checked': total_checked,
            'method_correct': method_correct,
            'method_accuracy': round(method_correct / total_checked * 100, 1) if total_checked > 0 else 0,
            'k1_accurate': k1_accurate,
            'k1_normal': k1_normal,
            'k1_accuracy': round((k1_accurate + k1_normal) / len(k1_rows) * 100, 1) if k1_rows else 0,
            'q1_accurate': q1_accurate,
            'q1_normal': q1_normal,
            'q1_accuracy': round((q1_accurate + q1_normal) / len(q1_rows) * 100, 1) if q1_rows else 0,
        }

    def update_actual_values(self, record_id: int, user_id: int,
                            k1_actual: str = None, q1_actual: str = None,
                            method_actual: str = None) -> bool:
        """更新预测记录的真实值"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            updates = []
            params = []

            if k1_actual is not None:
                updates.append('k1_actual = ?')
                params.append(k1_actual)
            if q1_actual is not None:
                updates.append('q1_actual = ?')
                params.append(q1_actual)
            if method_actual is not None:
                updates.append('method_actual = ?')
                params.append(method_actual)

            updates.append('accuracy_checked = 1')
            # 使用北京时间
            beijing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            updates.append("checked_time = '" + beijing_time + "'")

            params.extend([record_id, user_id])

            cursor.execute(f'''
                UPDATE prediction_records
                SET {', '.join(updates)}
                WHERE id = ? AND user_id = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"❌ 更新真实值失败: {e}")
            return False
        finally:
            conn.close()

    def get_accuracy_records(self, user_id: int, limit: int = 50,
                            offset: int = 0, status: str = None,
                            keyword: str = None) -> tuple:
        """获取用于准确率对比的记录，支持关键字搜索（按预测时间倒序）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查新字段是否存在
        cursor.execute('PRAGMA table_info(prediction_records)')
        columns = [row[1] for row in cursor.fetchall()]
        has_accuracy = 'accuracy_checked' in columns
        has_k1_actual = 'k1_actual' in columns
        has_q1_actual = 'q1_actual' in columns
        has_method_actual = 'method_actual' in columns

        conditions = ['user_id = ?']
        params = [user_id]

        if has_accuracy and status == 'checked':
            conditions.append('accuracy_checked = 1')
        elif has_accuracy and status == 'unchecked':
            conditions.append('(accuracy_checked = 0 OR accuracy_checked IS NULL)')

        if keyword:
            conditions.append('project_name LIKE ?')
            params.append(f'%{keyword}%')

        where_clause = ' AND '.join(conditions)

        cursor.execute(f'SELECT COUNT(*) FROM prediction_records WHERE {where_clause}', params)
        total = cursor.fetchone()[0]

        cursor.execute(f'''
            SELECT * FROM prediction_records
            WHERE {where_clause}
            ORDER BY prediction_time DESC
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])

        records = cursor.fetchall()
        conn.close()

        predictions = []
        for row in records:
            # 安全获取新字段值
            k1_actual = row[18] if len(row) > 18 and has_k1_actual else None
            q1_actual = row[19] if len(row) > 19 and has_q1_actual else None
            method_actual = row[20] if len(row) > 20 and has_method_actual else None
            accuracy_checked = bool(row[21]) if len(row) > 21 and has_accuracy else False
            checked_time = row[22] if len(row) > 22 else None

            # 计算偏差
            k1_deviation = None
            k1_level = 'unchecked'
            if row[11] and k1_actual:
                try:
                    k1_deviation = abs(float(row[11]) - float(k1_actual))
                    if k1_deviation == 0:
                        k1_level = 'accurate'
                    elif k1_deviation <= 0.01:
                        k1_level = 'normal'
                    else:
                        k1_level = 'deviated'
                except (ValueError, TypeError):
                    pass

            q1_deviation = None
            q1_level = 'unchecked'
            if row[14] and q1_actual:
                try:
                    q1_deviation = abs(float(row[14]) - float(q1_actual))
                    if q1_deviation == 0:
                        q1_level = 'accurate'
                    elif q1_deviation <= 0.1:
                        q1_level = 'normal'
                    else:
                        q1_level = 'deviated'
                except (ValueError, TypeError):
                    pass

            method_correct = None
            if row[9] and method_actual:
                method_correct = (str(row[9]).strip() == str(method_actual).strip())

            predictions.append({
                'id': row[0],
                'user_id': row[1],
                'prediction_time': row[2],
                'project_name': row[3] or '',
                'location_filter': row[4],
                'method_filter': row[5],
                'data_count': row[8],
                'method_prediction': row[9],
                'method_confidence': row[10],
                'k1_prediction': row[11],
                'k1_confidence': row[12],
                'q1_prediction': row[14],
                'q1_confidence': row[15],
                'used_ai': bool(row[17]),
                'k1_actual': k1_actual,
                'q1_actual': q1_actual,
                'method_actual': method_actual,
                'accuracy_checked': accuracy_checked,
                'checked_time': checked_time,
                # 偏差信息
                'k1_deviation': k1_deviation,
                'k1_level': k1_level,
                'q1_deviation': q1_deviation,
                'q1_level': q1_level,
                'method_correct': method_correct,
            })

        return predictions, total