/**
 * Dashboard page - 项目概览
 */

import { Link, useParams } from 'react-router-dom';
import { useState } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { QualityBadge } from '@/components/QualityBadge';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { useSessions, useSession } from '@/hooks/useSession';
import { useChapters } from '@/hooks/useChapter';
import { useForeshadowWarnings } from '@/hooks/useForeshadow';
import { useCharacterWarnings } from '@/hooks/useCharacterWarning';
import { useTaskStore } from '@/stores/taskStore';

export const Dashboard = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { sessions, pauseSession, resumeSession, stopSession, isPausing, isResuming, isStopping } = useSessions();
  const progress = useTaskStore((state) => state.progress);

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    sessionId || null
  );

  // Get the selected session object
  const selectedSession = sessions.find((s: any) => s.id === selectedSessionId);

  const { chapters } = useChapters(selectedSessionId || '');

  // 🔥 导出功能
  const { exportSession } = useSession(selectedSessionId || '');
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<'txt' | 'md' | 'json'>('txt');
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  // 🔥 处理导出
  const handleExport = async () => {
    if (!selectedSessionId) return;
    setIsExporting(true);
    try {
      await exportSession(exportFormat, includeMetadata);
      setExportModalOpen(false);
    } catch (error) {
      console.error('导出失败:', error);
      alert('导出失败，请重试');
    } finally {
      setIsExporting(false);
    }
  };

  // 🔥 控制处理函数
  const handlePause = async () => {
    if (!selectedSessionId) return;
    try {
      await pauseSession(selectedSessionId);
    } catch (error) {
      console.error('暂停失败:', error);
      alert('暂停失败，请重试');
    }
  };

  const handleResume = async () => {
    if (!selectedSessionId) return;
    try {
      await resumeSession(selectedSessionId);
    } catch (error) {
      console.error('继续失败:', error);
      alert('继续失败，请重试');
    }
  };

  const handleStop = async () => {
    if (!selectedSessionId) return;
    if (!confirm('确定要停止创作吗？')) return;
    try {
      await stopSession(selectedSessionId);
    } catch (error) {
      console.error('停止失败:', error);
      alert('停止失败，请重试');
    }
  };

  // 🔥 获取会话状态和样式
  const getSessionStatus = () => {
    if (progress?.status === 'running' || progress?.status === 'paused') {
      return progress.status;
    }
    return selectedSession?.status || 'idle';
  };

  const getStatusBadge = () => {
    const status = getSessionStatus();
    switch (status) {
      case 'running':
        return <Badge variant="success">运行中</Badge>;
      case 'paused':
        return <Badge variant="warning">已暂停</Badge>;
      case 'completed':
        return <Badge variant="success">已完成</Badge>;
      case 'failed':
        return <Badge variant="danger">已失败</Badge>;
      default:
        return <Badge variant="default">未开始</Badge>;
    }
  };

  // 获取伏笔警告和人物一致性警告
  const { warnings: foreshadowWarnings, isLoading: foreshadowLoading } = useForeshadowWarnings(
    selectedSessionId || ''
  );
  const { warnings: characterWarnings, isLoading: characterLoading } = useCharacterWarnings(
    selectedSessionId || ''
  );

  // 计算统计数据
  const totalChapters = chapters.length;
  const totalVersions = chapters.reduce((sum: number, ch: any) => sum + ch.total_versions, 0);

  // 计算质量概览
  const qualityStats = chapters.reduce(
    (acc: any, ch: any) => {
      if (ch.current_version?.score) {
        const score = ch.current_version.score;
        if (score >= 0.8) acc.excellent++;
        else if (score >= 0.6) acc.good++;
        else acc.needsImprovement++;
      }
      return acc;
    },
    { excellent: 0, good: 0, needsImprovement: 0 }
  );

  // 获取低质量章节
  const lowQualityChapters = chapters.filter(
    (ch: any) => ch.current_version && ch.current_version.score < 0.6
  );

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">项目概览</h1>
              {getStatusBadge()}
            </div>
            <p className="mt-2 text-gray-600">
              {progress?.current_task ? `正在执行: ${progress.current_task}` : '查看创作进度和质量统计'}
            </p>
          </div>
          <div className="flex gap-3">
            {/* 🔥 控制按钮 - 按文档规范 */}
            {getSessionStatus() === 'running' && (
              <>
                <Button variant="warning" onClick={handlePause} disabled={isPausing}>
                  {isPausing ? '暂停中...' : '⏸️ 暂停'}
                </Button>
                <Button variant="danger" onClick={handleStop} disabled={isStopping}>
                  {isStopping ? '停止中...' : '⏹️ 停止'}
                </Button>
              </>
            )}
            {getSessionStatus() === 'paused' && (
              <>
                <Button variant="success" onClick={handleResume} disabled={isResuming}>
                  {isResuming ? '继续中...' : '🚀 继续生成'}
                </Button>
                <Button variant="danger" onClick={handleStop} disabled={isStopping}>
                  {isStopping ? '停止中...' : '⏹️ 停止'}
                </Button>
              </>
            )}
            {getSessionStatus() === 'idle' && (
              <Link to={`/workspace/${selectedSessionId}`} className="inline-block">
                <Button>
                  🚀 开始生成
                </Button>
              </Link>
            )}
            <Link to={`/workspace/${selectedSessionId}`}>
              <Button variant="secondary">进入工作区</Button>
            </Link>
            <Link to={`/dashboard/${selectedSessionId}/derivative`}>
              <Button variant="secondary">二创配置</Button>
            </Link>
            <Button variant="secondary" onClick={() => setReportModalOpen(true)}>
              📊 查看详细报告
            </Button>
            <Button onClick={() => setExportModalOpen(true)}>
              导出项目
            </Button>
          </div>
        </div>

        {/* 🔥 实时进度条 */}
        {progress && (progress.status === 'running' || progress.status === 'paused') && (
          <Card className="p-4 mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                创作进度
              </span>
              <span className="text-sm text-gray-600">
                {progress.completed_tasks || 0} / {progress.total_tasks || 0} 任务
                {progress.percentage !== undefined && ` (${progress.percentage.toFixed(1)}%)`}
              </span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${progress.percentage || 0}%` }}
              />
            </div>
            {progress.current_task && (
              <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                <span>📝 当前任务:</span>
                <span className="font-medium">{progress.current_task}</span>
                {progress.current_task_provider && (
                  <>
                    <span>|</span>
                    <span>{progress.current_task_provider}</span>
                    {progress.current_task_model && <span>{progress.current_task_model}</span>}
                  </>
                )}
              </div>
            )}
          </Card>
        )}

        {/* 会话选择器 */}
        {!sessionId && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              选择项目
            </label>
            <select
              value={selectedSessionId || ''}
              onChange={(e) => setSelectedSessionId(e.target.value || null)}
              className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">请选择项目...</option>
              {sessions.map((s: any) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>
        )}

        {selectedSessionId ? (
          <>
            {/* 进度统计卡片 - 按文档规范 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <Card className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600">总章节数</p>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{totalChapters}</p>
                    <p className="text-xs text-gray-500 mt-1">目标: {progress?.total_chapters || '-'}章</p>
                  </div>
                  <div className="ml-4 text-3xl">📖</div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600">已完成</p>
                    <p className="mt-2 text-3xl font-bold text-green-600">
                      {chapters.filter((ch: any) => ch.status === 'completed').length}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">进行中: {chapters.filter((ch: any) => ch.status === 'running').length}章</p>
                  </div>
                  <div className="ml-4 text-3xl">✅</div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600">待审核</p>
                    <p className="mt-2 text-3xl font-bold text-orange-600">
                      {chapters.filter((ch: any) => ch.status === 'failed').length}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">质量未通过</p>
                  </div>
                  <div className="ml-4 text-3xl">⚠️</div>
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600">待生成</p>
                    <p className="mt-2 text-3xl font-bold text-gray-600">
                      {chapters.filter((ch: any) => !ch.status || ch.status === 'pending').length}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">剩余章节</p>
                  </div>
                  <div className="ml-4 text-3xl">⏳</div>
                </div>
              </Card>
            </div>

            {/* 质量概览 - 按文档规范 */}
            <div className="mb-8">
              <h2 className="text-xl font-bold text-gray-900 mb-4">🎯 质量概览</h2>
              <Card className="p-6">
                {totalChapters === 0 ? (
                  <p className="text-gray-500 text-center py-8">暂无章节数据</p>
                ) : (
                  <div className="space-y-4">
                    {/* 进度条可视化 */}
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-700 font-medium">完成进度</span>
                      <span className="text-sm text-gray-600">
                        {chapters.filter((ch: any) => ch.status === 'completed').length} / {totalChapters} 章
                      </span>
                    </div>
                    <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden flex">
                      <div
                        className="h-full bg-green-500"
                        style={{
                          width: `${totalChapters > 0 ? (chapters.filter((ch: any) => ch.status === 'completed').length / totalChapters) * 100 : 0}%`
                        }}
                      />
                      <div
                        className="h-full bg-orange-500"
                        style={{
                          width: `${totalChapters > 0 ? (chapters.filter((ch: any) => ch.status === 'failed').length / totalChapters) * 100 : 0}%`
                        }}
                      />
                      <div
                        className="h-full bg-gray-300"
                        style={{
                          width: `${totalChapters > 0 ? (chapters.filter((ch: any) => !ch.status || ch.status === 'pending').length / totalChapters) * 100 : 0}%`
                        }}
                      />
                    </div>
                    <div className="flex justify-center gap-6 text-sm">
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                        已完成 {chapters.filter((ch: any) => ch.status === 'completed').length}章
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-orange-500 rounded-full"></span>
                        待审核 {chapters.filter((ch: any) => ch.status === 'failed').length}章
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-gray-300 rounded-full"></span>
                        待生成 {chapters.filter((ch: any) => !ch.status || ch.status === 'pending').length}章
                      </span>
                    </div>

                    {/* 质量分数统计 */}
                    <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-green-600">
                          {(() => {
                            const completed = chapters.filter((c: any) => c.current_version?.score);
                            const scores = completed.map((c: any) => c.current_version.score * 100);
                            const avg = scores.length > 0 ? (scores.reduce((a: number, b: number) => a + b, 0) / scores.length).toFixed(1) : '-';
                            return avg;
                          })()}
                        </p>
                        <p className="text-xs text-gray-500">平均分</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-blue-600">
                          {(() => {
                            const completed = chapters.filter((c: any) => c.current_version?.score);
                            const scores = completed.map((c: any) => c.current_version.score * 100);
                            const max = scores.length > 0 ? Math.max(...scores).toFixed(1) : '-';
                            return max;
                          })()}
                        </p>
                        <p className="text-xs text-gray-500">最高分</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-red-600">
                          {(() => {
                            const completed = chapters.filter((c: any) => c.current_version?.score);
                            const scores = completed.map((c: any) => c.current_version.score * 100);
                            const min = scores.length > 0 ? Math.min(...scores).toFixed(1) : '-';
                            return min;
                          })()}
                        </p>
                        <p className="text-xs text-gray-500">最低分</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-gray-600">
                          {chapters.reduce((count: number, c: any) => count + (c.rewrite_count || 0), 0)}
                        </p>
                        <p className="text-xs text-gray-500">重写次数</p>
                      </div>
                    </div>

                    {/* 质量分布 */}
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-700">优秀 (≥80%)</span>
                        <div className="flex items-center gap-2">
                          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500"
                              style={{
                                width: `${totalChapters > 0 ? (qualityStats.excellent / totalChapters) * 100 : 0}%`
                              }}
                            />
                          </div>
                          <span className="text-sm font-medium w-10 text-right">{qualityStats.excellent}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-700">良好 (60-80%)</span>
                        <div className="flex items-center gap-2">
                          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500"
                              style={{
                                width: `${totalChapters > 0 ? (qualityStats.good / totalChapters) * 100 : 0}%`
                              }}
                            />
                          </div>
                          <span className="text-sm font-medium w-10 text-right">{qualityStats.good}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-700">待改进 (&lt;60%)</span>
                        <div className="flex items-center gap-2">
                          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-orange-500"
                              style={{
                                width: `${totalChapters > 0 ? (qualityStats.needsImprovement / totalChapters) * 100 : 0}%`
                              }}
                            />
                          </div>
                          <span className="text-sm font-medium w-10 text-right">{qualityStats.needsImprovement}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            </div>

            {/* 警告区域 - 按文档规范 */}
            <div className="mb-8 space-y-6">
              {/* 伏笔警告 */}
              {foreshadowWarnings.length > 0 && (
                <Card className="p-6 bg-yellow-50 border-yellow-200">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-yellow-900 flex items-center gap-2">
                      <span>🔮</span>
                      <span>伏笔警告</span>
                    </h2>
                    <Badge variant="warning">{foreshadowWarnings.length} 项警告</Badge>
                  </div>
                  <div className="space-y-3">
                    {foreshadowWarnings.slice(0, 3).map((warning: any) => (
                      <div key={warning.id} className="flex items-center justify-between p-3 bg-white rounded-lg border border-yellow-200">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-gray-900">{warning.name}</span>
                            <Badge variant={warning.importance === 'critical' ? 'danger' : warning.importance === 'major' ? 'primary' : 'default'}>
                              {warning.importance === 'critical' ? '关键' : warning.importance === 'major' ? '重要' : '次要'}
                            </Badge>
                            <Badge variant={warning.warning_type === 'overdue' ? 'danger' : 'warning'}>
                              {warning.warning_type === 'overdue' ? '已过期' : warning.warning_type === 'approaching' ? '即将到期' : '未埋设'}
                            </Badge>
                          </div>
                          <p className="text-sm text-yellow-700">{warning.message}</p>
                          {warning.plant_chapter && warning.payoff_chapter && (
                            <p className="text-xs text-gray-500 mt-1">
                              埋设: 第{warning.plant_chapter}章 → 预计回收: 第{warning.payoff_chapter}章
                            </p>
                          )}
                        </div>
                        <Link to={`/dashboard/${selectedSessionId}/foreshadow`}>
                          <Button size="sm" variant="secondary">
                            查看详情
                          </Button>
                        </Link>
                      </div>
                    ))}
                    {foreshadowWarnings.length > 3 && (
                      <div className="text-center">
                        <Link to={`/dashboard/${selectedSessionId}/foreshadow`}>
                          <Button size="sm" variant="secondary">
                            查看全部 {foreshadowWarnings.length} 个警告
                          </Button>
                        </Link>
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {/* 人物一致性警告 */}
              {characterWarnings.length > 0 && (
                <Card className="p-6 bg-orange-50 border-orange-200">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-orange-900 flex items-center gap-2">
                      <span>👥</span>
                      <span>人物一致性警告</span>
                    </h2>
                    <Badge variant="warning">{characterWarnings.length} 项警告</Badge>
                  </div>
                  <div className="space-y-3">
                    {characterWarnings.slice(0, 3).map((warning: any, index: number) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-white rounded-lg border border-orange-200">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-gray-900">{warning.character_name}</span>
                            <Badge variant={warning.severity === 'error' ? 'danger' : 'warning'}>
                              {warning.issue_type === 'voice_profile_missing' ? '缺少声音档案' :
                               warning.issue_type === 'personality_drift' ? '性格波动' :
                               warning.issue_type === 'relationship_inconsistent' ? '关系不一致' : '外观不匹配'}
                            </Badge>
                          </div>
                          <p className="text-sm text-orange-700">{warning.message}</p>
                          {warning.chapter_indices && warning.chapter_indices.length > 0 && (
                            <p className="text-xs text-gray-500 mt-1">
                              涉及章节: {warning.chapter_indices.join(', ')}
                            </p>
                          )}
                        </div>
                        <Link to={`/dashboard/${selectedSessionId}/characters`}>
                          <Button size="sm" variant="secondary">
                            查看详情
                          </Button>
                        </Link>
                      </div>
                    ))}
                    {characterWarnings.length > 3 && (
                      <div className="text-center">
                        <Link to={`/dashboard/${selectedSessionId}/characters`}>
                          <Button size="sm" variant="secondary">
                            查看全部 {characterWarnings.length} 个警告
                          </Button>
                        </Link>
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {/* 无警告提示 */}
              {foreshadowWarnings.length === 0 && characterWarnings.length === 0 && !foreshadowLoading && !characterLoading && (
                <Card className="p-6 bg-green-50 border-green-200">
                  <div className="flex items-center gap-3">
                    <div className="text-3xl">✅</div>
                    <div>
                      <h3 className="font-medium text-green-900">一切正常</h3>
                      <p className="text-sm text-green-700">暂无伏笔或人物一致性警告</p>
                    </div>
                  </div>
                </Card>
              )}
            </div>

            {/* 待处理问题 */}
            {lowQualityChapters.length > 0 && (
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">待处理问题</h2>
                <Card className="divide-y">
                  {lowQualityChapters.map((chapter: any) => (
                    <div key={chapter.chapter_index} className="p-4 flex items-center justify-between hover:bg-gray-50">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-gray-900">
                            第 {chapter.chapter_index} 章
                          </span>
                          <QualityBadge score={chapter.current_version?.score || 0} />
                        </div>
                        <p className="text-sm text-gray-500 mt-1">
                          当前评分: {((chapter.current_version?.score || 0) * 100).toFixed(1)}%
                        </p>
                      </div>
                      <Link
                        to={`/dashboard/${selectedSessionId}/chapters/${chapter.chapter_index}`}
                      >
                        <Button size="sm" variant="secondary">
                          查看详情
                        </Button>
                      </Link>
                    </div>
                  ))}
                </Card>
              </div>
            )}

            {lowQualityChapters.length === 0 && totalChapters > 0 && (
              <Card className="p-8 text-center">
                <div className="text-4xl mb-4">🎉</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  所有章节质量良好！
                </h3>
                <p className="text-gray-600">
                  暂无需要处理的低质量章节
                </p>
              </Card>
            )}
          </>
        ) : (
          <Card className="p-12 text-center">
            <div className="text-4xl mb-4">📋</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              请选择一个项目
            </h3>
            <p className="text-gray-600 mb-6">
              选择项目后查看详细的创作进度和质量统计
            </p>
            <Link to="/sessions">
              <Button>前往会话列表</Button>
            </Link>
          </Card>
        )}
      </div>

      {/* 🔥 导出对话框 */}
      <Modal
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        title="导出项目"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              导出格式
            </label>
            <div className="flex gap-3">
              <button
                type="button"
                className={`flex-1 px-4 py-3 rounded-lg border-2 text-center transition-colors ${
                  exportFormat === 'txt'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setExportFormat('txt')}
              >
                <div className="font-medium">TXT</div>
                <div className="text-xs text-gray-500 mt-1">纯文本格式</div>
              </button>
              <button
                type="button"
                className={`flex-1 px-4 py-3 rounded-lg border-2 text-center transition-colors ${
                  exportFormat === 'md'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setExportFormat('md')}
              >
                <div className="font-medium">Markdown</div>
                <div className="text-xs text-gray-500 mt-1">MD 格式</div>
              </button>
              <button
                type="button"
                className={`flex-1 px-4 py-3 rounded-lg border-2 text-center transition-colors ${
                  exportFormat === 'json'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setExportFormat('json')}
              >
                <div className="font-medium">JSON</div>
                <div className="text-xs text-gray-500 mt-1">结构化数据</div>
              </button>
            </div>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeMetadata}
                onChange={(e) => setIncludeMetadata(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">包含元数据（质量评分、创建时间等）</span>
            </label>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg">
            <p className="text-sm text-blue-800">
              💡 提示：导出将包含所有章节内容、人物设定、世界观信息等完整数据。
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => setExportModalOpen(false)}
              disabled={isExporting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleExport}
              disabled={isExporting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExporting ? '导出中...' : '导出'}
            </button>
          </div>
        </div>
      </Modal>

      {/* 🔥 详细报告对话框 */}
      <Modal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        title="详细报告"
        size="xl"
      >
        <div className="space-y-6">
          {/* 进度统计 */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">📈 进度统计</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">总章节数</span>
                <span className="font-medium">{chapters.length || 0} 章</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">已完成</span>
                <span className="font-medium text-green-600">
                  {chapters.filter((c: any) => c.status === 'completed').length} 章
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">待审核</span>
                <span className="font-medium text-orange-600">
                  {chapters.filter((c: any) => c.status === 'failed').length} 章
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">待生成</span>
                <span className="font-medium text-gray-600">
                  {chapters.filter((c: any) => !c.status || c.status === 'pending').length} 章
                </span>
              </div>
            </div>
          </div>

          {/* 质量概览 */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">🎯 质量概览</h3>
            <div className="space-y-3">
              {(() => {
                const completedChapters = chapters.filter((c: any) => c.status === 'completed' || c.status === 'failed');
                const scores = completedChapters.map((c: any) => (c.score || 0) * 100);
                const avgScore = scores.length > 0 ? (scores.reduce((a: number, b: number) => a + b, 0) / scores.length).toFixed(1) : '-';
                const maxScore = scores.length > 0 ? Math.max(...scores).toFixed(1) : '-';
                const minScore = scores.length > 0 ? Math.min(...scores).toFixed(1) : '-';
                const rewriteCount = chapters.reduce((count: number, c: any) => count + (c.rewrite_count || 0), 0);

                return (
                  <>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">平均分</span>
                      <span className="font-medium">{avgScore} 分</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">最高分</span>
                      <span className="font-medium text-green-600">{maxScore} 分</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">最低分</span>
                      <span className="font-medium text-red-600">{minScore} 分</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">重写次数</span>
                      <span className="font-medium">{rewriteCount} 次</span>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex justify-end pt-4 border-t">
            <Button variant="secondary" onClick={() => setReportModalOpen(false)}>
              关闭
            </Button>
          </div>
        </div>
      </Modal>
    </MainLayout>
  );
};
