/**
 * PreviewPanel - 预览面板
 *
 * 专注于单个任务的展示和审核功能
 * 任务切换由外部的 PanelTabBar 和主面板控制
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { StepProgress } from './StepProgress';
import { useTaskStore } from '@/stores/taskStore';
import { Task } from '@/types';
import { getWebSocketClient } from '@/api/websocket';
import logger from '@/utils/logger';

interface PreviewPanelProps {
  sessionId: string | null;
}

// 自动审核超时时间（秒）
const AUTO_APPROVE_TIMEOUT = 10;

// 实时计时器组件
function RunningTimer({ taskStartTime }: { taskStartTime: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let startTime: number;
    try {
      if (taskStartTime.includes('Z') || taskStartTime.includes('+') || taskStartTime.includes('T')) {
        startTime = new Date(taskStartTime).getTime();
      } else {
        startTime = new Date(taskStartTime + 'Z').getTime();
      }
    } catch (e) {
      logger.error('Failed to parse task start time:', taskStartTime, e);
      startTime = Date.now();
    }

    const updateTime = () => {
      const now = Date.now();
      const diff = (now - startTime) / 1000;
      setElapsed(Math.max(0, diff));
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [taskStartTime]);

  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}秒`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return `${mins}分${secs}秒`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      const secs = Math.floor(seconds % 60);
      return `${hours}小时${mins}分${secs}秒`;
    }
  };

  return (
    <div className="flex items-center gap-1.5 text-sm">
      <span className="text-blue-600">⏱️</span>
      <span className="font-mono font-medium text-blue-700">{formatTime(elapsed)}</span>
    </div>
  );
}

export const PreviewPanel = ({ sessionId }: PreviewPanelProps) => {
  const tasks = useTaskStore((state) => state.getTasks());

  // 使用 useMemo 创建稳定的依赖项
  const taskIds = useMemo(() => tasks.map(t => t.task_id).join(','), [tasks]);
  const pendingApprovalTaskId = useMemo(() => {
    const t = tasks.find(t => t.status === 'pending_approval');
    return t?.task_id || null;
  }, [tasks]);

  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [showEvaluation, setShowEvaluation] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);  // 🔥 新增：提示词展开状态
  const [isApproving, setIsApproving] = useState(false);
  const [autoApproveCountdown, setAutoApproveCountdown] = useState<number | null>(null);
  const [selectedIdea, setSelectedIdea] = useState<number | null>(null);
  const autoApproveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 审核任务（支持创意脑暴的点子选择）
  const handleApproveTask = useCallback((action: 'approve' | 'reject' | 'regenerate', ideaNumber?: number) => {
    if (!sessionId) return;

    // 清除自动审核计时器
    if (autoApproveTimerRef.current) {
      clearInterval(autoApproveTimerRef.current);
      autoApproveTimerRef.current = null;
    }
    setAutoApproveCountdown(null);

    setIsApproving(true);
    const ws = getWebSocketClient();
    ws.send({
      event: 'approve_task',
      session_id: sessionId,
      action: action,
      selected_idea: ideaNumber,
    });

    setTimeout(() => setIsApproving(false), 1000);
  }, [sessionId]);

  // 自动审核计时器
  useEffect(() => {
    const pendingTask = tasks.find(t => t.status === 'pending_approval');

    if (pendingTask) {
      // 创意脑暴任务需要用户选择点子，不允许自动通过
      const isBrainstormTask = pendingTask.task_type === '创意脑暴';
      const requiresSelection = isBrainstormTask || pendingTask.metadata?.requires_selection;

      if (requiresSelection) {
        setAutoApproveCountdown(null);
        if (autoApproveTimerRef.current) {
          clearInterval(autoApproveTimerRef.current);
          autoApproveTimerRef.current = null;
        }
        return;
      }

      // 开始倒计时
      setAutoApproveCountdown(AUTO_APPROVE_TIMEOUT);

      autoApproveTimerRef.current = setInterval(() => {
        setAutoApproveCountdown(prev => {
          if (prev === null || prev <= 1) {
            clearInterval(autoApproveTimerRef.current!);
            autoApproveTimerRef.current = null;
            handleApproveTask('approve');
            return null;
          }
          return prev - 1;
        });
      }, 1000);

      return () => {
        if (autoApproveTimerRef.current) {
          clearInterval(autoApproveTimerRef.current);
          autoApproveTimerRef.current = null;
        }
      };
    } else {
      if (autoApproveTimerRef.current) {
        clearInterval(autoApproveTimerRef.current);
        autoApproveTimerRef.current = null;
      }
      setAutoApproveCountdown(null);
    }
  }, [pendingApprovalTaskId, handleApproveTask]);

  // 自动选择任务
  useEffect(() => {
    if (tasks.length > 0 && !activeTaskId) {
      const latestTask = [...tasks]
        .reverse()
        .find(t => t.status === 'running' || t.status === 'completed' || t.status === 'pending_approval');
      if (latestTask) {
        logger.debug('🎯 Auto-selecting initial task:', latestTask.task_type);
        setActiveTaskId(latestTask.task_id);
      }
    }
  }, [tasks.length]);

  // 自动切换到运行中的任务
  useEffect(() => {
    const runningTask = tasks.find(t => t.status === 'running');
    if (runningTask && (!activeTaskId || !tasks.find(t => t.task_id === activeTaskId && t.status === 'running'))) {
      logger.debug('🔄 Auto-switching to running task:', runningTask.task_type);
      setActiveTaskId(runningTask.task_id);
    }
  }, [taskIds]);

  if (!sessionId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        请选择一个会话
      </div>
    );
  }

  const activeTask = tasks.find(t => t.task_id === activeTaskId);

  const getTaskTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      '风格元素': '🎨 风格元素',
      '主题确认': '📝 主题确认',
      '市场定位': '🎯 市场定位',
      '人物设计': '👤 人物设计',
      '世界观规则': '🌍 世界观规则',
      '事件': '📅 事件',
      '事件设定': '📅 事件设定',
      '场景物品冲突': '🎬 场景物品冲突',
      '伏笔列表': '🔮 伏笔列表',
      '大纲': '📋 故事大纲',
      '章节大纲': '📄 章节大纲',
      '章节内容': '📖 章节内容',
      '一致性检查': '✅ 一致性检查',
    };
    return labels[type] || type;
  };

  const getStatusBadge = (task: Task) => {
    if (task.status === 'running') {
      return <Badge variant="info">执行中</Badge>;
    } else if (task.status === 'completed') {
      return <Badge variant="success">已完成</Badge>;
    } else if (task.status === 'failed') {
      return <Badge variant="danger">失败</Badge>;
    } else if (task.status === 'pending_approval') {
      return <Badge variant="warning">待审核</Badge>;
    }
    return <Badge variant="default">待执行</Badge>;
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {activeTask ? (
          <div className="p-6">
            {/* Task Header */}
            <div className="mb-6">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    {getTaskTypeLabel(activeTask.task_type)}
                  </h2>
                  {activeTask.description && (
                    <p className="text-sm text-gray-600">{activeTask.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(activeTask)}
                  {activeTask.llm_provider && (
                    <Badge variant="default" size="sm">
                      {activeTask.llm_provider === 'aliyun' ? 'Qwen' :
                       activeTask.llm_provider === 'deepseek' ? 'DeepSeek' :
                       activeTask.llm_provider === 'ark' ? 'Doubao' :
                       activeTask.llm_provider}
                    </Badge>
                  )}
                </div>
              </div>

              {/* Evaluation Summary */}
              {activeTask.evaluation && (
                <div className="flex items-center gap-4 text-sm flex-wrap">
                  {activeTask.evaluation.quality_score !== undefined ? (
                    <span className={`font-semibold ${
                      activeTask.evaluation.quality_score >= 0.8 ? 'text-green-600' :
                      activeTask.evaluation.quality_score >= 0.6 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      📈 质量: {(activeTask.evaluation.quality_score * 10).toFixed(1)}/10
                    </span>
                  ) : (
                    <span className={`font-semibold ${
                      activeTask.evaluation.score >= 0.9 ? 'text-green-600' :
                      activeTask.evaluation.score >= 0.7 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      评分: {(activeTask.evaluation.score * 100).toFixed(0)}/100
                    </span>
                  )}

                  {activeTask.evaluation.consistency_score !== undefined && (
                    <span className={`font-semibold ${
                      activeTask.evaluation.consistency_score >= 0.8 ? 'text-green-600' :
                      activeTask.evaluation.consistency_score >= 0.6 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      🔍 一致性: {(activeTask.evaluation.consistency_score * 10).toFixed(1)}/10
                    </span>
                  )}

                  <span className={activeTask.evaluation.passed ? 'text-green-600' : 'text-red-600'}>
                    {activeTask.evaluation.passed ? '✓ 通过' : '✗ 未通过'}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowEvaluation(!showEvaluation)}
                  >
                    {showEvaluation ? '隐藏' : '显示'}评估详情
                  </Button>
                </div>
              )}

              {/* 任务统计信息 */}
              {activeTask.status === 'completed' && (
                <div className="mt-3 flex flex-wrap items-center gap-3 text-sm bg-gray-50 p-3 rounded-lg border">
                  {activeTask.execution_time_seconds !== undefined && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-lg">⏱️</span>
                      <span className="text-gray-700">
                        <span className="font-medium">{activeTask.execution_time_seconds.toFixed(1)}</span>
                        <span className="text-gray-500 ml-0.5">秒</span>
                      </span>
                    </div>
                  )}
                  {activeTask.total_tokens !== undefined && activeTask.total_tokens > 0 && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-lg">🔤</span>
                      <span className="text-gray-700">
                        <span className="font-medium">{activeTask.total_tokens.toLocaleString()}</span>
                        <span className="text-gray-500 ml-0.5">tokens</span>
                      </span>
                    </div>
                  )}
                  {activeTask.cost_usd !== undefined && activeTask.cost_usd > 0 && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-lg">💰</span>
                      <span className="text-green-600 font-medium">
                        ${activeTask.cost_usd.toFixed(4)}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 🔥 提示词显示区域 */}
            {activeTask.metadata?.prompt && (
              <div className="mb-6 border rounded-lg overflow-hidden">
                <button
                  onClick={() => setShowPrompt(!showPrompt)}
                  className="w-full px-4 py-3 bg-blue-50 hover:bg-blue-100 flex items-center justify-between text-sm font-medium text-blue-700 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">📝</span>
                    <span>提示词</span>
                    <span className="text-xs text-blue-600 font-normal">
                      ({activeTask.metadata.prompt_length || activeTask.metadata.prompt?.length || 0} 字符)
                    </span>
                  </div>
                  <span className="text-blue-500">{showPrompt ? '▼' : '▶'}</span>
                </button>
                {showPrompt && (
                  <div className="p-4 bg-gray-50 max-h-96 overflow-y-auto border-t">
                    <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
                      {activeTask.metadata.prompt}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Task Result */}
            {activeTask.result ? (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">生成结果</h3>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 prose prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      h1: ({children}) => <h1 className="text-xl font-bold mt-4 mb-2 text-gray-900">{children}</h1>,
                      h2: ({children}) => <h2 className="text-lg font-bold mt-3 mb-2 text-gray-800">{children}</h2>,
                      h3: ({children}) => <h3 className="text-base font-semibold mt-2 mb-1 text-gray-800">{children}</h3>,
                      p: ({children}) => <p className="my-2 text-gray-700 leading-relaxed">{children}</p>,
                      ul: ({children}) => <ul className="list-disc list-inside my-2 space-y-1">{children}</ul>,
                      ol: ({children}) => <ol className="list-decimal list-inside my-2 space-y-1">{children}</ol>,
                      li: ({children}) => <li className="text-gray-700">{children}</li>,
                      strong: ({children}) => <strong className="font-semibold text-gray-900">{children}</strong>,
                      blockquote: ({children}) => <blockquote className="border-l-4 border-blue-300 pl-4 my-2 text-gray-600 italic">{children}</blockquote>,
                    }}
                  >
                    {activeTask.result}
                  </ReactMarkdown>
                </div>

                {/* Approval Buttons */}
                {activeTask.status === 'pending_approval' && (() => {
                  const isBrainstormTask = activeTask.task_type === '创意脑暴';
                  const requiresSelection = isBrainstormTask || activeTask.metadata?.requires_selection;

                  return (
                    <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                      {requiresSelection && (
                        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <h3 className="text-sm font-semibold text-blue-800 mb-3">
                            🎯 请选择一个点子作为后续创作的基础
                          </h3>
                          <div className="grid grid-cols-2 gap-2 mb-2">
                            {[1, 2, 3, 4].map((num) => (
                              <button
                                key={num}
                                onClick={() => setSelectedIdea(num)}
                                disabled={isApproving}
                                className={`p-2 rounded-lg border-2 transition-all text-left text-sm ${
                                  selectedIdea === num
                                    ? 'border-blue-500 bg-blue-100 text-blue-800'
                                    : 'border-gray-300 bg-white hover:border-blue-300'
                                }`}
                              >
                                <span className="font-medium">点子 {num}</span>
                                {selectedIdea === num && (
                                  <span className="ml-2 text-blue-600">✓</span>
                                )}
                              </button>
                            ))}
                          </div>
                          {selectedIdea ? (
                            <p className="text-xs text-green-700">
                              ✅ 已选择点子 {selectedIdea}，请点击下方「确认选择并继续」按钮
                            </p>
                          ) : (
                            <p className="text-xs text-orange-600">
                              ⚠️ 请先选择一个点子才能继续
                            </p>
                          )}
                        </div>
                      )}

                      <div className="flex items-center justify-between mb-3">
                        <p className="text-sm text-yellow-800">
                          {requiresSelection
                            ? '🎨 创意脑暴任务需要您选择一个点子'
                            : '⏸️ 此任务正在等待您的审核，请确认后再继续'}
                        </p>
                        {autoApproveCountdown !== null && !requiresSelection && (
                          <span className="text-sm font-medium text-yellow-700 bg-yellow-100 px-2 py-1 rounded">
                            ⏱️ {autoApproveCountdown}秒后自动通过
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            if (requiresSelection && !selectedIdea) {
                              alert('请先选择一个点子！');
                              return;
                            }
                            handleApproveTask('approve', selectedIdea || undefined);
                            setSelectedIdea(null);
                          }}
                          isLoading={isApproving}
                          disabled={requiresSelection && !selectedIdea}
                        >
                          {requiresSelection ? '✓ 确认选择并继续' : '✓ 通过，继续下一步'}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleApproveTask('regenerate')}
                          isLoading={isApproving}
                        >
                          🔄 重新生成
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleApproveTask('reject')}
                          isLoading={isApproving}
                        >
                          ✗ 拒绝并跳过
                        </Button>
                      </div>
                    </div>
                  );
                })()}
              </div>
            ) : activeTask.status === 'running' ? (
              <div className="py-6">
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                      <span className="text-sm font-medium text-blue-700">任务执行中...</span>
                    </div>
                    <RunningTimer taskStartTime={activeTask.created_at} />
                  </div>
                </div>
                <StepProgress />
              </div>
            ) : (
              <div className="flex items-center justify-center py-12 text-gray-400">
                等待任务执行
              </div>
            )}

            {/* Evaluation Details */}
            {showEvaluation && activeTask.evaluation && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">评估详情</h3>

                {/* 🔥 质量问题 */}
                {activeTask.evaluation.quality_issues && activeTask.evaluation.quality_issues.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-xs font-medium text-orange-600 mb-2 flex items-center gap-1">
                      <span>📝</span>
                      <span>质量问题：</span>
                    </h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 bg-orange-50 p-3 rounded-lg border border-orange-200">
                      {activeTask.evaluation.quality_issues.map((issue, idx) => (
                        <li key={idx}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 🔥 一致性问题 */}
                {activeTask.evaluation.consistency_issues && activeTask.evaluation.consistency_issues.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-xs font-medium text-red-600 mb-2 flex items-center gap-1">
                      <span>🔍</span>
                      <span>一致性问题：</span>
                    </h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 bg-red-50 p-3 rounded-lg border border-red-200">
                      {activeTask.evaluation.consistency_issues.map((issue, idx) => (
                        <li key={idx}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {activeTask.evaluation.reasons && activeTask.evaluation.reasons.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-xs font-medium text-gray-600 mb-2">问题分析：</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 bg-red-50 p-3 rounded-lg">
                      {activeTask.evaluation.reasons.map((reason, idx) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {activeTask.evaluation.suggestions && activeTask.evaluation.suggestions.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-600 mb-2">改进建议：</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 bg-blue-50 p-3 rounded-lg">
                      {activeTask.evaluation.suggestions.map((suggestion, idx) => (
                        <li key={idx}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Error Message */}
            {activeTask.error && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-red-700 mb-3">错误信息</h3>
                <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                  <pre className="whitespace-pre-wrap text-sm text-red-800 font-mono">
                    {activeTask.error}
                  </pre>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <p className="text-lg mb-2">等待任务启动</p>
              <p className="text-sm">任务开始执行后，结果将在这里实时显示</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
