# 前端组件规范

> Creative AutoGPT React 组件设计规范

## 1. 组件架构

### 1.1 目录结构

```
frontend/src/
├── components/                 # 通用组件
│   ├── common/                # 基础组件
│   │   ├── Button/
│   │   ├── Input/
│   │   ├── Modal/
│   │   ├── Toast/
│   │   └── Loading/
│   ├── layout/                # 布局组件
│   │   ├── Header/
│   │   ├── Sidebar/
│   │   ├── MainLayout/
│   │   └── MobileNav/
│   ├── task/                  # 任务相关组件
│   │   ├── TaskCard/
│   │   ├── TaskList/
│   │   ├── TaskProgress/
│   │   └── TaskStatus/
│   ├── preview/               # 预览相关组件
│   │   ├── PreviewPanel/
│   │   ├── ContentViewer/
│   │   ├── QualityBadge/
│   │   └── KeyPoints/
│   ├── chat/                  # 聊天相关组件
│   │   ├── ChatPanel/
│   │   ├── ChatMessage/
│   │   ├── ChatInput/
│   │   ├── QuickFeedback/
│   │   └── ScopeSelector/
│   ├── session/               # 会话相关组件
│   │   ├── SessionCard/
│   │   ├── SessionList/
│   │   └── SessionConfig/
│   └── chapter/               # 章节相关组件
│       ├── ChapterList/
│       ├── ChapterReader/
│       └── ChapterNav/
├── pages/                     # 页面组件
│   ├── Home/                  # 首页（会话列表）
│   ├── Create/                # 新建会话
│   ├── Workspace/             # 主工作区
│   ├── Reader/                # 章节阅读
│   └── Export/                # 导出页面
├── hooks/                     # 自定义 Hooks
│   ├── useSession.ts
│   ├── useTask.ts
│   ├── useWebSocket.ts
│   ├── usePreview.ts
│   └── useChat.ts
├── stores/                    # 状态管理
│   ├── sessionStore.ts
│   ├── taskStore.ts
│   ├── chatStore.ts
│   └── uiStore.ts
├── api/                       # API 调用
│   ├── client.ts
│   ├── sessions.ts
│   ├── tasks.ts
│   ├── prompts.ts
│   └── websocket.ts
├── types/                     # TypeScript 类型
│   ├── session.ts
│   ├── task.ts
│   ├── chat.ts
│   └── api.ts
├── utils/                     # 工具函数
│   ├── format.ts
│   ├── storage.ts
│   └── constants.ts
└── styles/                    # 全局样式
    ├── variables.scss
    ├── mixins.scss
    └── global.scss
```

---

## 2. 核心组件接口

### 2.1 TaskCard

```tsx
// components/task/TaskCard/index.tsx

import { FC } from 'react';

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'reviewing' | 'paused';
export type TaskType = 'outline' | 'character' | 'event' | 'chapter' | 'polish' | string;

export interface TaskCardProps {
  /** 任务ID */
  taskId: string;
  /** 任务类型 */
  taskType: TaskType;
  /** 任务名称 */
  taskName: string;
  /** 任务状态 */
  status: TaskStatus;
  /** 进度 0-100 */
  progress?: number;
  /** 是否当前选中 */
  isActive?: boolean;
  /** 是否可点击 */
  clickable?: boolean;
  /** 点击事件 */
  onClick?: () => void;
  /** 重试事件 */
  onRetry?: () => void;
  /** 跳过事件 */
  onSkip?: () => void;
  /** 自定义类名 */
  className?: string;
}

export const TaskCard: FC<TaskCardProps> = ({
  taskId,
  taskType,
  taskName,
  status,
  progress,
  isActive = false,
  clickable = true,
  onClick,
  onRetry,
  onSkip,
  className,
}) => {
  // 根据任务类型获取图标
  const getIcon = () => {
    const icons: Record<string, string> = {
      outline: '📋',
      character: '👤',
      event: '📅',
      chapter: '📖',
      polish: '✨',
    };
    return icons[taskType] || '📝';
  };
  
  // 根据状态获取样式
  const getStatusStyle = () => {
    const styles: Record<TaskStatus, string> = {
      pending: 'task-card--pending',
      running: 'task-card--running',
      completed: 'task-card--completed',
      failed: 'task-card--failed',
      reviewing: 'task-card--reviewing',
      paused: 'task-card--paused',
    };
    return styles[status];
  };
  
  return (
    <div
      className={`task-card ${getStatusStyle()} ${isActive ? 'task-card--active' : ''} ${className || ''}`}
      onClick={clickable ? onClick : undefined}
    >
      <div className="task-card__icon">{getIcon()}</div>
      <div className="task-card__content">
        <div className="task-card__name">{taskName}</div>
        <div className="task-card__status">
          <TaskStatusBadge status={status} />
        </div>
        {progress !== undefined && (
          <div className="task-card__progress">
            <div 
              className="task-card__progress-bar" 
              style={{ width: `${progress}%` }} 
            />
          </div>
        )}
      </div>
      {status === 'failed' && (
        <div className="task-card__actions">
          <button onClick={onRetry}>重试</button>
          <button onClick={onSkip}>跳过</button>
        </div>
      )}
    </div>
  );
};
```

