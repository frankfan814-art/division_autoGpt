# WebSocket 实时更新实现文档

## 📡 概述

本文档说明 Creative AutoGPT 前端 WebSocket 实时更新系统的完整实现。

## 🎯 功能特性

### 1. 核心功能
- ✅ **自动重连**: 断线后自动重连，最多重试 5 次
- ✅ **心跳检测**: 每 30 秒发送心跳，保持连接活跃
- ✅ **连接状态管理**: 实时显示连接状态(连接中/已连接/断开/错误)
- ✅ **事件订阅系统**: 支持多个组件订阅不同事件
- ✅ **状态同步**: 自动同步会话状态、任务状态、进度信息

### 2. 支持的事件类型

#### session.update (会话更新)
```typescript
{
  event: 'session.update',
  session_id: string,
  data: {
    status: 'running' | 'completed' | 'failed' | 'paused',
    completed_tasks: number,
    total_tasks: number,
    // ... other session fields
  }
}
```

#### task.update (任务更新)
```typescript
{
  event: 'task.update',
  data: {
    task_id: string,
    status: 'pending' | 'running' | 'completed' | 'failed',
    result?: string,
    error?: string,
    evaluation?: EvaluationResult,
    // ... other task fields
  }
}
```

#### progress.update (进度更新)
```typescript
{
  event: 'progress.update',
  data: {
    total_tasks: number,
    completed_tasks: number,
    current_task?: string,
  }
}
```

#### error (错误事件)
```typescript
{
  event: 'error',
  data: {
    message: string,
    code?: string,
  }
}
```

## 🏗️ 架构设计

### 1. WebSocket 客户端 (websocket.ts)

**职责**: 
- 管理 WebSocket 连接生命周期
- 处理自动重连和心跳
- 事件分发

**核心方法**:
```typescript
class WebSocketClient {
  connect(): void                    // 建立连接
  disconnect(): void                 // 断开连接
  send(data: any): boolean          // 发送消息
  subscribe(event, handler): () => void  // 订阅事件
  private startHeartbeat(): void    // 开始心跳
  private stopHeartbeat(): void     // 停止心跳
  private scheduleReconnect(): void // 调度重连
}
```

**重连策略**:
- 指数退避算法: delay = min(1000 * 2^attempts, 10000)
- 最大重试次数: 5 次
- 延迟范围: 1s - 10s

### 2. WebSocket Hook (useWebSocket.ts)

**职责**:
- React 组件集成
- 自动订阅/取消订阅
- Store 状态同步

**用法示例**:
```typescript
const MyComponent = () => {
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
  
  // Component logic...
};
```

### 3. 状态管理 (wsStatusStore.ts)

**职责**:
- 跟踪连接状态
- 记录重连次数
- 存储错误信息

**状态类型**:
```typescript
type ConnectionStatus = 
  | 'connected'      // 已连接
  | 'disconnected'   // 已断开
  | 'connecting'     // 连接中
  | 'error';         // 错误
```

### 4. UI 组件 (WebSocketStatus.tsx)

**职责**:
- 显示连接状态
- 提醒用户断线重连
- 显示错误信息

**显示规则**:
- 已连接: 不显示(隐藏)
- 连接中: 黄色提示 "正在连接..."
- 已断开: 橙色提示 "重连中 (X/5)"
- 错误: 红色提示 "连接错误"

## 📄 已集成页面

### 1. Workspace 主页面 (Workspace.tsx)
```typescript
useWebSocket({
  onSessionUpdate: (data) => {
    // 会话完成提示
    if (data.data?.status === 'completed') {
      toast.success('🎉 创作任务已完成！');
    }
  },
  onTaskUpdate: (data) => {
    // 自动同步到 taskStore
  },
  onProgress: (data) => {
    // 自动同步到 taskStore
  },
  onError: (data) => {
    toast.error(data.data?.message || '发生错误');
  },
});
```

### 2. Tasks 页面 (Tasks.tsx)
```typescript
useWebSocket({
  onTaskUpdate: (data) => {
    const task = data.data;
    if (task?.status === 'completed') {
      toast.success(`✅ 任务完成: ${task.task_type}`);
    } else if (task?.status === 'failed') {
      toast.error(`❌ 任务失败: ${task.task_type}`);
    }
  },
});
```

### 3. Home 页面 (Home.tsx)
```typescript
useWebSocket({
  onSessionUpdate: () => {
    // 会话列表自动同步到 sessionStore
  },
});
```

### 4. Sessions 页面 (Sessions.tsx)
```typescript
useWebSocket({
  onSessionUpdate: () => {
    // 会话列表自动同步到 sessionStore
  },
});
```

## 🔄 数据流

