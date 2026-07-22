#!/bin/bash
# V6.0 重启脚本
# 用于重启工程开标参数预测系统 V6.0

echo "🔄 正在重启 V6.0 服务..."

# 设置工作目录
WORK_DIR="/root/.openclaw/workspace/v6"
cd $WORK_DIR

# 停止旧服务 - 多重保障
echo "⏹️  停止旧进程..."

# 步骤 1: 通过端口查找并终止（最可靠）
echo "🔍 检查端口 5001..."
PORT_PIDS=$(lsof -t -i:5001 2>/dev/null)
if [ -n "$PORT_PIDS" ]; then
    echo "📋 端口 5001 被占用，进程 ID: $PORT_PIDS"
    echo "⚡ 强制终止进程..."
    kill -9 $PORT_PIDS 2>/dev/null
    sleep 2
    
    # 再次检查
    PORT_PIDS2=$(lsof -t -i:5001 2>/dev/null)
    if [ -n "$PORT_PIDS2" ]; then
        echo "⚠️  进程仍在运行，再次强制终止..."
        kill -9 $PORT_PIDS2 2>/dev/null
        sleep 2
    fi
fi

# 步骤 2: 通过 PID 文件查找并终止
echo ""
echo "🔍 检查 PID 文件..."
if [ -f "$WORK_DIR/bid-v6.pid" ]; then
    V6_PID=$(cat $WORK_DIR/bid-v6.pid)
    if [ -n "$V6_PID" ]; then
        echo "📋 PID 文件中的进程 ID: $V6_PID"
        kill -9 $V6_PID 2>/dev/null
        sleep 2
        echo "✅ 已清理 PID 文件"
        rm -f $WORK_DIR/bid-v6.pid
    fi
fi

# 步骤 3: 通过进程名查找并终止
echo ""
echo "🔍 检查 bid_parameter 进程..."
V6_PIDS=$(ps aux | grep "[b]id_parameter_predictor.py" | grep -v grep | awk '{print $2}')
if [ -n "$V6_PIDS" ]; then
    echo "📋 找到 V6.0 进程：$V6_PIDS"
    echo "⚡ 强制终止..."
    kill -9 $V6_PIDS 2>/dev/null
    sleep 2
fi

# 步骤 4: 检查模块化服务进程
echo ""
echo "🔍 检查模块化服务进程..."
MODULAR_PIDS=$(ps aux | grep "[s]tart-modular.py" | grep -v grep | awk '{print $2}')
if [ -n "$MODULAR_PIDS" ]; then
    echo "📋 找到模块化服务进程：$MODULAR_PIDS"
    echo "⚡ 强制终止..."
    kill -9 $MODULAR_PIDS 2>/dev/null
    sleep 2
fi

# 步骤 5: 使用 fuser 释放端口（如果可用）
if command -v fuser > /dev/null 2>&1; then
    echo ""
    echo "🔧 使用 fuser 检查端口 5001..."
    FUSER_PIDS=$(fuser 5001/tcp 2>/dev/null)
    if [ -n "$FUSER_PIDS" ]; then
        echo "📋 fuser 找到进程：$FUSER_PIDS"
        fuser -k 5001/tcp 2>/dev/null
        sleep 2
    fi
fi

# 步骤 6: 等待并验证
echo ""
echo "⏳ 等待端口释放..."
sleep 3

# 最终验证
FINAL_CHECK=$(lsof -i:5001 2>/dev/null | wc -l)
if [ "$FINAL_CHECK" -gt 0 ]; then
    echo "⚠️  端口 5001 仍被占用，等待 5 秒..."
    sleep 5
    FINAL_CHECK=$(lsof -i:5001 2>/dev/null | wc -l)
fi

if [ "$FINAL_CHECK" -gt 0 ]; then
    echo "❌ 无法释放端口 5001，请手动检查:"
    lsof -i:5001 2>/dev/null
    exit 1
fi

echo "✅ 端口 5001 已释放"

# 启动新服务 - 智能检测架构
echo ""
echo "🚀 检测服务架构并启动..."

