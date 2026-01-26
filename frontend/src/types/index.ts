/**
 * TypeScript type definitions
 */

// Session types
export interface Session {
  id: string;
  title: string;
  mode: string;
  status: SessionStatus;
  goal: Record<string, any>;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  llm_calls: number;
  tokens_used: number;
  // 🔥 新增：重写状态字段
  is_rewriting?: boolean;  // 是否正在重写
  rewrite_attempt?: number;  // 当前重写尝试次数
  rewrite_task_id?: string;  // 正在重写的任务 ID
  rewrite_task_type?: string;  // 正在重写的任务类型
}

export type SessionStatus = 'created' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';

export interface SessionCreateRequest {
  title: string;
  mode?: string;
  goal?: Record<string, any>;
  config?: Record<string, any>;
}

// Task types
export interface Task {
  id: string;
  task_id: string;
  task_type: string;
  description?: string;
  status: TaskStatus;
  result?: string;
  error?: string;
  metadata?: Record<string, any>;
  evaluation?: EvaluationResult;
  created_at: string;
  chapter_index?: number;
  llm_provider?: string;
  llm_model?: string;
  // 🔥 新增任务统计字段
  started_at?: string;
  completed_at?: string;
  execution_time_seconds?: number;
  total_tokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  cost_usd?: number;
  failed_attempts?: number;
  retry_count?: number;
}

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'pending_approval' | 'skipped';

export interface EvaluationResult {
  score: number;
  passed: boolean;
  reasons?: string[];
  suggestions?: string[];
  criteria?: Record<string, number>;
  dimension_scores?: Record<string, { score: number; reason?: string }>;
  // 🔥 新增：分别的质量和一致性评分
  quality_score?: number;
  consistency_score?: number;
  quality_issues?: string[];
  consistency_issues?: string[];
}

export interface TaskProgress {
  session_id: string;
  status: SessionStatus;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  percentage: number;
  current_task?: string;
  current_task_provider?: string;
  current_task_model?: string;
  retry_count?: number;  // 当前任务的重试次数
  task_started_at?: string; // 当前任务开始时间
  is_completed?: boolean; // 是否全部完成
  // 🔥 新增：重写状态字段
  is_rewriting?: boolean;  // 是否正在重写
  rewrite_attempt?: number;  // 当前重写尝试次数
  rewrite_task_type?: string;  // 正在重写的任务类型
}

// Chat types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatFeedback {
  message: string;
  scope?: 'current_task' | 'chapter' | 'all';
}

// WebSocket types
export interface WebSocketMessage {
  event: string;
  session_id?: string;
  data?: any;
}

// API Response types
export interface ApiResponse<T = any> {
  success?: boolean;
  data?: T;
  error?: string;
  detail?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_providers: string[];
  storage_status: string;
  memory_status: string;
}
