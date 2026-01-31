/**
 * WebSocket hook for real-time communication
 */

import { useEffect, useRef, useCallback } from 'react';
import { getWebSocketClient, WebSocketEventHandler } from '@/api/websocket';
import { useSessionStore } from '@/stores/sessionStore';
import { useTaskStore } from '@/stores/taskStore';
import logger from '@/utils/logger';

export interface UseWebSocketOptions {
  onSessionUpdate?: WebSocketEventHandler;
  onTaskUpdate?: WebSocketEventHandler;
  onProgress?: WebSocketEventHandler;
  onStepProgress?: WebSocketEventHandler;  // 🔥 新增
  onError?: WebSocketEventHandler;
  onMessage?: WebSocketEventHandler;
  autoConnect?: boolean;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    onSessionUpdate,
    onTaskUpdate,
    onProgress,
    onStepProgress,  // 🔥 新增
    onError,
    onMessage,
    autoConnect = true,
  } = options;

  const wsRef = useRef<ReturnType<typeof getWebSocketClient> | null>(null);
  const updateSession = useSessionStore((state) => state.updateSession);
  const upsertTask = useTaskStore((state) => state.upsertTask);
  const setProgress = useTaskStore((state) => state.setProgress);
  const setStepProgress = useTaskStore((state) => state.setStepProgress);  // 🔥 新增

  // Initialize WebSocket connection
  useEffect(() => {
    if (!autoConnect) return;

    const ws = getWebSocketClient();
    wsRef.current = ws;

    // Subscribe to backend events
    // Backend sends: task_start, task_complete, progress, started, completed, failed, subscribed
    
    const unsubscribeTaskStart = ws.subscribe('task_start', (data) => {
      const { task } = data as any;
      if (task) {
        logger.debug('📋 Task started:', task.task_type, 'using', task.llm_provider);
        logger.debug('📋 Full task object:', task);
        logger.debug('📋 Calling upsertTask with:', task);
        // 🔥 调试：检查 prompt 是否存在
        logger.debug('🔍 Task metadata.prompt exists:', !!task.metadata?.prompt);
        logger.debug('🔍 Task prompt exists:', !!task.prompt);
        if (task.metadata?.prompt) {
          logger.debug('📝 Prompt length:', task.metadata.prompt.length);
        }
        upsertTask(task);
        // Update progress with current task info (preserve existing progress data)
        setProgress((prev: any) => {
          if (!prev) {
            // If no progress yet, create minimal object with current task info
            return {
              session_id: '',
              status: 'running',
              total_tasks: 0,
              completed_tasks: 0,
              failed_tasks: 0,
              percentage: 0,
              current_task: task.task_type,
              current_task_provider: task.llm_provider,
              current_task_model: task.llm_model,
              task_started_at: task.metadata?.started_at,
              retry_count: task.metadata?.retry_count || 0,
            };
          }
          // Merge with existing progress
          const updated = {
            ...prev,
            current_task: task.task_type,
            current_task_provider: task.llm_provider,
            current_task_model: task.llm_model,
            task_started_at: task.metadata?.started_at,
            retry_count: task.metadata?.retry_count || 0,
          };
          logger.debug('📊 Updated progress after task_start:', updated);
          return updated;
        });
      }
      onTaskUpdate?.(data);
    });

    const unsubscribeTaskComplete = ws.subscribe('task_complete', (data) => {
      const { task } = data as any;
      if (task) {
        logger.debug('✅ Task complete event received for:', task.task_type);
        logger.debug('✅ Task complete stats:', JSON.stringify({
          execution_time_seconds: task.execution_time_seconds,
          total_tokens: task.total_tokens,
          prompt_tokens: task.prompt_tokens,
          completion_tokens: task.completion_tokens,
          cost_usd: task.cost_usd,
          failed_attempts: task.failed_attempts,
        }));
        // 🔥 调试：检查 prompt 是否存在
        logger.debug('🔍 Task metadata.prompt exists:', !!task.metadata?.prompt);
        logger.debug('🔍 Task prompt exists:', !!task.prompt);
        if (task.metadata?.prompt) {
          logger.debug('📝 Prompt length:', task.metadata.prompt.length);
        }
        upsertTask(task);
      }
      onTaskUpdate?.(data);
    });

    // Subscribe to task failure events
    const unsubscribeTaskFail = ws.subscribe('task_fail', (data) => {
      const { task } = data as any;
      if (task) {
        logger.error('❌ Task failed:', task.task_type, task.error);
        upsertTask(task);
      }
      onTaskUpdate?.(data);
    });

    // Subscribe to task approval needed events
    const unsubscribeTaskApprovalNeeded = ws.subscribe('task_approval_needed', (data) => {
      const { task } = data as any;
      if (task) {
        logger.debug('⏸️ Task needs approval:', task.task_type);
        upsertTask(task);
      }
      onTaskUpdate?.(data);
    });

    // Subscribe to progress updates
    const unsubscribeProgress = ws.subscribe('progress', (data) => {
      const { progress: progressData } = data as any;
      logger.debug('📊 Progress event received:', progressData);
      if (progressData) {
        setProgress(progressData);
      }
      onProgress?.(data);
    });

    // 🔥 Subscribe to step progress updates (详细步骤进度)
    const unsubscribeStepProgress = ws.subscribe('step_progress', (data) => {
      const { step } = data as any;
      logger.debug('📍 Step progress event received:', step);
      if (step) {
        setStepProgress(step);
      }
      onStepProgress?.(data);
    });

    // 🔥 新增：章节进度事件 (章节生成进度)
    ws.subscribe('chapter_progress', (data) => {
      const { chapter_index, status, progress } = data as any;
      logger.debug('📖 Chapter progress:', chapter_index, status, progress);
      // 更新进度状态，添加章节信息
      setProgress((prev: any) => ({
        ...prev,
        current_chapter: chapter_index,
        current_chapter_status: status,
        current_chapter_progress: progress,
      }));
      onProgress?.(data);
    });

    // 🔥 新增：章节完成事件
    ws.subscribe('chapter_completed', (data) => {
      const { chapter_index, status, score } = data as any;
      logger.debug('✅ Chapter completed:', chapter_index, status, score);
      // 更新任务存储中的章节信息
      onTaskUpdate?.(data);
    });

    // 🔥 新增：重写尝试事件
    ws.subscribe('rewrite_attempt', (data) => {
      const { chapter_index, attempt, score, issues } = data as any;
      logger.debug('🔄 Rewrite attempt:', chapter_index, attempt, score);
      // 更新进度状态，添加重写信息
      setProgress((prev: any) => ({
        ...prev,
        is_rewriting: true,
        rewrite_attempt: attempt,
        rewrite_score: score,
        rewrite_issues: issues,
      }));
      onProgress?.(data);
    });

    // Subscribe to session status events
    const unsubscribeCompleted = ws.subscribe('completed', (data) => {
      const { session_id, stats } = data as any;
      if (session_id) {
        updateSession(session_id, { status: 'completed' });
        // 同时更新 progress 为已完成状态
        setProgress((prev: any) => ({
          ...prev,
          status: 'completed',
          is_completed: true,
          completed_tasks: stats?.completed_tasks || prev?.total_tasks || 0,
          percentage: 100,
          current_task: null,
        }));
        logger.debug('🎉 Session completed!', session_id);
      }
      onSessionUpdate?.(data);
    });

    const unsubscribeFailed = ws.subscribe('failed', (data) => {
      const { session_id } = data as any;
      if (session_id) {
        updateSession(session_id, { status: 'failed' });
      }
      onSessionUpdate?.(data);
    });

    const unsubscribeStarted = ws.subscribe('started', (data) => {
      const { session_id } = data as any;
      if (session_id) {
        updateSession(session_id, { status: 'running' });
      }
      onSessionUpdate?.(data);
    });

    const unsubscribeSubscribed = ws.subscribe('subscribed', (data) => {
      // Connection confirmed, initialize progress if provided
      const { progress: initialProgress } = data as any;
      if (initialProgress) {
        logger.debug('📊 Initial progress:', initialProgress);
        setProgress(initialProgress);
      }
      onSessionUpdate?.(data);
    });

    // Subscribe to errors
    const unsubscribeError = ws.subscribe('error', (data) => {
      logger.error('WebSocket error event:', data);
      onError?.(data);
    });

    // Generic message handler
    const unsubscribeMessage = ws.subscribe('message', (data) => {
      onMessage?.(data);
    });

    // Connection is already managed by the global singleton
    // No need to call connect() here

    return () => {
      unsubscribeTaskStart();
      unsubscribeTaskComplete();
      unsubscribeTaskFail();
      unsubscribeTaskApprovalNeeded();
      unsubscribeProgress();
      unsubscribeStepProgress();
      unsubscribeCompleted();
      unsubscribeFailed();
      unsubscribeStarted();
      unsubscribeSubscribed();
      unsubscribeError();
      unsubscribeMessage();
    };
  }, [autoConnect, onSessionUpdate, onTaskUpdate, onProgress, onStepProgress, onError, onMessage]);

  const send = useCallback((data: any) => {
    wsRef.current?.send(data);
  }, []);

  const sendFeedback = useCallback((feedback: { message: string; scope?: string }) => {
    send({
      event: 'feedback',
      data: feedback,
    });
  }, [send]);

  const getSessionId = useCallback(() => {
    return wsRef.current?.getSessionId() || null;
  }, []);

  return {
    send,
    sendFeedback,
    getSessionId,
  };
};
