/**
 * Reader page for workspace
 */

import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { usePreview } from '@/hooks/usePreview';
import { useTaskProgress } from '@/hooks/useTask';
import { Button } from '@/components/ui/Button';

export const Reader = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { progress } = useTaskProgress(sessionId!);
  const {
    outline,
    currentChapter,
    currentContent,
    totalChapters,
    nextChapter,
    prevChapter,
  } = usePreview(sessionId!);

  const [showOutline, setShowOutline] = useState(false);

  if (!sessionId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        请选择一个会话
      </div>
    );
  }

  return (
    <div className="h-full flex bg-gray-900">
      {/* Sidebar - Outline */}
      {showOutline && (
        <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-700 flex items-center justify-between">
            <h3 className="text-white font-semibold">大纲</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowOutline(false)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {outline ? (
              <div className="prose prose-invert prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-gray-300 text-sm leading-relaxed">
                  {outline}
                </pre>
              </div>
            ) : (
              <div className="text-gray-500 text-sm">暂无大纲</div>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowOutline(!showOutline)}
              className="text-gray-400 hover:text-white"
            >
              {showOutline ? '隐藏' : '显示'}大纲
            </Button>

            {totalChapters > 0 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={prevChapter}
                  disabled={currentChapter <= 1}
                  className="text-gray-400 hover:text-white disabled:opacity-50"
                >
                  ← 上一章
                </Button>
                <span className="text-gray-300 text-sm">
                  第 {currentChapter} / {totalChapters} 章
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={nextChapter}
                  disabled={currentChapter >= totalChapters}
                  className="text-gray-400 hover:text-white disabled:opacity-50"
                >
                  下一章 →
                </Button>
              </div>
            )}
          </div>

          {/* Progress indicator */}
          {progress && (
            <div className="text-gray-400 text-sm">
              进度: {progress.completed_tasks}/{progress.total_tasks}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {totalChapters > 0 ? (
            <div className="max-w-3xl mx-auto px-8 py-12">
              <h1 className="text-3xl font-bold text-gray-100 mb-8 text-center">
                第 {currentChapter} 章
              </h1>

              {currentContent ? (
                <div className="prose prose-lg prose-invert max-w-none">
                  <div className="text-gray-200 leading-loose text-lg whitespace-pre-wrap font-serif">
                    {currentContent}
                  </div>
                </div>
              ) : (
                <div className="text-center py-20 text-gray-500">
                  {progress?.status === 'running' ? '正在生成内容...' : '等待内容生成...'}
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="text-6xl mb-4">📖</div>
                <p className="text-lg">等待内容生成...</p>
                {progress?.status === 'running' && (
                  <p className="text-sm mt-2">AI正在创作中</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
