# Creative AutoGPT 前端应用

基于 React + TypeScript + Vite 构建的现代化小说创作辅助系统前端。

## ✨ 功能特性

### 🎯 核心功能
- ✅ **智能创作辅助**: AI 驱动的小说创作流程
- ✅ **实时预览**: 即时查看 AI 生成内容
- ✅ **交互式反馈**: 快速反馈和范围选择
- ✅ **任务管理**: 可视化任务列表和状态追踪
- ✅ **质量评估**: 多维度内容质量评分
- ✅ **智能生成**: PromptEnhancer AI 自动配置
- ✅ **多格式导出**: 支持 txt/md/docx/pdf
- ✅ **实时更新**: WebSocket 实时状态同步

### 🚀 技术亮点
- **React 18**: 最新 React 特性
- **TypeScript**: 完整类型安全
- **Vite**: 极速开发体验
- **Zustand**: 轻量状态管理
- **React Query**: 智能数据缓存
- **Tailwind CSS**: 原子化 CSS
- **WebSocket**: 实时双向通信

## 📦 项目结构

```
frontend/
├── src/
│   ├── api/              # API 客户端和 WebSocket
│   │   ├── client.ts     # Axios 实例
│   │   └── websocket.ts  # WebSocket 客户端
│   ├── components/       # React 组件
│   │   ├── ui/           # 基础 UI 组件
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   └── ...
│   │   ├── ChatPanel.tsx
│   │   ├── PreviewPanel.tsx
│   │   ├── TaskCard.tsx
│   │   ├── SessionCard.tsx
│   │   ├── ScopeSelector.tsx
│   │   ├── ExportDialog.tsx
│   │   └── WebSocketStatus.tsx
│   ├── hooks/            # 自定义 Hooks
│   │   ├── useSession.ts
│   │   ├── useTask.ts
│   │   ├── useChat.ts
│   │   ├── usePreview.ts
│   │   ├── useWebSocket.ts
│   │   └── useExport.ts
│   ├── pages/            # 页面组件
│   │   ├── Home.tsx
│   │   ├── Create.tsx
│   │   ├── Sessions.tsx
│   │   └── Workspace/
│   │       ├── Workspace.tsx
│   │       ├── Tasks.tsx
│   │       ├── Preview.tsx
│   │       └── Reader.tsx
│   ├── stores/           # Zustand 状态管理
│   │   ├── sessionStore.ts
│   │   ├── taskStore.ts
│   │   ├── chatStore.ts
│   │   ├── previewStore.ts
│   │   └── wsStatusStore.ts
│   ├── types/            # TypeScript 类型定义
│   │   └── index.ts
│   ├── App.tsx           # 根组件
│   └── main.tsx          # 入口文件
├── public/               # 静态资源
├── index.html            # HTML 模板
├── package.json          # 依赖配置
├── tsconfig.json         # TypeScript 配置
├── vite.config.ts        # Vite 配置
└── tailwind.config.js    # Tailwind 配置
```

## 🛠️ 开发指南

### 环境要求
- Node.js >= 16
- npm >= 8

### 安装依赖
```bash
cd frontend
npm install
```

### 环境配置
创建 `.env` 文件：
```bash
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws/ws
```

### 开发模式
```bash
npm run dev
```
访问 http://localhost:5173

### 生产构建
```bash
npm run build
```
构建产物在 `dist/` 目录

### 预览构建
```bash
npm run preview
```

### 类型检查
```bash
npm run type-check
```

## 📋 主要依赖

### 核心库
- `react` ^18.2.0 - UI 框架
- `react-dom` ^18.2.0 - DOM 渲染
- `react-router-dom` ^6.x - 路由管理
- `typescript` ^5.x - 类型系统

### 状态管理
- `zustand` ^4.x - 状态管理
- `@tanstack/react-query` ^5.x - 数据请求

### UI/样式
- `tailwindcss` ^3.x - CSS 框架
- `lucide-react` ^0.x - 图标库

### 工具库
- `axios` ^1.x - HTTP 客户端
- `clsx` ^2.x - 类名合并

### 开发工具
- `vite` ^5.x - 构建工具
- `@vitejs/plugin-react` ^4.x - React 插件
- `eslint` ^8.x - 代码检查
- `prettier` ^3.x - 代码格式化

## 🎨 核心组件

### SessionCard
会话信息卡片，显示进度、状态、统计信息。

