/**
 * Characters page - 人物管理
 */

import { Link, useParams } from 'react-router-dom';
import { useState } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { CharacterForm } from '@/components/CharacterForm';
import { useCharacters, Character } from '@/hooks/useCharacter';

type RoleFilterType = 'all' | 'protagonist' | 'antagonist' | 'supporting' | 'minor';
type SortType = 'name' | 'appearances' | 'relationships';

const roleLabels: Record<RoleFilterType, string> = {
  all: '全部',
  protagonist: '主角',
  antagonist: '反派',
  supporting: '配角',
  minor: '路人',
};

const roleBadgeVariants: Record<string, 'primary' | 'danger' | 'success' | 'default'> = {
  protagonist: 'primary',
  antagonist: 'danger',
  supporting: 'success',
  minor: 'default',
};

export const Characters = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [filter, setFilter] = useState<RoleFilterType>('all');
  const [sort, setSort] = useState<SortType>('appearances');

  // 模态框状态
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);

  const {
    characters,
    isLoading,
    stats,
    createCharacter,
    updateCharacter,
    deleteCharacter,
    isCreating,
    isUpdating,
    isDeleting,
  } = useCharacters(sessionId || '', filter !== 'all' ? filter : undefined);

  // 排序人物
  const sortedCharacters = [...characters].sort((a, b) => {
    if (sort === 'name') return (a.name || '').localeCompare(b.name || '');
    if (sort === 'appearances') return (b.appearances || 0) - (a.appearances || 0);
    if (sort === 'relationships') return (b.relationships_count || 0) - (a.relationships_count || 0);
    return 0;
  });

  // 统计数据
  const statsData = {
    total: stats?.total_characters || 0,
    protagonist: stats?.role_counts?.protagonist || 0,
    supporting: stats?.role_counts?.supporting || 0,
    antagonist: stats?.role_counts?.antagonist || 0,
    minor: stats?.role_counts?.minor || 0,
  };

  // 处理新增人物
  const handleCreate = async (data: Partial<Character>) => {
    try {
      await createCharacter(data);
      setCreateModalOpen(false);
    } catch (error) {
      console.error('创建人物失败:', error);
      alert('创建人物失败，请重试');
    }
  };

  // 处理编辑人物
  const handleEdit = async (data: Partial<Character>) => {
    if (!selectedCharacter?.id) return;
    try {
      await updateCharacter({ characterId: selectedCharacter.id, data });
      setEditModalOpen(false);
      setSelectedCharacter(null);
    } catch (error) {
      console.error('更新人物失败:', error);
      alert('更新人物失败，请重试');
    }
  };

  // 处理删除人物
  const handleDelete = async () => {
    if (!selectedCharacter?.id) return;
    try {
      await deleteCharacter(selectedCharacter.id);
      setDeleteModalOpen(false);
      setSelectedCharacter(null);
    } catch (error) {
      console.error('删除人物失败:', error);
      alert('删除人物失败，请重试');
    }
  };

  // 打开编辑对话框
  const openEditModal = (character: Character) => {
    setSelectedCharacter(character);
    setEditModalOpen(true);
  };

  // 打开删除对话框
  const openDeleteModal = (character: Character) => {
    setSelectedCharacter(character);
    setDeleteModalOpen(true);
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">人物管理</h1>
            <p className="mt-2 text-gray-600">管理小说中的人物设定和关系</p>
          </div>
          <div className="flex gap-3">
            <Link to={`/dashboard/${sessionId}`}>
              <Button variant="secondary">返回概览</Button>
            </Link>
            <Button onClick={() => setCreateModalOpen(true)}>新增人物</Button>
          </div>
        </div>

        {/* 筛选和排序 */}
        <Card className="p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">角色类型:</span>
              <div className="flex rounded-md shadow-sm" role="group">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-4 py-2 text-sm font-medium rounded-l-lg border ${
                    filter === 'all'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  全部 ({statsData.total})
                </button>
                <button
                  onClick={() => setFilter('protagonist')}
                  className={`px-4 py-2 text-sm font-medium border-t border-b ${
                    filter === 'protagonist'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  主角 ({statsData.protagonist})
                </button>
                <button
                  onClick={() => setFilter('supporting')}
                  className={`px-4 py-2 text-sm font-medium border-t border-b ${
                    filter === 'supporting'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  配角 ({statsData.supporting})
                </button>
                <button
                  onClick={() => setFilter('antagonist')}
                  className={`px-4 py-2 text-sm font-medium rounded-r-lg border ${
                    filter === 'antagonist'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  反派 ({statsData.antagonist})
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">排序:</span>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortType)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="appearances">出场次数</option>
                <option value="name">姓名</option>
                <option value="relationships">关系数量</option>
              </select>
            </div>
          </div>
        </Card>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">总人数</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{statsData.total}</p>
              </div>
              <div className="ml-4 text-3xl">👥</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">主角</p>
                <p className="mt-2 text-3xl font-bold text-blue-600">{statsData.protagonist}</p>
              </div>
              <div className="ml-4 text-3xl">⭐</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">配角</p>
                <p className="mt-2 text-3xl font-bold text-green-600">{statsData.supporting}</p>
              </div>
              <div className="ml-4 text-3xl">🎭</div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">反派</p>
                <p className="mt-2 text-3xl font-bold text-red-600">{statsData.antagonist}</p>
              </div>
              <div className="ml-4 text-3xl">😈</div>
            </div>
          </Card>
        </div>

        {/* 人物列表 */}
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
        ) : sortedCharacters.length === 0 ? (
          <Card className="p-12 text-center">
            <div className="text-4xl mb-4">👥</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              暂无人物数据
            </h3>
            <p className="text-gray-600 mb-6">
              {filter !== 'all' ? '该分类下暂无人物' : '点击"新增人物"开始创建'}
            </p>
            {filter === 'all' && (
              <Button onClick={() => setCreateModalOpen(true)}>新增人物</Button>
            )}
          </Card>
        ) : (
          <div className="space-y-4">
            {sortedCharacters.map((character) => (
              <Card key={character.id} className="p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">{character.name}</h3>
                      <Badge variant={roleBadgeVariants[character.role || 'minor'] || 'default'}>
                        {roleLabels[character.role as RoleFilterType] || character.role}
                      </Badge>
                      <span className="text-xs text-gray-500">
                        {character.gender === 'male' ? '男' : character.gender === 'female' ? '女' : '未知'}
                        {character.age && ` · ${character.age}岁`}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>出场: {character.appearances || 0}章</span>
                        <span>关系: {character.relationships_count || 0}个</span>
                        <span>成长阶段: {character.arc_stages || 0}个</span>
                      </div>

                      {character.personality?.traits && character.personality.traits.length > 0 && (
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-700">性格:</span>
                          <div className="flex gap-1">
                            {character.personality.traits.map((trait: any, i: number) => (
                              <span key={i} className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded-full">
                                {trait}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {character.background && (
                        <p className="text-sm text-gray-600 line-clamp-2">{character.background}</p>
                      )}

                      {character.goals?.main && (
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-medium text-gray-700">目标:</span>
                          <p className="text-sm text-gray-600">{character.goals.main}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2 ml-4">
                    <Link to={`/dashboard/${sessionId}/characters/${character.id}`}>
                      <Button size="sm" variant="secondary">
                        查看详情
                      </Button>
                    </Link>
                    <Button size="sm" onClick={() => openEditModal(character)}>
                      编辑
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="text-red-600 hover:bg-red-50"
                      onClick={() => openDeleteModal(character)}
                    >
                      删除
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* 新增人物对话框 */}
        <Modal
          isOpen={createModalOpen}
          onClose={() => setCreateModalOpen(false)}
          title="新增人物"
        >
          <CharacterForm
            onSubmit={handleCreate}
            onCancel={() => setCreateModalOpen(false)}
            submitLabel="创建"
            isSubmitting={isCreating}
          />
        </Modal>

        {/* 编辑人物对话框 */}
        <Modal
          isOpen={editModalOpen}
          onClose={() => {
            setEditModalOpen(false);
            setSelectedCharacter(null);
          }}
          title={`编辑人物: ${selectedCharacter?.name || ''}`}
        >
          <CharacterForm
            character={selectedCharacter || undefined}
            onSubmit={handleEdit}
            onCancel={() => {
              setEditModalOpen(false);
              setSelectedCharacter(null);
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
            setSelectedCharacter(null);
          }}
          title="确认删除"
        >
          <div className="space-y-4">
            <p className="text-gray-700">
              确定要删除人物 <strong>"{selectedCharacter?.name}"</strong> 吗？
            </p>
            <p className="text-sm text-red-600">
              ⚠️ 此操作不可恢复，相关的人物关系和成长弧光也会被删除。
            </p>
            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="secondary"
                onClick={() => {
                  setDeleteModalOpen(false);
                  setSelectedCharacter(null);
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
