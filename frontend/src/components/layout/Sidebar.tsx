/**
 * Sidebar component for workspace - 优化的侧边栏组件
 */

import { Link, useParams, useLocation } from 'react-router-dom';
import { useSessionStore } from '@/stores/sessionStore';
import { Badge } from '@/components/ui/Badge';
import {
  LayoutDashboard,
  ListTodo,
  Eye,
  ArrowLeft,
  Sparkles,
  Clock,
  CheckCircle2,
  XCircle,
  Pause,
  Play,
} from 'lucide-react';

interface SidebarProps {
  className?: string;
}

export const Sidebar = ({ className = '' }: SidebarProps) => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const location = useLocation();
  const currentSession = useSessionStore((state) => state.currentSession);
  const totalTasks = useSessionStore((state) => state.currentSession?.total_tasks || 0);
  const completedTasks = useSessionStore((state) => state.currentSession?.completed_tasks || 0);

  const statusConfig = {
    running: { icon: Play, color: 'info', label: '运行中' },
    completed: { icon: CheckCircle2, color: 'success', label: '已完成' },
    failed: { icon: XCircle, color: 'danger', label: '失败' },
    paused: { icon: Pause, color: 'warning', label: '已暂停' },
    created: { icon: Clock, color: 'default', label: '已创建' },
  };

  const currentStatus = currentSession?.status || 'created';
  const statusInfo = statusConfig[currentStatus as keyof typeof statusConfig] || statusConfig.created;
  const StatusIcon = statusInfo.icon;

  // 侧边栏菜单：总览、预览、任务列表
  // 阅读模式从会话列表直接进入，不在侧边栏显示
  const navItems = [
    {
      id: 'overview',
      label: '总览',
      icon: LayoutDashboard,
      path: `/workspace/${sessionId}`,
    },
    {
      id: 'preview',
      label: '预览',
      icon: Eye,
      path: `/workspace/${sessionId}/preview`,
    },
    {
      id: 'tasks',
      label: '任务列表',
      icon: ListTodo,
      path: `/workspace/${sessionId}/tasks`,
      badge: totalTasks > 0 ? `${completedTasks}/${totalTasks}` : undefined,
    },
  ];

  const progress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <aside
      className={`bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col ${className}`}
    >
      {/* Session Info */}
      {currentSession && (
        <div className="p-5 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
                {currentSession.title}
              </h3>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant={statusInfo.color as any} size="sm">
                  <StatusIcon className="w-3 h-3 mr-1" />
                  {statusInfo.label}
                </Badge>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {totalTasks} 个任务
                </span>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {totalTasks > 0 && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                <span>{progress >= 100 ? '✅ 已完成' : '完成进度'}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="progress-bar h-1.5 !bg-gray-200 dark:!bg-gray-700">
                <div
                  className={`progress-value ${progress >= 100 ? '!bg-green-500' : ''}`}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;

          return (
            <Link
              key={item.id}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group ${
                isActive
                  ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <Icon
                className={`w-5 h-5 flex-shrink-0 ${
                  isActive
                    ? 'text-primary-600 dark:text-primary-400'
                    : 'text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300'
                }`}
              />
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span
                  className={`text-xs ${
                    isActive
                      ? 'text-primary-600 dark:text-primary-400'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <Link
          to="/sessions"
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-all duration-200"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>返回会话列表</span>
        </Link>
      </div>
    </aside>
  );
};
