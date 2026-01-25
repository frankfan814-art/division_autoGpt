/**
 * PreviewPanel component for displaying task results in tabs
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { useTaskStore } from '@/stores/taskStore';
import { Task } from '@/types';
import { getWebSocketClient } from '@/api/websocket';

interface PreviewPanelProps {
  sessionId: string | null;
}

// 当任务超过这个数量时，切换到紧凑模式
const COMPACT_MODE_THRESHOLD = 8;

// 自动审核超时时间（秒）
const AUTO_APPROVE_TIMEOUT = 10;

export const PreviewPanel = ({ sessionId }: PreviewPanelProps) => {
  const tasks = useTaskStore((state) => state.tasks);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [showEvaluation, setShowEvaluation] = useState(false);
  const [showTaskList, setShowTaskList] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [autoApproveCountdown, setAutoApproveCountdown] = useState<number | null>(null);
  const [selectedIdea, setSelectedIdea] = useState<number | null>(null);  // 🎯 创意脑暴选择的点子
  const dropdownRef = useRef<HTMLDivElement>(null);
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
      selected_idea: ideaNumber,  // 🎯 传递选中的点子编号
    });
    
    // 等待后端响应后会自动更新状态
    setTimeout(() => setIsApproving(false), 1000);
  }, [sessionId]);

  // 自动审核计时器
  useEffect(() => {
    const pendingTask = tasks.find(t => t.status === 'pending_approval');
    
    if (pendingTask) {
      // 🎯 创意脑暴任务需要用户选择点子，不允许自动通过
      const isBrainstormTask = pendingTask.task_type === '创意脑暴';
      const requiresSelection = isBrainstormTask || pendingTask.metadata?.requires_selection;
      
      if (requiresSelection) {
        // 创意脑暴任务：禁用自动通过，必须等待用户选择
        setAutoApproveCountdown(null);
        if (autoApproveTimerRef.current) {
          clearInterval(autoApproveTimerRef.current);
          autoApproveTimerRef.current = null;
        }
        return;
      }
      
      // 其他任务：开始倒计时
      setAutoApproveCountdown(AUTO_APPROVE_TIMEOUT);
      
      autoApproveTimerRef.current = setInterval(() => {
        setAutoApproveCountdown(prev => {
          if (prev === null || prev <= 1) {
            // 倒计时结束，自动通过
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
      // 没有待审核任务，清除计时器
      if (autoApproveTimerRef.current) {
        clearInterval(autoApproveTimerRef.current);
        autoApproveTimerRef.current = null;
      }
      setAutoApproveCountdown(null);
    }
  }, [tasks, handleApproveTask]);

  // Auto-select the latest running or completed task
  useEffect(() => {
    if (tasks.length > 0 && !activeTaskId) {
      // Find the latest running or completed task
      const latestTask = [...tasks]
        .reverse()
        .find(t => t.status === 'running' || t.status === 'completed' || t.status === 'pending_approval');
      if (latestTask) {
        setActiveTaskId(latestTask.task_id);
      }
    }
  }, [tasks, activeTaskId]);

  // Auto-switch to newly started task
  useEffect(() => {
    const runningTask = tasks.find(t => t.status === 'running');
    if (runningTask && runningTask.task_id !== activeTaskId) {
      setActiveTaskId(runningTask.task_id);
    }
  }, [tasks]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowTaskList(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!sessionId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        请选择一个会话
      </div>
    );
  }

  const activeTask = tasks.find(t => t.task_id === activeTaskId);
  const isCompactMode = tasks.length > COMPACT_MODE_THRESHOLD;

  const getTaskTypeLabel = (type: string, short?: boolean) => {
    const labels: Record<string, { full: string; short: string }> = {
      '风格元素': { full: '🎨 风格元素', short: '🎨 风格' },
      '主题确认': { full: '📝 主题确认', short: '📝 主题' },
      '市场定位': { full: '🎯 市场定位', short: '🎯 市场' },
      '人物设计': { full: '👤 人物设计', short: '👤 人物' },
      '世界观规则': { full: '🌍 世界观规则', short: '🌍 世界观' },
      '事件': { full: '📅 事件', short: '📅 事件' },
      '事件设定': { full: '📅 事件设定', short: '📅 事件' },
      '场景物品冲突': { full: '🎬 场景物品冲突', short: '🎬 场景' },
      '伏笔列表': { full: '🔮 伏笔列表', short: '🔮 伏笔' },
      '大纲': { full: '📋 故事大纲', short: '📋 大纲' },
      '章节大纲': { full: '📄 章节大纲', short: '📄 章纲' },
      '章节内容': { full: '📖 章节内容', short: '📖 章节' },
      '一致性检查': { full: '✅ 一致性检查', short: '✅ 检查' },
    };
    const label = labels[type] || { full: type, short: type };
    return short ? label.short : label.full;
  };

  const getStatusBadge = (task: Task, compact?: boolean) => {
    const size = compact ? 'xs' : 'sm';
    if (task.status === 'running') {
      return <Badge variant="info" size={size as any}>{compact ? '⏳' : '执行中'}</Badge>;
    } else if (task.status === 'completed') {
      return <Badge variant="success" size={size as any}>{compact ? '✓' : '已完成'}</Badge>;
    } else if (task.status === 'failed') {
      return <Badge variant="danger" size={size as any}>{compact ? '✗' : '失败'}</Badge>;
    } else if (task.status === 'pending_approval') {
      return <Badge variant="warning" size={size as any}>{compact ? '⏸' : '待审核'}</Badge>;
    }
    return <Badge variant="default" size={size as any}>{compact ? '○' : '待执行'}</Badge>;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'pending_approval': return 'bg-yellow-500';
      default: return 'bg-gray-300';
    }
  };

  // 计算任务统计
  const taskStats = {
    total: tasks.length,
    completed: tasks.filter(t => t.status === 'completed').length,
    running: tasks.filter(t => t.status === 'running').length,
    pending: tasks.filter(t => t.status === 'pending').length,
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Tab Bar */}
      <div className="border-b bg-gray-50">
        {isCompactMode ? (
          /* 紧凑模式：下拉选择器 + 状态条 */
          <div className="flex items-center p-2 gap-2">
            {/* 当前任务选择器 */}
            <div className="relative flex-1" ref={dropdownRef}>
              <button
                onClick={() => setShowTaskList(!showTaskList)}
                className="w-full px-3 py-2 bg-white border rounded-lg text-left flex items-center justify-between hover:border-blue-400 transition-colors"
              >
                <span className="flex items-center gap-2">
                  {activeTask ? (
                    <>
                      {getTaskTypeLabel(activeTask.task_type)}
                      {getStatusBadge(activeTask, true)}
                    </>
                  ) : (
                    <span className="text-gray-400">选择任务...</span>
                  )}
                </span>
                <svg className={`w-4 h-4 transition-transform ${showTaskList ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              {/* 下拉列表 */}
              {showTaskList && (
                <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-80 overflow-y-auto">
                  {tasks.map((task, index) => (
                    <button
                      key={task.task_id}
                      onClick={() => {
                        setActiveTaskId(task.task_id);
                        setShowTaskList(false);
                      }}
                      className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-gray-50 ${
                        activeTaskId === task.task_id ? 'bg-blue-50' : ''
                      } ${index !== tasks.length - 1 ? 'border-b' : ''}`}
                    >
                      <span className="flex items-center gap-2">
                        <span className="text-xs text-gray-400 w-4">{index + 1}</span>
                        <span className={activeTaskId === task.task_id ? 'text-blue-700 font-medium' : ''}>
                          {getTaskTypeLabel(task.task_type)}
                        </span>
                      </span>
                      {getStatusBadge(task, true)}
                    </button>
                  ))}
                </div>
              )}
            </div>
            
            {/* 进度指示器 */}
            <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-lg">
              <span className="text-xs text-gray-500">{taskStats.completed}/{taskStats.total}</span>
              <div className="flex gap-0.5">
                {tasks.slice(0, 12).map((task, i) => (
                  <div
                    key={i}
                    className={`w-2 h-2 rounded-full ${getStatusColor(task.status)} ${
                      task.task_id === activeTaskId ? 'ring-2 ring-blue-400' : ''
                    }`}
                    title={getTaskTypeLabel(task.task_type)}
                  />
                ))}
                {tasks.length > 12 && (
                  <span className="text-xs text-gray-400 ml-1">+{tasks.length - 12}</span>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* 普通模式：Tab 按钮 */
          <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
            <div className="flex items-center gap-1 p-2 min-w-min">
              {tasks.length === 0 ? (
                <div className="px-4 py-2 text-sm text-gray-400">
                  等待任务启动...
                </div>
              ) : (
                tasks.map((task) => (
                  <button
                    key={task.task_id}
                    onClick={() => setActiveTaskId(task.task_id)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap flex items-center gap-2 flex-shrink-0 ${
                      activeTaskId === task.task_id
                        ? 'bg-blue-100 text-blue-700 shadow-sm'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {getTaskTypeLabel(task.task_type, tasks.length > 6)}
                    {getStatusBadge(task, tasks.length > 6)}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>

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
                <div className="flex items-center gap-4 text-sm">
                  <span className={`font-semibold ${
                    activeTask.evaluation.score >= 0.9 ? 'text-green-600' :
                    activeTask.evaluation.score >= 0.7 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    评分: {(activeTask.evaluation.score * 100).toFixed(0)}/100
                  </span>
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
              
              {/* 🔥 任务统计信息 - 执行时间、tokens、费用、重试次数 */}
              {activeTask.status === 'completed' && (
                <div className="mt-3 flex flex-wrap items-center gap-3 text-sm bg-gray-50 p-3 rounded-lg border">
                  {activeTask.execution_time_seconds !== undefined && (
                    <div className="flex items-center gap-1.5" title="执行时间">
                      <span className="text-lg">⏱️</span>
                      <span className="text-gray-700">
                        <span className="font-medium">{activeTask.execution_time_seconds.toFixed(1)}</span>
                        <span className="text-gray-500 ml-0.5">秒</span>
                      </span>
                    </div>
                  )}
                  {activeTask.total_tokens !== undefined && activeTask.total_tokens > 0 && (
                    <div className="flex items-center gap-1.5" title={`输入: ${activeTask.prompt_tokens || 0} | 输出: ${activeTask.completion_tokens || 0}`}>
                      <span className="text-lg">🔤</span>
                      <span className="text-gray-700">
                        <span className="font-medium">{activeTask.total_tokens.toLocaleString()}</span>
                        <span className="text-gray-500 ml-0.5">tokens</span>
                      </span>
                      <span className="text-xs text-gray-400">
                        (输入:{activeTask.prompt_tokens?.toLocaleString() || 0} / 输出:{activeTask.completion_tokens?.toLocaleString() || 0})
                      </span>
                    </div>
                  )}
                  {activeTask.cost_usd !== undefined && activeTask.cost_usd > 0 && (
                    <div className="flex items-center gap-1.5" title="API 费用">
                      <span className="text-lg">💰</span>
                      <span className="text-green-600 font-medium">
                        ${activeTask.cost_usd.toFixed(4)}
                      </span>
                    </div>
                  )}
                  {((activeTask.retry_count && activeTask.retry_count > 1) || 
                    (activeTask.failed_attempts && activeTask.failed_attempts > 0)) && (
                    <div className="flex items-center gap-1.5" title="重试信息">
                      <span className="text-lg">🔄</span>
                      <span className="text-orange-600">
                        {activeTask.failed_attempts && activeTask.failed_attempts > 0 && (
                          <span className="font-medium">{activeTask.failed_attempts} 次失败</span>
                        )}
                        {activeTask.retry_count && activeTask.retry_count > 1 && (
                          <span className="font-medium ml-1">/ 共 {activeTask.retry_count} 次尝试</span>
                        )}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Task Result */}
            {activeTask.result ? (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">生成结果</h3>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 prose prose-sm max-w-none">
                  <ReactMarkdown
                    components={{
                      // 自定义样式
                      h1: ({children}) => <h1 className="text-xl font-bold mt-4 mb-2 text-gray-900">{children}</h1>,
                      h2: ({children}) => <h2 className="text-lg font-bold mt-3 mb-2 text-gray-800">{children}</h2>,
                      h3: ({children}) => <h3 className="text-base font-semibold mt-2 mb-1 text-gray-800">{children}</h3>,
                      p: ({children}) => <p className="my-2 text-gray-700 leading-relaxed">{children}</p>,
                      ul: ({children}) => <ul className="list-disc list-inside my-2 space-y-1">{children}</ul>,
                      ol: ({children}) => <ol className="list-decimal list-inside my-2 space-y-1">{children}</ol>,
                      li: ({children}) => <li className="text-gray-700">{children}</li>,
                      strong: ({children}) => <strong className="font-semibold text-gray-900">{children}</strong>,
                      em: ({children}) => <em className="italic text-gray-600">{children}</em>,
                      blockquote: ({children}) => <blockquote className="border-l-4 border-blue-300 pl-4 my-2 text-gray-600 italic">{children}</blockquote>,
                      code: ({children, className}) => {
                        const isInline = !className;
                        return isInline ? (
                          <code className="bg-gray-200 px-1 rounded text-sm text-red-600">{children}</code>
                        ) : (
                          <code className="block bg-gray-800 text-gray-100 p-3 rounded-lg overflow-x-auto text-sm">{children}</code>
                        );
                      },
                      hr: () => <hr className="my-4 border-gray-300" />,
                    }}
                  >
                    {activeTask.result}
                  </ReactMarkdown>
                </div>
                
                {/* Approval Buttons */}
                {activeTask.status === 'pending_approval' && (() => {
                  // 🎯 检查是否是创意脑暴任务
                  const isBrainstormTask = activeTask.task_type === '创意脑暴';
                  const requiresSelection = isBrainstormTask || activeTask.metadata?.requires_selection;
                  
                  return (
                    <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                      {/* 创意脑暴点子选择 */}
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
                            setSelectedIdea(null);  // 重置选择
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
              <div className="flex items-center justify-center py-12 text-gray-400">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
                  <p>正在生成中...</p>
                </div>
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
