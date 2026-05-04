#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据模型
定义用户相关的数据结构和数据库操作
"""

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

class User:
    """用户模型类"""
    
    def __init__(self, db_path=None):
        """初始化用户模型"""
        from backend.config.config import Config
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_table()
    
    def init_table(self):
        """初始化用户表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                last_login TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        
        # 数据库迁移：为旧表添加 is_active 字段（如果不存在）
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1')
        except sqlite3.OperationalError:
            pass  # 字段已存在，跳过
        
        # 创建默认管理员账户
        admin_password_hash = generate_password_hash('admin123')
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, phone, email, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin', admin_password_hash, '13800138000', 'admin@bid-v6.com', 1))
        except sqlite3.IntegrityError:
            # 管理员已存在
            pass
        
        conn.commit()
        conn.close()
    
    def authenticate(self, username, password):
        """用户认证
        Returns:
            dict: 用户信息（登录成功）
            None: 用户名不存在或密码错误
            'DISABLED': 用户已禁用
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password_hash, phone, email, is_admin, created_at, is_active
            FROM users WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            # 用户不存在
            return None
        
        # 用户名存在，检查密码
        if not check_password_hash(user[2], password):
            return None
        
        # 密码正确，检查是否被禁用
        is_active = bool(user[7]) if user[7] is not None else True
        if not is_active:
            return 'DISABLED'
        
        # 更新最后登录时间
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
        conn.commit()
        conn.close()
        
        return {
            'id': user[0],
            'username': user[1],
            'phone': user[3],
            'email': user[4],
            'is_admin': bool(user[5]),
            'created_at': user[6]
        }
    
    def create_user(self, username, password, phone='', email=''):
        """创建新用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, phone, email)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, phone, email))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # 用户名已存在
            return False
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, phone, email, created_at, is_admin
            FROM users WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'username': row[1],
                'phone': row[2],
                'email': row[3],
                'created_at': row[4],
                'is_admin': bool(row[5])
            }
        return None
    
    def get_all_users(self, limit=50, offset=0):
        """获取所有用户（分页）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取总数
        cursor.execute('SELECT COUNT(*) FROM users')
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        cursor.execute('''
            SELECT id, username, phone, email, created_at, is_admin, is_active, last_login
            FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'username': row[1],
                'phone': row[2],
                'email': row[3],
                'created_at': row[4],
                'is_admin': bool(row[5]),
                'is_active': bool(row[6]) if row[6] is not None else True,
                'last_login': row[7]
            })
        
        return users, total
    
    def update_password(self, user_id, new_password):
        """更新用户密码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = generate_password_hash(new_password)
        cursor.execute('''
            UPDATE users SET password_hash = ? WHERE id = ?
        ''', (password_hash, user_id))
        
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return changed
    
    def delete_user(self, user_id):
        """删除用户（管理员）"""
        if user_id == 1:  # 不允许删除默认管理员
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted
    
    def toggle_user_status(self, user_id, active):
        """启用/禁用用户"""
        if user_id == 1:  # 不允许禁用管理员
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if active else 0, user_id))
        changed = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return changed
    
    def update_user_info(self, user_id, phone='', email='', is_admin=None):
        """更新用户信息（管理员操作）"""
        if user_id == 1:  # 不允许修改管理员基本信息
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        fields = []
        params = []
        
        if phone:
            fields.append('phone = ?')
            params.append(phone)
        if email:
            fields.append('email = ?')
            params.append(email)
        if is_admin is not None:
            fields.append('is_admin = ?')
            params.append(1 if is_admin else 0)
        
        if not fields:
            conn.close()
            return False
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, params)
        changed = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return changed
    
    def get_user_by_username(self, username):
        """根据用户名获取用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password_hash, phone, email, created_at, is_admin, is_active, last_login
            FROM users WHERE username = ?
        ''', (username,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'username': row[1],
                'password_hash': row[2],
                'phone': row[3],
                'email': row[4],
                'created_at': row[5],
                'is_admin': bool(row[6]),
                'is_active': bool(row[7]) if row[7] is not None else True,
                'last_login': row[8]
            }
        return None