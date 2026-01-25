/**
 * Preview hook for content preview management
 */

import { useCallback, useEffect } from 'react';
import { usePreviewStore } from '@/stores/previewStore';
import { useTaskStore } from '@/stores/taskStore';

export const usePreview = (sessionId: string | null) => {
  const {
    outline,
    currentChapter,
    chapters,
    showMetadata,
    showEvaluation,
    setOutline,
    setCurrentChapter,
    setChapterContent,
    getChapterContent,
    setShowMetadata,
    setShowEvaluation,
    setError,
  } = usePreviewStore();

  const tasks = useTaskStore((state) => state.tasks);

  // Extract outline from tasks
  useEffect(() => {
    if (!sessionId) return;

    const outlineTask = tasks.find(
      (t) => t.task_type === '大纲' && t.status === 'completed' && t.result
    );

    if (outlineTask?.result) {
      setOutline(outlineTask.result);
    }
  }, [tasks, sessionId, setOutline]);

  // Extract chapter content from tasks
  useEffect(() => {
    if (!sessionId) return;

    const chapterTasks = tasks.filter(
      (t) => t.task_type === '章节内容' && t.status === 'completed' && t.result
    );

    chapterTasks.forEach((task) => {
      if (task.chapter_index !== undefined && task.result) {
        setChapterContent(task.chapter_index, task.result);
      }
    });
  }, [tasks, sessionId, setChapterContent]);

  const goToChapter = useCallback((chapterIndex: number) => {
    setCurrentChapter(chapterIndex);
  }, [setCurrentChapter]);

  const nextChapter = useCallback(() => {
    setCurrentChapter((prev) => prev + 1);
  }, [setCurrentChapter]);

  const prevChapter = useCallback(() => {
    setCurrentChapter((prev) => Math.max(1, prev - 1));
  }, [setCurrentChapter]);

  const getCurrentContent = useCallback(() => {
    return getChapterContent(currentChapter);
  }, [currentChapter, getChapterContent]);

  const getChapterTask = useCallback((chapterIndex: number) => {
    return tasks.find(
      (t) => t.task_type === '章节内容' && t.chapter_index === chapterIndex
    );
  }, [tasks]);

  const getTotalChapters = useCallback(() => {
    // Count unique chapter indices from chapter content tasks
    const chapterTasks = tasks.filter((t) => t.task_type === '章节内容');
    const uniqueChapters = new Set(chapterTasks.map((t) => t.chapter_index).filter(Boolean));
    return uniqueChapters.size || 0;
  }, [tasks]);

  return {
    // Content
    outline,
    currentChapter,
    currentContent: getCurrentContent(),
    chapters,
    totalChapters: getTotalChapters(),

    // Settings
    showMetadata,
    showEvaluation,

    // Actions
    goToChapter,
    nextChapter,
    prevChapter,
    getChapterTask,
    getChapterContent,
    setShowMetadata,
    setShowEvaluation,
    setError,
  };
};
