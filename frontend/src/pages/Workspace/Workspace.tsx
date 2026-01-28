/**
 * Workspace - 统一工作区页面
 *
 * 整合所有功能到一个页面，使用 ResizablePanels 实现可调整大小的面板布局
 * - 侧边栏：会话信息和快捷操作
 * - 主面板：预览/任务/阅读（通过标签切换）
 * - 聊天面板：用户反馈
 */

import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useLayoutStore } from '@/stores/layoutStore';
import { ResizablePanels } from '@/components/layout/ResizablePanels';
import { CollapsibleSidebar } from '@/components/layout/CollapsibleSidebar';
import { PanelTabBar } from '@/components/layout/PanelTabBar';
import { PreviewPanel } from '@/components/PreviewPanel';
import { TaskListPanel } from '@/components/TaskListPanel';
import { ReaderPanel } from '@/components/ReaderPanel';
import { SettingsPanel } from '@/components/SettingsPanel';
import { ChatPanel } from '@/components/ChatPanel';
import { StepProgress } from '@/components/StepProgress';
import { Progress } from '@/components/ui/Progress';
import { useTaskProgress } from '@/hooks/useTask';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useToast } from '@/components/ui/Toast';
import { getWebSocketClient } from '@/api/websocket';
import { useTaskStore } from '@/stores/taskStore';

