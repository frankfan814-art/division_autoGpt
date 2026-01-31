/**
 * Chapter hook for chapter version management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chaptersApi } from '@/api/client';
import logger from '@/utils/logger';

export interface ChapterVersion {
  id: string;
  version_number: number;
  is_current: boolean;
  content: string;
  score: number;
  quality_score: number;
  consistency_score: number;
  evaluation: any;
  created_at: string;
  created_by: string;
  rewrite_reason?: string;
  token_stats: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
  };
}

export interface ChapterInfo {
  chapter_index: number;
  total_versions: number;
  current_version: {
    id: string;
    version_number: number;
    content: string;
    score: number;
  } | null;
  versions: ChapterVersion[];
}

export const useChapters = (sessionId: string) => {
  const queryClient = useQueryClient();

  // 获取所有章节版本概览
  const { data: chaptersData, isLoading: isLoadingChapters, error: chaptersError } = useQuery({
    queryKey: ['chapters', sessionId],
    queryFn: () => chaptersApi.listVersions(sessionId),
    enabled: !!sessionId,
    refetchInterval: 5000, // 每5秒刷新一次
  });

  // 重写章节
  const rewriteMutation = useMutation({
    mutationFn: ({
      chapterIndex,
      reason,
      feedback,
      maxRetries
    }: {
      chapterIndex: number;
      reason?: string;
      feedback?: string;
      maxRetries?: number;
    }) => chaptersApi.rewrite(sessionId, chapterIndex, reason, feedback, maxRetries),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
    onError: (error) => {
      logger.error('章节重写失败:', error);
    },
  });

  // 恢复版本
  const restoreMutation = useMutation({
    mutationFn: ({ chapterIndex, versionId }: { chapterIndex: number; versionId: string }) =>
      chaptersApi.restoreVersion(sessionId, chapterIndex, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', sessionId] });
    },
    onError: (error) => {
      logger.error('版本恢复失败:', error);
    },
  });

  // 手动编辑章节
  const manualEditMutation = useMutation({
    mutationFn: ({
      chapterIndex,
      content,
      editReason
    }: {
      chapterIndex: number;
      content: string;
      editReason?: string;
    }) => chaptersApi.manualEdit(sessionId, chapterIndex, content, editReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['chapter-versions', sessionId] });
    },
    onError: (error) => {
      logger.error('手动编辑保存失败:', error);
    },
  });

  return {
    chapters: chaptersData?.chapters || [],
    isLoadingChapters,
    chaptersError,

    rewriteChapter: rewriteMutation.mutateAsync,
    restoreVersion: restoreMutation.mutateAsync,
    manualEditChapter: manualEditMutation.mutateAsync,

    isRewriting: rewriteMutation.isPending,
    isRestoring: restoreMutation.isPending,
    isEditing: manualEditMutation.isPending,
  };
};

export const useChapterVersions = (sessionId: string, chapterIndex: number) => {
  // 获取指定章节的所有版本
  const { data: versionsData, isLoading, error, refetch } = useQuery({
    queryKey: ['chapter-versions', sessionId, chapterIndex],
    queryFn: () => chaptersApi.getChapterVersions(sessionId, chapterIndex),
    enabled: !!sessionId && chapterIndex >= 0,
  });

  // 恢复版本
  const queryClient = useQueryClient();
  const restoreMutation = useMutation({
    mutationFn: (versionId: string) =>
      chaptersApi.restoreVersion(sessionId, chapterIndex, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapter-versions', sessionId, chapterIndex] });
      queryClient.invalidateQueries({ queryKey: ['chapters', sessionId] });
    },
    onError: (error) => {
      logger.error('版本恢复失败:', error);
    },
  });

  return {
    versions: versionsData?.versions || [],
    totalVersions: versionsData?.total_versions || 0,
    isLoading,
    error,
    refetch,
    restoreVersion: restoreMutation.mutateAsync,
    isRestoring: restoreMutation.isPending,
  };
};

export const useChapterVersionDetail = (
  sessionId: string,
  chapterIndex: number,
  versionId: string
) => {
  // 获取版本详情
  const { data: versionData, isLoading, error } = useQuery({
    queryKey: ['chapter-version', sessionId, chapterIndex, versionId],
    queryFn: () => chaptersApi.getVersionDetail(sessionId, chapterIndex, versionId),
    enabled: !!sessionId && chapterIndex >= 0 && !!versionId,
  });

  return {
    version: versionData?.version,
    isLoading,
    error,
  };
};