### 2.2 PreviewPanel

```tsx
// components/preview/PreviewPanel/index.tsx

import { FC } from 'react';
import ReactMarkdown from 'react-markdown';

export interface PreviewContent {
  content: string;
  summary: string;
  keyPoints: string[];
  wordCount: number;
}

export interface QualityInfo {
  score: number;
  maxScore: number;
  passed: boolean;
  details?: {
    completeness?: number;
    consistency?: number;
    creativity?: number;
  };
}

export interface PreviewPanelProps {
  /** 任务ID */
  taskId: string;
  /** 任务名称 */
  taskName: string;
  /** 预览内容 */
  preview: PreviewContent;
  /** 质量信息 */
  quality: QualityInfo;
  /** 状态 */
  status: 'pending_review' | 'approved' | 'needs_revision';
  /** 修订次数 */
  revisionCount?: number;
  /** 是否正在加载 */
  loading?: boolean;
  /** 确认事件 */
  onApprove: () => void;
  /** 重新生成事件 */
  onRegenerate: () => void;
  /** 跳过事件 */
  onSkip?: () => void;
  /** 反馈事件 */
  onFeedback?: (feedback: string) => void;
}

export const PreviewPanel: FC<PreviewPanelProps> = ({
  taskId,
  taskName,
  preview,
  quality,
  status,
  revisionCount = 0,
  loading = false,
  onApprove,
  onRegenerate,
  onSkip,
  onFeedback,
}) => {
  if (loading) {
    return <PreviewSkeleton />;
  }
  
  return (
    <div className="preview-panel">
      {/* 标题栏 */}
      <div className="preview-panel__header">
        <h3>📄 {taskName}</h3>
        {revisionCount > 0 && (
          <span className="preview-panel__revision">
            第 {revisionCount + 1} 版
          </span>
        )}
      </div>
      
      {/* 内容区 */}
      <div className="preview-panel__content">
        <ReactMarkdown>{preview.content}</ReactMarkdown>
      </div>
      
      {/* 摘要区 */}
      <div className="preview-panel__summary">
        <h4>【摘要】</h4>
        <p>{preview.summary}</p>
        
        <h4>【关键点】</h4>
        <ul>
          {preview.keyPoints.map((point, index) => (
            <li key={index}>{point}</li>
          ))}
        </ul>
      </div>
      
      {/* 质量评分 */}
      <div className="preview-panel__quality">
        <QualityBadge 
          score={quality.score} 
          maxScore={quality.maxScore}
          showStars 
        />
        <span className="preview-panel__word-count">
          {preview.wordCount.toLocaleString()} 字
        </span>
      </div>
      
      {/* 操作按钮 */}
      <div className="preview-panel__actions">
        <button 
          className="btn btn--primary"
          onClick={onApprove}
        >
          ✅ 确认通过
        </button>
        <button 
          className="btn btn--secondary"
          onClick={onRegenerate}
        >
          🔄 重新生成
        </button>
        {onSkip && (
          <button 
            className="btn btn--ghost"
            onClick={onSkip}
          >
            ⏭️ 跳过
          </button>
        )}
      </div>
    </div>
  );
};
```

### 2.3 ChatPanel

