/**
 * Task hook for task management
 */

import { useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { sessionsApi } from '@/api/client';
import { useTaskStore } from '@/stores/taskStore';
import logger from '@/utils/logger';

export const useTasks = (sessionId: string, params?: { task_type?: string; chapter_index?: number }) => {
  const { getTasks, upsertTask, setLoading, setError } = useTaskStore();  // 🔥 修复：使用 getTasks

  const { data: tasks, isLoading, error, refetch } = useQuery({
    queryKey: ['tasks', sessionId, params],
    queryFn: () => sessionsApi.getTasks(sessionId, params),
    enabled: !!sessionId,
    staleTime: 3000,
  });

  const storeTasks = getTasks();  // 🔥 获取当前会话任务

  useEffect(() => {
    logger.debug('📦 useTasks received from API:', tasks?.length || 0, 'tasks');
    logger.debug('📦 Current store has:', storeTasks.length, 'tasks');
    if (tasks && tasks.length > 0) {
      // Merge API tasks with store tasks (upsert each task to preserve WebSocket updates)
      logger.debug('📦 Merging API tasks into store...');
      tasks.forEach(task => upsertTask(task, sessionId));  // 🔥 传递 sessionId 参数
    }
    setLoading(isLoading);
    setError(error?.message || null);
  }, [tasks, isLoading, error, upsertTask, setLoading, setError, sessionId]);  // 🔥 添加 sessionId 依赖

  logger.debug('📦 useTasks returning:', storeTasks.length, 'tasks');
  return {
    tasks: storeTasks, // Return tasks from store, not from API
    isLoading,
    error: error?.message || null,
    refetch,
  };
};

export const useTaskProgress = (_sessionId: string) => {
  const { progress } = useTaskStore();

  // Progress is now updated via WebSocket (through useWebSocket hook)
  // No need for HTTP polling anymore

  return {
    progress,
    isLoading: false,
    error: null,
    refetch: () => Promise.resolve(), // No-op, progress comes from WebSocket
  };
};

// Helper hook for filtering tasks
export const useFilteredTasks = () => {
  const tasks = useTaskStore((state) => state.getTasks());  // 🔥 修复：使用 getTasks()

  const getTasksByChapter = useCallback((chapterIndex: number) => {
    return tasks.filter((t) => t.chapter_index === chapterIndex);
  }, [tasks]);

  const getTasksByType = useCallback((taskType: string) => {
    return tasks.filter((t) => t.task_type === taskType);
  }, [tasks]);

  const getTasksByStatus = useCallback((status: string) => {
    return tasks.filter((t) => t.status === status);
  }, [tasks]);

  const getPendingTasks = useCallback(() => {
    return tasks.filter((t) => t.status === 'pending');
  }, [tasks]);

  const getRunningTasks = useCallback(() => {
    return tasks.filter((t) => t.status === 'running');
  }, [tasks]);

  const getCompletedTasks = useCallback(() => {
    return tasks.filter((t) => t.status === 'completed');
  }, [tasks]);

  const getFailedTasks = useCallback(() => {
    return tasks.filter((t) => t.status === 'failed');
  }, [tasks]);

  return {
    allTasks: tasks,
    getTasksByChapter,
    getTasksByType,
    getTasksByStatus,
    getPendingTasks,
    getRunningTasks,
    getCompletedTasks,
    getFailedTasks,
  };
};
