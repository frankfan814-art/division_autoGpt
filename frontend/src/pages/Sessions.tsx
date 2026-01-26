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
import { useToast } from '@/components/ui/Toast';

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'running', label: '运行中' },
  { value: 'completed', label: '已完成' },
  { value: 'paused', label: '已暂停' },
  { value: 'failed', label: '失败' },
];

export const Sessions = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState<SessionStatus | ''>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportSessionId, setExportSessionId] = useState<string | null>(null);
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(new Set());
  const [showBatchDeleteConfirm, setShowBatchDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const pageSize = 20;  // 🔥 增加到每页20个

  const {
    sessions,
    total,
    isLoading,
    deleteSession,
    restoreSession,
    isRestoring,
    resumableSessions,
    refetch,
  } = useSessions({
    page: currentPage,
    page_size: pageSize,
    status: statusFilter || undefined,
  });

  const totalPages = Math.ceil(total / pageSize);
  const filteredSessions = sessions;

  // 🔥 批量选择处理
  const handleSelectSession = (sessionId: string) => {
    setSelectedSessions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sessionId)) {
        newSet.delete(sessionId);
      } else {
        newSet.add(sessionId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedSessions.size === sessions.length) {
      setSelectedSessions(new Set());
    } else {
      setSelectedSessions(new Set(sessions.map((s: Session) => s.id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedSessions.size === 0) {
      toast.error('请先选择要删除的项目');
      return;
    }
    setShowBatchDeleteConfirm(true);
  };

  const handleConfirmBatchDelete = async () => {
    setIsDeleting(true);
    try {
      const sessionIds = Array.from(selectedSessions);
      let successCount = 0;
      let failCount = 0;

      // 逐个删除（以便处理错误）
      for (const sessionId of sessionIds) {
        try {
          await deleteSession(sessionId);
          successCount++;
        } catch (error) {
          console.error(`删除会话 ${sessionId} 失败:`, error);
          failCount++;
        }
      }

      setSelectedSessions(new Set());
      setShowBatchDeleteConfirm(false);
      refetch();  // 刷新列表

      if (failCount === 0) {
        toast.success(`✅ 成功删除 ${successCount} 个项目`);
      } else if (successCount === 0) {
        toast.error(`❌ 删除失败，请重试`);
      } else {
        toast.warning(`⚠️ 部分删除成功：成功 ${successCount} 个，失败 ${failCount} 个`);
      }
    } catch (error) {
      console.error('批量删除失败:', error);
      toast.error('❌ 批量删除失败，请重试');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleExport = (id: string) => {
    setExportSessionId(id);
    setExportDialogOpen(true);
  };

  const handleRestore = async (id: string) => {
    try {
      await restoreSession(id);
      // 恢复成功后跳转到工作区
      navigate(`/workspace/${id}`);
    } catch (error: any) {
      console.error('恢复会话失败:', error);
      // 🔥 如果 restore 失败（比如没有 engine_state），自动使用 start
      // start 现在已经支持从已完成任务继续
      console.log('尝试使用 start 继续执行...');
      try {
        await startSession(id);
        navigate(`/workspace/${id}`);
      } catch (startError: any) {
        console.error('启动会话也失败:', startError);
        // 可以显示错误提示
      }
    }
  };

  // WebSocket real-time updates
  useWebSocket({
    onSessionUpdate: () => {
      // Session list updated via store automatically
    },
  });

  // 检查会话是否可以恢复
  const isResumable = (sessionId: string) => {
    return resumableSessions.some(s => s.id === sessionId);
  };

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
            {/* 🔥 批量操作按钮 */}
            {selectedSessions.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  已选择 {selectedSessions.size} 项
                </span>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={handleBatchDelete}
                >
                  🗑️ 批量删除
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedSessions(new Set())}
                >
                  取消选择
                </Button>
              </div>
            )}
            {selectedSessions.size === 0 && (
              <>
                <span className="text-sm text-gray-500">
                  共 {total} 个项目
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleSelectAll}
                >
                  ☑️ 全选
                </Button>
              </>
            )}
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
            {/* 可恢复会话提示 */}
            {resumableSessions.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-amber-800">
                      发现 {resumableSessions.length} 个可恢复的会话
                    </p>
                    <p className="text-xs text-amber-600 mt-1">
                      这些会话之前正在运行，可以恢复并继续创作
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="grid gap-4">
              {filteredSessions.map((session: Session) => (
                <div key={session.id} className="relative group">
                  {/* 🔥 复选框 - 改进样式 */}
                  <input
                    type="checkbox"
                    checked={selectedSessions.has(session.id)}
                    onChange={() => handleSelectSession(session.id)}
                    className="absolute top-5 left-5 z-10 w-5 h-5 rounded border-2 border-gray-300 text-blue-600 focus:ring-blue-500 focus:ring-2 cursor-pointer transition-all group-hover:scale-110"
                  />
                  <SessionCard
                    session={session}
                    onContinue={(id) => navigate(`/workspace/${id}`)}
                    onView={(id) => navigate(`/workspace/${id}/preview`)}
                    onRead={(id) => navigate(`/workspace/${id}/reader`)}
                    onExport={handleExport}
                    onDelete={deleteSession}
                    onRestore={isResumable(session.id) ? handleRestore : undefined}
                    isRestoring={isRestoring}
                    isResumable={isResumable(session.id)}
                    isSelected={selectedSessions.has(session.id)}
                  />
                </div>
              ))}
            </div>

            {/* 🔥 分页组件 - 始终显示总页数信息 */}
            <div className="flex items-center justify-center gap-2 py-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                上一页
              </Button>
              <div className="flex items-center gap-1">
                {/* 显示页码 */}
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-1 text-sm rounded ${
                        currentPage === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              <span className="text-sm text-gray-600">
                / {totalPages} 页
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

      {/* 🔥 批量删除确认对话框 */}
      {showBatchDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              确认批量删除
            </h3>
            <p className="text-gray-600 mb-4">
              确定要删除选中的 <span className="font-semibold">{selectedSessions.size}</span> 个项目吗？
            </p>
            <p className="text-sm text-gray-500 mb-6">
              此操作将删除每个项目的所有数据，包括：
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
                onClick={() => setShowBatchDeleteConfirm(false)}
                disabled={isDeleting}
              >
                取消
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleConfirmBatchDelete}
                disabled={isDeleting}
                isLoading={isDeleting}
              >
                {isDeleting ? '删除中...' : `确认删除 (${selectedSessions.size})`}
              </Button>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
};
