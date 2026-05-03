#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作日志模型
处理操作日志的数据库操作
"""

import sqlite3
import json
from datetime import datetime, timezone, timedelta
from backend.config.config import Config


class OperationLog:
    """操作日志模型类"""
    
    def __init__(self, db_path=None):
        """初始化操作日志模型"""
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_table()
    
    def init_table(self):
        """初始化操作日志表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                module TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                user_agent TEXT,
                status TEXT DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_user_id ON operation_logs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_action ON operation_logs(action)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_created_at ON operation_logs(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_module ON operation_logs(module)')
        
        conn.commit()
        conn.close()
    
    def log(self, user_id, username, action, module, table_name=None,
            record_id=None, old_value=None, new_value=None,
            ip_address=None, user_agent=None, status='success', error_message=None):
        """记录操作日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        old_value_json = json.dumps(old_value, ensure_ascii=False, default=str) if old_value else None
        new_value_json = json.dumps(new_value, ensure_ascii=False, default=str) if new_value else None
        
        beijing_tz = timezone(timedelta(hours=8))
        created_at = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT INTO operation_logs 
                (user_id, username, action, module, table_name, record_id, 
                 old_value, new_value, ip_address, user_agent, status, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, username, action, module, table_name, record_id,
                old_value_json, new_value_json, ip_address, user_agent, status, error_message, created_at
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 记录操作日志失败：{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_logs(self, page=1, page_size=20, username=None, action=None,
                 module=None, status=None, start_date=None, end_date=None, keyword=None):
        """查询操作日志"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if username:
            conditions.append('username = ?')
            params.append(username)
        if action:
            conditions.append('action = ?')
            params.append(action)
        if module:
            conditions.append('module = ?')
            params.append(module)
        if status:
            conditions.append('status = ?')
            params.append(status)
        if start_date:
            conditions.append('created_at >= ?')
            params.append(start_date)
        if end_date:
            conditions.append('created_at <= ?')
            params.append(end_date)
        if keyword:
            conditions.append('(username LIKE ? OR action LIKE ? OR module LIKE ?)')
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
        
        where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        
        cursor.execute(f'SELECT COUNT(*) FROM operation_logs{where_clause}', params)
        total = cursor.fetchone()[0]
        
        offset = (page - 1) * page_size
        query = f'''
            SELECT * FROM operation_logs{where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        '''
        cursor.execute(query, params + [page_size, offset])
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            log = dict(row)
            if log.get('old_value'):
                try: log['old_value'] = json.loads(log['old_value'])
                except: pass
            if log.get('new_value'):
                try: log['new_value'] = json.loads(log['new_value'])
                except: pass
            logs.append(log)
        
        conn.close()
        
        return {
            'logs': logs,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    
    def get_all_users(self):
        """获取所有操作过的用户名"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT username FROM operation_logs ORDER BY username')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_statistics(self, days=7):
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM operation_logs
            WHERE created_at >= datetime('now', ?)
        ''', (f'-{days} days',))
        total_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM operation_logs WHERE created_at >= datetime('now', ?)
            GROUP BY status
        ''', (f'-{days} days',))
        status_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT module, COUNT(*) as count
            FROM operation_logs WHERE created_at >= datetime('now', ?)
            GROUP BY module ORDER BY count DESC LIMIT 10
        ''', (f'-{days} days',))
        module_stats = [{'module': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT action, COUNT(*) as count
            FROM operation_logs WHERE created_at >= datetime('now', ?)
            GROUP BY action ORDER BY count DESC LIMIT 10
        ''', (f'-{days} days',))
        action_stats = [{'action': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_count': total_count,
            'success_count': status_stats.get('success', 0),
            'failure_count': status_stats.get('failure', 0),
            'module_stats': module_stats,
            'action_stats': action_stats
        }
    
    def delete_old_logs(self, days=90):
        """删除指定天数前的日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM operation_logs WHERE created_at < datetime("now", ?)', (f'-{days} days',))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count