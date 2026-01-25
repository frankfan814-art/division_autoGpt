# Creative AutoGPT 项目启动指南

## 📋 前置要求

### 系统要求
- **Python**: 3.10 或更高版本
- **Node.js**: 16 或更高版本
- **npm**: 8 或更高版本

### 检查版本
```bash
python3 --version  # 应该 >= 3.10
node --version     # 应该 >= 16
npm --version      # 应该 >= 8
```

---

## 🚀 快速启动（推荐）

### 一键启动（同时启动前后端）

在项目根目录执行：

```bash
# 方法1: 使用 tmux（推荐）
tmux new-session -s creative-autogpt \; \
  send-keys 'cd /Users/fanhailiang/Desktop/ai/division_autoGpt && source venv/bin/activate && python scripts/run_server.py' C-m \; \
  split-window -h \; \
  send-keys 'cd /Users/fanhailiang/Desktop/ai/division_autoGpt/frontend && npm run dev' C-m

# 方法2: 使用两个终端窗口（见下面详细步骤）
```

---

## 🔧 详细启动步骤

### 第一步：初始化项目（仅首次需要）

#### 1.1 后端初始化

```bash
# 进入项目根目录
cd /Users/fanhailiang/Desktop/ai/division_autoGpt

# 创建虚拟环境（如果还没有）
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py init
```

#### 1.2 前端初始化

```bash
# 进入前端目录
cd /Users/fanhailiang/Desktop/ai/division_autoGpt/frontend

# 安装依赖
npm install
```

#### 1.3 环境配置

确保 `.env` 文件已配置好 API Keys（已完成，无需修改）：

```bash
# 查看当前配置
cat .env

# 主要配置项：
# - ALIYUN_API_KEY: 阿里云千问（已配置）
# - DEEPSEEK_API_KEY: DeepSeek（已配置）
# - ARK_API_KEY: 火山方舟/豆包（已配置）
# - NVIDIA_API_KEY: NVIDIA（已配置）
```

---

### 第二步：启动后端服务

**打开第一个终端窗口**：

```bash
# 进入项目根目录
cd /Users/fanhailiang/Desktop/ai/division_autoGpt

# 激活虚拟环境
source venv/bin/activate

# 启动后端服务
python scripts/run_server.py
```

**成功启动后会看到**：
```
╔═══════════════════════════════════════════════════════╗
║           Creative AutoGPT API Server                  ║
╠═══════════════════════════════════════════════════════╣
║  Environment: development                              ║
║  Host:        0.0.0.0:8000                            ║
║  Docs:        http://0.0.0.0:8000/docs                ║
╚═══════════════════════════════════════════════════════╝

INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**后端服务地址**：
- API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws/ws

---

### 第三步：启动前端服务

**打开第二个终端窗口**：

```bash
# 进入前端目录
cd /Users/fanhailiang/Desktop/ai/division_autoGpt/frontend

# 启动前端开发服务器
npm run dev
```

**成功启动后会看到**：
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**前端服务地址**：
- 应用: http://localhost:5173

---

## 🌐 访问应用

### 前端界面
浏览器打开: **http://localhost:5173**

可用页面：
- `/` - 首页
- `/create` - 创建新项目（支持智能生成）
- `/sessions` - 会话列表
- `/workspace/:id` - 工作区

### 后端 API 文档
浏览器打开: **http://localhost:8000/docs**

可以在这里测试所有 API 接口。

---

## 🛑 停止服务

### 停止后端
在后端终端按 `Ctrl + C`

### 停止前端
在前端终端按 `Ctrl + C`

### 停止 tmux 会话
```bash
# 列出所有会话
tmux ls

# 关闭会话
tmux kill-session -t creative-autogpt
```

---

## 📝 常用命令

### 后端命令

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动服务器
python scripts/run_server.py

# 初始化数据库
python scripts/init_db.py init

# 测试 LLM 连接
python scripts/test_llm.py --test llm

# 运行系统测试
python scripts/test_system.py

# 代码格式化
black src/

# 类型检查
mypy src/
```

### 前端命令

```bash
# 开发模式（热更新）
npm run dev

# 生产构建
npm run build

# 预览构建产物
npm run preview

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

---

## 🔍 验证安装

### 1. 检查后端
```bash
# 测试 API 是否正常
curl http://localhost:8000/health

