#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6 系统每日自动备份脚本
由 cron 定时任务调用，每天 03:00 执行
"""

import sys
import os

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.services.backup_service import BackupService
from datetime import datetime

def main():
    log_dir = os.path.join(PROJECT_ROOT, 'log')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'backup-cron.log')

    service = BackupService()
    result = service.create_backup('auto')

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if result['success']:
        msg = f"[{timestamp}] 自动备份成功: {result['filename']} ({BackupService._format_size(result['size'])})"
        if result.get('auto_cleaned', 0) > 0:
            msg += f" (已清理 {result['auto_cleaned']} 个旧备份)"
        print(msg)
    else:
        msg = f"[{timestamp}] 自动备份失败: {result.get('error', '未知错误')}"
        print(msg)

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

if __name__ == '__main__':
    main()