```tsx
// components/chat/ChatPanel/index.tsx

import { FC, useState, useRef, useEffect } from 'react';

export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  scopeQuestion?: ScopeQuestion;
}

export interface ScopeQuestion {
  required: boolean;
  message: string;
  options: ScopeOption[];
}

export interface ScopeOption {
  id: 'current_task' | 'future' | 'global';
  label: string;
  description: string;
  isDefault?: boolean;
  warning?: string;
}

export interface QuickFeedback {
  id: string;
  label: string;
  icon: string;
}

export interface ChatPanelProps {
  /** 任务ID */
  taskId: string;
  /** 消息列表 */
  messages: ChatMessage[];
  /** 快捷反馈选项 */
  quickFeedbacks: QuickFeedback[];
  /** 是否正在处理 */
  processing?: boolean;
  /** 发送消息 */
  onSendMessage: (message: string) => void;
  /** 快捷反馈 */
  onQuickFeedback: (feedbackId: string) => void;
  /** 选择作用域 */
  onScopeSelect: (scope: string) => void;
}

export const ChatPanel: FC<ChatPanelProps> = ({
  taskId,
  messages,
  quickFeedbacks,
  processing = false,
  onSendMessage,
  onQuickFeedback,
  onScopeSelect,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !processing) {
      onSendMessage(input.trim());
      setInput('');
    }
  };
  
  return (
    <div className="chat-panel">
      {/* 标题 */}
      <div className="chat-panel__header">
        <h3>💬 AI 助手</h3>
      </div>
      
      {/* 消息列表 */}
      <div className="chat-panel__messages">
        {messages.map((msg) => (
          <ChatMessage 
            key={msg.id} 
            message={msg}
            onScopeSelect={onScopeSelect}
          />
        ))}
        {processing && (
          <div className="chat-message chat-message--assistant">
            <span className="chat-message__typing">正在思考...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* 快捷反馈 */}
      <div className="chat-panel__quick-feedbacks">
        <div className="chat-panel__quick-feedbacks-label">📊 快捷反馈</div>
        <div className="chat-panel__quick-feedbacks-list">
          {quickFeedbacks.map((fb) => (
            <button
              key={fb.id}
              className="quick-feedback-btn"
              onClick={() => onQuickFeedback(fb.id)}
              disabled={processing}
            >
              {fb.icon} {fb.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* 输入框 */}
      <form className="chat-panel__input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入反馈或建议..."
          disabled={processing}
        />
        <button 
          type="submit" 
          disabled={!input.trim() || processing}
        >
          发送 ↵
        </button>
      </form>
    </div>
  );
};
```

### 2.4 ScopeSelector

```tsx
// components/chat/ScopeSelector/index.tsx

import { FC, useState } from 'react';

export interface ScopeSelectorProps {
  /** 选项列表 */
  options: ScopeOption[];
  /** 默认选中 */
  defaultScope?: string;
  /** 选择回调 */
  onSelect: (scope: string) => void;
  /** 取消回调 */
  onCancel?: () => void;
}

export const ScopeSelector: FC<ScopeSelectorProps> = ({
  options,
  defaultScope,
  onSelect,
  onCancel,
}) => {
  const [selected, setSelected] = useState(
    defaultScope || options.find(o => o.isDefault)?.id || options[0]?.id
  );
  
  const handleConfirm = () => {
    onSelect(selected);
  };
  
  return (
    <div className="scope-selector">
      <div className="scope-selector__title">
        🎯 这个修改应该影响哪些内容？
      </div>
      
      <div className="scope-selector__options">
        {options.map((option) => (
          <label 
            key={option.id}
            className={`scope-option ${selected === option.id ? 'scope-option--selected' : ''}`}
          >
            <input
              type="radio"
              name="scope"
              value={option.id}
              checked={selected === option.id}
              onChange={() => setSelected(option.id)}
            />
            <div className="scope-option__content">
              <div className="scope-option__label">{option.label}</div>
              <div className="scope-option__description">{option.description}</div>
              {option.warning && (
                <div className="scope-option__warning">
                  ⚠️ {option.warning}
                </div>
              )}
            </div>
          </label>
        ))}
      </div>
      
      <div className="scope-selector__actions">
        {onCancel && (
          <button 
            className="btn btn--ghost"
            onClick={onCancel}
          >
            取消
          </button>
        )}
        <button 
          className="btn btn--primary"
          onClick={handleConfirm}
        >
          确认
        </button>
      </div>
    </div>
  );
};
```

### 2.5 SessionCard

