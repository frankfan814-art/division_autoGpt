/**
 * Chapter Detail page - 章节详情和版本管理
 */

import { Link, useParams } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useChapterVersions, useChapters } from '@/hooks/useChapter';
import { useSessions } from '@/hooks/useSession';
import { QualityBadge } from '@/components/QualityBadge';
import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Textarea } from '@/components/ui/Textarea';
import { Input } from '@/components/ui/Input';
import { chaptersApi } from '@/api/client';

export const ChapterDetail = () => {
  const { sessionId, chapterIndex } = useParams<{
    sessionId: string;
    chapterIndex: string;
  }>();

  const chapterIndexNum = parseInt(chapterIndex || '0', 10);

  const {
    versions,
    totalVersions,
    isLoading,
    restoreVersion
  } = useChapterVersions(sessionId || '', chapterIndexNum);

  const { rewriteChapter, isRewriting, manualEditChapter, isEditing } = useChapters(sessionId || '');
  const { skipChapter, isSkipping } = useSessions();

  const [rewriteModalOpen, setRewriteModalOpen] = useState(false);
  const [rewriteReason, setRewriteReason] = useState('');
  const [rewriteFeedback, setRewriteFeedback] = useState('');

  // 🔥 手动编辑模式
  const [isEditMode, setIsEditMode] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editReason, setEditReason] = useState('');

  // 🔥 上下文信息
  const [contextData, setContextData] = useState<any>(null);

  // 获取章节上下文信息
  useEffect(() => {
    const fetchContext = async () => {
      if (!sessionId || chapterIndexNum === null) return;
      try {
        const response = await chaptersApi.getChapterContext(sessionId, chapterIndexNum);
        if (response.success) {
          setContextData(response.context);
        }
      } catch (error) {
        console.error('获取上下文失败:', error);
      }
    };
    fetchContext();
  }, [sessionId, chapterIndexNum]);

  const currentVersion = versions.find((v: any) => v.is_current);

  // 🔥 进入编辑模式
  const handleStartEdit = () => {
    setEditContent(currentVersion?.content || '');
    setIsEditMode(true);
  };

  // 🔥 保存手动编辑
  const handleSaveEdit = async () => {
    if (!editContent.trim()) {
      alert('内容不能为空');
      return;
    }

    try {
      await manualEditChapter({
        chapterIndex: chapterIndexNum,
        content: editContent,
        editReason: editReason || undefined,
      });
      setIsEditMode(false);
      setEditContent('');
      setEditReason('');
    } catch (error) {
      console.error('保存失败:', error);
      alert('保存失败，请重试');
    }
  };

  // 🔥 取消编辑
  const handleCancelEdit = () => {
    setIsEditMode(false);
    setEditContent('');
    setEditReason('');
  };

  const handleRewrite = async () => {
    try {
      await rewriteChapter({
        chapterIndex: chapterIndexNum,
        reason: rewriteReason || undefined,
        feedback: rewriteFeedback || undefined,
      });
      setRewriteModalOpen(false);
      setRewriteReason('');
      setRewriteFeedback('');
    } catch (error) {
      console.error('重写失败:', error);
    }
  };

  const handleRestore = async (versionId: string) => {
    if (confirm('确定要恢复到这个版本吗？当前版本将被替换。')) {
      try {
        await restoreVersion(versionId);
      } catch (error) {
        console.error('恢复失败:', error);
      }
    }
  };

  // 跳过章节处理函数
  const handleSkip = async () => {
    if (!confirm(`确定要跳过第 ${chapterIndexNum} 章吗？跳过后可以继续执行后续任务。`)) {
      return;
    }

    try {
      await skipChapter({ sessionId: sessionId || '', chapterIndex: chapterIndexNum });
      alert(`第 ${chapterIndexNum} 章已跳过`);
      // 可以选择跳转回章节列表
      // window.location.href = `/dashboard/${sessionId}/chapters`;
    } catch (error) {
      console.error('跳过失败:', error);
      alert('跳过失败，请重试');
    }
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              第 {chapterIndexNum} 章 - 详情
            </h1>
            <p className="mt-2 text-gray-600">
              查看章节内容、版本历史和质量评分
            </p>
          </div>
          <div className="flex gap-3">
            <Link to={`/dashboard/${sessionId}/chapters`}>
              <Button variant="secondary">返回列表</Button>
            </Link>
            {!isEditMode && (
              <>
                <Button variant="secondary" onClick={handleStartEdit}>
                  手动编辑
                </Button>
                <Button onClick={() => setRewriteModalOpen(true)}>
                  重写章节
                </Button>
                {/* 跳过按钮 - 当章节质量未通过时显示 */}
                {currentVersion && currentVersion.score < 0.8 && (
                  <Button variant="warning" onClick={handleSkip} disabled={isSkipping}>
                    {isSkipping ? '跳过中...' : '⏭️ 跳过章节'}
                  </Button>
                )}
              </>
            )}
            {isEditMode && (
              <>
                <Button variant="secondary" onClick={handleCancelEdit} disabled={isEditing}>
                  取消
                </Button>
                <Button onClick={handleSaveEdit} disabled={isEditing}>
                  {isEditing ? '保存中...' : '保存'}
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：当前版本内容 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 当前版本 */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  {isEditMode ? '编辑章节' : '当前版本'}
                </h2>
                {currentVersion && (
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      v{currentVersion.version_number}
                    </Badge>
                    <QualityBadge score={currentVersion.score} />
                  </div>
                )}
              </div>

              {currentVersion ? (
                <>
                  <div className="space-y-4 mb-6">
                    <div className="flex items-center gap-6 text-sm text-gray-600">
                      <div>
                        <span className="font-medium">质量评分:</span>{' '}
                        {(currentVersion.score * 100).toFixed(1)}%
                      </div>
                      <div>
                        <span className="font-medium">内容质量:</span>{' '}
                        {(currentVersion.quality_score * 100).toFixed(1)}%
                      </div>
                      <div>
                        <span className="font-medium">一致性:</span>{' '}
                        {(currentVersion.consistency_score * 100).toFixed(1)}%
                      </div>
                    </div>
                    {currentVersion.rewrite_reason && !isEditMode && (
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <span className="font-medium text-blue-900">重写原因: </span>
                        <span className="text-blue-800">{currentVersion.rewrite_reason}</span>
                      </div>
                    )}
                  </div>

                  {/* 查看模式 */}
                  {!isEditMode && (
                    <div className="prose max-w-none bg-gray-50 p-6 rounded-lg">
                      <p className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                        {currentVersion.content}
                      </p>
                    </div>
                  )}

                  {/* 编辑模式 */}
                  {isEditMode && (
                    <div className="space-y-4">
                      <Textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        placeholder="请输入章节内容..."
                        rows={20}
                        className="w-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          编辑原因（可选）
                        </label>
                        <Input
                          type="text"
                          value={editReason}
                          onChange={(e) => setEditReason(e.target.value)}
                          placeholder="例如：修正人物对话，增加场景描写..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <p className="text-sm text-blue-800">
                          💡 提示：手动编辑会创建一个新版本，原版本将被保留在历史记录中。
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="mt-4 pt-4 border-t text-sm text-gray-500">
                    <div>
                      创建时间: {new Date(currentVersion.created_at).toLocaleString('zh-CN')}
                    </div>
                    <div>
                      创建方式: {currentVersion.created_by === 'auto' ? '自动生成' : currentVersion.created_by === 'rewrite' ? '自动重写' : currentVersion.created_by === 'manual' ? '手动编辑' : '手动重写'}
                    </div>
                    {currentVersion.token_stats && (
                      <div>
                        Token 消耗: {currentVersion.token_stats.total_tokens} (成本: ${currentVersion.token_stats.cost_usd.toFixed(4)})
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  暂无内容
                </div>
              )}
            </Card>

            {/* 质量评估详情 */}
            {currentVersion?.evaluation && (
              <Card className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">质量评估详情</h2>
                <div className="space-y-4">
                  {currentVersion.evaluation.reasons && currentVersion.evaluation.reasons.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900 mb-2">优点</h3>
                      <ul className="list-disc list-inside space-y-1 text-gray-700">
                        {currentVersion.evaluation.reasons.map((reason: any, i: number) => (
                          <li key={i}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {currentVersion.evaluation.suggestions && currentVersion.evaluation.suggestions.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900 mb-2">建议</h3>
                      <ul className="list-disc list-inside space-y-1 text-gray-700">
                        {currentVersion.evaluation.suggestions.map((suggestion: any, i: number) => (
                          <li key={i}>{suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </Card>
            )}
          </div>

          {/* 右侧：版本历史 */}
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                版本历史 ({totalVersions})
              </h2>

              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-16 bg-gray-200 rounded"></div>
                    </div>
                  ))}
                </div>
              ) : versions.length === 0 ? (
                <p className="text-gray-500 text-center py-8">暂无版本历史</p>
              ) : (
                <div className="space-y-3">
                  {versions.map((version: any) => (
                    <div
                      key={version.id}
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                        version.is_current
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => !version.is_current && handleRestore(version.id)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={version.is_current ? 'primary' : 'secondary'}>
                            v{version.version_number}
                          </Badge>
                          {version.is_current && (
                            <Badge variant="success">当前</Badge>
                          )}
                        </div>
                        <QualityBadge score={version.score} size="sm" />
                      </div>

                      <div className="text-sm text-gray-600 mb-2">
                        <div>评分: {(version.score * 100).toFixed(1)}%</div>
                        {version.rewrite_reason && (
                          <div className="text-xs text-gray-500 mt-1">
                            {version.rewrite_reason}
                          </div>
                        )}
                      </div>

                      <div className="text-xs text-gray-500">
                        {new Date(version.created_at).toLocaleString('zh-CN')}
                      </div>

                      {!version.is_current && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <span className="text-xs text-blue-600">点击恢复此版本</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* 版本统计 */}
            {totalVersions > 1 && (
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">版本统计</h2>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">总版本数</span>
                    <span className="font-medium">{totalVersions}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">最高评分</span>
                    <span className="font-medium">
                      {(Math.max(...versions.map((v: any) => v.score)) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">平均评分</span>
                    <span className="font-medium">
                      {(versions.reduce((sum: number, v: any) => sum + v.score, 0) / versions.length * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </Card>
            )}

            {/* 🔥 上下文信息 - 按文档规范 */}
            {contextData && (
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">上下文信息</h2>

                {/* 相关人物 */}
                {contextData.characters && contextData.characters.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">相关人物</h3>
                    <div className="space-y-2">
                      {contextData.characters.slice(0, 5).map((char: any) => (
                        <div key={char.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{char.name}</span>
                            <Badge variant="secondary">
                              {char.role === 'protagonist' ? '主角' : char.role === 'supporting' ? '配角' : char.role === 'antagonist' ? '反派' : '路人'}
                            </Badge>
                          </div>
                          {char.personality_traits && char.personality_traits.length > 0 && (
                            <div className="flex gap-1">
                              {char.personality_traits.slice(0, 3).map((trait: string, i: number) => (
                                <span key={i} className="text-xs text-gray-600">
                                  {trait}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 相关门派 - 按文档要求 */}
                {contextData.factions && contextData.factions.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">相关门派</h3>
                    <div className="space-y-2">
                      {contextData.factions.map((faction: any) => (
                        <div key={faction.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{faction.name}</span>
                            <Badge variant={faction.relation === 'ally' ? 'success' : faction.relation === 'enemy' ? 'danger' : 'default'}>
                              {faction.relation === 'ally' ? '盟友' : faction.relation === 'enemy' ? '敌对' : '中立'}
                            </Badge>
                          </div>
                          {faction.core_value && (
                            <span className="text-xs text-gray-600">
                              {faction.core_value}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 相关伏笔 */}
                {contextData.foreshadows && contextData.foreshadows.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">相关伏笔</h3>
                    <div className="space-y-2">
                      {contextData.foreshadows.map((fs: any) => (
                        <div key={fs.id} className="p-2 bg-gray-50 rounded">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-gray-900 text-sm">{fs.name}</span>
                            <Badge variant={fs.importance === 'critical' ? 'danger' : fs.importance === 'major' ? 'primary' : 'default'}>
                              {fs.importance === 'critical' ? '关键' : fs.importance === 'major' ? '重要' : '次要'}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <span>{fs.relation === 'plant' ? '[埋设]' : fs.relation === 'payoff' ? '[回收]' : ''}</span>
                            {fs.plant_chapter && <span>第{fs.plant_chapter}章</span>}
                            {fs.payoff_chapter && <span>→ 第{fs.payoff_chapter}章</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 相邻章节 */}
                <div className="flex items-center justify-between text-sm pt-2 border-t">
                  <div>
                    {contextData.previous_chapter ? (
                      <Link
                        to={`/dashboard/${sessionId}/chapters/${contextData.previous_chapter.chapter_index}`}
                        className="text-blue-600 hover:underline"
                      >
                        ← 第{contextData.previous_chapter.chapter_index}章 {contextData.previous_chapter.title || ''}
                      </Link>
                    ) : (
                      <span className="text-gray-400">← 已是首章</span>
                    )}
                  </div>
                  <div>
                    {contextData.next_chapter ? (
                      <Link
                        to={`/dashboard/${sessionId}/chapters/${contextData.next_chapter.chapter_index}`}
                        className="text-blue-600 hover:underline"
                      >
                        第{contextData.next_chapter.chapter_index}章 {contextData.next_chapter.title || ''} →
                      </Link>
                    ) : (
                      <span className="text-gray-400">已是末章 →</span>
                    )}
                  </div>
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* 重写对话框 */}
        <Modal
          isOpen={rewriteModalOpen}
          onClose={() => setRewriteModalOpen(false)}
          title="重写章节"
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                重写原因（可选）
              </label>
              <Textarea
                value={rewriteReason}
                onChange={(e) => setRewriteReason(e.target.value)}
                placeholder="例如：质量不够好，需要更生动的描写..."
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                用户反馈（可选）
              </label>
              <Textarea
                value={rewriteFeedback}
                onChange={(e) => setRewriteFeedback(e.target.value)}
                placeholder="例如：人物对话不够自然，情节发展太慢..."
                rows={3}
              />
            </div>

            <div className="bg-yellow-50 p-4 rounded-lg">
              <p className="text-sm text-yellow-800">
                ⚠️ 重写将创建一个新版本，原版本将被保留在历史记录中。重写过程可能需要几分钟时间。
              </p>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                variant="secondary"
                onClick={() => setRewriteModalOpen(false)}
                disabled={isRewriting}
              >
                取消
              </Button>
              <Button
                onClick={handleRewrite}
                disabled={isRewriting || (!rewriteReason && !rewriteFeedback)}
              >
                {isRewriting ? '重写中...' : '开始重写'}
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </MainLayout>
  );
};