# 预期输出：
# {"status":"healthy","version":"0.1.0"}
```

### 2. 检查前端
浏览器访问 http://localhost:5173，应该看到 Creative AutoGPT 首页。

### 3. 检查 WebSocket
打开前端应用，右下角应该**不显示**连接状态提示（说明已连接）。

如果显示 "正在连接..." 或 "已断开连接"，说明 WebSocket 连接有问题。

---

## ⚠️ 常见问题

### 问题1: 后端启动失败 - 端口被占用

**错误信息**：
```
ERROR: [Errno 48] Address already in use
```

**解决方案**：
```bash
# 查找占用 8000 端口的进程
lsof -ti:8000

# 杀死进程
kill -9 $(lsof -ti:8000)

# 或者修改端口（编辑 .env）
# APP_PORT=8001
```

### 问题2: 前端启动失败 - 依赖未安装

**错误信息**：
```
Cannot find module 'xxx'
```

**解决方案**：
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 问题3: 虚拟环境激活失败

**错误信息**：
```
venv/bin/activate: No such file or directory
```

**解决方案**：
```bash
# 重新创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 问题4: WebSocket 连接失败

**现象**: 前端右下角显示 "已断开连接"

**解决方案**：
1. 确认后端服务已启动
2. 检查前端 `.env` 配置：
```bash
cd frontend
cat .env

# 应该包含：
# VITE_API_URL=http://localhost:8000/api
# VITE_WS_URL=ws://localhost:8000/ws/ws
```

3. 如果没有前端 `.env`，创建它：
```bash
cd frontend
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws/ws
EOF
```

### 问题5: API Key 未配置

**错误信息**：
```
Configuration error: Missing API key
```

**解决方案**：
检查根目录 `.env` 文件，确保以下 API Key 已配置：
- ALIYUN_API_KEY
- DEEPSEEK_API_KEY
- ARK_API_KEY

---

## 🎯 开发工作流

### 推荐工作流程

1. **启动服务**（使用 tmux 一键启动）
```bash
tmux new-session -s dev \; \
  send-keys 'cd /Users/fanhailiang/Desktop/ai/division_autoGpt && source venv/bin/activate && python scripts/run_server.py' C-m \; \
  split-window -h \; \
  send-keys 'cd /Users/fanhailiang/Desktop/ai/division_autoGpt/frontend && npm run dev' C-m
```

2. **开发前端**
   - 修改 `frontend/src/` 下的文件
   - Vite 自动热更新

3. **开发后端**
   - 修改 `src/creative_autogpt/` 下的文件
   - Uvicorn 自动重载（开发模式）

4. **测试功能**
   - 前端：http://localhost:5173
   - API 文档：http://localhost:8000/docs

5. **提交代码**
```bash
# 代码格式化
black src/
npm run lint --fix

# 类型检查
mypy src/
npm run type-check

# 提交
git add .
git commit -m "feat: 描述"
git push
```

---

## 📊 端口占用情况

| 服务 | 端口 | 地址 |
|------|------|------|
| 后端 API | 8000 | http://localhost:8000 |
| 前端应用 | 5173 | http://localhost:5173 |
| WebSocket | 8000 | ws://localhost:8000/ws/ws |

---

## 🎉 启动成功标志

### 后端成功
✅ 终端显示 ASCII 欢迎界面  
✅ http://localhost:8000/docs 可访问  
✅ http://localhost:8000/health 返回正常

### 前端成功
✅ 终端显示 Vite ready  
✅ http://localhost:5173 可访问  
✅ 右下角**不显示**连接状态提示

### 完整系统成功
✅ 前端页面正常显示  
✅ 创建项目功能正常  
✅ WebSocket 实时更新正常  
✅ Toast 通知正常弹出

---

## 📚 下一步

- 📖 查看 [前端开发文档](frontend/README.md)
- 📖 查看 [WebSocket 实现文档](docs/WEBSOCKET_IMPLEMENTATION.md)
- 📖 查看 [实现总结](docs/IMPLEMENTATION_SUMMARY.md)
- 🎯 开始使用智能创作功能

---

**最后更新**: 2026-01-24  
**维护者**: Creative AutoGPT Team
