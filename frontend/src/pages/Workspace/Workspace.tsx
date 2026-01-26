/**
 * Workspace page - main workspace with sidebar and panels
 */

import { useState, useRef, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { PreviewPanel } from '@/components/PreviewPanel';
import { ChatPanel } from '@/components/ChatPanel';
import { StepProgress } from '@/components/StepProgress';
import { useTaskProgress } from '@/hooks/useTask';
import { Progress } from '@/components/ui/Progress';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSession } from '@/hooks/useSession';
import { useToast } from '@/components/ui/Toast';
import { getWebSocketClient } from '@/api/websocket';
import { useTaskStore } from '@/stores/taskStore';

export const Workspace = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const location = useLocation();
  const { progress } = useTaskProgress(sessionId!);
  const toast = useToast();
  const { session: currentSession } = useSession(sessionId!);
  const setCurrentSession = useTaskStore((state) => state.setCurrentSession);

  // 🔥 确认对话框状态
  const [showStartConfirm, setShowStartConfirm] = useState(false);

  // Use sessionId as key for hasStarted to reset per session
  const hasStartedRef = useRef<Record<string, boolean>>({});
  const hasPromptedRef = useRef<Record<string, boolean>>({});  // 🔥 新增：是否已经弹出过确认框

  // 🔥 设置当前会话到 taskStore
  useEffect(() => {
    if (sessionId) {
      console.log('🔄 Setting current session in taskStore:', sessionId);
      setCurrentSession(sessionId);
    }
    return () => {
      // 可选：在离开时清理当前 sessionId，或者保留以便返回时恢复
      // setCurrentSession(null);
    };
  }, [sessionId, setCurrentSession]);

  const { send: _send } = useWebSocket({
    onSessionUpdate: (data) => {
      const { event, session_id, error } = data as any;

      if (session_id !== sessionId) return;

      if (event === 'completed') {
        toast.success('🎉 创作任务已完成！', 6000);
      } else if (event === 'failed') {
        const errorMsg = error ? `创作任务失败：${error}` : '创作任务失败，请检查错误信息';
        toast.error(`❌ ${errorMsg}`, 10000);
      } else if (event === 'started') {
        toast.success('✨ 创作任务已启动', 5000);
        setShowStartConfirm(false);  // 关闭确认框
        if (sessionId) {
          hasStartedRef.current[sessionId] = true;
        }
      }
    },
    onTaskUpdate: (data) => {
      const { event, task } = data as any;
      console.log('Task update:', event, data);

      if (event === 'task_start' && sessionId && !hasStartedRef.current[sessionId]) {
        hasStartedRef.current[sessionId] = true;
      }

      if (event === 'task_fail' && task) {
        const taskType = task.task_type || '任务';
        const errorMsg = task.error || '未知错误';
        toast.error(`❌ ${taskType} 执行失败：${errorMsg}`, 8000);
      }
    },
    onProgress: (data) => {
      const { progress: progressData } = data as any;
      console.log('Progress update:', progressData);
    },
    onError: (data) => {
      const { message } = data as any;
      if (message?.includes('already running')) {
        if (sessionId) {
          hasStartedRef.current[sessionId] = true;
          setShowStartConfirm(false);  // 关闭确认框
        }
        return;
      }
      toast.error(message || '发生错误');
    },
  });

  // 🔥 启动会话的函数（提取出来，供确认对话框调用）
  const startSession = async () => {
    try {
      const ws = getWebSocketClient();
      console.log('📡 Got WebSocket client, checking connection...');

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

      const subscribeSent = ws.send({
        event: 'subscribe',
        session_id: sessionId,
      });
      console.log('📨 Subscribe event sent:', subscribeSent);

      if (!subscribeSent) {
        throw new Error('Failed to send subscribe event');
      }

      const startSent = ws.send({
        event: 'start',
        session_id: sessionId,
      });
      console.log('🚀 Start event sent for session:', sessionId, 'success:', startSent);

      if (!startSent) {
        console.error('❌ Failed to send start event - WebSocket not ready');
        toast.error('启动失败，请刷新页面重试');
        setShowStartConfirm(false);
      }
    } catch (error) {
      console.error('❌ Failed to start session:', error);
      toast.error('启动会话失败，请刷新重试', 5000);
      setShowStartConfirm(false);
    }
  };

  // 🔥 处理确认启动
  const handleConfirmStart = () => {
    if (!sessionId) return;
    hasStartedRef.current[sessionId] = true;
    hasPromptedRef.current[sessionId] = true;
    setShowStartConfirm(false);
    startSession();
  };

  // 🔥 处理取消启动
  const handleCancelStart = () => {
    setShowStartConfirm(false);
    // 清除已启动标记，允许后续手动启动
    if (sessionId) {
      hasStartedRef.current[sessionId] = false;
    }
  };

  // 🔥 检查是否应该显示确认对话框
  useEffect(() => {
    console.log('🔍 Workspace useEffect triggered, sessionId:', sessionId);

    if (!sessionId) {
      console.log('❌ No sessionId, skipping');
      return;
    }

    // 🔥 先订阅 WebSocket（无论是否启动，都需要订阅以接收更新）
    const subscribeToSession = async () => {
      try {
        const ws = getWebSocketClient();

        // 等待 WebSocket 连接
        const maxWait = 5000;
        const startTime = Date.now();
        while (!ws.isConnected() && (Date.now() - startTime < maxWait)) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        if (ws.isConnected()) {
          ws.send({
            event: 'subscribe',
            session_id: sessionId,
          });
          console.log('📨 Subscribed to session:', sessionId);
        }
      } catch (error) {
        console.error('❌ Failed to subscribe:', error);
      }
    };

    subscribeToSession();

    const sessionStatus = currentSession?.status;
    const completedTasks = currentSession?.completed_tasks || 0;
    console.log('🔍 Session status:', sessionStatus, 'completed_tasks:', completedTasks);

    // 已经运行或完成的会话，不显示确认框，也不自动启动
    if (sessionStatus && ['running', 'completed', 'failed'].includes(sessionStatus)) {
      console.log('⏭️ Session already in progress/done, status:', sessionStatus);
      return;
    }

    // 已经启动过，不重复
    if (hasStartedRef.current[sessionId]) {
      console.log('⏭️ Session already started, skipping:', sessionId);
      return;
    }

    // 已经弹出过确认框，不再重复
    if (hasPromptedRef.current[sessionId]) {
      console.log('⏭️ Already prompted user, skipping:', sessionId);
      return;
    }

    // 🔥 关键判断：区分新会话和老会话
    if (completedTasks === 0) {
      // 🆕 新会话：自动启动，不显示确认弹窗
      console.log('🚀 New session detected, auto-starting...');
      hasStartedRef.current[sessionId] = true;
      // 稍微延迟一下，确保 WebSocket 订阅完成
      setTimeout(() => {
        startSession();
      }, 500);
      return;
    }

    // 📋 老会话（有任务执行记录，现在是暂停状态）：显示确认对话框
    console.log('📋 Paused session detected, showing confirmation');
    setShowStartConfirm(true);
    hasPromptedRef.current[sessionId] = true;  // 标记已弹出

  }, [sessionId, currentSession?.status, currentSession?.completed_tasks]);

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

          {/* 🔥 详细步骤进度显示 */}
          <StepProgress />

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

      {/* 🔥 启动确认对话框 */}
      {showStartConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 mx-4">
            <h2 className="text-xl font-bold text-gray-900 mb-3">继续创作</h2>
            <p className="text-gray-600 mb-6">
              是否继续执行创作任务？AI 将开始自动创作内容。
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={handleCancelStart}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleConfirmStart}
                className="px-4 py-2 text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium"
              >
                继续创作
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
