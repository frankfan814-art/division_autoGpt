/**
 * SessionCard component for displaying session information
 */

import { useState } from 'react';
import { Session, SessionStatus } from '@/types';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Progress } from './ui/Progress';

export interface SessionCardProps {
  session: Session;
  onContinue?: (sessionId: string) => void;
  onView?: (sessionId: string) => void;
  onRead?: (sessionId: string) => void;  // 🔥 新增：阅读按钮回调
  onExport?: (sessionId: string) => void;
  onDelete?: (sessionId: string) => void;
  onRestore?: (sessionId: string) => void;
  isRestoring?: boolean;
  isResumable?: boolean;
  isSelected?: boolean;  // 🔥 新增：是否被选中
}

const statusConfig: Record<SessionStatus, { icon: string; text: string; variant: 'default' | 'success' | 'warning' | 'danger' | 'info' }> = {
  created: { icon: '⏳', text: '未开始', variant: 'default' },
  running: { icon: '🟢', text: '进行中', variant: 'info' },
  paused: { icon: '🟡', text: '已暂停', variant: 'warning' },
  completed: { icon: '✅', text: '已完成', variant: 'success' },
  failed: { icon: '❌', text: '失败', variant: 'danger' },
  cancelled: { icon: '⛔', text: '已取消', variant: 'default' },
};

export const SessionCard = ({
  session,
  onContinue,
  onView,
  onRead,
  onExport,
  onDelete,
  onRestore,
  isRestoring,
  isResumable,
  isSelected = false,
}: SessionCardProps) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const statusInfo = statusConfig[session.status];
  const progress = session.total_tasks > 0
    ? Math.round((session.completed_tasks / session.total_tasks) * 100)
    : 0;

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = () => {
    if (onDelete) {
      onDelete(session.id);
    }
    setShowDeleteConfirm(false);
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <div className={`bg-white border rounded-lg p-5 pl-12 shadow-sm hover:shadow-md transition-all ${isResumable ? 'border-amber-300 bg-amber-50/30' : ''} ${isSelected ? 'ring-2 ring-blue-500 bg-blue-50/30' : ''}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-gray-900">
              📖 {session.title}
            </h3>
            {isResumable && (
              <Badge variant="warning" size="sm">
                🔄 可恢复
              </Badge>
            )}
          </div>
          {session.mode && (
            <span className="inline-block px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 rounded">
              {session.mode}
            </span>
          )}
        </div>
        <Badge variant={statusInfo.variant}>
          {statusInfo.icon} {statusInfo.text}
        </Badge>
      </div>

      {/* Progress */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-sm text-gray-600">完成进度</span>
          <span className="text-sm font-medium text-gray-900">{progress}%</span>
        </div>
        <Progress value={session.completed_tasks} max={session.total_tasks} />
        <div className="flex items-center justify-between mt-1.5 text-xs text-gray-500">
          <span>{session.completed_tasks} / {session.total_tasks} 任务</span>
          {session.failed_tasks > 0 && (
            <span className="text-red-600">失败: {session.failed_tasks}</span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-3 p-3 bg-gray-50 rounded-lg">
        <div>
          <div className="text-xs text-gray-500 mb-0.5">LLM 调用</div>
          <div className="text-sm font-semibold text-gray-900">
            {session.llm_calls.toLocaleString()} 次
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Token 消耗</div>
          <div className="text-sm font-semibold text-gray-900">
            {(session.tokens_used / 1000).toFixed(1)}K
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t">
        <span className="text-xs text-gray-500">
          最后编辑: {formatDate(session.updated_at)}
        </span>
        <div className="flex items-center gap-2">
          {/* 恢复按钮（优先显示） */}
          {isResumable && onRestore && (
            <Button
              size="sm"
              variant="primary"
              onClick={() => onRestore(session.id)}
              disabled={isRestoring}
            >
              {isRestoring ? '恢复中...' : '🔄 恢复会话'}
            </Button>
          )}
          {/* 继续按钮（非可恢复会话） */}
          {!isResumable && session.status !== 'completed' && session.status !== 'failed' && onContinue && (
            <Button
              size="sm"
              variant="primary"
              onClick={() => onContinue(session.id)}
            >
              继续
            </Button>
          )}
          {/* 阅读按钮（有内容时显示） */}
          {onRead && (session.status === 'completed' || session.completed_tasks > 0) && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onRead(session.id)}
            >
              📖 阅读
            </Button>
          )}
          {/* 查看按钮（只读总览） */}
          {onView && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onView(session.id)}
            >
              查看
            </Button>
          )}
          {/* 导出按钮（已完成会话） */}
          {session.status === 'completed' && onExport && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onExport(session.id)}
            >
              导出
            </Button>
          )}
          {onDelete && (
            <button
              onClick={handleDeleteClick}
              className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50 transition-colors"
              title="删除项目"
            >
              🗑️
            </button>
          )}
        </div>
      </div>

      {/* 🔥 删除确认对话框 */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              确认删除项目
            </h3>
            <p className="text-gray-600 mb-4">
              确定要删除项目 <span className="font-semibold">{session.title}</span> 吗？
            </p>
            <p className="text-sm text-gray-500 mb-6">
              此操作将删除项目的所有数据，包括：
            </p>
            <ul className="text-sm text-gray-600 mb-6 space-y-1 pl-4">
              <li>• 数据库中的会话记录</li>
              <li>• 任务结果和评估数据</li>
              <li>• 向量数据库中的所有向量数据</li>
              <li>• 生成的文件内容</li>
            </ul>
            <p className="text-sm text-red-600 font-medium mb-4">
              ⚠️ 此操作不可恢复！
            </p>
            <div className="flex items-center justify-end gap-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleCancelDelete}
              >
                取消
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleConfirmDelete}
              >
                确认删除
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
