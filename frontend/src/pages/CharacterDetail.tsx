/**
 * CharacterDetail page - 人物详情页面
 */

import { Link, useParams } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { CharacterForm } from '@/components/CharacterForm';
import { useCharacter, useCharacters, Character } from '@/hooks/useCharacter';
import { useState } from 'react';

const roleLabels: Record<string, string> = {
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

export const CharacterDetail = () => {
  const { sessionId, characterId } = useParams<{ sessionId: string; characterId: string }>();

  const { character, isLoading } = useCharacter(sessionId || '', characterId || '');
  const { updateCharacter, deleteCharacter } = useCharacters(sessionId || '');

  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const handleEdit = async (data: Partial<Character>) => {
    try {
      await updateCharacter({ characterId: characterId || '', data });
      setEditModalOpen(false);
    } catch (error) {
      console.error('更新人物失败:', error);
      alert('更新人物失败，请重试');
    }
  };

  const handleDelete = async () => {
    try {
      await deleteCharacter(characterId || '');
      setDeleteModalOpen(false);
      // 返回列表页
      window.location.href = `/dashboard/${sessionId}/characters`;
    } catch (error) {
      console.error('删除人物失败:', error);
      alert('删除人物失败，请重试');
    }
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-8"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (!character) {
    return (
      <MainLayout>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Card className="p-12 text-center">
            <div className="text-4xl mb-4">👤</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">人物不存在</h3>
            <p className="text-gray-600 mb-6">未找到该人物的信息</p>
            <Link to={`/dashboard/${sessionId}/characters`}>
              <Button>返回人物列表</Button>
            </Link>
          </Card>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link to={`/dashboard/${sessionId}/characters`} className="text-blue-600 hover:underline text-sm">
              ← 返回人物列表
            </Link>
            <h1 className="text-3xl font-bold text-gray-900 mt-2">{character.name}</h1>
            <div className="flex items-center gap-3 mt-2">
              <Badge variant={roleBadgeVariants[character.role || 'minor'] || 'default'}>
                {roleLabels[character.role || ''] || character.role}
              </Badge>
              {character.age && (
                <span className="text-gray-600">{character.age}岁</span>
              )}
              {character.gender && (
                <span className="text-gray-600">
                  {character.gender === 'male' ? '男' : character.gender === 'female' ? '女' : '其他'}
                </span>
              )}
              {character.appearances && (
                <span className="text-gray-600">出场 {character.appearances} 章</span>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setEditModalOpen(true)}>
              编辑人物
            </Button>
            <Button
              variant="secondary"
              className="text-red-600 hover:bg-red-50"
              onClick={() => setDeleteModalOpen(true)}
            >
              删除人物
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：主要信息 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 基本信息 */}
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">基本信息</h2>
              <div className="space-y-4">
                {character.appearance && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">外貌描写</h3>
                    <p className="text-gray-800">{character.appearance}</p>
                  </div>
                )}

                {character.background && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">背景故事</h3>
                    <p className="text-gray-800 whitespace-pre-wrap">{character.background}</p>
                  </div>
                )}

                {character.goals?.main && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">核心目标</h3>
                    <p className="text-gray-800">{character.goals.main}</p>
                  </div>
                )}
              </div>
            </Card>

            {/* 性格设定 */}
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">性格设定</h2>
              <div className="space-y-4">
                {character.personality?.traits && character.personality.traits.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">性格标签</h3>
                    <div className="flex flex-wrap gap-2">
                      {character.personality.traits.map((trait: any, i: number) => (
                        <Badge key={i} variant="primary">
                          {trait}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {character.personality?.description && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">性格描述</h3>
                    <p className="text-gray-800">{character.personality.description}</p>
                  </div>
                )}
              </div>
            </Card>

            {/* 对话风格 */}
            {character.voice_profile && (
              <Card className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">对话风格</h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2">语调</h3>
                      <Badge variant="secondary">
                        {character.voice_profile.voice === 'calm' && '冷静'}
                        {character.voice_profile.voice === 'energetic' && '活力'}
                        {character.voice_profile.voice === 'formal' && '正式'}
                        {character.voice_profile.voice === 'casual' && '随意'}
                        {character.voice_profile.voice === 'aggressive' && '强势'}
                        {character.voice_profile.voice === 'gentle' && '温和'}
                      </Badge>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2">说话方式</h3>
                      <Badge variant="secondary">
                        {character.voice_profile.speech_pattern === 'normal' && '正常'}
                        {character.voice_profile.speech_pattern === 'direct' && '直爽'}
                        {character.voice_profile.speech_pattern === 'polite' && '礼貌'}
                        {character.voice_profile.speech_pattern === 'formal' && '正式'}
                        {character.voice_profile.speech_pattern === 'casual' && '随意'}
                        {character.voice_profile.speech_pattern === 'aggressive' && '粗鲁'}
                      </Badge>
                    </div>
                  </div>

                  {character.voice_profile.catchphrases && character.voice_profile.catchphrases.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2">口头禅</h3>
                      <div className="flex flex-wrap gap-2">
                        {character.voice_profile.catchphrases.map((phrase, i) => (
                          <span key={i} className="px-3 py-1 bg-gray-100 text-gray-800 rounded-lg text-sm">
                            "{phrase}"
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* 人际关系 */}
            {character.relationships && character.relationships.length > 0 && (
              <Card className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">人际关系</h2>
                <div className="space-y-3">
                  {character.relationships.map((rel, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">
                          与 {rel.character_id} 的关系
                        </div>
                        <div className="text-sm text-gray-600 mt-1">{rel.description}</div>
                      </div>
                      <Badge variant="secondary">{rel.type}</Badge>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* 成长弧光 */}
            {character.development_arcs && character.development_arcs.length > 0 && (
              <Card className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">成长弧光</h2>
                <div className="space-y-4">
                  {character.development_arcs.map((arc, i) => (
                    <div key={i} className="border-l-4 border-blue-500 pl-4">
                      <div className="font-medium text-gray-900 mb-1">{arc.stage}</div>
                      <div className="text-sm text-gray-600 mb-2">{arc.description}</div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>章节: </span>
                        {arc.chapters.map((chapter, j) => (
                          <span key={j} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
                            第{chapter}章
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* 右侧：统计信息 */}
          <div className="space-y-6">
            {/* 统计概览 */}
            <Card className="p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">统计概览</h2>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">出场次数</span>
                  <span className="font-medium">{character.appearances || 0} 章</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">关系数量</span>
                  <span className="font-medium">{character.relationships?.length || 0} 个</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">成长阶段</span>
                  <span className="font-medium">{character.development_arcs?.length || 0} 个</span>
                </div>
              </div>
            </Card>

            {/* 快捷操作 */}
            <Card className="p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">快捷操作</h2>
              <div className="space-y-2">
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => setEditModalOpen(true)}
                >
                  编辑人物信息
                </Button>
                <Link to={`/dashboard/${sessionId}/chapters`}>
                  <Button variant="secondary" className="w-full">
                    查看相关章节
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        </div>

        {/* 编辑人物对话框 */}
        <Modal
          isOpen={editModalOpen}
          onClose={() => setEditModalOpen(false)}
          title={`编辑人物: ${character.name}`}
        >
          <CharacterForm
            character={character}
            onSubmit={handleEdit}
            onCancel={() => setEditModalOpen(false)}
            submitLabel="保存"
          />
        </Modal>

        {/* 删除确认对话框 */}
        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          title="确认删除"
        >
          <div className="space-y-4">
            <p className="text-gray-700">
              确定要删除人物 <strong>"{character.name}"</strong> 吗？
            </p>
            <p className="text-sm text-red-600">
              ⚠️ 此操作不可恢复，相关的人物关系和成长弧光也会被删除。
            </p>
            <div className="flex justify-end gap-3 pt-4">
              <Button variant="secondary" onClick={() => setDeleteModalOpen(false)}>
                取消
              </Button>
              <Button onClick={handleDelete}>确认删除</Button>
            </div>
          </div>
        </Modal>
      </div>
    </MainLayout>
  );
};
