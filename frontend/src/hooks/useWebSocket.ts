/**
 * WebSocket hook for real-time communication
 */

import { useEffect, useRef, useCallback } from 'react';
import { getWebSocketClient, WebSocketEventHandler } from '@/api/websocket';
import { useSessionStore } from '@/stores/sessionStore';
import { useTaskStore } from '@/stores/taskStore';

export interface UseWebSocketOptions {
  onSessionUpdate?: WebSocketEventHandler;
  onTaskUpdate?: WebSocketEventHandler;
  onProgress?: WebSocketEventHandler;
  onError?: WebSocketEventHandler;
  onMessage?: WebSocketEventHandler;
  autoConnect?: boolean;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    onSessionUpdate,
    onTaskUpdate,
    onProgress,
    onError,
    onMessage,
    autoConnect = true,
  } = options;

  const wsRef = useRef<ReturnType<typeof getWebSocketClient> | null>(null);
  const updateSession = useSessionStore((state) => state.updateSession);
  const upsertTask = useTaskStore((state) => state.upsertTask);
  const setProgress = useTaskStore((state) => state.setProgress);

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
        console.log('📋 Task started:', task.task_type, 'using', task.llm_provider);
        console.log('📋 Full task object:', task);
        console.log('📋 Calling upsertTask with:', task);
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
          console.log('📊 Updated progress after task_start:', updated);
          return updated;
        });
      }
      onTaskUpdate?.(data);
    });

    const unsubscribeTaskComplete = ws.subscribe('task_complete', (data) => {
      const { task } = data as any;
      if (task) {
        console.log('✅ Task complete event received for:', task.task_type);
        console.log('✅ Task complete stats:', JSON.stringify({
          execution_time_seconds: task.execution_time_seconds,
          total_tokens: task.total_tokens,
          prompt_tokens: task.prompt_tokens,
          completion_tokens: task.completion_tokens,
          cost_usd: task.cost_usd,
          failed_attempts: task.failed_attempts,
        }));
        upsertTask(task);
      }
      onTaskUpdate?.(data);
    });

    // Subscribe to task failure events
    const unsubscribeTaskFail = ws.subscribe('task_fail', (data) => {
      const { task } = data as any;
      if (task) {
        console.error('❌ Task failed:', task.task_type, task.error);
        upsertTask(task);
      }
      onTaskUpdate?.(data);
    });

    // Subscribe to task approval needed events
    const unsubscribeTaskApprovalNeeded = ws.subscribe('task_approval_needed', (data) => {
      const { task } = data as any;
      if (task) {
        console.log('⏸️ Task needs approval:', task.task_type);
        upsertTask(task);
      }
      onTaskUpdate?.(data);
    });

    // Subscribe to progress updates
    const unsubscribeProgress = ws.subscribe('progress', (data) => {
      const { progress: progressData } = data as any;
      console.log('📊 Progress event received:', progressData);
      if (progressData) {
        setProgress(progressData);
      }
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
        console.log('🎉 Session completed!', session_id);
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
        console.log('📊 Initial progress:', initialProgress);
        setProgress(initialProgress);
      }
      onSessionUpdate?.(data);
    });

    // Subscribe to errors
    const unsubscribeError = ws.subscribe('error', (data) => {
      console.error('WebSocket error event:', data);
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
      unsubscribeCompleted();
      unsubscribeFailed();
      unsubscribeStarted();
      unsubscribeSubscribed();
      unsubscribeError();
      unsubscribeMessage();
    };
  }, [autoConnect, onSessionUpdate, onTaskUpdate, onProgress, onError, onMessage]);

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
