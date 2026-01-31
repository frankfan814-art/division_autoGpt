/**
 * Foreshadow page - 伏笔追踪
 */

import { Link, useParams } from 'react-router-dom';
import { useState } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { ForeshadowForm } from '@/components/ForeshadowForm';
import {
  useForeshadowCRUD,
  Foreshadow,
  ForeshadowImportance,
  ForeshadowStatus,
} from '@/hooks/useForeshadow';

type StatusFilterType = 'all' | ForeshadowStatus;
type ImportanceFilterType = 'all' | ForeshadowImportance;

const statusLabels: Record<StatusFilterType, string> = {
  all: '全部',
  planted: '已埋设',
  paid_off: '已回收',
  pending: '未开始',
};

const importanceLabels: Record<ImportanceFilterType, string> = {
  all: '全部',
  critical: '关键',
  major: '重要',
  minor: '次要',
};

const statusBadgeVariants: Record<string, 'success' | 'default' | 'warning'> = {
  paid_off: 'success',
  planted: 'default',
  pending: 'warning',
};

const importanceBadgeVariants: Record<string, 'danger' | 'primary' | 'default'> = {
  critical: 'danger',
  major: 'primary',
  minor: 'default',
};

export const ForeshadowPage = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [statusFilter, setStatusFilter] = useState<StatusFilterType>('all');
  const [importanceFilter, setImportanceFilter] = useState<ImportanceFilterType>('all');

  // 模态框状态
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedForeshadow, setSelectedForeshadow] = useState<Foreshadow | null>(null);

  const {
    foreshadows,
    stats,
    warnings,
    isLoading,
    createForeshadow,
    updateForeshadow,
    deleteForeshadow,
    isCreating,
    isUpdating,
    isDeleting,
  } = useForeshadowCRUD(sessionId || '');

  // 过滤伏笔
  const filteredForeshadows = foreshadows.filter((fs) => {
    if (statusFilter !== 'all' && fs.status !== statusFilter) return false;
    if (importanceFilter !== 'all' && fs.importance !== importanceFilter) return false;
    return true;
  });

  // 排序：按重要性和章节
  const sortedForeshadows = [...filteredForeshadows].sort((a, b) => {
    const importanceOrder = { critical: 0, major: 1, minor: 2 };
    const aImportance = importanceOrder[a.importance] ?? 3;
    const bImportance = importanceOrder[b.importance] ?? 3;
    if (aImportance !== bImportance) return aImportance - bImportance;
    return (a.plant_chapter ?? 999) - (b.plant_chapter ?? 999);
  });

  // 统计数据
  const statsData = {
    total: stats?.total_elements || 0,
    planted: stats?.status_counts?.planted || 0,
    paid_off: stats?.status_counts?.paid_off || 0,
    pending: stats?.status_counts?.pending || 0,
    critical: stats?.importance_counts?.critical || 0,
    major: stats?.importance_counts?.major || 0,
    minor: stats?.importance_counts?.minor || 0,
  };

  // 处理新增伏笔
  const handleCreate = async (data: Partial<Foreshadow>) => {
    try {
      await createForeshadow(data as any);
      setCreateModalOpen(false);
    } catch (error) {
      console.error('创建伏笔失败:', error);
      alert('创建伏笔失败，请重试');
    }
  };

  // 处理编辑伏笔
  const handleEdit = async (data: Partial<Foreshadow>) => {
    if (!selectedForeshadow?.id) return;
    try {
      await updateForeshadow({ elementId: selectedForeshadow.id, data: data as any });
      setEditModalOpen(false);
      setSelectedForeshadow(null);
    } catch (error) {
      console.error('更新伏笔失败:', error);
      alert('更新伏笔失败，请重试');
    }
  };

  // 处理删除伏笔
  const handleDelete = async () => {
    if (!selectedForeshadow?.id) return;
    try {
      await deleteForeshadow(selectedForeshadow.id);
      setDeleteModalOpen(false);
      setSelectedForeshadow(null);
    } catch (error) {
      console.error('删除伏笔失败:', error);
      alert('删除伏笔失败，请重试');
    }
  };

  // 打开编辑对话框
  const openEditModal = (foreshadow: Foreshadow) => {
    setSelectedForeshadow(foreshadow);
    setEditModalOpen(true);
  };

  // 打开删除对话框
  const openDeleteModal = (foreshadow: Foreshadow) => {
    setSelectedForeshadow(foreshadow);
    setDeleteModalOpen(true);
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">伏笔追踪</h1>
            <p className="mt-2 text-gray-600">管理小说中的伏笔埋设和回收</p>
          </div>
          <div className="flex gap-3">
            <Link to={`/dashboard/${sessionId}`}>
              <Button variant="secondary">返回概览</Button>
            </Link>
            <Button onClick={() => setCreateModalOpen(true)}>新增伏笔</Button>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">总伏笔</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{statsData.total}</p>
              </div>
              <div className="ml-4 text-3xl">🔮</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">已埋设</p>
                <p className="mt-2 text-3xl font-bold text-blue-600">{statsData.planted}</p>
              </div>
              <div className="ml-4 text-3xl">🌱</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">已回收</p>
                <p className="mt-2 text-3xl font-bold text-green-600">{statsData.paid_off}</p>
              </div>
              <div className="ml-4 text-3xl">✅</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">未开始</p>
                <p className="mt-2 text-3xl font-bold text-orange-600">{statsData.pending}</p>
              </div>
              <div className="ml-4 text-3xl">⏳</div>
            </div>
          </Card>
        </div>

        {/* 警告区域 - 按文档规范 */}
        {warnings.length > 0 && (
          <Card className="p-6 mb-6 bg-yellow-50 border-yellow-200">
            <h2 className="text-lg font-bold text-yellow-900 mb-4">⚠️ 警告</h2>
            <div className="space-y-2 text-sm">
              {/* 汇总统计警告 */}
              {warnings.filter(w => w.type === 'approaching').length > 0 && (
                <div className="text-orange-800">
                  • 有 {warnings.filter(w => w.type === 'approaching').length} 个伏笔即将到达预计回收章节，请确认是否已安排
                </div>
              )}
              {warnings.filter(w => w.type === 'overdue').length > 0 && (
                <div className="text-red-800">
                  • 有 {warnings.filter(w => w.type === 'overdue').length} 个伏笔已超过预计回收章节，请尽快安排
                </div>
              )}

              {/* 详细警告列表（可折叠） */}
              <details className="mt-3">
                <summary className="cursor-pointer text-yellow-900 hover:text-yellow-800">
                  查看详细警告 ({warnings.length})
                </summary>
                <div className="mt-3 space-y-2">
                  {warnings.map((warning) => (
                    <div
                      key={warning.element_id}
                      className={`p-3 rounded-lg border ${
                        warning.severity === 'high'
                          ? 'bg-red-50 border-red-200'
                          : 'bg-orange-50 border-orange-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{warning.name}</span>
                            <Badge variant={importanceBadgeVariants[warning.importance]}>
                              {importanceLabels[warning.importance]}
                            </Badge>
                            <Badge variant={warning.type === 'overdue' ? 'danger' : 'warning'}>
                              {warning.type === 'overdue' ? '已过期' : '即将到期'}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-700 mt-1">{warning.message}</p>
                        </div>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            const fs = foreshadows.find((f) => f.id === warning.element_id);
                            if (fs) openEditModal(fs);
                          }}
                        >
                          查看详情
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          </Card>
        )}

        {/* 筛选和排序 */}
        <Card className="p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">状态:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as StatusFilterType)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">全部 ({statsData.total})</option>
                <option value="planted">已埋设 ({statsData.planted})</option>
                <option value="paid_off">已回收 ({statsData.paid_off})</option>
                <option value="pending">未开始 ({statsData.pending})</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">重要性:</span>
              <select
                value={importanceFilter}
                onChange={(e) => setImportanceFilter(e.target.value as ImportanceFilterType)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">全部</option>
                <option value="critical">关键 ({statsData.critical})</option>
                <option value="major">重要 ({statsData.major})</option>
                <option value="minor">次要 ({statsData.minor})</option>
              </select>
            </div>
          </div>
        </Card>

        {/* 伏笔列表 */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="p-6">
                <div className="animate-pulse">
                  <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              </Card>
            ))}
          </div>
        ) : sortedForeshadows.length === 0 ? (
          <Card className="p-12 text-center">
            <div className="text-4xl mb-4">📭</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              暂无伏笔数据
            </h3>
            <p className="text-gray-600 mb-6">
              {statusFilter !== 'all' || importanceFilter !== 'all'
                ? '没有符合条件的伏笔'
                : '点击"新增伏笔"开始创建'}
            </p>
            {statusFilter === 'all' && importanceFilter === 'all' && (
              <Button onClick={() => setCreateModalOpen(true)}>新增伏笔</Button>
            )}
          </Card>
        ) : (
          <div className="space-y-4">
            {sortedForeshadows.map((foreshadow) => (
              <Card
                key={foreshadow.id}
                className="p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">{foreshadow.name}</h3>
                      <Badge variant={statusBadgeVariants[foreshadow.status] || 'default'}>
                        {statusLabels[foreshadow.status]}
                      </Badge>
                      <Badge variant={importanceBadgeVariants[foreshadow.importance] || 'default'}>
                        {importanceLabels[foreshadow.importance]}
                      </Badge>
                    </div>

                    <p className="text-sm text-gray-600 mb-3">{foreshadow.description}</p>

                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      {foreshadow.plant_chapter && (
                        <span>埋设: 第{foreshadow.plant_chapter}章</span>
                      )}
                      {foreshadow.payoff_chapter && (
                        <span>预计回收: 第{foreshadow.payoff_chapter}章</span>
                      )}
                      {foreshadow.warning && (
                        <span className="text-yellow-600">⚠️ {foreshadow.warning}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2 ml-4">
                    <Button size="sm" onClick={() => openEditModal(foreshadow)}>
                      编辑
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="text-red-600 hover:bg-red-50"
                      onClick={() => openDeleteModal(foreshadow)}
                    >
                      删除
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* 新增伏笔对话框 */}
        <Modal
          isOpen={createModalOpen}
          onClose={() => setCreateModalOpen(false)}
          title="新增伏笔"
        >
          <ForeshadowForm
            onSubmit={handleCreate}
            onCancel={() => setCreateModalOpen(false)}
            submitLabel="创建"
            isSubmitting={isCreating}
          />
        </Modal>

        {/* 编辑伏笔对话框 */}
        <Modal
          isOpen={editModalOpen}
          onClose={() => {
            setEditModalOpen(false);
            setSelectedForeshadow(null);
          }}
          title={`编辑伏笔: ${selectedForeshadow?.name || ''}`}
        >
          <ForeshadowForm
            foreshadow={selectedForeshadow || undefined}
            onSubmit={handleEdit}
            onCancel={() => {
              setEditModalOpen(false);
              setSelectedForeshadow(null);
            }}
            submitLabel="保存"
            isSubmitting={isUpdating}
          />
        </Modal>

        {/* 删除确认对话框 */}
        <Modal
          isOpen={deleteModalOpen}
          onClose={() => {
            setDeleteModalOpen(false);
            setSelectedForeshadow(null);
          }}
          title="确认删除"
        >
          <div className="space-y-4">
            <p className="text-gray-700">
              确定要删除伏笔 <strong>"{selectedForeshadow?.name}"</strong> 吗？
            </p>
            <p className="text-sm text-red-600">
              ⚠️ 此操作不可恢复。
            </p>
            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="secondary"
                onClick={() => {
                  setDeleteModalOpen(false);
                  setSelectedForeshadow(null);
                }}
                disabled={isDeleting}
              >
                取消
              </Button>
              <Button onClick={handleDelete} disabled={isDeleting}>
                {isDeleting ? '删除中...' : '确认删除'}
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </MainLayout>
  );
};
