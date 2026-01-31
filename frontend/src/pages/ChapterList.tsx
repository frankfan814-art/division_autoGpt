/**
 * Chapter List page - 章节列表
 */

import { Link, useParams } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useChapters } from '@/hooks/useChapter';
import { useSession } from '@/hooks/useSession';
import { QualityBadge } from '@/components/QualityBadge';
import { Modal } from '@/components/ui/Modal';
import { useState } from 'react';

type FilterType = 'all' | 'completed' | 'running' | 'failed' | 'pending';
type SortType = 'index' | 'quality' | 'versions';

export const ChapterList = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { chapters, isLoadingChapters } = useChapters(sessionId || '');

  // 🔥 导出功能
  const { exportSession } = useSession(sessionId || '');
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<'txt' | 'md' | 'json'>('txt');
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  const [filter, setFilter] = useState<FilterType>('all');
  const [sort, setSort] = useState<SortType>('index');

  // 🔥 处理导出
  const handleExport = async () => {
    if (!sessionId) return;
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

  // 过滤章节 - 按文档规范
  const filteredChapters = chapters.filter((ch: any) => {
    if (filter === 'completed') return ch.status === 'completed';
    if (filter === 'running') return ch.status === 'running';
    if (filter === 'failed') return ch.status === 'failed';
    if (filter === 'pending') return !ch.status || ch.status === 'pending';
    return true; // all
  });

  // 统计各状态数量
  const statusCounts = {
    all: chapters.length,
    completed: chapters.filter((ch: any) => ch.status === 'completed').length,
    running: chapters.filter((ch: any) => ch.status === 'running').length,
    failed: chapters.filter((ch: any) => ch.status === 'failed').length,
    pending: chapters.filter((ch: any) => !ch.status || ch.status === 'pending').length,
  };

  // 排序章节
  const sortedChapters = [...filteredChapters].sort((a, b) => {
    if (sort === 'index') return a.chapter_index - b.chapter_index;
    if (sort === 'quality') {
      const scoreA = a.current_version?.score || 0;
      const scoreB = b.current_version?.score || 0;
      return scoreB - scoreA; // 降序
    }
    if (sort === 'versions') return b.total_versions - a.total_versions;
    return 0;
  });

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">章节列表</h1>
            <p className="mt-2 text-gray-600">查看和管理所有章节</p>
          </div>
          <div className="flex gap-3">
            <Link to={`/dashboard/${sessionId}`}>
              <Button variant="secondary">返回概览</Button>
            </Link>
            <Button onClick={() => setExportModalOpen(true)}>
              导出项目
            </Button>
          </div>
        </div>

        {/* 筛选和排序 - 按文档规范 */}
        <Card className="p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">筛选:</span>
              <div className="flex rounded-md shadow-sm" role="group">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-3 py-2 text-sm font-medium rounded-l-lg border ${
                    filter === 'all'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  全部 ({statusCounts.all})
                </button>
                <button
                  onClick={() => setFilter('completed')}
                  className={`px-3 py-2 text-sm font-medium border-t border-b ${
                    filter === 'completed'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  已完成 ({statusCounts.completed})
                </button>
                <button
                  onClick={() => setFilter('running')}
                  className={`px-3 py-2 text-sm font-medium border-t border-b ${
                    filter === 'running'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  进行中 ({statusCounts.running})
                </button>
                <button
                  onClick={() => setFilter('failed')}
                  className={`px-3 py-2 text-sm font-medium border-t border-b ${
                    filter === 'failed'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  待审核 ({statusCounts.failed})
                </button>
                <button
                  onClick={() => setFilter('pending')}
                  className={`px-3 py-2 text-sm font-medium rounded-r-lg border-t border-b border-r ${
                    filter === 'pending'
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  待生成 ({statusCounts.pending})
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
                <option value="index">章节号</option>
                <option value="quality">质量评分</option>
                <option value="versions">版本数量</option>
              </select>
            </div>
          </div>
        </Card>

        {/* 章节列表 */}
        {isLoadingChapters ? (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Card key={i} className="p-6">
                <div className="animate-pulse">
                  <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              </Card>
            ))}
          </div>
        ) : sortedChapters.length === 0 ? (
          <Card className="p-12 text-center">
            <div className="text-4xl mb-4">📭</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              没有找到符合条件的章节
            </h3>
            <p className="text-gray-600">
              {filter === 'all' ? '还没有任何章节。' : `没有${filter === 'completed' ? '已完成' : filter === 'running' ? '进行中' : filter === 'failed' ? '待审核' : '待生成'}的章节。`}
            </p>
          </Card>
        ) : (
          <div className="space-y-4">
            {sortedChapters.map((chapter) => (
              <Card key={chapter.chapter_index} className="p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        第 {chapter.chapter_index} 章
                      </h3>
                      <QualityBadge score={chapter.current_version?.score || 0} />
                      <span className="text-xs text-gray-500">
                        {chapter.total_versions} 个版本
                      </span>
                    </div>

                    {chapter.current_version ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <span>
                            当前版本: v{chapter.current_version.version_number}
                          </span>
                          <span>
                            质量评分: {(chapter.current_version.score * 100).toFixed(1)}%
                          </span>
                          <span>
                            Token: {chapter.current_version.content.length}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 line-clamp-2">
                          {chapter.current_version.content.substring(0, 200)}...
                        </p>
                      </div>
                    ) : (
                      <p className="text-gray-500">尚未生成内容</p>
                    )}
                  </div>

                  <div className="flex gap-2 ml-4">
                    <Link to={`/dashboard/${sessionId}/chapters/${chapter.chapter_index}`}>
                      <Button size="sm" variant="secondary">
                        查看详情
                      </Button>
                    </Link>
                  </div>
                </div>
              </Card>
            ))}
          </div>
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
    </MainLayout>
  );
};