# 清理旧的日志文件（迁移到 log/ 目录）
mkdir -p $WORK_DIR/log
if [ -f "$WORK_DIR/bid-v6.log" ]; then
    mv $WORK_DIR/bid-v6.log $WORK_DIR/log/bid-v6.log.old.$(date +%Y%m%d_%H%M%S)
fi
# 清理根目录下的旧日志文件
for f in $WORK_DIR/bid-v6.log.20*; do
    [ -f "$f" ] && mv "$f" "$WORK_DIR/log/"
done

# 检查是否使用模块化架构
if [ -f "$WORK_DIR/app.py" ]; then
    echo "🏗️  检测到 V6.0 模块化架构，启动服务..."
    START_CMD="app.py"
    SERVICE_TYPE="V6.0 模块化"
else
    echo "❌ 未找到 app.py，无法启动服务"
    exit 1
fi

# 启动服务（使用 Python 3.11 虚拟环境）
if [ -f "$WORK_DIR/.venv311/bin/python" ]; then
    PYTHON_CMD="$WORK_DIR/.venv311/bin/python"
else
    PYTHON_CMD="python3"
fi
nohup $PYTHON_CMD $START_CMD >> $WORK_DIR/log/bid-v6.log 2>&1 &
V6_PID=$!
echo $V6_PID > bid-v6.pid
echo "📝 $SERVICE_TYPE架构 - 进程 PID: $V6_PID"

# 等待启动（逐步检查）
echo "⏳ 等待服务启动..."
SUCCESS=false
for i in {1..20}; do
    sleep 1
    
    # 检查 1: 进程是否存在
    if ! ps -p $V6_PID > /dev/null 2>&1; then
        echo "❌ 进程已退出"
        break
    fi
    
    # 检查 2: 端口是否监听（使用多种方法）
    PORT_CHECK1=$(lsof -i:5001 2>/dev/null | wc -l)
    PORT_CHECK2=$(netstat -tlnp 2>/dev/null | grep ":5001" | wc -l)
    
    if [ "$PORT_CHECK1" -gt 0 ] || [ "$PORT_CHECK2" -gt 0 ]; then
        echo "✅ 端口 5001 已监听 (第 $i 秒)"
        SUCCESS=true
        break
    fi
    
    echo "  等待中... ($i/20)"
done

# 最终检查
echo ""
echo "🔍 验证服务状态..."

if [ "$SUCCESS" = false ]; then
    echo "❌ V6.0 启动失败！"
    echo ""
    echo "错误日志:"
    tail -30 $WORK_DIR/bid-v6.log
    exit 1
fi

# 检查 HTTP 响应（可选）
HTTP_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001 2>/dev/null)
if [ "$HTTP_CHECK" = "200" ]; then
    echo "✅ HTTP 检查通过"
elif [ "$HTTP_CHECK" = "000" ]; then
    echo "⚠️  HTTP 检查超时，但服务可能正在启动"
else
    echo "⚠️  HTTP 状态：$HTTP_CHECK"
fi

echo ""
echo "========================================"
echo "✅ V6.0 已成功重启！($SERVICE_TYPE架构)"
echo "========================================"
echo ""
echo "📊 服务信息:"
echo "  ✅ 架构类型: $SERVICE_TYPE"
echo "  ✅ 进程 PID: $V6_PID"
echo "  ✅ 端口：5001"
echo "  ✅ 访问地址：http://localhost:5001"
echo ""
echo "📝 日志目录：$WORK_DIR/log/"
echo "📝 当前日志：$WORK_DIR/log/bid-v6.log"
echo ""
echo "📋 最近日志:"
echo "----------------------------------------"
tail -10 $WORK_DIR/log/bid-v6.log 2>/dev/null || echo "(日志文件为空，服务正在初始化)"
echo "----------------------------------------"
echo ""
echo "🗂️  运行日志管理..."
bash $WORK_DIR/manage-logs.sh
echo ""
echo "💡 提示：使用 'tail -f $WORK_DIR/log/bid-v6.log' 查看实时日志"