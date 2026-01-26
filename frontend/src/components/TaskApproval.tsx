/**
 * Task Approval Component - Preview and approve task results
 */

import { useState } from 'react';
import { Task } from '@/types';
import { Button } from './ui/Button';
import { Card } from './ui';
import { Badge } from './ui/Badge';
import { getWebSocketClient } from '@/api/websocket';

interface TaskApprovalProps {
  task: Task;
  sessionId: string;
  onApprove?: () => void;
  onReject?: () => void;
  onRegenerate?: () => void;
}

export const TaskApproval = ({ task, sessionId, onApprove, onReject, onRegenerate }: TaskApprovalProps) => {
  const [feedback, setFeedback] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedIdea, setSelectedIdea] = useState<number | null>(null);

  // 检查是否是创意脑暴任务，需要用户选择点子
  const isBrainstormTask = task.task_type === '创意脑暴';
  const requiresSelection = isBrainstormTask || task.metadata?.requires_selection;

  const handleApprove = () => {
    // 如果是创意脑暴任务且没有选择点子，提示用户
    if (requiresSelection && !selectedIdea) {
      alert('请先选择一个点子！');
      return;
    }
    
    setIsProcessing(true);
    const ws = getWebSocketClient();
    ws.send({
      event: 'approve_task',
      session_id: sessionId,
      action: 'approve',
      selected_idea: selectedIdea,
    });
    onApprove?.();
  };

  const handleReject = () => {
    setIsProcessing(true);
    const ws = getWebSocketClient();
    ws.send({
      event: 'approve_task',
      session_id: sessionId,
      action: 'reject',
    });
    onReject?.();
  };

  const handleRegenerate = () => {
    setIsProcessing(true);
    const ws = getWebSocketClient();
    ws.send({
      event: 'approve_task',
      session_id: sessionId,
      action: 'regenerate',
      feedback,
    });
    onRegenerate?.();
  };

  const getTaskTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      '创意脑暴': '创意脑暴',
      '故事核心': '故事核心',
      '风格元素': '风格元素',
      '主题确认': '主题确认',
      '市场定位': '市场定位',
      '人物设计': '人物设计',
      '世界观规则': '世界观规则',
      '事件设定': '事件设定',
      '伏笔列表': '伏笔列表',
      '大纲': '故事大纲',
      '章节大纲': '章节大纲',
      '章节内容': '章节内容',
    };
    return labels[type] || type;
  };

  const evaluation = task.evaluation;
  const score = evaluation?.score || 0;
  const qualityScore = evaluation?.quality_score;
  const consistencyScore = evaluation?.consistency_score;
  const scoreColor = score >= 0.9 ? 'text-green-600' : score >= 0.7 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-2xl font-bold text-gray-900">
              任务结果预览
            </h2>
            <Badge variant={score >= 0.9 ? 'success' : score >= 0.7 ? 'warning' : 'danger'}>
              {getTaskTypeLabel(task.task_type)}
            </Badge>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-600 flex-wrap">
            <span>🤖 {task.llm_provider} - {task.llm_model}</span>
            {evaluation && (
              <>
                <span>•</span>
                {/* 🔥 显示质量和一致性评分 */}
                {qualityScore !== undefined ? (
                  <>
                    <span className={`font-semibold ${
                      qualityScore >= 0.8 ? 'text-green-600' :
                      qualityScore >= 0.6 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      📈 质量: {(qualityScore * 10).toFixed(1)}/10
                    </span>
                    {consistencyScore !== undefined && (
                      <>
                        <span>•</span>
                        <span className={`font-semibold ${
                          consistencyScore >= 0.8 ? 'text-green-600' :
                          consistencyScore >= 0.6 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          🔍 一致性: {(consistencyScore * 10).toFixed(1)}/10
                        </span>
                      </>
                    )}
                  </>
                ) : (
                  <span className={`font-semibold ${scoreColor}`}>
                    评分: {(score * 100).toFixed(0)}/100
                  </span>
                )}
                <span>•</span>
                <span className={evaluation.passed ? 'text-green-600' : 'text-red-600'}>
                  {evaluation.passed ? '✓ 通过' : '✗ 未通过'}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* Task Description */}
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">任务描述</h3>
            <p className="text-sm text-gray-600">{task.description}</p>
          </div>

          {/* Result */}
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">生成结果</h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">
                {task.result}
              </pre>
            </div>
          </div>

          {/* Idea Selection for Brainstorm Task */}
          {requiresSelection && (
            <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h3 className="text-sm font-semibold text-yellow-800 mb-3">
                🎯 请选择一个点子作为后续创作的基础
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {[1, 2, 3, 4].map((num) => (
                  <button
                    key={num}
                    onClick={() => setSelectedIdea(num)}
                    disabled={isProcessing}
                    className={`p-3 rounded-lg border-2 transition-all text-left ${
                      selectedIdea === num
                        ? 'border-blue-500 bg-blue-50 text-blue-800'
                        : 'border-gray-300 bg-white hover:border-gray-400'
                    }`}
                  >
                    <span className="font-semibold">点子 {num}</span>
                    {selectedIdea === num && (
                      <span className="ml-2 text-blue-600">✓ 已选择</span>
                    )}
                  </button>
                ))}
              </div>
              {selectedIdea && (
                <p className="mt-3 text-sm text-green-700">
                  ✅ 已选择点子 {selectedIdea}，点击「确认选择并继续」进入下一步
                </p>
              )}
            </div>
          )}

          {/* Evaluation Details */}
          {evaluation && (
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">评估详情</h3>
              
              {evaluation.reasons && evaluation.reasons.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-xs font-medium text-gray-600 mb-1">问题分析：</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                    {evaluation.reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}

              {evaluation.suggestions && evaluation.suggestions.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-600 mb-1">改进建议：</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                    {evaluation.suggestions.map((suggestion, idx) => (
                      <li key={idx}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Feedback Input */}
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">反馈说明（可选）</h3>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="如果选择重新生成，可以在这里说明你的期望..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
              disabled={isProcessing}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
          <div className="flex gap-3">
            <Button
              onClick={handleApprove}
              disabled={isProcessing || (requiresSelection && !selectedIdea)}
              variant="primary"
              className="bg-green-600 hover:bg-green-700"
            >
              {requiresSelection 
                ? `✓ 确认选择点子${selectedIdea || '?'}并继续`
                : '✓ 接受并继续'
              }
            </Button>
            <Button
              onClick={handleRegenerate}
              disabled={isProcessing}
              variant="secondary"
            >
              🔄 重新生成{requiresSelection ? '4个新点子' : ''}
            </Button>
          </div>
          <Button
            onClick={handleReject}
            disabled={isProcessing}
            variant="danger"
          >
            ✗ 拒绝并跳过
          </Button>
        </div>
      </Card>
    </div>
  );
};
