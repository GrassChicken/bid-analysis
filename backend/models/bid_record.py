#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开标记录数据模型
处理开标记录的数据库操作
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any


class BidRecord:
    """开标记录模型"""
    
    def __init__(self, db_path: str = "bid_database.db"):
        """初始化模型"""
        self.db_path = db_path
        self.init_table()
    
    def init_table(self):
        """初始化数据表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建开标记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bid_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_name TEXT NOT NULL,
                bid_date TEXT,
                bid_time TEXT,
                bid_location TEXT,
                method_category TEXT,
                k2_value TEXT,
                k1_value TEXT,
                q1_value TEXT,
                import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, project_name),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bid_records_user ON bid_records(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bid_records_date ON bid_records(bid_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bid_records_location ON bid_records(bid_location)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bid_records_method ON bid_records(method_category)')
        
        # 清理重复数据（保留每组中 id 最大的记录）
        cursor.execute('''
            DELETE FROM bid_records
            WHERE id NOT IN (
                SELECT MAX(id) FROM bid_records
                GROUP BY user_id, project_name
            )
        ''')
        
        # 创建唯一索引（清理重复后才能成功）
        try:
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_bid_records_user_project ON bid_records(user_id, project_name)')
        except sqlite3.Error as e:
            print(f"⚠️ 创建唯一索引失败（可能仍有重复数据）: {e}")
        
        conn.commit()
        conn.close()
    
    def create_record(self, user_id: int, record_data: Dict[str, Any]) -> bool:
        """创建开标记录（使用北京时间）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 使用北京时间
        beijing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT INTO bid_records 
                (user_id, project_name, bid_date, bid_time, bid_location, 
                 method_category, k2_value, k1_value, q1_value, import_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                record_data.get('project_name'),
                record_data.get('bid_date'),
                record_data.get('bid_time'),
                record_data.get('bid_location'),
                record_data.get('method_category'),
                record_data.get('k2_value'),
                record_data.get('k1_value'),
                record_data.get('q1_value'),
                beijing_time
            ))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"❌ 创建开标记录失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_records(self, user_id: int, filters: Dict[str, Any] = None, 
                   limit: int = 50, offset: int = 0) -> tuple:
        """获取开标记录（支持过滤和分页）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询
        query = 'SELECT * FROM bid_records WHERE user_id = ?'
        params = [user_id]
        
        if filters:
            if filters.get('location'):
                query += ' AND bid_location LIKE ?'
                params.append(f"%{filters['location']}%")
            if filters.get('method'):
                query += ' AND method_category = ?'
                params.append(filters['method'])
            if filters.get('datetime_from'):
                # 支持日期+时间精确过滤
                dt_val = filters['datetime_from']
                if ' ' in dt_val:
                    query += " AND (bid_date || ' ' || COALESCE(bid_time, '00:00')) >= ?"
                else:
                    query += ' AND bid_date >= ?'
                params.append(dt_val)
            elif filters.get('date_from'):
                query += ' AND bid_date >= ?'
                params.append(filters['date_from'])
            if filters.get('datetime_to'):
                # 支持日期+时间精确过滤
                dt_val = filters['datetime_to']
                if ' ' in dt_val:
                    query += " AND (bid_date || ' ' || COALESCE(bid_time, '00:00')) <= ?"
                else:
                    query += ' AND bid_date <= ?'
                params.append(dt_val)
            elif filters.get('date_to'):
                query += ' AND bid_date <= ?'
                params.append(filters['date_to'])
        
        query += ' ORDER BY bid_date DESC, bid_time DESC , project_name DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        # 获取总数
        count_query = query.replace('*', 'COUNT(*)', 1)
        # Remove ORDER BY and LIMIT for count
        count_query = count_query.split('ORDER BY')[0]
        count_params = list(params)
        # Remove LIMIT and OFFSET params (last two)
        count_params = count_params[:-2]
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return records, total
    
    def get_record_by_id(self, record_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bid_records 
            WHERE id = ? AND user_id = ?
        ''', (record_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'project_name': row[2],
                'bid_date': row[3],
                'bid_time': row[4],
                'bid_location': row[5],
                'method_category': row[6],
                'k2_value': row[7],
                'k1_value': row[8],
                'q1_value': row[9],
                'import_time': row[10]
            }
        return None
    
    def update_record(self, record_id: int, user_id: int, 
                     update_data: Dict[str, Any]) -> bool:
        """更新记录（使用北京时间）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建更新语句
        fields = []
        params = []
        for key, value in update_data.items():
            if key in ['project_name', 'bid_date', 'bid_time', 'bid_location', 
                      'method_category', 'k2_value', 'k1_value', 'q1_value']:
                fields.append(f"{key} = ?")
                params.append(value)
        
        if not fields:
            return False
        
        # 同时刷新 import_time 为北京时间
        beijing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields.append("import_time = ?")
        params.append(beijing_time)
            
        query = f"UPDATE bid_records SET {','.join(fields)} WHERE id = ? AND user_id = ?"
        params.extend([record_id, user_id])
        
        cursor.execute(query, params)
        updated = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return updated
    
    def delete_record(self, record_id: int, user_id: int) -> bool:
        """删除记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM bid_records 
            WHERE id = ? AND user_id = ?
        ''', (record_id, user_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def bulk_delete(self, record_ids: List[int], user_id: int) -> int:
        """批量删除记录"""
        if not record_ids:
            return 0
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(record_ids))
        cursor.execute(f'''
            DELETE FROM bid_records 
            WHERE id IN ({placeholders}) AND user_id = ?
        ''', record_ids + [user_id])
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count
    
    def clear_all(self, user_id: int) -> int:
        """清空用户的所有记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM bid_records WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        return deleted_count
    
    def get_statistics(self, user_id: int) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) FROM bid_records WHERE user_id = ?', (user_id,))
        total_count = cursor.fetchone()[0]
        
        # 今日新增（北京时间，已直接存储）
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM bid_records 
            WHERE user_id = ? AND DATE(import_time) = ?
        ''', (user_id, today))
        today_count = cursor.fetchone()[0]
        
        # 方法类别分布
        cursor.execute('''
            SELECT method_category, COUNT(*) 
            FROM bid_records 
            WHERE user_id = ? AND method_category IS NOT NULL
            GROUP BY method_category
        ''', (user_id,))
        method_distribution = dict(cursor.fetchall())
        
        # K1 值分布
        cursor.execute('''
            SELECT k1_value, COUNT(*) 
            FROM bid_records 
            WHERE user_id = ? AND k1_value IS NOT NULL
            GROUP BY k1_value
            ORDER BY k1_value
        ''', (user_id,))
        k1_distribution = dict(cursor.fetchall())
        
        # Q1 值分布（排除空值和空字符串）
        cursor.execute('''
            SELECT q1_value, COUNT(*) 
            FROM bid_records 
            WHERE user_id = ? AND q1_value IS NOT NULL AND q1_value != ''
            GROUP BY q1_value
            ORDER BY q1_value
        ''', (user_id,))
        q1_distribution = dict(cursor.fetchall())
        
        # 开标地点分布（TOP 8）
        cursor.execute('''
            SELECT bid_location, COUNT(*) as cnt
            FROM bid_records 
            WHERE user_id = ? AND bid_location IS NOT NULL
            GROUP BY bid_location
            ORDER BY cnt DESC
            LIMIT 8
        ''', (user_id,))
        location_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_count': total_count,
            'today_count': today_count,
            'method_distribution': method_distribution,
            'k1_distribution': k1_distribution,
            'q1_distribution': q1_distribution,
            'location_distribution': location_distribution
        }
