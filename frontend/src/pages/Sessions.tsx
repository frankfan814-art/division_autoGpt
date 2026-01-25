/**
 * Sessions list page
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { SessionCard } from '@/components/SessionCard';
import { ExportDialog } from '@/components/ExportDialog';
import { useSessions } from '@/hooks/useSession';
import { useWebSocket } from '@/hooks/useWebSocket';
import { SessionStatus, Session } from '@/types';
import { Link } from 'react-router-dom';

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'running', label: '运行中' },
  { value: 'completed', label: '已完成' },
  { value: 'paused', label: '已暂停' },
  { value: 'failed', label: '失败' },
];

export const Sessions = () => {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<SessionStatus | ''>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportSessionId, setExportSessionId] = useState<string | null>(null);
  const pageSize = 10;

  const {
    sessions,
    total,
    isLoading,
    deleteSession,
  } = useSessions({ 
    page: currentPage, 
    page_size: pageSize,
    status: statusFilter || undefined,
  });

  const totalPages = Math.ceil(total / pageSize);
  const filteredSessions = sessions;

  const handleExport = (id: string) => {
    setExportSessionId(id);
    setExportDialogOpen(true);
  };

  // WebSocket real-time updates
  useWebSocket({
    onSessionUpdate: () => {
      // Session list updated via store automatically
    },
  });

  return (
    <MainLayout>
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">会话列表</h1>
            <p className="text-gray-600 mt-1">管理您的所有创作项目</p>
          </div>
          <Link to="/create">
            <Button>创建新项目</Button>
          </Link>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg border shadow-sm p-4 mb-6">
          <div className="flex items-center gap-4">
            <Select
              options={statusOptions}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as SessionStatus | '');
                setCurrentPage(1);
              }}
              className="w-40"
            />
            <div className="flex-1" />
            <span className="text-sm text-gray-500">
              共 {total} 个项目
            </span>
          </div>
        </div>

        {/* Sessions Grid */}
        {isLoading ? (
          <div className="grid gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-gray-100 rounded-lg h-48 animate-pulse" />
            ))}
          </div>
        ) : filteredSessions.length > 0 ? (
          <div className="space-y-6">
            <div className="grid gap-4">
              {filteredSessions.map((session: Session) => (
                <SessionCard
                  key={session.id}
                  session={session}
                  onContinue={(id) => navigate(`/workspace/${id}`)}
                  onView={(id) => navigate(`/workspace/${id}`)}
                  onExport={handleExport}
                  onDelete={deleteSession}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  上一页
                </Button>
                <span className="text-sm text-gray-600">
                  第 {currentPage} / {totalPages} 页
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  下一页
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-lg border shadow-sm p-12 text-center">
            <div className="text-gray-400 mb-4">
              <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">暂无项目</h3>
            <p className="text-gray-500 mb-4">创建第一个项目，开始AI辅助创作</p>
            <Link to="/create">
              <Button>创建新项目</Button>
            </Link>
          </div>
        )}
      </div>

      {/* Export Dialog */}
      {exportSessionId && (
        <ExportDialog
          sessionId={exportSessionId}
          isOpen={exportDialogOpen}
          onClose={() => {
            setExportDialogOpen(false);
            setExportSessionId(null);
          }}
        />
      )}
    </MainLayout>
  );
};
