/**
 * SessionCard component for displaying session information
 */

import { Session, SessionStatus } from '@/types';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Progress } from './ui/Progress';

export interface SessionCardProps {
  session: Session;
  onContinue?: (sessionId: string) => void;
  onView?: (sessionId: string) => void;
  onExport?: (sessionId: string) => void;
  onDelete?: (sessionId: string) => void;
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
  onExport,
  onDelete,
}: SessionCardProps) => {
  const statusInfo = statusConfig[session.status];
  const progress = session.total_tasks > 0
    ? Math.round((session.completed_tasks / session.total_tasks) * 100)
    : 0;

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
    <div className="bg-white border rounded-lg p-5 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            📖 {session.title}
          </h3>
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
          {session.status !== 'completed' && session.status !== 'failed' && onContinue && (
            <Button
              size="sm"
              variant="primary"
              onClick={() => onContinue(session.id)}
            >
              继续
            </Button>
          )}
          {onView && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onView(session.id)}
            >
              查看
            </Button>
          )}
          {session.status === 'completed' && onExport && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onExport(session.id)}
            >
              导出
            </Button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(session.id)}
              className="p-1.5 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"
              title="更多操作"
            >
              ⋯
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
