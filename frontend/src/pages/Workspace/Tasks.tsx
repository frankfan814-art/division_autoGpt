/**
 * Tasks page for workspace
 */

import { useParams } from 'react-router-dom';
import { useTasks, useFilteredTasks } from '@/hooks/useTask';
import { TaskCard } from '@/components/TaskCard';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { useState, useEffect } from 'react';
import { useTaskStore } from '@/stores/taskStore';
import { useToast } from '@/components/ui/Toast';
import { useWebSocket } from '@/hooks/useWebSocket';
import apiClient from '@/api/client';

const filterOptions = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待执行' },
  { value: 'running', label: '执行中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
];

export const Tasks = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { isLoading } = useTasks(sessionId!);
  const { allTasks, getTasksByStatus } = useFilteredTasks();
  const [filter, setFilter] = useState('all');
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const toast = useToast();
  const setCurrentSession = useTaskStore((state) => state.setCurrentSession);  // 🔥 新增
  const progress = useTaskStore((state) => state.progress);  // 🔥 获取进度信息（包含重写状态）

  // 🔥 新增：设置当前会话到 taskStore
  useEffect(() => {
    if (sessionId) {
      console.log('🔄 Tasks: Setting current session:', sessionId);
      setCurrentSession(sessionId);
    }
  }, [sessionId, setCurrentSession]);
  const setCurrentTask = useTaskStore((state) => state.setCurrentTask);

  const filteredTasks = filter === 'all'
    ? allTasks
    : getTasksByStatus(filter);

  const stats = {
    total: allTasks.length,
    pending: getTasksByStatus('pending').length,
    running: getTasksByStatus('running').length,
    completed: getTasksByStatus('completed').length,
    failed: getTasksByStatus('failed').length,
  };

  // 🔥 计算总统计
  const completedTasks = getTasksByStatus('completed');
  const totalStats = {
    totalTokens: completedTasks.reduce((sum, t) => sum + (t.total_tokens || 0), 0),
    totalCost: completedTasks.reduce((sum, t) => sum + (t.cost_usd || 0), 0),
    totalTime: completedTasks.reduce((sum, t) => sum + (t.execution_time_seconds || 0), 0),
    totalFailedAttempts: completedTasks.reduce((sum, t) => sum + (t.failed_attempts || 0), 0),
  };

  const handleTaskClick = (taskId: string) => {
    setActiveTaskId(taskId);
    const task = allTasks.find(t => t.task_id === taskId);
    if (task) {
      setCurrentTask(task);
    }
  };

  const handleRetry = async (taskId: string) => {
    try {
      await apiClient.post(`/tasks/${taskId}/retry`);
      toast.success('任务重试中...');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || '重试失败');
    }
  };

  const handleSkip = async (taskId: string) => {
    try {
      await apiClient.post(`/tasks/${taskId}/skip`);
      toast.success('任务已跳过');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || '跳过失败');
    }
  };

  // WebSocket real-time updates
  useWebSocket({
    onTaskUpdate: (data) => {
      const task = data.data;
      if (task?.status === 'completed') {
        toast.success(`✅ 任务完成: ${task.task_type}`);
      } else if (task?.status === 'failed') {
        toast.error(`❌ 任务失败: ${task.task_type}`);
      }
    },
  });

  return (
    <div className="h-full flex flex-col">
      {/* 🔥 重写状态横幅 */}
      {progress?.is_rewriting && (
        <div className="bg-orange-50 border-b border-orange-200 px-4 py-2 animate-pulse">
          <div className="flex items-center gap-2">
            <span className="text-lg">🔄</span>
            <span className="font-medium text-orange-800">
              正在重写 {progress.rewrite_task_type || '当前任务'}...
            </span>
            {progress.rewrite_attempt !== undefined && (
              <span className="text-sm text-orange-600">
                (第 {progress.rewrite_attempt} 次尝试)
              </span>
            )}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="border-b bg-white p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">任务列表</h2>
          <Select
            options={filterOptions}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-32"
          />
        </div>

        {/* Stats */}
        <div className="flex gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Badge variant="default" size="sm">全部: {stats.total}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="default" size="sm">待执行: {stats.pending}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="info" size="sm">执行中: {stats.running}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="success" size="sm">已完成: {stats.completed}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="danger" size="sm">失败: {stats.failed}</Badge>
          </div>
        </div>
        
        {/* 🔥 总统计信息 */}
        {stats.completed > 0 && (
          <div className="mt-3 p-3 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg border">
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-1">
                <span className="text-gray-500">⏱️ 总耗时:</span>
                <span className="font-medium">{(totalStats.totalTime / 60).toFixed(1)} 分钟</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-gray-500">🔤 总 Tokens:</span>
                <span className="font-medium">{totalStats.totalTokens.toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-gray-500">💰 总费用:</span>
                <span className="font-bold text-green-600">${totalStats.totalCost.toFixed(4)}</span>
              </div>
              {totalStats.totalFailedAttempts > 0 && (
                <div className="flex items-center gap-1">
                  <span className="text-gray-500">⚠️ 失败重试:</span>
                  <span className="font-medium text-orange-600">{totalStats.totalFailedAttempts} 次</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
        {isLoading ? (
          <div className="text-center py-12 text-gray-400">加载中...</div>
        ) : filteredTasks.length > 0 ? (
          <div className="grid gap-4">
            {filteredTasks.map((task) => (
              <TaskCard 
                key={task.id} 
                task={task}
                isActive={task.task_id === activeTaskId}
                onClick={() => handleTaskClick(task.task_id)}
                onRetry={handleRetry}
                onSkip={handleSkip}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-400">
            {filter === 'all' ? '暂无任务' : '没有符合条件的任务'}
          </div>
        )}
      </div>
    </div>
  );
};
