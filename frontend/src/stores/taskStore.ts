/**
 * Task store for managing tasks
 */

import { create } from 'zustand';
import { Task, TaskProgress } from '@/types';

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  progress: TaskProgress | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setTasks: (tasks: Task[]) => void;
  setCurrentTask: (task: Task | null) => void;
  setProgress: (progress: TaskProgress | null | ((prev: TaskProgress | null) => TaskProgress | null)) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  upsertTask: (task: Task) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  currentTask: null,
  progress: null,
  isLoading: false,
  error: null,

  setTasks: (tasks) => set({ tasks }),

  setCurrentTask: (task) => set({ currentTask: task }),

  setProgress: (progress) => set((state) => ({ 
    progress: typeof progress === 'function' ? progress(state.progress) : progress 
  })),

  addTask: (task) =>
    set((state) => ({
      tasks: [...state.tasks, task],
    })),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.task_id === taskId ? { ...t, ...updates } : t
      ),
    })),

  upsertTask: (task) =>
    set((state) => {
      console.log('🔄 upsertTask called:', task.task_id, task.task_type, 'Current tasks count:', state.tasks.length);
      const existingIndex = state.tasks.findIndex(
        (t) => t.task_id === task.task_id
      );
      if (existingIndex >= 0) {
        console.log('✏️ Updating existing task at index:', existingIndex);
        const newTasks = [...state.tasks];
        newTasks[existingIndex] = task;
        console.log('✅ Updated tasks count:', newTasks.length);
        return { tasks: newTasks };
      }
      console.log('➕ Adding new task, new count will be:', state.tasks.length + 1);
      const newTasks = [...state.tasks, task];
      console.log('✅ New tasks count:', newTasks.length);
      return { tasks: newTasks };
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),
}));

// Selectors
export const selectTasksByChapter = (
  state: TaskState,
  chapterIndex: number
): Task[] =>
  state.tasks.filter((t) => t.chapter_index === chapterIndex);

export const selectTasksByType = (
  state: TaskState,
  taskType: string
): Task[] =>
  state.tasks.filter((t) => t.task_type === taskType);

export const selectPendingTasks = (state: TaskState): Task[] =>
  state.tasks.filter((t) => t.status === 'pending');

export const selectRunningTasks = (state: TaskState): Task[] =>
  state.tasks.filter((t) => t.status === 'running');

export const selectCompletedTasks = (state: TaskState): Task[] =>
  state.tasks.filter((t) => t.status === 'completed');

export const selectFailedTasks = (state: TaskState): Task[] =>
  state.tasks.filter((t) => t.status === 'failed');
