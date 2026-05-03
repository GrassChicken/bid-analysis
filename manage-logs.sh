#!/bin/bash
# V6.0 日志管理脚本
# 功能：
# 1. 将轮转日志（bid-v6.log.1 到 bid-v6.log.5）打包成 zip
# 2. 清理超过 20 个的压缩包（保留最新的）
# 3. 清理超过 7 天的压缩包
# 4. 清理旧日志文件（非标准格式的）

set -e

# 切换到 V6 目录
cd "$(dirname "$0")"

LOG_DIR="log"
ARCHIVE_DIR="$LOG_DIR/archive"
LOG_PATTERN="bid-v6.log.*"
ARCHIVE_PREFIX="bid-v6-logs"
MAX_ARCHIVES=20
MAX_AGE_DAYS=7

# 创建归档目录
mkdir -p "$ARCHIVE_DIR"

echo "=========================================="
echo "🗂️  V6.0 日志管理 - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# ------------------------------------------
# 1. 清理旧的非标准格式日志文件（带时间戳的）
# ------------------------------------------
echo ""
echo "📋 清理旧格式日志文件..."
OLD_COUNT=0
for f in $LOG_DIR/bid-v6.log.20*; do
    [ -f "$f" ] && rm -v "$f" && OLD_COUNT=$((OLD_COUNT + 1))
done
echo "   已清理 $OLD_COUNT 个旧格式日志文件"

# ------------------------------------------
# 2. 打包轮转日志（RotatingFileHandler 格式：bid-v6.log.1 到 bid-v6.log.5）
# ------------------------------------------
echo ""
echo "📦 检查轮转日志..."
# 只匹配数字后缀的轮转文件（bid-v6.log.1, bid-v6.log.2 等）
ROTATE_COUNT=$(ls -1 "$LOG_DIR"/bid-v6.log.[1-5] 2>/dev/null | wc -l)

if [ "$ROTATE_COUNT" -gt 0 ]; then
    # 生成带时间戳的压缩包名称
    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    ARCHIVE_NAME="${ARCHIVE_PREFIX}-${TIMESTAMP}.zip"
    ARCHIVE_PATH="$ARCHIVE_DIR/$ARCHIVE_NAME"
    
    echo "   发现 $ROTATE_COUNT 个轮转文件，开始打包..."
    
    # 打包（只打包轮转文件，不打包当前日志）
    cd "$LOG_DIR"
    zip -q "$ARCHIVE_PATH" bid-v6.log.[1-5]
    cd ..
    
    # 打包成功后删除轮转文件
    if [ -f "$ARCHIVE_PATH" ]; then
        ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
        echo "   ✅ 已打包: $ARCHIVE_NAME ($ARCHIVE_SIZE)"
        rm -f "$LOG_DIR"/bid-v6.log.[1-5]
    else
        echo "   ❌ 打包失败"
    fi
else
    echo "   无轮转文件，跳过打包"
fi

# ------------------------------------------
# 3. 清理策略 A: 超过 20 个压缩包时删除最早的
# ------------------------------------------
echo ""
echo "🗑️  清理策略 A: 限制压缩包数量（最大 $MAX_ARCHIVES 个）..."
ARCHIVE_COUNT=$(ls -1 "$ARCHIVE_DIR"/${ARCHIVE_PREFIX}-*.zip 2>/dev/null | wc -l)

if [ "$ARCHIVE_COUNT" -gt "$MAX_ARCHIVES" ]; then
    DELETE_COUNT=$((ARCHIVE_COUNT - MAX_ARCHIVES))
    echo "   当前 $ARCHIVE_COUNT 个，需删除 $DELETE_COUNT 个最早的..."
    ls -1t "$ARCHIVE_DIR"/${ARCHIVE_PREFIX}-*.zip | tail -n "$DELETE_COUNT" | while read f; do
        rm -v "$f"
    done
    echo "   ✅ 已清理 $DELETE_COUNT 个压缩包"
else
    echo "   当前 $ARCHIVE_COUNT 个，未超限"
fi

# ------------------------------------------
# 4. 清理策略 B: 超过 7 天的压缩包
# ------------------------------------------
echo ""
echo "🗑️  清理策略 B: 清理超过 $MAX_AGE_DAYS 天的压缩包..."
OLD_FILES=$(find "$ARCHIVE_DIR" -name "${ARCHIVE_PREFIX}-*.zip" -mtime +$MAX_AGE_DAYS 2>/dev/null)
if [ -n "$OLD_FILES" ]; then
    echo "$OLD_FILES" | while read f; do
        rm -v "$f"
    done
    echo "   ✅ 已清理过期压缩包"
else
    echo "   无过期压缩包"
fi

# ------------------------------------------
# 5. 统计当前状态
# ------------------------------------------
echo ""
echo "📊 当前状态:"
echo "   当前日志大小: $(du -h "$LOG_DIR/bid-v6.log" 2>/dev/null | cut -f1 || echo '0')"
echo "   轮转文件数:  $(ls -1 "$LOG_DIR"/bid-v6.log.[1-5] 2>/dev/null | wc -l)"
echo "   压缩包数量:  $(ls -1 "$ARCHIVE_DIR"/${ARCHIVE_PREFIX}-*.zip 2>/dev/null | wc -l)"
echo "   压缩包总大小: $(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1 || echo '0')"

echo ""
echo "=========================================="
echo "✅ 日志管理完成"
echo "=========================================="
