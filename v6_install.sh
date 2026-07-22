#!/bin/bash
# ============================================================
# V6.0 一键安装脚本
# 功能：检查 Python 3.11 → 创建虚拟环境 → 安装依赖
# 用法：bash v6_install.sh
# ============================================================

set -e

WORK_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$WORK_DIR/.venv311"
PYTHON_MIN="3.11"
PYTHON_CMD=""

echo "=========================================="
echo "🚀 V6.0 系统安装脚本"
echo "=========================================="
echo ""

# ============================================================
# 步骤 1：检查系统是否已安装 Python 3.11+
# ============================================================
echo "🔍 [1/4] 检查 Python 版本..."

# 按优先级查找 python3.11+
for cmd in python3.11 python3.12 python3.13; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$("$cmd" -c 'import sys; print(sys.version_info.major)')
        minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)')
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON_CMD="$cmd"
            echo "   ✅ 找到 $cmd (Python $version)"
            break
        fi
    fi
done

# 如果没找到，尝试检查已有的虚拟环境
if [ -z "$PYTHON_CMD" ]; then
    if [ -x "$VENV_DIR/bin/python" ]; then
        venv_version=$("$VENV_DIR/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        venv_minor=$("$VENV_DIR/bin/python" -c 'import sys; print(sys.version_info.minor)')
        if [ "$venv_minor" -ge 11 ]; then
            echo "   ✅ 已有虚拟环境 Python $venv_version"
            echo ""
            echo "⚠️  未找到系统级 Python 3.11+，但虚拟环境可用。"
            echo "💡 如需重新创建虚拟环境，请先安装 Python 3.11+："
            echo ""
            echo "   # CentOS/RHEL/Alibaba Cloud Linux"
            echo "   dnf install -y python3.11 python3.11-devel"
            echo ""
            echo "   # Ubuntu/Debian"
            echo "   apt install -y python3.11 python3.11-venv"
            echo ""
            echo "🔄 跳过虚拟环境创建，直接安装依赖..."
            echo ""

            # 直接跳到安装依赖
            echo "📦 [4/4] 安装 Python 依赖..."
            "$VENV_DIR/bin/pip" install --upgrade pip -q
            "$VENV_DIR/bin/pip" install -r "$WORK_DIR/requirements.txt"
            echo ""
            echo "=========================================="
            echo "✅ V6.0 安装完成！"
            echo "=========================================="
            echo ""
            echo "📝 启动服务："
            echo "   bash $WORK_DIR/restart-v6.sh"
            exit 0
        fi
    fi

    echo "   ❌ 未找到 Python 3.11+"
    echo ""
    echo "📋 请先安装 Python 3.11："
    echo ""
    echo "   # CentOS/RHEL/Alibaba Cloud Linux"
    echo "   dnf install -y python3.11 python3.11-devel"
    echo ""
    echo "   # Ubuntu/Debian"
    echo "   apt install -y python3.11 python3.11-venv"
    echo ""
    echo "   # 源码编译（通用）"
    echo "   curl -O https://www.python.org/ftp/python/3.11.13/Python-3.11.13.tgz"
    echo "   tar xzf Python-3.11.13.tgz && cd Python-3.11.13"
    echo "   ./configure --prefix=/usr/local && make -j\$(nproc) && make install"
    echo ""
    exit 1
fi

# ============================================================
# 步骤 2：创建虚拟环境
# ============================================================
echo ""
echo "🔧 [2/4] 创建虚拟环境..."

if [ -d "$VENV_DIR" ]; then
    echo "   ⚠️  虚拟环境已存在：$VENV_DIR"
    read -p "   是否重新创建？(y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo "   🗑️  删除旧虚拟环境..."
        rm -rf "$VENV_DIR"
        "$PYTHON_CMD" -m venv "$VENV_DIR"
        echo "   ✅ 虚拟环境已重建"
    else
        echo "   ✅ 保留现有虚拟环境"
    fi
else
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "   ✅ 虚拟环境已创建：$VENV_DIR"
fi

# 升级 pip
echo ""
echo "📦 [3/4] 升级 pip..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
echo "   ✅ pip 已升级"

# ============================================================
# 步骤 3：安装依赖
# ============================================================
echo ""
echo "📦 [4/4] 安装 Python 依赖..."
"$VENV_DIR/bin/pip" install -r "$WORK_DIR/requirements.txt"

echo ""
echo "=========================================="
echo "✅ V6.0 安装完成！"
echo "=========================================="
echo ""
echo "📊 环境信息："
echo "   Python：$("$VENV_DIR/bin/python" --version)"
echo "   虚拟环境：$VENV_DIR"
echo "   依赖数量：$(wc -l < "$WORK_DIR/requirements.txt") 个包"
echo ""
echo "📝 启动服务："
echo "   bash $WORK_DIR/restart-v6.sh"
echo ""
