/**
 * Task store for managing tasks
 */

import { create } from 'zustand';
import { Task, TaskProgress } from '@/types';

// 🔥 步骤进度类型
export interface StepProgress {
  step: string;
  message: string;
  task_id?: string;
  task_type?: string;
  timestamp?: string;
  // 上下文检索
  context_count?: number;
  context_types?: string[];
  // LLM 调用
  llm_provider?: string;
  llm_model?: string;
  tokens_used?: number;
  content_length?: number;
  // 评估
  quality_score?: number;
  consistency_score?: number;
  passed?: boolean;
  // 一致性检查
  consistency_passed?: boolean;
  consistency_issues?: string[];
  // 重写
  rewrite_attempt?: number;
  quality_issues?: string[];
  consistency_issues_2?: string[];  // 避免 naming conflict
  error?: string;
}

interface TaskState {
  // 🔥 改为按 sessionId 存储任务
  tasksBySession: Record<string, Task[]>;
  currentSessionId: string | null;
  currentTask: Task | null;
  progress: TaskProgress | null;
  stepProgress: StepProgress | null;  // 🔥 当前步骤级进度
  stepHistory: StepProgress[];  // 🔥 新增：步骤历史列表（保留最近10条）
  isLoading: boolean;
  error: string | null;

  // Actions
  setCurrentSession: (sessionId: string | null) => void;
  setTasks: (tasks: Task[]) => void;
  clearTasks: () => void;  // 🔥 新增：清除当前会话任务
  setCurrentTask: (task: Task | null) => void;
  setProgress: (progress: TaskProgress | null | ((prev: TaskProgress | null) => TaskProgress | null)) => void;
  setStepProgress: (step: StepProgress | null) => void;  // 🔥 更新：同时更新历史
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  upsertTask: (task: Task) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // 🔥 新增：获取当前会话任务的 getter
  getTasks: () => Task[];
}

export const useTaskStore = create<TaskState>((set, get) => ({
  // 🔥 按会话存储任务
  tasksBySession: {},
  currentSessionId: null,
  currentTask: null,
  progress: null,
  stepProgress: null,
  stepHistory: [],  // 🔥 初始化为空数组
  isLoading: false,
  error: null,

  // 🔥 新增：设置当前会话
  setCurrentSession: (sessionId) => {
    set({ currentSessionId: sessionId });
  },

  // 🔥 获取当前会话的任务
  getTasks: () => {
    const state = get();
    const sessionId = state.currentSessionId;
    if (!sessionId) return [];
    return state.tasksBySession[sessionId] || [];
  },

  setTasks: (tasks) => set((state) => {
    const sessionId = state.currentSessionId;
    if (!sessionId) return {};
    return {
      tasksBySession: {
        ...state.tasksBySession,
        [sessionId]: tasks,
      }
    };
  }),

  // 🔥 新增：清除当前会话任务
  clearTasks: () => set((state) => {
    const sessionId = state.currentSessionId;
    if (!sessionId) return {};
    return {
      tasksBySession: {
        ...state.tasksBySession,
        [sessionId]: [],
      }
    };
  }),

  setCurrentTask: (task) => set({ currentTask: task }),

  setProgress: (progress) => set((state) => ({
    progress: typeof progress === 'function' ? progress(state.progress) : progress
  })),

  // 🔥 更新：设置步骤进度并添加到历史
  setStepProgress: (step) => set((state) => {
    if (!step) {
      return { stepProgress: null };
    }

    // 添加时间戳
    const stepWithTimestamp = { ...step, timestamp: new Date().toISOString() };

    // 更新历史：保留最近10条
    const newHistory = [stepWithTimestamp, ...state.stepHistory].slice(0, 10);

    return {
      stepProgress: stepWithTimestamp,
      stepHistory: newHistory,
    };
  }),

  addTask: (task) =>
    set((state) => {
      const sessionId = state.currentSessionId;
      if (!sessionId) return {};
      const currentTasks = state.tasksBySession[sessionId] || [];
      return {
        tasksBySession: {
          ...state.tasksBySession,
          [sessionId]: [...currentTasks, task],
        }
      };
    }),

  updateTask: (taskId, updates) =>
    set((state) => {
      const sessionId = state.currentSessionId;
      if (!sessionId) return {};
      const currentTasks = state.tasksBySession[sessionId] || [];
      return {
        tasksBySession: {
          ...state.tasksBySession,
          [sessionId]: currentTasks.map((t) =>
            t.task_id === taskId ? { ...t, ...updates } : t
          ),
        }
      };
    }),

  upsertTask: (task) =>
    set((state) => {
      const sessionId = state.currentSessionId;
      if (!sessionId) return {};
      const currentTasks = state.tasksBySession[sessionId] || [];

      const existingIndex = currentTasks.findIndex(
        (t) => t.task_id === task.task_id
      );
      if (existingIndex >= 0) {
        const newTasks = [...currentTasks];
        newTasks[existingIndex] = task;
        return {
          tasksBySession: {
            ...state.tasksBySession,
            [sessionId]: newTasks,
          }
        };
      }
      return {
        tasksBySession: {
          ...state.tasksBySession,
          [sessionId]: [...currentTasks, task],
        }
      };
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),
}));

// 🔥 辅助函数：从 state 获取当前会话的任务
const getCurrentTasks = (state: TaskState): Task[] => {
  const sessionId = state.currentSessionId;
  if (!sessionId) return [];
  return state.tasksBySession[sessionId] || [];
};

// Selectors
export const selectTasksByChapter = (
  state: TaskState,
  chapterIndex: number
): Task[] =>
  getCurrentTasks(state).filter((t) => t.chapter_index === chapterIndex);

export const selectTasksByType = (
  state: TaskState,
  taskType: string
): Task[] =>
  getCurrentTasks(state).filter((t) => t.task_type === taskType);

export const selectPendingTasks = (state: TaskState): Task[] =>
  getCurrentTasks(state).filter((t) => t.status === 'pending');

export const selectRunningTasks = (state: TaskState): Task[] =>
  getCurrentTasks(state).filter((t) => t.status === 'running');

export const selectCompletedTasks = (state: TaskState): Task[] =>
  getCurrentTasks(state).filter((t) => t.status === 'completed');

export const selectFailedTasks = (state: TaskState): Task[] =>
  getCurrentTasks(state).filter((t) => t.status === 'failed');