```
Backend WebSocket Server
         ↓
[WebSocket Message]
         ↓
WebSocketClient.onmessage
         ↓
handleMessage(message)
         ↓
eventHandlers.get(event)
         ↓
forEach handler.call(message)
         ↓
┌────────────────┬────────────────┬────────────────┐
│  sessionStore  │   taskStore    │   Component    │
│  updateSession │   upsertTask   │   onXxxUpdate  │
└────────────────┴────────────────┴────────────────┘
         ↓
React Component Re-render
```

## 🛠️ Store 更新逻辑

### sessionStore
```typescript
// useWebSocket 自动调用
updateSession(session_id, {
  status: data.status,
  completed_tasks: data.completed_tasks,
  total_tasks: data.total_tasks,
  // ... 其他字段
});
```

### taskStore
```typescript
// useWebSocket 自动调用
upsertTask({
  task_id: data.task_id,
  status: data.status,
  result: data.result,
  error: data.error,
  evaluation: data.evaluation,
  // ... 其他字段
});

setProgress({
  total_tasks: data.total_tasks,
  completed_tasks: data.completed_tasks,
  current_task: data.current_task,
});
```

## 🎨 用户体验

### 1. 连接状态提示
- **位置**: 屏幕右下角
- **样式**: 带图标的浮动卡片，带动画效果
- **自动隐藏**: 连接成功后自动消失

### 2. 实时通知
- **任务完成**: Toast 绿色提示 "✅ 任务完成: XXX"
- **任务失败**: Toast 红色提示 "❌ 任务失败: XXX"
- **会话完成**: Toast 绿色提示 "🎉 创作任务已完成！"
- **会话失败**: Toast 红色提示 "❌ 创作任务失败，请检查错误信息"

### 3. 状态同步
- **无需刷新**: 所有数据自动同步，无需手动刷新页面
- **实时更新**: 任务状态、进度条、统计信息实时更新
- **多标签页同步**: 同一浏览器多个标签页数据保持同步

## 🧪 测试场景

### 1. 正常连接
1. 打开应用
2. WebSocket 自动连接
3. 连接成功后状态指示器消失

### 2. 断线重连
1. 模拟网络断开(关闭后端)
2. 显示 "已断开连接" 提示
3. 自动重连，显示 "重连中 (1/5)"
4. 重连成功后提示消失

### 3. 实时更新
1. 创建新会话
2. 导航到 Workspace 页面
3. 观察任务自动创建和更新
4. 观察进度条实时变化
5. 任务完成时收到 Toast 通知

### 4. 多事件订阅
1. 同一页面订阅多个事件
2. 确保所有事件都能正确处理
3. 确保取消订阅后不再收到事件

## 📋 配置

### 环境变量
```bash
# .env
VITE_WS_URL=ws://localhost:8000/ws/ws
```

### 默认配置
```typescript
// websocket.ts
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/ws';
const maxReconnectAttempts = 5;
const heartbeatInterval = 30000; // 30 seconds
```

## 🚀 优化建议

### 已实现
- ✅ 自动重连
- ✅ 心跳检测
- ✅ 状态管理
- ✅ 事件订阅系统
- ✅ Store 自动同步
- ✅ 用户提示

### 未来优化
- ⬜ 离线消息队列
- ⬜ 二进制消息支持
- ⬜ 消息压缩
- ⬜ 更精细的错误处理
- ⬜ WebSocket 连接池
- ⬜ 更多统计信息(延迟、吞吐量等)

## 📝 开发注意事项

### 1. 订阅清理
- 使用 useEffect 订阅时，必须返回清理函数
- useWebSocket hook 已自动处理清理逻辑

### 2. 状态同步
- WebSocket 更新和 API 更新可能冲突
- 建议以 WebSocket 更新为准
- React Query 缓存时间设置为 5 秒

### 3. 性能考虑
- WebSocket 客户端是全局单例
- 多个组件可共享同一连接
- 事件处理器使用 Set 去重

### 4. 错误处理
- 连接错误自动重连
- 消息解析错误仅打印日志
- 事件处理器错误不影响其他处理器

## 📖 API 参考

### useWebSocket
```typescript
interface UseWebSocketOptions {
  onSessionUpdate?: (data: any) => void;
  onTaskUpdate?: (data: any) => void;
  onProgress?: (data: any) => void;
  onError?: (data: any) => void;
  onMessage?: (data: any) => void;
  autoConnect?: boolean;  // 默认 true
}

function useWebSocket(options: UseWebSocketOptions): void;
```

### getWebSocketClient
```typescript
function getWebSocketClient(): WebSocketClient;
```

### WebSocketClient
```typescript
class WebSocketClient {
  connect(): void;
  disconnect(): void;
  send(data: any): boolean;
  subscribe(event: string, handler: WebSocketEventHandler): () => void;
  getSessionId(): string | null;
}
```

---

**文档版本**: 1.0  
**更新日期**: 2026-01-23  
**维护者**: Creative AutoGPT Team
