/**
 * TaskCard component for displaying task information with interactions
 */

import { useState } from 'react';
import { Task } from '@/types';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';

interface TaskCardProps {
  task: Task;
  showEvaluation?: boolean;
  isActive?: boolean;
  onClick?: () => void;
  onRetry?: (taskId: string) => void;
  onSkip?: (taskId: string) => void;
}

const statusConfig: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'danger' | 'info' }> = {
  pending: { label: '待执行', variant: 'default' },
  running: { label: '执行中', variant: 'info' },
  completed: { label: '已完成', variant: 'success' },
  failed: { label: '失败', variant: 'danger' },
  pending_approval: { label: '待审核', variant: 'warning' },
  skipped: { label: '已跳过', variant: 'default' },
};

const defaultStatusInfo = { label: '未知', variant: 'default' as const };

export const TaskCard = ({
  task,
  showEvaluation = true,
  isActive = false,
  onClick,
  onRetry,
  onSkip,
}: TaskCardProps) => {
  // 安全获取状态信息，防止未知状态导致崩溃
  const statusInfo = statusConfig[task.status] || defaultStatusInfo;

  // 🔥 新增：提示词展开/折叠状态
  const [showPrompt, setShowPrompt] = useState(false);

  const handleRetry = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRetry?.(task.task_id);
  };

  const handleSkip = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSkip?.(task.task_id);
  };

  const renderEvaluation = () => {
    if (!showEvaluation || !task.evaluation || task.status !== 'completed') {
      return null;
    }

    const { evaluation } = task;
    const { quality_score, consistency_score, score } = evaluation;

    return (
      <div className="mt-3 p-3 bg-gray-50 rounded-lg border">
        {/* 🔥 分别显示质量和一致性评分 */}
        {quality_score !== undefined && consistency_score !== undefined ? (
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div className={`p-2 rounded border ${quality_score >= 0.8 ? 'bg-green-50 border-green-200' : quality_score >= 0.6 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'}`}>
              <p className="text-xs font-medium text-gray-700">📈 文学质量</p>
              <p className={`text-lg font-bold ${quality_score >= 0.8 ? 'text-green-600' : quality_score >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`}>
                {(quality_score * 10).toFixed(1)}/10
              </p>
            </div>
            <div className={`p-2 rounded border ${consistency_score >= 0.8 ? 'bg-green-50 border-green-200' : consistency_score >= 0.6 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'}`}>
              <p className="text-xs font-medium text-gray-700">🔍 逻辑一致性</p>
              <p className={`text-lg font-bold ${consistency_score >= 0.8 ? 'text-green-600' : consistency_score >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`}>
                {(consistency_score * 10).toFixed(1)}/10
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">质量评分</span>
            <span className={`text-lg font-bold ${score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
              {score}/100
            </span>
          </div>
        )}

        {evaluation.reasons && evaluation.reasons.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-gray-600 mb-1">评估结果:</p>
            <ul className="text-xs text-gray-600 space-y-1">
              {evaluation.reasons.map((reason, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="mr-1">•</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {evaluation.suggestions && evaluation.suggestions.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-gray-600 mb-1">改进建议:</p>
            <ul className="text-xs text-gray-600 space-y-1">
              {evaluation.suggestions.map((suggestion, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="mr-1">→</span>
                  <span>{suggestion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 🔥 显示质量问题和一致性问题 */}
        {evaluation.quality_issues && evaluation.quality_issues.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-gray-600 mb-1">质量问题:</p>
            <ul className="text-xs text-red-600 space-y-1">
              {evaluation.quality_issues.map((issue, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="mr-1">•</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {evaluation.consistency_issues && evaluation.consistency_issues.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-gray-600 mb-1">一致性问题:</p>
            <ul className="text-xs text-orange-600 space-y-1">
              {evaluation.consistency_issues.map((issue, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="mr-1">•</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {evaluation.dimension_scores && Object.keys(evaluation.dimension_scores).length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-2">
            {Object.entries(evaluation.dimension_scores).map(([dim, scoreData]) => (
              <div key={dim} className="bg-white p-2 rounded border">
                <p className="text-xs font-medium text-gray-700">{dim}</p>
                <p className="text-sm font-bold text-gray-900">{scoreData.score}/100</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div 
      className={`bg-white border rounded-lg p-4 shadow-sm transition-all ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      } ${
        isActive ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:border-gray-300'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-900">{task.task_type}</h3>
            {task.chapter_index !== undefined && (
              <Badge variant="info" size="sm">第 {task.chapter_index} 章</Badge>
            )}
            {isActive && (
              <span className="text-xs text-blue-600 font-medium">● 当前</span>
            )}
            {/* 显示重试次数 */}
            {task.metadata?.retry_count && task.metadata.retry_count > 0 && (
              <Badge variant="warning" size="sm">
                🔄 重试 #{task.metadata.retry_count}
              </Badge>
            )}
            {/* 显示最终重试次数（已完成的任务） */}
            {task.retry_count && task.retry_count > 1 && task.status === 'completed' && (
              <Badge variant="default" size="sm">
                经过 {task.retry_count} 次尝试
              </Badge>
            )}
            {/* 🔥 显示失败尝试次数 */}
            {task.failed_attempts && task.failed_attempts > 0 && (
              <Badge variant="danger" size="sm">
                ⚠️ {task.failed_attempts} 次失败
              </Badge>
            )}
          </div>
          <p className="text-xs text-gray-500 font-mono">{task.task_id}</p>
          
          {/* 🔥 显示任务统计信息（已完成的任务） */}
          {task.status === 'completed' && (
            <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-gray-500">
              {task.execution_time_seconds !== undefined && (
                <span title="执行时间">⏱️ {task.execution_time_seconds.toFixed(1)}s</span>
              )}
              {task.total_tokens !== undefined && task.total_tokens > 0 && (
                <span title={`输入: ${task.prompt_tokens || 0} | 输出: ${task.completion_tokens || 0}`}>
                  🔤 {task.total_tokens.toLocaleString()} tokens
                </span>
              )}
              {task.cost_usd !== undefined && task.cost_usd > 0 && (
                <span title="API 费用" className="text-green-600 font-medium">
                  💰 ${task.cost_usd.toFixed(4)}
                </span>
              )}
            </div>
          )}
        </div>
        <Badge variant={statusInfo.variant} size="sm">{statusInfo.label}</Badge>
      </div>

      {/* 重试原因提示 */}
      {task.status === 'running' && task.metadata?.retry_reason && (
        <div className="mb-2 p-2 bg-orange-50 border border-orange-200 rounded text-sm text-orange-700">
          🔄 {task.metadata.retry_reason}
        </div>
      )}

      {task.result && (
        <div className="mt-2 p-2 bg-gray-50 rounded border text-sm text-gray-700 max-h-32 overflow-y-auto">
          {task.result}
        </div>
      )}

      {task.error && (
        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          ❌ {task.error}
        </div>
      )}

      {renderEvaluation()}

      {/* 🔥 新增：提示词显示区域 */}
      {task.metadata?.prompt && (
        <div className="mt-3 border rounded-lg overflow-hidden">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowPrompt(!showPrompt);
            }}
            className="w-full px-3 py-2 bg-blue-50 hover:bg-blue-100 flex items-center justify-between text-sm font-medium text-blue-700 transition-colors"
          >
            <span>📝 提示词 ({task.metadata.prompt_length || task.metadata.prompt?.length || 0} 字符)</span>
            <span className="text-blue-500">{showPrompt ? '▼' : '▶'}</span>
          </button>
          {showPrompt && (
            <div className="p-3 bg-gray-50 max-h-96 overflow-y-auto">
              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                {task.metadata.prompt}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Action buttons for failed tasks */}
      {task.status === 'failed' && (onRetry || onSkip) && (
        <div className="mt-3 flex items-center gap-2 pt-3 border-t">
          {onRetry && (
            <Button
              size="sm"
              variant="secondary"
              onClick={handleRetry}
            >
              🔄 重试
            </Button>
          )}
          {onSkip && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleSkip}
            >
              ⏭️ 跳过
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
