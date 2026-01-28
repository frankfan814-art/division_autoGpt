/**
 * CollapsibleSidebar - 可折叠侧边栏
 *
 * 整合原 Overview 和 Sidebar 的功能：
 * - 会话信息展示
 * - 快捷操作（启动/暂停/停止）
 * - 统计信息（任务进度、耗时、LLM调用）
 * - 系统状态
 */

import { Link, useParams } from 'react-router-dom';
import React, { useEffect } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import { useTaskProgress } from '@/hooks/useTask';
import { useTaskStore } from '@/stores/taskStore';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { getWebSocketClient } from '@/api/websocket';
import {
  Sparkles,
  ArrowLeft,
  Play,
  Pause,
  Square,
  Clock,
} from 'lucide-react';

interface CollapsibleSidebarProps {
  className?: string;
}

export const CollapsibleSidebar = ({ className = '' }: CollapsibleSidebarProps) => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const currentSession = useSessionStore((state) => state.currentSession);
  const { progress } = useTaskProgress(sessionId!);
  const setCurrentSession = useTaskStore((state) => state.setCurrentSession);

  // 设置当前会话到 taskStore
  useEffect(() => {
    if (sessionId) {
      setCurrentSession(sessionId);
    }
  }, [sessionId, setCurrentSession]);

  // 控制操作
  const handleStart = () => {
    if (!sessionId) return;
    const ws = getWebSocketClient();
    ws.send({ event: 'start', session_id: sessionId });
  };

  const handlePause = () => {
    if (!sessionId) return;
    const ws = getWebSocketClient();
    ws.send({ event: 'pause', session_id: sessionId });
  };

  const handleStop = () => {
    if (!sessionId) return;
    const ws = getWebSocketClient();
    ws.send({ event: 'stop', session_id: sessionId });
  };

  const statusConfig = {
    running: { color: 'info', label: '运行中' },
    completed: { color: 'success', label: '已完成' },
    failed: { color: 'danger', label: '失败' },
    paused: { color: 'warning', label: '已暂停' },
    created: { color: 'default', label: '已创建' },
  };

  const currentStatus = currentSession?.status || 'created';
  const statusInfo = statusConfig[currentStatus as keyof typeof statusConfig] || statusConfig.created;
  const progressPercentage = currentSession?.total_tasks
    ? (currentSession.completed_tasks / currentSession.total_tasks) * 100
    : 0;

  // 判断是否全部完成
  const isAllCompleted = currentStatus === 'completed' ||
    progress?.is_completed === true ||
    (currentSession?.total_tasks && currentSession.completed_tasks >= currentSession.total_tasks);

  return (
    <aside className={`bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col h-full ${className}`}>
      {/* Session Info */}
      {currentSession && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate text-sm">
                {currentSession.title}
              </h3>
              <div className="flex items-center gap-2 mt-1.5">
                <Badge variant={statusInfo.color as any} size="sm">
                  {statusInfo.label}
                </Badge>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {currentSession.total_tasks > 0 && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1.5">
                <span>{progressPercentage >= 100 ? '✅ 已完成' : '任务进度'}</span>
                <span>{currentSession.completed_tasks}/{currentSession.total_tasks}</span>
              </div>
              <Progress
                value={currentSession.completed_tasks}
                max={currentSession.total_tasks}
                size="sm"
              />
            </div>
          )}
        </div>
      )}

      {/* Quick Actions */}
      {currentSession && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <p className="text-xs font-medium text-gray-500 uppercase mb-3">快捷操作</p>
          <div className="flex flex-col gap-2">
            {currentStatus === 'paused' || currentStatus === 'created' ? (
              <button
                onClick={handleStart}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                <Play className="w-4 h-4" />
                开始创作
              </button>
            ) : currentStatus === 'running' ? (
              <>
                <button
                  onClick={handlePause}
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  <Pause className="w-4 h-4" />
                  暂停
                </button>
                <button
                  onClick={handleStop}
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                >
                  <Square className="w-4 h-4" />
                  停止
                </button>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* Statistics */}
      {currentSession && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex-1 overflow-y-auto">
          <p className="text-xs font-medium text-gray-500 uppercase mb-3">统计信息</p>

          {/* Task Stats */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg text-center">
              <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                {currentSession.total_tasks}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">总任务</p>
            </div>
            <div className={`${isAllCompleted ? 'bg-green-100 dark:bg-green-900/30' : 'bg-green-50 dark:bg-green-900/20'} p-3 rounded-lg text-center`}>
              <p className="text-xl font-bold text-green-600 dark:text-green-400">
                {currentSession.completed_tasks}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">已完成</p>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg text-center">
              <p className="text-xl font-bold text-red-600 dark:text-red-400">
                {currentSession.failed_tasks || 0}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">失败</p>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg text-center">
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {currentSession.llm_calls || 0}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">LLM调用</p>
            </div>
          </div>

          {/* Current Task */}
          {!isAllCompleted && progress?.current_task && (
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300">当前任务</p>
                <TaskTimer startedAt={progress.task_started_at} />
              </div>
              <p className="text-sm text-blue-800 dark:text-blue-300 font-medium line-clamp-2">
                {progress.current_task}
              </p>
            </div>
          )}

          {/* Goal Info */}
          {currentSession.goal && Object.keys(currentSession.goal).length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-gray-500 mb-2">项目目标</p>
              <dl className="space-y-2 text-sm">
                {currentSession.goal.genre && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">类型</span>
                    <span className="text-gray-900 dark:text-gray-100">{currentSession.goal.genre}</span>
                  </div>
                )}
                {currentSession.goal.chapter_count && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">章节</span>
                    <span className="text-gray-900 dark:text-gray-100">{currentSession.goal.chapter_count}章</span>
                  </div>
                )}
                {currentSession.goal.word_count && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">字数</span>
                    <span className="text-gray-900 dark:text-gray-100">
                      {currentSession.goal.word_count >= 10000
                        ? `${currentSession.goal.word_count / 10000}万字`
                        : `${currentSession.goal.word_count}字`}
                    </span>
                  </div>
                )}
              </dl>
            </div>
          )}
        </div>
      )}

      {/* Footer - Back to Sessions */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <Link
          to="/sessions"
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>返回会话列表</span>
        </Link>
      </div>
    </aside>
  );
};

// 任务计时器组件
const TaskTimer = ({ startedAt }: { startedAt?: string }) => {
  const [elapsed, setElapsed] = React.useState(0);

  React.useEffect(() => {
    if (!startedAt) {
      setElapsed(0);
      return;
    }

    const startTime = new Date(startedAt).getTime();

    const updateElapsed = () => {
      const now = Date.now();
      setElapsed(Math.floor((now - startTime) / 1000));
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);

    return () => clearInterval(interval);
  }, [startedAt]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) {
      return `${mins}分${secs}秒`;
    }
    return `${secs}秒`;
  };

  if (!startedAt || elapsed === 0) return null;

  return (
    <span className="text-xs text-gray-500 flex items-center gap-1">
      <Clock className="w-3 h-3" />
      {formatTime(elapsed)}
    </span>
  );
};
