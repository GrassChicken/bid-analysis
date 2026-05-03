#!/bin/bash
# V6.0 启动脚本
# 使用独立的 5006 端口，与 V5.0 完全隔离

echo "🚀 启动 V6.0 服务..."

# 设置工作目录
WORK_DIR="/root/.openclaw/workspace/v6"
cd $WORK_DIR

# 停止旧服务
echo "⏹️  停止旧进程..."
lsof -i:5006 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null

# 等待端口释放
sleep 2

# 启动服务
echo "🚀 启动 V6.0 服务 (端口 5006)..."
nohup python3 app.py > v6.log 2>&1 &
V6_PID=$!
echo $V6_PID > v6.pid

echo "✅ V6.0 服务已启动 (PID: $V6_PID)"
echo "🌐 访问地址: http://localhost:5006"
echo "📊 日志文件: $WORK_DIR/v6.log"

# 等待服务启动
sleep 5
if lsof -i:5006 >/dev/null 2>&1; then
    echo "✅ 服务正在运行"
else
    echo "❌ 服务启动失败，检查日志: tail -f v6.log"
fi