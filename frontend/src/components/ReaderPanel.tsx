/**
 * ReaderPanel - 阅读器面板（增强版）
 *
 * 支持查看所有任务生成的内容：
 * - 大纲、世界观、人物、事件等基础任务
 * - 所有章节内容
 * - 按任务类型筛选浏览
 */

import { useState, useEffect, useMemo } from 'react';
import { usePreview } from '@/hooks/usePreview';
import { useTaskProgress } from '@/hooks/useTask';
import { useTasks } from '@/hooks/useTask';
import { Button } from '@/components/ui/Button';
import { useTaskStore } from '@/stores/taskStore';
import logger from '@/utils/logger';
import { ChevronLeft, ChevronRight, BookOpen, FileText, Users, Map, Clock, Zap, Shield, Star, Sparkles } from 'lucide-react';

interface ReaderPanelProps {
  sessionId: string;
}

// 任务类型配置
const taskTypeConfig: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  '创意脑暴': { icon: <Sparkles size={16} />, label: '创意脑暴', color: 'text-yellow-400' },
  '大纲': { icon: <BookOpen size={16} />, label: '大纲', color: 'text-blue-400' },
  '世界观规则': { icon: <Map size={16} />, label: '世界观', color: 'text-green-400' },
  '势力设计': { icon: <Shield size={16} />, label: '势力', color: 'text-purple-400' },
  '场景设计': { icon: <Map size={16} />, label: '场景', color: 'text-teal-400' },
  '人物设计': { icon: <Users size={16} />, label: '人物', color: 'text-pink-400' },
  '功法法宝': { icon: <Zap size={16} />, label: '功法法宝', color: 'text-orange-400' },
  '主角成长': { icon: <Star size={16} />, label: '主角成长', color: 'text-yellow-400' },
  '反派设计': { icon: <Shield size={16} />, label: '反派', color: 'text-red-400' },
  '事件': { icon: <FileText size={16} />, label: '事件', color: 'text-cyan-400' },
  '时间线': { icon: <Clock size={16} />, label: '时间线', color: 'text-indigo-400' },
  '伏笔列表': { icon: <Sparkles size={16} />, label: '伏笔', color: 'text-purple-400' },
  '章节内容': { icon: <BookOpen size={16} />, label: '章节', color: 'text-white' },
};

type ViewMode = 'chapters' | 'tasks';
type TaskFilter = 'all' | string;