```tsx
// components/session/SessionCard/index.tsx

import { FC } from 'react';

export type SessionStatus = 'created' | 'running' | 'paused' | 'completed' | 'failed';

export interface SessionCardProps {
  /** 会话ID */
  sessionId: string;
  /** 项目名称 */
  name: string;
  /** 风格/类型 */
  style: string;
  /** 状态 */
  status: SessionStatus;
  /** 进度 0-100 */
  progress: number;
  /** 当前字数 */
  currentWords: number;
  /** 目标字数 */
  targetWords: number;
  /** 最后更新时间 */
  lastUpdated: string;
  /** 继续事件 */
  onContinue?: () => void;
  /** 查看事件 */
  onView?: () => void;
  /** 导出事件 */
  onExport?: () => void;
  /** 删除事件 */
  onDelete?: () => void;
}

export const SessionCard: FC<SessionCardProps> = ({
  sessionId,
  name,
  style,
  status,
  progress,
  currentWords,
  targetWords,
  lastUpdated,
  onContinue,
  onView,
  onExport,
  onDelete,
}) => {
  const getStatusConfig = () => {
    const configs: Record<SessionStatus, { icon: string; text: string; color: string }> = {
      created: { icon: '⏳', text: '未开始', color: 'gray' },
      running: { icon: '🟢', text: '进行中', color: 'green' },
      paused: { icon: '🟡', text: '已暂停', color: 'yellow' },
      completed: { icon: '✅', text: '已完成', color: 'blue' },
      failed: { icon: '❌', text: '失败', color: 'red' },
    };
    return configs[status];
  };
  
  const statusConfig = getStatusConfig();
  
  return (
    <div className={`session-card session-card--${statusConfig.color}`}>
      <div className="session-card__header">
        <h3 className="session-card__name">
          📖 {name}
        </h3>
        <span className="session-card__style">{style}</span>
      </div>
      
      <div className="session-card__info">
        <div className="session-card__status">
          状态: {statusConfig.icon} {statusConfig.text}
        </div>
        <div className="session-card__progress">
          <div className="progress-bar">
            <div 
              className="progress-bar__fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span>{progress}%</span>
        </div>
        <div className="session-card__words">
          {(currentWords / 10000).toFixed(1)}万 / {(targetWords / 10000).toFixed(1)}万字
        </div>
        <div className="session-card__time">
          最后编辑: {lastUpdated}
        </div>
      </div>
      
      <div className="session-card__actions">
        {status !== 'completed' && onContinue && (
          <button className="btn btn--primary" onClick={onContinue}>
            继续
          </button>
        )}
        {onView && (
          <button className="btn btn--secondary" onClick={onView}>
            查看
          </button>
        )}
        {status === 'completed' && onExport && (
          <button className="btn btn--secondary" onClick={onExport}>
            导出
          </button>
        )}
        <button className="btn btn--icon" onClick={onDelete}>
          ⋯
        </button>
      </div>
    </div>
  );
};
```

---

## 3. 自定义 Hooks

### 3.1 useWebSocket

```tsx
// hooks/useWebSocket.ts

import { useEffect, useRef, useCallback, useState } from 'react';

interface WebSocketOptions {
  sessionId: string;
  onMessage?: (data: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export const useWebSocket = (options: WebSocketOptions) => {
  const {
    sessionId,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoReconnect = true,
    reconnectInterval = 3000,
  } = options;
  
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const reconnectTimer = useRef<NodeJS.Timeout>();
  
  const connect = useCallback(() => {
    const url = `ws://localhost:8000/ws?session_id=${sessionId}`;
    ws.current = new WebSocket(url);
    
    ws.current.onopen = () => {
      setConnected(true);
      setReconnecting(false);
      onConnect?.();
    };
    
    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };
    
    ws.current.onclose = () => {
      setConnected(false);
      onDisconnect?.();
      
      if (autoReconnect) {
        setReconnecting(true);
        reconnectTimer.current = setTimeout(connect, reconnectInterval);
      }
    };
    
    ws.current.onerror = (error) => {
      onError?.(error);
    };
  }, [sessionId, onMessage, onConnect, onDisconnect, onError, autoReconnect, reconnectInterval]);
  
  const send = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);
  
  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    ws.current?.close();
  }, []);
  
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);
  
  return { connected, reconnecting, send, disconnect };
};
```

### 3.2 usePreview

```tsx
// hooks/usePreview.ts

import { useState, useCallback } from 'react';
import { api } from '@/api/client';

