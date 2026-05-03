#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户业务服务层
处理用户相关的业务逻辑
"""

from backend.models.user import User
from backend.utils.database import DatabaseManager
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict, Optional, Any


class UserService:
    """用户服务类"""
    
    def __init__(self, db_path: str = "bid_database.db"):
        """初始化服务"""
        self.db_path = db_path
        self.user_model = User(db_path)
        self.db_manager = DatabaseManager(db_path)
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证
        Returns:
            dict: 用户信息（登录成功）
            None: 用户名不存在或密码错误
            'DISABLED': 用户已禁用
        """
        user = self.user_model.get_user_by_username(username)
        if not user:
            return None
        if not check_password_hash(user['password_hash'], password):
            return None
        # 检查是否被禁用
        is_active = user.get('is_active', True)
        if not is_active:
            return 'DISABLED'
        return {
            'id': user['id'],
            'username': user['username'],
            'phone': user.get('phone'),
            'email': user.get('email'),
            'is_admin': user.get('is_admin', False),
            'created_at': user.get('created_at')
        }
    
    def create_user(self, username: str, password: str, 
                   phone: str = '', email: str = '') -> bool:
        """创建新用户"""
        password_hash = generate_password_hash(password)
        return self.user_model.create_user(username, password_hash, phone, email)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户信息"""
        return self.user_model.get_user_by_id(user_id)
    
    def get_all_users(self, limit: int = 50, offset: int = 0) -> tuple:
        """获取所有用户（分页）"""
        return self.user_model.get_all_users(limit, offset)
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """更新用户密码"""
        password_hash = generate_password_hash(new_password)
        return self.user_model.update_password(user_id, password_hash)
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户（管理员）"""
        return self.user_model.delete_user(user_id)
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.user_model.get_user_by_id(user_id)
        if user and check_password_hash(user['password_hash'], old_password):
            new_hash = generate_password_hash(new_password)
            return self.user_model.update_password(user_id, new_hash)
        return False