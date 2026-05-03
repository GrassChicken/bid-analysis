#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库工具类
提供数据库连接和通用操作方法
"""

import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str):
        """初始化数据库管理器"""
        self.db_path = db_path
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 启用字典式访问
        return conn
    
    @contextmanager
    def get_db(self):
        """数据库连接上下文管理器"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, 
                     fetch_all: bool = True) -> Any:
        """执行查询"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """执行批量操作"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            return cursor.fetchone() is not None
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            return [{
                'cid': col['cid'],
                'name': col['name'],
                'type': col['type'],
                'notnull': bool(col['notnull']),
                'dflt_value': col['dflt_value'],
                'pk': bool(col['pk'])
            } for col in columns]
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(backup_path)
            
            source_conn.backup(backup_conn)
            
            backup_conn.close()
            source_conn.close()
            return True
        except Exception as e:
            print(f"备份数据库失败: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """恢复数据库"""
        try:
            backup_conn = sqlite3.connect(backup_path)
            source_conn = sqlite3.connect(self.db_path)
            
            backup_conn.backup(source_conn)
            
            source_conn.close()
            backup_conn.close()
            return True
        except Exception as e:
            print(f"恢复数据库失败: {e}")
            return False