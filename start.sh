#!/bin/bash

# Creative AutoGPT 启动脚本
# 在一个窗口中同时启动后端和前端

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Creative AutoGPT 启动脚本"
echo "================================"
echo "项目目录: $PROJECT_DIR"
echo ""

# 激活虚拟环境
VENV_DIR="$PROJECT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    echo "🔧 激活虚拟环境..."
    source "$VENV_DIR/bin/activate"
    echo "  ✅ 虚拟环境已激活"
else
    echo "⚠️  未找到虚拟环境 venv/，跳过激活"
fi
echo ""

# 检查必要的工具
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未安装 Python 3"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未安装 Node.js"
    exit 1
fi

# 检查依赖
echo "📦 检查并安装 Python 依赖..."

# 检查并安装 requirements.txt
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "  正在安装 Python 依赖..."
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    echo "  ✅ Python 依赖已安装"
else
    echo "  ⚠️ 未找到 requirements.txt"
fi

echo ""

# 清理占用的端口
echo "🧹 清理占用的端口..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :4173 | xargs kill -9 2>/dev/null || true
sleep 1
echo "  ✅ 端口已清理"
echo ""

# 启动后端
echo "🔧 启动后端服务 (Port 8000)..."
cd "$PROJECT_DIR"
PYTHONPATH=src uvicorn creative_autogpt.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 启动前端
echo "⚛️  启动前端服务 (Port 4173)..."
cd "$PROJECT_DIR/frontend"
VITE_API_BASE_URL=http://localhost:8000 npm run dev -- --host --port 4173 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

echo ""
echo "================================"
echo "🎉 所有服务已启动！"
echo ""
echo "📱 访问应用: http://localhost:4173"
echo "🔌 API 服务: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "================================"
echo ""

# 等待中断信号
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '✅ 已关闭所有服务'; exit 0" INT TERM

wait