export const ReaderPanel = ({ sessionId }: ReaderPanelProps) => {
  const { progress } = useTaskProgress(sessionId);
  const setCurrentSession = useTaskStore((state) => state.setCurrentSession);
  const { isLoading: tasksLoading } = useTasks(sessionId);
  const tasks = useTaskStore((state) => state.getTasks());

  const {
    outline,
    currentChapter,
    currentContent,
    totalChapters,
    nextChapter,
    prevChapter,
  } = usePreview(sessionId);

  // 视图状态
  const [viewMode, setViewMode] = useState<ViewMode>('chapters');
  const [selectedTaskType, setSelectedTaskType] = useState<TaskFilter>('all');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);

  // 设置当前会话到 taskStore
  useEffect(() => {
    logger.debug('🔄 ReaderPanel: Setting current session:', sessionId);
    setCurrentSession(sessionId);
  }, [sessionId, setCurrentSession]);

  // 获取所有非章节任务
  const nonChapterTasks = useMemo(() => {
    return tasks.filter(t => 
      t.task_type !== '章节内容' && 
      t.status === 'completed' && 
      t.result
    );
  }, [tasks]);

  // 获取所有章节任务
  const chapterTasks = useMemo(() => {
    return tasks.filter(t => 
      t.task_type === '章节内容' && 
      t.status === 'completed' && 
      t.result
    ).sort((a, b) => (a.chapter_index || 0) - (b.chapter_index || 0));
  }, [tasks]);

  // 获取筛选后的任务
  const filteredTasks = useMemo(() => {
    if (selectedTaskType === 'all') return nonChapterTasks;
    return nonChapterTasks.filter(t => t.task_type === selectedTaskType);
  }, [nonChapterTasks, selectedTaskType]);

  // 获取当前选中的任务内容
  const selectedTaskContent = useMemo(() => {
    if (!selectedTaskId) return null;
    const task = tasks.find(t => t.task_id === selectedTaskId);
    return task?.result || null;
  }, [selectedTaskId, tasks]);

  // 获取任务类型统计
  const taskTypeStats = useMemo(() => {
    const stats: Record<string, number> = {};
    nonChapterTasks.forEach(t => {
      stats[t.task_type] = (stats[t.task_type] || 0) + 1;
    });
    return stats;
  }, [nonChapterTasks]);

  // 加载状态指示
  if (tasksLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900">
        <div className="text-center text-gray-400">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p>正在加载内容...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex bg-gray-900">
      {/* Sidebar */}
      {showSidebar && (
        <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
          {/* Sidebar Header */}
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">内容导航</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowSidebar(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </Button>
            </div>

            {/* View Mode Toggle */}
            <div className="flex bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setViewMode('chapters')}
                className={`flex-1 px-3 py-2 rounded-md text-sm transition-colors ${
                  viewMode === 'chapters'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                章节 ({chapterTasks.length})
              </button>
              <button
                onClick={() => setViewMode('tasks')}
                className={`flex-1 px-3 py-2 rounded-md text-sm transition-colors ${
                  viewMode === 'tasks'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                任务 ({nonChapterTasks.length})
              </button>
            </div>
          </div>

          {/* Sidebar Content */}
          <div className="flex-1 overflow-y-auto">
            {viewMode === 'chapters' ? (
              // 章节列表
              <div className="p-2">
                {outline && (
                  <button
                    onClick={() => {
                      setSelectedTaskId(null);
                      setViewMode('chapters');
                    }}
                    className="w-full text-left p-3 rounded-lg mb-2 bg-gray-700 hover:bg-gray-600 transition-colors"
                  >
                    <div className="flex items-center gap-2 text-blue-400">
                      <BookOpen size={16} />
                      <span className="font-medium">📋 大纲</span>
                    </div>
                  </button>
                )}

                <div className="text-xs text-gray-500 uppercase tracking-wider mb-2 px-2">
                  章节 ({chapterTasks.length}章)
                </div>

                {chapterTasks.map((task, index) => (
                  <button
                    key={task.task_id}
                    onClick={() => {
                      setSelectedTaskId(null);
                      setViewMode('chapters');
                    }}
                    className={`w-full text-left p-3 rounded-lg mb-1 transition-colors ${
                      currentChapter === (task.chapter_index || index + 1)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span>第{task.chapter_index || index + 1}章</span>
                      {task.evaluation?.score !== undefined && (
                        <span className={`text-xs ${
                          task.evaluation.score >= 0.7 ? 'text-green-400' : 'text-orange-400'
                        }`}>
                          {(task.evaluation.score * 100).toFixed(0)}分
                        </span>
                      )}
                    </div>
                  </button>
                ))}

                {chapterTasks.length === 0 && (
                  <div className="text-gray-500 text-sm p-4 text-center">
                    暂无章节内容
                  </div>
                )}
              </div>
            ) : (
              // 任务列表
              <div className="p-2">
                {/* 任务类型筛选 */}
                <div className="mb-4">
                  <div className="text-xs text-gray-500 uppercase tracking-wider mb-2 px-2">
                    筛选任务类型
                  </div>
                  <button
                    onClick={() => setSelectedTaskType('all')}
                    className={`w-full text-left px-3 py-2 rounded-lg mb-1 text-sm transition-colors ${
                      selectedTaskType === 'all'
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    全部任务 ({nonChapterTasks.length})
                  </button>

                  {Object.entries(taskTypeStats).map(([type, count]) => {
                    const config = taskTypeConfig[type] || { icon: <FileText size={16} />, label: type, color: 'text-gray-400' };
                    return (
                      <button
                        key={type}
                        onClick={() => setSelectedTaskType(type)}
                        className={`w-full text-left px-3 py-2 rounded-lg mb-1 text-sm transition-colors flex items-center justify-between ${
                          selectedTaskType === type
                            ? 'bg-gray-700 text-white'
                            : 'text-gray-400 hover:bg-gray-700'
                        }`}
                      >
                        <span className={`flex items-center gap-2 ${config.color}`}>
                          {config.icon}
                          {config.label}
                        </span>
                        <span className="text-gray-500 text-xs">{count}</span>
                      </button>
                    );
                  })}
                </div>

                {/* 任务列表 */}
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-2 px-2">
                  任务结果
                </div>

                {filteredTasks.map((task) => {
                  const config = taskTypeConfig[task.task_type] || { icon: <FileText size={16} />, label: task.task_type, color: 'text-gray-400' };
                  return (
                    <button
                      key={task.task_id}
                      onClick={() => setSelectedTaskId(task.task_id)}
                      className={`w-full text-left p-3 rounded-lg mb-1 transition-colors ${
                        selectedTaskId === task.task_id
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                      }`}
                    >
                      <div className={`flex items-center gap-2 mb-1 ${
                        selectedTaskId === task.task_id ? 'text-white' : config.color
                      }`}>
                        {config.icon}
                        <span className="font-medium text-sm">{config.label}</span>
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {task.result?.substring(0, 50)}...
                      </div>
                    </button>
                  );
                })}

                {filteredTasks.length === 0 && (
                  <div className="text-gray-500 text-sm p-4 text-center">
                    {selectedTaskType === 'all' ? '暂无已完成的任务' : '该类型暂无任务'}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {!showSidebar && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowSidebar(true)}
                className="text-gray-400 hover:text-white"
              >
                ☰ 导航
              </Button>
            )}

            {viewMode === 'chapters' && !selectedTaskId && totalChapters > 0 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={prevChapter}
                  disabled={currentChapter <= 1}
                  className="text-gray-400 hover:text-white disabled:opacity-50"
                >
                  <ChevronLeft size={16} />
                  上一章
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
                  下一章
                  <ChevronRight size={16} />
                </Button>
              </div>
            )}

            {selectedTaskId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedTaskId(null)}
                className="text-gray-400 hover:text-white"
              >
                ← 返回章节
              </Button>
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
          {selectedTaskId ? (
            // 显示选中的任务内容
            <div className="max-w-4xl mx-auto px-8 py-12">
              {(() => {
                const task = tasks.find(t => t.task_id === selectedTaskId);
                const config = task ? (taskTypeConfig[task.task_type] || { label: task.task_type, color: 'text-gray-400' }) : { label: '未知任务', color: 'text-gray-400' };
                
                return (
                  <>
                    <div className="flex items-center gap-3 mb-6">
                      <span className={config.color}>{config.label}</span>
                      <h1 className="text-2xl font-bold text-gray-100">
                        {task?.task_type === '章节内容' ? `第 ${task?.chapter_index} 章` : task?.task_type}
                      </h1>
                      {task?.evaluation?.score !== undefined && (
                        <span className={`px-2 py-1 rounded text-sm ${
                          task.evaluation.score >= 0.7 
                            ? 'bg-green-900 text-green-400' 
                            : 'bg-orange-900 text-orange-400'
                        }`}>
                          质量: {(task.evaluation.score * 100).toFixed(0)}分
                        </span>
                      )}
                    </div>

                    <div className="prose prose-lg prose-invert max-w-none">
                      <div className="text-gray-200 leading-loose text-lg whitespace-pre-wrap font-serif">
                        {selectedTaskContent}
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          ) : viewMode === 'chapters' ? (
            // 显示章节内容
            totalChapters > 0 ? (
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
                    该章节内容尚未生成
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <div className="text-6xl mb-4">📖</div>
                  <p className="text-lg">暂无章节内容</p>
                  {progress?.status === 'running' && (
                    <p className="text-sm mt-2">AI正在创作中...</p>
                  )}
                </div>
              </div>
            )
          ) : (
            // 任务模式但未选择任务
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="text-6xl mb-4">📋</div>
                <p className="text-lg">请选择左侧的任务查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