```tsx
<SessionCard
  session={session}
  onContinue={(id) => navigate(`/workspace/${id}`)}
  onView={(id) => navigate(`/workspace/${id}`)}
  onExport={(id) => handleExport(id)}
  onDelete={(id) => deleteSession(id)}
/>
```

### ScopeSelector
反馈范围选择器，支持当前任务/后续任务/全局影响。

```tsx
<ScopeSelector
  isOpen={isOpen}
  options={scopeOptions}
  onSelect={(scope) => handleScopeSelect(scope)}
  onCancel={() => setIsOpen(false)}
/>
```

### ExportDialog
导出对话框，支持多种格式导出。

```tsx
<ExportDialog
  sessionId={sessionId}
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
/>
```

### Toast 通知
全局通知系统。

```tsx
const toast = useToast();

toast.success('操作成功！');
toast.error('操作失败！');
toast.warning('警告信息');
toast.info('提示信息');
```

## 🌐 WebSocket 实时更新

### 使用 useWebSocket Hook
```tsx
useWebSocket({
  onSessionUpdate: (data) => {
    console.log('Session updated:', data);
  },
  onTaskUpdate: (data) => {
    console.log('Task updated:', data);
  },
  onProgress: (data) => {
    console.log('Progress:', data);
  },
  onError: (data) => {
    console.error('Error:', data);
  },
});
```

### 支持的事件
- `session.update` - 会话状态变化
- `task.update` - 任务状态变化
- `progress.update` - 进度更新
- `error` - 错误事件

## 📊 状态管理

### Session Store
```tsx
const sessions = useSessionStore((state) => state.sessions);
const updateSession = useSessionStore((state) => state.updateSession);
```

### Task Store
```tsx
const tasks = useTaskStore((state) => state.tasks);
const currentTask = useTaskStore((state) => state.currentTask);
const setCurrentTask = useTaskStore((state) => state.setCurrentTask);
```

### WebSocket Status Store
```tsx
const status = useWebSocketStatusStore((state) => state.status);
const reconnectAttempts = useWebSocketStatusStore((state) => state.reconnectAttempts);
```

## 🔌 API 集成

所有 API 请求通过 `src/api/client.ts` 统一管理：

```typescript
import apiClient from '@/api/client';

// GET 请求
const sessions = await apiClient.get('/sessions');

// POST 请求
const newSession = await apiClient.post('/sessions', data);

// DELETE 请求
await apiClient.delete(`/sessions/${id}`);
```

## 🎯 核心页面

### Home - 首页
- 项目概览
- 最近项目列表
- 快速导航

### Create - 创建页面
- 智能生成模式(AI 辅助)
- 手动填写模式
- 表单验证

### Sessions - 会话列表
- 状态筛选
- 分页浏览
- 批量操作

### Workspace - 工作区
- 预览面板
- 聊天面板
- 任务列表
- 阅读模式

## 📖 开发规范

### 组件规范
- 使用函数组件 + Hooks
- Props 定义 TypeScript 接口
- 导出命名组件

### 样式规范
- 使用 Tailwind CSS 类
- 避免内联样式
- 响应式设计优先

### 代码规范
- ESLint 检查
- Prettier 格式化
- TypeScript 严格模式

## 🚀 性能优化

- ✅ React Query 数据缓存
- ✅ 组件懒加载
- ✅ WebSocket 连接复用
- ✅ 防抖/节流处理
- ✅ 虚拟滚动(大列表)

## 📚 相关文档

- [实现总结](../docs/IMPLEMENTATION_SUMMARY.md)
- [WebSocket 实现](../docs/WEBSOCKET_IMPLEMENTATION.md)
- [完成清单](../docs/COMPLETION_CHECKLIST.md)
- [架构文档](../docs/ARCHITECTURE.md)

## 🐛 故障排查

### WebSocket 连接失败
检查环境变量 `VITE_WS_URL` 是否正确配置。

### API 请求失败
检查环境变量 `VITE_API_URL` 和后端服务是否启动。

### 样式不生效
运行 `npm run build` 重新构建。

### 类型错误
运行 `npm run type-check` 检查类型定义。

## 📝 更新日志

### v2.0.0 (2026-01-23)
- ✅ 完成 WebSocket 实时更新
- ✅ 添加智能创建功能
- ✅ 实现导出系统
- ✅ 完善 Toast 通知
- ✅ 优化所有交互功能

### v1.0.0
- ✅ 初始版本发布
- ✅ 核心功能实现

## 👥 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**开发团队**: Creative AutoGPT Team  
**最后更新**: 2026-01-23
