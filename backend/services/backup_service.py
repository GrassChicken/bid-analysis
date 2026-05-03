#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据备份与恢复服务
支持手动备份、自动备份、备份恢复、备份删除
"""

import os
import tarfile
import shutil
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from backend.config.config import Config


class BackupService:
    """数据备份与恢复服务"""

    def __init__(self):
        self.backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'backups')
        self.db_path = Config.DATABASE_PATH
        self.uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

    def create_backup(self, backup_type: str = 'manual') -> Dict:
        """创建备份
        Args:
            backup_type: 'manual'(手动), 'auto'(自动), 'pre_restore'(恢复前)
        Returns:
            备份结果 {'success': bool, 'filename': str, 'size': int, 'error': str}
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'backup_{timestamp}_{backup_type}.tar.gz'
            filepath = os.path.join(self.backup_dir, filename)

            # 临时工作目录
            temp_dir = os.path.join(self.backup_dir, f'_temp_{timestamp}')
            os.makedirs(temp_dir, exist_ok=True)

            # 1. 备份数据库（直接复制文件）
            temp_db = os.path.join(temp_dir, 'database.db')
            try:
                # 先执行 VACUUM 确保数据一致性
                conn = sqlite3.connect(self.db_path)
                conn.execute('VACUUM')
                conn.close()
                # 复制数据库文件
                shutil.copy2(self.db_path, temp_db)
            except Exception as e:
                shutil.rmtree(temp_dir)
                return {'success': False, 'error': f'数据库备份失败: {str(e)}'}

            # 2. 备份上传文件（如果有）
            if os.path.exists(self.uploads_dir) and os.listdir(self.uploads_dir):
                temp_uploads = os.path.join(temp_dir, 'uploads')
                shutil.copytree(self.uploads_dir, temp_uploads)

            # 3. 写入备份信息
            backup_info = {
                'type': backup_type,
                'timestamp': timestamp,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'db_path': self.db_path,
                'version': 'V6.0'
            }
            import json
            with open(os.path.join(temp_dir, 'backup_info.json'), 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)

            # 4. 压缩为 tar.gz
            with tarfile.open(filepath, 'w:gz') as tar:
                tar.add(temp_dir, arcname='backup')

            # 清理临时目录
            shutil.rmtree(temp_dir)

            # 获取文件大小
            file_size = os.path.getsize(filepath)

            # 自动清理旧备份，保持总数不超过 MAX_BACKUP_COUNT
            MAX_BACKUP_COUNT = 15
            clean_result = self.cleanup_old_backups(keep_count=MAX_BACKUP_COUNT)
            auto_cleaned = clean_result.get('deleted', 0)

            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'size': file_size,
                'type': backup_type,
                'timestamp': timestamp,
                'auto_cleaned': auto_cleaned  # 自动清理的旧备份数量
            }

        except Exception as e:
            return {'success': False, 'error': f'创建备份失败: {str(e)}'}

    def list_backups(self) -> List[Dict]:
        """获取备份列表"""
        backups = []
        if not os.path.exists(self.backup_dir):
            return backups

        for filename in sorted(os.listdir(self.backup_dir), reverse=True):
            if not filename.endswith('.tar.gz'):
                continue
            filepath = os.path.join(self.backup_dir, filename)
            stat = os.stat(filepath)

            # 解析备份类型
            parts = filename.replace('.tar.gz', '').split('_')
            backup_type = parts[-1] if len(parts) >= 4 else 'unknown'
            timestamp_str = '_'.join(parts[1:-1]) if len(parts) >= 4 else 'unknown'

            # 尝试读取备份信息
            backup_info = self._read_backup_info(filepath)

            backups.append({
                'filename': filename,
                'filepath': filepath,
                'size': stat.st_size,
                'size_display': self._format_size(stat.st_size),
                'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'type': backup_type,
                'timestamp': timestamp_str,
                'version': backup_info.get('version', 'V6.0') if backup_info else 'V6.0'
            })

        return backups

    def restore_backup(self, filename: str) -> Dict:
        """恢复备份
        Args:
            filename: 备份文件名
        Returns:
            恢复结果
        """
        filepath = os.path.join(self.backup_dir, filename)

        if not os.path.exists(filepath):
            return {'success': False, 'error': '备份文件不存在'}

        # 1. 恢复前先自动备份当前状态
        pre_backup = self.create_backup('pre_restore')
        if not pre_backup['success']:
            return {'success': False, 'error': f'恢复前自动备份失败: {pre_backup["error"]}'}

        # 2. 解压备份文件到临时目录
        temp_dir = os.path.join(self.backup_dir, '_restore_temp')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            with tarfile.open(filepath, 'r:gz') as tar:
                tar.extractall(temp_dir)

            # 3. 验证备份内容
            backup_dir_content = os.path.join(temp_dir, 'backup')
            temp_db = os.path.join(backup_dir_content, 'database.db')

            if not os.path.exists(temp_db):
                shutil.rmtree(temp_dir)
                return {'success': False, 'error': '备份文件损坏，缺少数据库'}

            # 4. 验证数据库完整性
            try:
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()
                if result[0] != 'ok':
                    shutil.rmtree(temp_dir)
                    return {'success': False, 'error': f'备份数据库损坏: {result[0]}'}
            except Exception as e:
                shutil.rmtree(temp_dir)
                return {'success': False, 'error': f'数据库验证失败: {str(e)}'}

            # 5. 替换数据库（先备份原文件，再替换）
            backup_old_db = self.db_path + '.bak_restore'
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, backup_old_db)
            shutil.copy2(temp_db, self.db_path)

            # 6. 恢复上传文件（如果有）
            temp_uploads = os.path.join(backup_dir_content, 'uploads')
            if os.path.exists(temp_uploads):
                if os.path.exists(self.uploads_dir):
                    shutil.rmtree(self.uploads_dir)
                shutil.copytree(temp_uploads, self.uploads_dir)

            # 清理
            shutil.rmtree(temp_dir)
            # 清理旧备份（保留7天）
            if os.path.exists(backup_old_db):
                os.remove(backup_old_db)

            return {
                'success': True,
                'message': '恢复成功',
                'pre_backup': pre_backup.get('filename')
            }

        except Exception as e:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return {'success': False, 'error': f'恢复失败: {str(e)}'}

    def delete_backup(self, filename: str) -> Dict:
        """删除备份"""
        filepath = os.path.join(self.backup_dir, filename)

        if not os.path.exists(filepath):
            return {'success': False, 'error': '备份文件不存在'}

        # 不能删除 pre_restore 类型的备份（它是恢复前的安全保障）
        if 'pre_restore' in filename:
            return {'success': False, 'error': '不能删除恢复前自动备份'}

        try:
            os.remove(filepath)
            return {'success': True, 'message': '删除成功'}
        except Exception as e:
            return {'success': False, 'error': f'删除失败: {str(e)}'}

    def download_backup(self, filename: str) -> Optional[str]:
        """获取备份文件路径用于下载"""
        filepath = os.path.join(self.backup_dir, filename)
        if not os.path.exists(filepath):
            return None
        return filepath

    def cleanup_old_backups(self, keep_days: int = 7, keep_count: int = 10) -> Dict:
        """清理旧备份
        Args:
            keep_days: 保留天数
            keep_count: 最少保留数量
        Returns:
            清理结果
        """
        backups = self.list_backups()
        deleted = 0
        errors = 0

        # 按时间排序，保留最新的 keep_count 个
        if len(backups) <= keep_count:
            return {'success': True, 'deleted': 0, 'message': '备份数量未超过限制'}

        to_delete = backups[keep_count:]

        for backup in to_delete:
            if 'pre_restore' in backup['filename']:
                continue  # 跳过恢复前备份
            try:
                os.remove(backup['filepath'])
                deleted += 1
            except Exception:
                errors += 1

        return {
            'success': True,
            'deleted': deleted,
            'errors': errors,
            'message': f'清理完成，删除 {deleted} 个旧备份'
        }

    def _read_backup_info(self, filepath: str) -> Optional[Dict]:
        """读取备份中的信息文件"""
        try:
            import json
            with tarfile.open(filepath, 'r:gz') as tar:
                info_member = tar.extractfile('backup/backup_info.json')
                if info_member:
                    return json.loads(info_member.read().decode('utf-8'))
        except Exception:
            pass
        return None

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f'{size_bytes} B'
        elif size_bytes < 1024 * 1024:
            return f'{size_bytes / 1024:.1f} KB'
        elif size_bytes < 1024 * 1024 * 1024:
            return f'{size_bytes / (1024 * 1024):.1f} MB'
        else:
            return f'{size_bytes / (1024 * 1024 * 1024):.1f} GB'