interface UsePreviewOptions {
  sessionId: string;
  taskId: string;
}

export const usePreview = ({ sessionId, taskId }: UsePreviewOptions) => {
  const [preview, setPreview] = useState<PreviewContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fetchPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(`/sessions/${sessionId}/tasks/${taskId}/preview`);
      setPreview(response.data.data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId, taskId]);
  
  const approve = useCallback(async () => {
    try {
      await api.post(`/sessions/${sessionId}/tasks/${taskId}/preview/confirm`, {
        action: 'approve'
      });
      return true;
    } catch (e) {
      return false;
    }
  }, [sessionId, taskId]);
  
  const regenerate = useCallback(async (reason?: string) => {
    try {
      await api.post(`/sessions/${sessionId}/tasks/${taskId}/preview/confirm`, {
        action: 'regenerate',
        reason
      });
      return true;
    } catch (e) {
      return false;
    }
  }, [sessionId, taskId]);
  
  return {
    preview,
    loading,
    error,
    fetchPreview,
    approve,
    regenerate,
  };
};
```

### 3.3 useChat

```tsx
// hooks/useChat.ts

import { useState, useCallback } from 'react';
import { api } from '@/api/client';

interface UseChatOptions {
  sessionId: string;
  taskId: string;
}

export const useChat = ({ sessionId, taskId }: UseChatOptions) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [processing, setProcessing] = useState(false);
  const [pendingScope, setPendingScope] = useState<string | null>(null);
  
  const sendFeedback = useCallback(async (message: string) => {
    setProcessing(true);
    
    // 添加用户消息到列表
    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    
    try {
      const response = await api.post(
        `/sessions/${sessionId}/tasks/${taskId}/feedback`,
        { message, feedback_type: 'modification' }
      );
      
      const { transformed, scope_required, ai_response } = response.data.data;
      
      // 添加 AI 响应
      const assistantMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: ai_response,
        timestamp: new Date().toISOString(),
        scopeQuestion: scope_required ? {
          required: true,
          message: '这个修改应该影响哪些内容？',
          options: response.data.data.scope_options,
        } : undefined,
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      if (scope_required) {
        setPendingScope(response.data.data.feedback_id);
      }
    } catch (e) {
      // 添加错误消息
      setMessages(prev => [...prev, {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: '抱歉，处理反馈时出错了，请重试。',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setProcessing(false);
    }
  }, [sessionId, taskId]);
  
  const selectScope = useCallback(async (scope: string) => {
    if (!pendingScope) return;
    
    setProcessing(true);
    
    try {
      await api.post(
        `/sessions/${sessionId}/tasks/${taskId}/feedback/${pendingScope}/scope`,
        { scope }
      );
      
      // 添加系统消息
      setMessages(prev => [...prev, {
        id: `msg_${Date.now()}`,
        role: 'system',
        content: `作用域已选择：${getScopeLabel(scope)}`,
        timestamp: new Date().toISOString(),
      }]);
      
      setPendingScope(null);
    } catch (e) {
      console.error('Failed to select scope', e);
    } finally {
      setProcessing(false);
    }
  }, [sessionId, taskId, pendingScope]);
  
  const sendQuickFeedback = useCallback(async (feedbackId: string) => {
    setProcessing(true);
    
    try {
      await api.post(
        `/sessions/${sessionId}/tasks/${taskId}/quick-feedback`,
        { quick_feedback_id: feedbackId }
      );
    } catch (e) {
      console.error('Failed to send quick feedback', e);
    } finally {
      setProcessing(false);
    }
  }, [sessionId, taskId]);
  
  return {
    messages,
    processing,
    pendingScope,
    sendFeedback,
    selectScope,
    sendQuickFeedback,
  };
};

function getScopeLabel(scope: string): string {
  const labels: Record<string, string> = {
    current_task: '仅当前任务',
    future: '当前及后续任务',
    global: '全局设定',
  };
  return labels[scope] || scope;
}
```

---

## 4. 状态管理

### 4.1 Session Store

```tsx
// stores/sessionStore.ts

import { create } from 'zustand';
import { api } from '@/api/client';

interface Session {
  sessionId: string;
  name: string;
  mode: string;
  status: SessionStatus;
  config: any;
  progress: number;
  currentWords: number;
  targetWords: number;
  createdAt: string;
  updatedAt: string;
}

interface SessionState {
  // 状态
  sessions: Session[];
  currentSession: Session | null;
  loading: boolean;
  error: string | null;
  
  // 操作
  fetchSessions: () => Promise<void>;
  fetchSession: (sessionId: string) => Promise<void>;
  createSession: (config: any) => Promise<string>;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  deleteSession: (sessionId: string) => Promise<void>;
  setCurrentSession: (session: Session | null) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSession: null,
  loading: false,
  error: null,
  
  fetchSessions: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.get('/sessions');
      set({ sessions: response.data.data.sessions, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },
  
  fetchSession: async (sessionId) => {
    set({ loading: true, error: null });
    try {
      const response = await api.get(`/sessions/${sessionId}`);
      set({ currentSession: response.data.data, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },
  
  createSession: async (config) => {
    set({ loading: true, error: null });
    try {
      const response = await api.post('/sessions', config);
      const newSession = response.data.data;
      set(state => ({
        sessions: [...state.sessions, newSession],
        loading: false,
      }));
      return newSession.sessionId;
    } catch (e: any) {
      set({ error: e.message, loading: false });
      throw e;
    }
  },
  
  updateSession: (sessionId, updates) => {
    set(state => ({
      sessions: state.sessions.map(s => 
        s.sessionId === sessionId ? { ...s, ...updates } : s
      ),
      currentSession: state.currentSession?.sessionId === sessionId
        ? { ...state.currentSession, ...updates }
        : state.currentSession,
    }));
  },
  
  deleteSession: async (sessionId) => {
    try {
      await api.delete(`/sessions/${sessionId}`);
      set(state => ({
        sessions: state.sessions.filter(s => s.sessionId !== sessionId),
        currentSession: state.currentSession?.sessionId === sessionId 
          ? null 
          : state.currentSession,
      }));
    } catch (e: any) {
      set({ error: e.message });
      throw e;
    }
  },
  
  setCurrentSession: (session) => {
    set({ currentSession: session });
  },
}));
```

### 4.2 Task Store

```tsx
// stores/taskStore.ts

import { create } from 'zustand';

interface Task {
  taskId: string;
  taskType: string;
  taskName: string;
  status: TaskStatus;
  progress: number;
  result?: any;
  evaluation?: any;
}

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  
  setTasks: (tasks: Task[]) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  setCurrentTask: (task: Task | null) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  currentTask: null,
  
  setTasks: (tasks) => set({ tasks }),
  
  updateTask: (taskId, updates) => {
    set(state => ({
      tasks: state.tasks.map(t => 
        t.taskId === taskId ? { ...t, ...updates } : t
      ),
      currentTask: state.currentTask?.taskId === taskId
        ? { ...state.currentTask, ...updates }
        : state.currentTask,
    }));
  },
  
  setCurrentTask: (task) => set({ currentTask: task }),
}));
```

---

## 5. API 调用

### 5.1 API Client

```tsx
// api/client.ts

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证 token（如果有）
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      // 处理未授权
    } else if (error.response?.status === 500) {
      // 处理服务器错误
    }
    return Promise.reject(error);
  }
);
```

### 5.2 Sessions API

```tsx
// api/sessions.ts

import { api } from './client';

export const sessionsApi = {
  // 获取会话列表
  list: (params?: { page?: number; pageSize?: number; status?: string }) => 
    api.get('/sessions', { params }),
  
  // 获取单个会话
  get: (sessionId: string) => 
    api.get(`/sessions/${sessionId}`),
  
  // 创建会话
  create: (config: any) => 
    api.post('/sessions', config),
  
  // 智能创建
  smartCreate: (userInput: string, autoConfirm = true) =>
    api.post('/sessions/smart-create', { user_input: userInput, auto_confirm: autoConfirm }),
  
  // 删除会话
  delete: (sessionId: string) => 
    api.delete(`/sessions/${sessionId}`),
  
  // 启动执行
  start: (sessionId: string, mode = 'auto') =>
    api.post(`/sessions/${sessionId}/start`, { mode }),
  
  // 暂停执行
  pause: (sessionId: string) =>
    api.post(`/sessions/${sessionId}/pause`),
  
  // 继续执行
  resume: (sessionId: string) =>
    api.post(`/sessions/${sessionId}/resume`),
};
```

---

*版本: 1.0*  
*最后更新: 2026-01-23*