export const Workspace = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { progress } = useTaskProgress(sessionId!);
  const toast = useToast();
  const { session: currentSession } = useSession(sessionId!);
  const setCurrentSession = useTaskStore((state) => state.setCurrentSession);
  const { activePanelTab } = useLayoutStore();

  // 确认对话框状态
  const [showStartConfirm, setShowStartConfirm] = useState(false);

  // Use sessionId as key for hasStarted to reset per session
  const hasStartedRef = useRef<Record<string, boolean>>({});
  const hasPromptedRef = useRef<Record<string, boolean>>({});

  // 设置当前会话到 taskStore
  useEffect(() => {
    if (sessionId) {
      logger.debug('🔄 Setting current session in taskStore:', sessionId);
      setCurrentSession(sessionId);
    }
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
        setShowStartConfirm(false);
        if (sessionId) {
          hasStartedRef.current[sessionId] = true;
        }
      }
    },
    onTaskUpdate: (data) => {
      const { event, task } = data as any;
      logger.debug('Task update:', event, data);

      if (event === 'task_start' && sessionId && !hasStartedRef.current[sessionId]) {
        hasStartedRef.current[sessionId] = true;
      }

      if (event === 'task_fail' && task) {
        const taskType = task.task_type || '任务';
        const errorMsg = task.error || '未知错误';
        toast.error(`❌ ${taskType} 执行失败：${errorMsg}`, 8000);
      }
    },
    onError: (data) => {
      const { message } = data as any;
      if (message?.includes('already running')) {
        if (sessionId) {
          hasStartedRef.current[sessionId] = true;
          setShowStartConfirm(false);
        }
        return;
      }
      toast.error(message || '发生错误');
    },
  });

  // 启动会话的函数
  const startSession = async () => {
    try {
      const ws = getWebSocketClient();
      logger.debug('📡 Got WebSocket client, checking connection...');

      const maxWait = 10000;
      const startTime = Date.now();

      logger.debug('⏳ Waiting for WebSocket connection...');
      while (!ws.isConnected() && (Date.now() - startTime < maxWait)) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      if (!ws.isConnected()) {
        throw new Error('WebSocket connection timeout');
      }

      logger.debug('✅ WebSocket ready, starting session:', sessionId);

      ws.send({
        event: 'subscribe',
        session_id: sessionId,
      });

      ws.send({
        event: 'start',
        session_id: sessionId,
      });

      logger.debug('🚀 Start event sent for session:', sessionId);
    } catch (error) {
      logger.error('❌ Failed to start session:', error);
      toast.error('启动会话失败，请刷新重试', 5000);
      setShowStartConfirm(false);
    }
  };

  // 处理确认启动
  const handleConfirmStart = () => {
    if (!sessionId) return;
    hasStartedRef.current[sessionId] = true;
    hasPromptedRef.current[sessionId] = true;
    setShowStartConfirm(false);
    startSession();
  };

  // 处理取消启动
  const handleCancelStart = () => {
    setShowStartConfirm(false);
    if (sessionId) {
      hasStartedRef.current[sessionId] = false;
    }
  };

  // 检查是否应该显示确认对话框
  useEffect(() => {
    logger.debug('🔍 Workspace useEffect triggered, sessionId:', sessionId);

    if (!sessionId) {
      logger.debug('❌ No sessionId, skipping');
      return;
    }

    // 先订阅 WebSocket
    const subscribeToSession = async () => {
      try {
        const ws = getWebSocketClient();

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
          logger.debug('📨 Subscribed to session:', sessionId);
        }
      } catch (error) {
        logger.error('❌ Failed to subscribe:', error);
      }
    };

    subscribeToSession();

    const sessionStatus = currentSession?.status;
    const completedTasks = currentSession?.completed_tasks || 0;
    logger.debug('🔍 Session status:', sessionStatus, 'completed_tasks:', completedTasks);

    // 已经运行或完成的会话，不显示确认框，也不自动启动
    if (sessionStatus && ['running', 'completed', 'failed'].includes(sessionStatus)) {
      logger.debug('⏭️ Session already in progress/done, status:', sessionStatus);
      return;
    }

    // 已经启动过，不重复
    if (hasStartedRef.current[sessionId]) {
      logger.debug('⏭️ Session already started, skipping:', sessionId);
      return;
    }

    // 已经弹出过确认框，不再重复
    if (hasPromptedRef.current[sessionId]) {
      logger.debug('⏭️ Already prompted user, skipping:', sessionId);
      return;
    }

    // 新会话：自动启动，不显示确认弹窗
    if (completedTasks === 0) {
      logger.debug('🚀 New session detected, auto-starting...');
      hasStartedRef.current[sessionId] = true;
      setTimeout(() => {
        startSession();
      }, 500);
      return;
    }

    // 老会话（有任务执行记录，现在是暂停状态）：显示确认对话框
    logger.debug('📋 Paused session detected, showing confirmation');
    setShowStartConfirm(true);
    hasPromptedRef.current[sessionId] = true;

  }, [sessionId, currentSession?.status, currentSession?.completed_tasks]);

  // 渲染主面板内容
  const renderMainPanel = () => {
    if (!sessionId) return null;

    switch (activePanelTab) {
      case 'preview':
        return <PreviewPanel sessionId={sessionId} />;
      case 'tasks':
        return <TaskListPanel sessionId={sessionId} />;
      case 'reader':
        return <ReaderPanel sessionId={sessionId} />;
      case 'settings':
        return <SettingsPanel sessionId={sessionId} />;
      default:
        return <PreviewPanel sessionId={sessionId} />;
    }
  };

  // 渲染聊天面板（包含进度显示）
  const renderChatPanel = () => {
    if (!sessionId) return null;

    return (
      <div className="h-full flex flex-col bg-gray-50">
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

          {/* 详细步骤进度显示 */}
          <StepProgress />

          {!progress?.current_task && (
            <p className="text-xs text-gray-400 mt-2">
              等待任务启动...
            </p>
          )}
        </div>

        {/* Chat */}
        <div className="flex-1 overflow-hidden">
          <ChatPanel sessionId={sessionId} />
        </div>
      </div>
    );
  };

  if (!sessionId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        请选择一个会话
      </div>
    );
  }

  return (
    <>
      <ResizablePanels
        sidebar={<CollapsibleSidebar />}
        main={renderMainPanel()}
        chat={renderChatPanel()}
        panelTabs={<PanelTabBar />}
      />

      {/* 启动确认对话框 */}
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
    </>
  );
};

// 修复 useSession hook 引用
import { useSession } from '@/hooks/useSession';
import logger from '@/utils/logger';
