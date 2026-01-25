# Creative AutoGPT - 开发指南

## 🚀 快速开始

### 方式一：使用启动脚本（推荐）

```bash
cd /Users/fanhailiang/Desktop/ai/division_autoGpt
./start.sh
```

这会在后台启动后端和前端服务，然后访问 http://localhost:4173

### 方式二：手动启动

**终端 1 - 启动后端：**
```bash
cd /Users/fanhailiang/Desktop/ai/division_autoGpt
PYTHONPATH=src uvicorn creative_autogpt.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - 启动前端：**
```bash
cd /Users/fanhailiang/Desktop/ai/division_autoGpt/frontend
VITE_API_BASE_URL=http://localhost:8000 npm run dev -- --host --port 4173
```

## 📍 服务地址

- **前端应用**: http://localhost:4173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **API 文档**: http://localhost:8000/redoc (ReDoc)

## 🧪 运行测试

### E2E 测试（无界面）

```bash
cd frontend
npm run test:e2e
```

### E2E 测试（可视化）

```bash
cd frontend
npm run test:e2e:headed  # 显示浏览器
npm run test:e2e:debug  # 调试模式
npm run test:e2e:ui     # UI 模式
```

### 查看测试报告

运行完测试后，会生成 HTML 报告：

```bash
cd frontend
npx playwright show-report
```

## 📦 项目结构

```
division_autoGpt/
├── src/                          # 后端源代码
│   └── creative_autogpt/
│       ├── api/                  # FastAPI 应用
│       │   ├── main.py           # 应用入口
│       │   └── routes/           # API 路由
│       │       ├── sessions.py   # 会话管理
│       │       ├── websocket.py  # WebSocket
│       │       └── prompts.py    # 提示词增强
│       ├── core/                 # 核心逻辑
│       ├── modes/                # 创作模式
│       ├── storage/              # 数据存储
│       └── utils/                # 工具函数
│
├── frontend/                     # 前端代码
│   ├── src/
│   │   ├── pages/                # 页面组件
│   │   ├── components/           # 可复用组件
│   │   ├── hooks/                # React Hooks
│   │   ├── api/                  # API 客户端
│   │   └── stores/               # Zustand 状态
│   ├── e2e/                      # Playwright E2E 测试
│   └── playwright.config.ts      # Playwright 配置
│
└── start.sh                      # 启动脚本
```

## 🔌 核心技术栈

**后端:**
- FastAPI - Web 框架
- WebSocket - 实时通信
- SQLAlchemy - ORM
- Pydantic - 数据验证

**前端:**
- React 18 - UI 框架
- Vite - 构建工具
- TypeScript - 类型检查
- Zustand - 状态管理
- Playwright - E2E 测试

## 🐛 常见问题

### Q: `uvicorn: command not found`

```bash
pip install uvicorn
```

### Q: 后端无法连接

检查 Python 依赖是否已安装：
```bash
cd /Users/fanhailiang/Desktop/ai/division_autoGpt
pip install -r requirements.txt  # 如果存在
```

### Q: 前端无法启动

检查 npm 依赖：
```bash
cd frontend
npm install
```

### Q: WebSocket 连接失败

确保后端已启动，且前端的 API 地址正确：
```bash
export VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

### Q: 测试找不到模块

确保在 frontend 目录运行测试：
```bash
cd frontend
npm run test:e2e
```

## 📊 E2E 测试覆盖

✅ **12 个测试用例全部通过**

1. ✓ 首页加载
2. ✓ 导航到创建页
3. ✓ 手动创建会话
4. ✓ Workspace 加载和 WebSocket
5. ✓ 会话列表页
6. ✓ API 端点测试
7. ✓ API 创建会话
8. ✓ WebSocket 事件流
9. ✓ 错误处理（无效会话）
10. ✓ 完整创建流程
11. ✓ 智能增强功能
12. ✓ 清理测试数据

**总耗时**: ~43 秒

## 🔄 工作流

### 创建会话流程

```
创建会话 (POST /sessions)
    ↓
进入 Workspace
    ↓
WebSocket 连接并自动启动
    ↓
后端生成大纲、章节、内容
    ↓
WebSocket 实时推送 progress 和 task_complete 事件
    ↓
前端更新状态和显示
    ↓
会话完成或失败
```

### WebSocket 事件流

**前端 → 后端:**
- `connect` - 心跳连接确认
- `subscribe` - 订阅会话事件
- `start` - 启动会话
- `pause`, `resume`, `stop` - 控制命令

**后端 → 前端:**
- `subscribed` - 订阅确认
- `started` - 会话启动
- `task_start` - 任务开始
- `task_complete` - 任务完成
- `progress` - 进度更新
- `completed` - 会话完成
- `failed` - 会话失败

## 📝 开发建议

1. **修改 API 后端代码** → 自动热重载，无需重启
2. **修改前端代码** → 自动热更新
3. **添加新依赖** → 重启开发服务器
4. **运行测试前** → 确保后端和前端都已启动

## 🔗 相关资源

- [Playwright 文档](https://playwright.dev/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React 文档](https://react.dev/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
