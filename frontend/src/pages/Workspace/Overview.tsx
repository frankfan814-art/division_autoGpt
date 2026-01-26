/**
 * Overview page for workspace
 */

import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useSession } from '@/hooks/useSession';
import { useTaskProgress } from '@/hooks/useTask';
import { Progress } from '@/components/ui/Progress';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useSessionStore } from '@/stores/sessionStore';
import { useTaskStore } from '@/stores/taskStore';  // 🔥 新增

export const Overview = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { session, isLoading } = useSession(sessionId!);
  const { progress } = useTaskProgress(sessionId!);
  const setCurrentSession = useTaskStore((state) => state.setCurrentSession);  // 🔥 新增

  // 🔥 新增：设置当前会话到 taskStore
  useEffect(() => {
    if (sessionId) {
      console.log('🔄 Overview: Setting current session:', sessionId);
      setCurrentSession(sessionId);
    }
  }, [sessionId, setCurrentSession]);

  const pauseSession = useSessionStore((state) => state.updateSession);

  const handlePause = async () => {
    if (!sessionId) return;
    // Trigger pause via API
    pauseSession(sessionId, { status: 'paused' });
  };

  const handleResume = async () => {
    if (!sessionId) return;
    // Trigger resume via API
    pauseSession(sessionId, { status: 'running' });
  };

  if (isLoading || !session) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-400">加载中...</div>
      </div>
    );
  }

  const progressPercentage = session.total_tasks > 0
    ? (session.completed_tasks / session.total_tasks) * 100
    : 0;
  
  // 判断是否全部完成 - 从多个来源判断
  const isAllCompleted = session.status === 'completed' || 
    progress?.is_completed === true ||
    progress?.status === 'completed' ||
    (session.total_tasks > 0 && session.completed_tasks >= session.total_tasks);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 全部完成提示 */}
        {isAllCompleted && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
            <div className="text-4xl mb-3">🎉</div>
            <h2 className="text-xl font-bold text-green-800 mb-2">创作任务已全部完成！</h2>
            <p className="text-green-600">
              共完成 {session.completed_tasks} 个任务，耗时 {session.llm_calls} 次 LLM 调用
            </p>
          </div>
        )}

        {/* Session Info */}
        <div className="bg-white rounded-lg border shadow-sm p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{session.title}</h1>
              <p className="text-gray-500 mt-1">
                创建于 {new Date(session.created_at).toLocaleString('zh-CN')}
              </p>
            </div>
            <Badge variant={
              session.status === 'running' ? 'info' :
              session.status === 'completed' ? 'success' :
              session.status === 'failed' ? 'danger' :
              session.status === 'paused' ? 'warning' : 'default'
            }>
              {session.status === 'running' ? '运行中' :
               session.status === 'completed' ? '✅ 已全部完成' :
               session.status === 'failed' ? '失败' :
               session.status === 'paused' ? '已暂停' : '已创建'}
            </Badge>
          </div>

          {/* Progress */}
          <div className="mb-4">
            <Progress
              value={session.completed_tasks}
              max={session.total_tasks}
              showLabel
              label={isAllCompleted ? "✅ 已全部完成" : "任务进度"}
              color={isAllCompleted ? 'green' : progressPercentage >= 50 ? 'blue' : 'yellow'}
            />
            {isAllCompleted && (
              <p className="text-sm text-green-600 mt-1 text-center">
                🎊 所有 {session.total_tasks} 个任务已完成！
              </p>
            )}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-50 p-3 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-900">{session.total_tasks}</p>
              <p className="text-sm text-gray-500">总任务</p>
            </div>
            <div className={`${isAllCompleted ? 'bg-green-100' : 'bg-green-50'} p-3 rounded-lg text-center`}>
              <p className="text-2xl font-bold text-green-600">{session.completed_tasks}</p>
              <p className="text-sm text-gray-500">已完成</p>
            </div>
            <div className="bg-red-50 p-3 rounded-lg text-center">
              <p className="text-2xl font-bold text-red-600">{session.failed_tasks}</p>
              <p className="text-sm text-gray-500">失败</p>
            </div>
            <div className="bg-blue-50 p-3 rounded-lg text-center">
              <p className="text-2xl font-bold text-blue-600">{session.llm_calls}</p>
              <p className="text-sm text-gray-500">LLM调用</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 mt-6">
            {session.status === 'running' && (
              <Button onClick={handlePause} variant="secondary">
                暂停
              </Button>
            )}
            {session.status === 'paused' && (
              <Button onClick={handleResume} variant="primary">
                继续
              </Button>
            )}
          </div>
        </div>

        {/* Goal Info */}
        {session.goal && Object.keys(session.goal).length > 0 && (
          <div className="bg-white rounded-lg border shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">项目目标</h2>
            <dl className="grid grid-cols-2 gap-4">
              {session.goal.genre && (
                <div>
                  <dt className="text-sm text-gray-500">类型</dt>
                  <dd className="text-gray-900">{session.goal.genre}</dd>
                </div>
              )}
              {session.goal.style && (
                <div>
                  <dt className="text-sm text-gray-500">风格</dt>
                  <dd className="text-gray-900">{session.goal.style}</dd>
                </div>
              )}
              {session.goal.chapter_count && (
                <div>
                  <dt className="text-sm text-gray-500">章节数</dt>
                  <dd className="text-gray-900">{session.goal.chapter_count}</dd>
                </div>
              )}
              {session.goal.word_count && (
                <div>
                  <dt className="text-sm text-gray-500">目标字数</dt>
                  <dd className="text-gray-900">
                    {session.goal.word_count >= 10000 
                      ? `${session.goal.word_count / 10000}万字` 
                      : `${session.goal.word_count}字`}
                  </dd>
                </div>
              )}
            </dl>
            {session.goal.requirements && (
              <div className="mt-4">
                <dt className="text-sm text-gray-500">创作要求</dt>
                <dd className="text-gray-900 mt-1 whitespace-pre-wrap">{session.goal.requirements}</dd>
              </div>
            )}
          </div>
        )}

        {/* Current Task - 只在未完成时显示 */}
        {!isAllCompleted && progress?.current_task && (
          <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold text-gray-900">当前任务</h2>
              <TaskTimer startedAt={progress.task_started_at} />
            </div>
            <p className="text-blue-800 text-lg font-medium">{progress.current_task}</p>
            {progress.retry_count !== undefined && progress.retry_count > 0 && (
              <div className="mt-3 bg-orange-100 border border-orange-300 rounded-lg px-4 py-2">
                <p className="text-orange-700 font-medium">
                  🔄 正在重试... 第 {progress.retry_count} 次尝试
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
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
    <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
      ⏱️ {formatTime(elapsed)}
    </span>
  );
};
