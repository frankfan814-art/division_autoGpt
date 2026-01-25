/**
 * Workspace page - main workspace with sidebar and panels
 */

import { useParams } from 'react-router-dom';
import { PreviewPanel } from '@/components/PreviewPanel';
import { ChatPanel } from '@/components/ChatPanel';
import { useTaskProgress } from '@/hooks/useTask';
import { Progress } from '@/components/ui/Progress';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useEffect, useRef } from 'react';
import { useSession } from '@/hooks/useSession';
import { useToast } from '@/components/ui/Toast';
import { getWebSocketClient } from '@/api/websocket';

export const Workspace = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { progress } = useTaskProgress(sessionId!);
  const toast = useToast();
  // Use useSession hook to properly fetch and sync session data
  const { session: currentSession } = useSession(sessionId!);
  
  // Use sessionId as key for hasStarted to reset per session
  const hasStartedRef = useRef<Record<string, boolean>>({});

  const { send: _send } = useWebSocket({
    onSessionUpdate: (data) => {
      // Backend sends: completed, failed, started, subscribed
      const { event, session_id, error } = data as any;
      
      if (session_id !== sessionId) return;
      
      if (event === 'completed') {
        toast.success('🎉 创作任务已完成！', 6000);
      } else if (event === 'failed') {
        const errorMsg = error ? `创作任务失败：${error}` : '创作任务失败，请检查错误信息';
        toast.error(`❌ ${errorMsg}`, 10000);
      } else if (event === 'started') {
        toast.success('✨ 创作任务已启动', 5000);
        if (sessionId) {
          hasStartedRef.current[sessionId] = true;
        }
      }
    },
    onTaskUpdate: (data) => {
      // Task status updated via store automatically (task_start, task_complete, task_fail)
      const { event, task } = data as any;
      console.log('Task update:', event, data);
      
      // Mark as started when first task starts
      if (event === 'task_start' && sessionId && !hasStartedRef.current[sessionId]) {
        hasStartedRef.current[sessionId] = true;
      }
      
      // Show task failure notification
      if (event === 'task_fail' && task) {
        const taskType = task.task_type || '任务';
        const errorMsg = task.error || '未知错误';
        toast.error(`❌ ${taskType} 执行失败：${errorMsg}`, 8000);
      }
    },
    onProgress: (data) => {
      // Progress updated via store automatically
      const { progress: progressData } = data as any;
      console.log('Progress update:', progressData);
    },
    onError: (data) => {
      const { message } = data as any;
      // Silently ignore "already running" error as it's expected
      if (message?.includes('already running')) {
        if (sessionId) {
          hasStartedRef.current[sessionId] = true;
        }
        return;
      }
      toast.error(message || '发生错误');
    },
  });

  // Auto-start session when entering workspace
  // Use a module-level flag to track which sessions have been started
  // This survives React StrictMode double-mounts
  useEffect(() => {
    console.log('🔍 Workspace useEffect triggered, sessionId:', sessionId);
    
    if (!sessionId) {
      console.log('❌ No sessionId, skipping auto-start');
      return;
    }
    
    // For sessions already running/completed, skip
    const sessionStatus = currentSession?.status;
    console.log('🔍 Session status:', sessionStatus);
    
    if (sessionStatus && ['running', 'completed', 'failed'].includes(sessionStatus)) {
      console.log('⏭️ Session already in progress/done, status:', sessionStatus);
      return;
    }
    
    // Check if already started for this session
    if (hasStartedRef.current[sessionId]) {
      console.log('⏭️ Session already started, skipping:', sessionId);
      return;
    }

    // Mark as started IMMEDIATELY to prevent any double execution
    // This is the key - mark it before any async operation
    hasStartedRef.current[sessionId] = true;
    console.log('✅ Marked session as started:', sessionId);

    const startSession = async () => {
      try {
        const ws = getWebSocketClient();
        console.log('📡 Got WebSocket client, checking connection...');
        
        // Wait for WebSocket to be ready (max 10 seconds)
        const maxWait = 10000;
        const startTime = Date.now();
        
        console.log('⏳ Waiting for WebSocket connection...');
        while (!ws.isConnected() && (Date.now() - startTime < maxWait)) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        if (!ws.isConnected()) {
          throw new Error('WebSocket connection timeout');
        }
        
        console.log('✅ WebSocket ready, starting session:', sessionId);

        // Send subscribe event
        const subscribeSent = ws.send({
          event: 'subscribe',
          session_id: sessionId,
        });
        console.log('📨 Subscribe event sent:', subscribeSent);
        
        if (!subscribeSent) {
          throw new Error('Failed to send subscribe event');
        }

        // Send start event immediately after subscribe
        const startSent = ws.send({
          event: 'start',
          session_id: sessionId,
        });
        console.log('🚀 Start event sent for session:', sessionId, 'success:', startSent);
        
        if (!startSent) {
          console.error('❌ Failed to send start event - WebSocket not ready');
          toast.error('启动失败，请刷新页面重试');
        }
      } catch (error) {
        console.error('❌ Failed to start session:', error);
        // Don't reset hasStartedRef - backend may have received partial request
        toast.error('启动会话失败，请刷新重试', 5000);
      }
    };

    // Execute immediately - don't use setTimeout which gets cancelled by StrictMode
    startSession();

  }, [sessionId, toast]); // Don't include currentSession to avoid re-running

  return (
    <div className="h-full flex">
      {/* Left Panel - Preview with Task Tabs */}
      <div className="flex-1 min-w-0 border-r">
        <PreviewPanel sessionId={sessionId || null} />
      </div>

      {/* Right Panel - Chat - 固定最小宽度 */}
      <div className="w-96 min-w-[320px] max-w-[400px] flex-shrink-0 flex flex-col border-l bg-gray-50">
        {/* Progress Bar */}
        <div className="p-4 border-b bg-white">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">任务进度</span>
            <span className="text-sm text-gray-500">
              {progress ? `${progress.completed_tasks}/${progress.total_tasks}` : '0/0'}
            </span>
          </div>
          <Progress 
            value={progress?.completed_tasks || 0} 
            max={progress?.total_tasks || 10} 
            size="sm" 
          />
          {progress?.current_task && (
            <div className="mt-2 space-y-1">
              <p className="text-xs text-blue-600 font-medium animate-pulse">
                ▶ 正在执行: {progress.current_task}
              </p>
              {progress.current_task_provider && (
                <p className="text-xs text-gray-500">
                  🤖 使用模型: {
                    progress.current_task_provider === 'aliyun' ? 'Aliyun Qwen' :
                    progress.current_task_provider === 'deepseek' ? 'DeepSeek' :
                    progress.current_task_provider === 'ark' ? 'Doubao' :
                    progress.current_task_provider
                  }
                </p>
              )}
            </div>
          )}
          {!progress?.current_task && (
            <p className="text-xs text-gray-400 mt-2">
              等待任务启动...
            </p>
          )}
        </div>

        {/* Chat */}
        <div className="flex-1 overflow-hidden">
          <ChatPanel sessionId={sessionId || null} />
        </div>
      </div>
    </div>
  );
};
