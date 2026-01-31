/**
 * useForeshadow hook - 伏笔数据管理
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { foreshadowsApi } from '@/api/client';

// 伏笔类型定义
export type ForeshadowType = 'plot' | 'character' | 'worldview' | 'dialogue';
export type ForeshadowImportance = 'critical' | 'major' | 'minor';
export type ForeshadowStatus = 'pending' | 'planted' | 'paid_off';

export interface Foreshadow {
  id: string;
  name: string;
  type: ForeshadowType;
  importance: ForeshadowImportance;
  description: string;
  status: ForeshadowStatus;
  plant_chapter?: number;
  payoff_chapter?: number;
  warning?: string;
}

export interface ForeshadowDetail extends Foreshadow {
  plants: Array<{
    chapter_index: number;
    content: string;
    timestamp: string;
  }>;
  payoffs: Array<{
    chapter_index: number;
    content: string;
    timestamp: string;
  }>;
}

export interface ForeshadowStats {
  total_elements: number;
  status_counts: {
    pending: number;
    planted: number;
    paid_off: number;
  };
  importance_counts: {
    critical: number;
    major: number;
    minor: number;
  };
  warning_count: number;
}

export interface ForeshadowWarning {
  element_id: string;
  name: string;
  importance: ForeshadowImportance;
  type: 'overdue' | 'approaching';
  severity: 'high' | 'medium' | 'low';
  message: string;
  payoff_chapter?: number;
  current_chapter?: number;
}

export interface ForeshadowCreateInput {
  name: string;
  type?: ForeshadowType;
  importance?: ForeshadowImportance;
  description?: string;
  plant_chapter?: number;
  payoff_chapter?: number;
}

export interface ForeshadowUpdateInput {
  name?: string;
  type?: ForeshadowType;
  importance?: ForeshadowImportance;
  description?: string;
  plant_chapter?: number;
  payoff_chapter?: number;
}

// 获取伏笔列表
export const useForeshadows = (
  sessionId: string,
  filters?: { status?: ForeshadowStatus; importance?: ForeshadowImportance }
): {
  foreshadows: Foreshadow[];
  total: number;
  isLoading: boolean;
  error: unknown;
  refetch: () => void;
} => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['foreshadows', sessionId, filters],
    queryFn: () => foreshadowsApi.list(sessionId, filters?.status, filters?.importance),
    enabled: !!sessionId,
  });

  return {
    foreshadows: data?.foreshadows || [],
    total: data?.total || 0,
    isLoading,
    error,
    refetch,
  };
};

// 获取单个伏笔详情
export const useForeshadow = (
  sessionId: string,
  elementId: string
): {
  foreshadow: ForeshadowDetail | undefined;
  isLoading: boolean;
  error: unknown;
  refetch: () => void;
} => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['foreshadow', sessionId, elementId],
    queryFn: () => foreshadowsApi.getDetail(sessionId, elementId),
    enabled: !!sessionId && !!elementId,
  });

  return {
    foreshadow: data?.foreshadow,
    isLoading,
    error,
    refetch,
  };
};

// 获取伏笔统计
export const useForeshadowStats = (sessionId: string): {
  stats: ForeshadowStats | undefined;
  isLoading: boolean;
  error: unknown;
} => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['foreshadowStats', sessionId],
    queryFn: () => foreshadowsApi.getStats(sessionId),
    enabled: !!sessionId,
  });

  return {
    stats: data?.stats,
    isLoading,
    error,
  };
};

// 获取伏笔警告
export const useForeshadowWarnings = (sessionId: string): {
  warnings: ForeshadowWarning[];
  total: number;
  isLoading: boolean;
  error: unknown;
} => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['foreshadowWarnings', sessionId],
    queryFn: () => foreshadowsApi.getWarnings(sessionId),
    enabled: !!sessionId,
    refetchInterval: 30000, // 每30秒刷新一次
  });

  return {
    warnings: data?.warnings || [],
    total: data?.total || 0,
    isLoading,
    error,
  };
};

// 创建伏笔
export const useCreateForeshadow = (sessionId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ForeshadowCreateInput) =>
      foreshadowsApi.create(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['foreshadows', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowStats', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowWarnings', sessionId] });
    },
  });
};

// 更新伏笔
export const useUpdateForeshadow = (sessionId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ elementId, data }: { elementId: string; data: ForeshadowUpdateInput }) =>
      foreshadowsApi.update(sessionId, elementId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['foreshadows', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadow', sessionId, variables.elementId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowStats', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowWarnings', sessionId] });
    },
  });
};

// 删除伏笔
export const useDeleteForeshadow = (sessionId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (elementId: string) =>
      foreshadowsApi.delete(sessionId, elementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['foreshadows', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowStats', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowWarnings', sessionId] });
    },
  });
};

// 组合 Hook：伏笔管理的完整功能
export const useForeshadowCRUD = (sessionId: string) => {
  const queryClient = useQueryClient();
  const { foreshadows, total, isLoading, refetch } = useForeshadows(sessionId);
  const { stats } = useForeshadowStats(sessionId);
  const { warnings } = useForeshadowWarnings(sessionId);

  const createMutation = useMutation({
    mutationFn: (data: ForeshadowCreateInput) =>
      foreshadowsApi.create(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['foreshadows', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowStats', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowWarnings', sessionId] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ elementId, data }: { elementId: string; data: ForeshadowUpdateInput }) =>
      foreshadowsApi.update(sessionId, elementId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['foreshadows', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowStats', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowWarnings', sessionId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (elementId: string) =>
      foreshadowsApi.delete(sessionId, elementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['foreshadows', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowStats', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['foreshadowWarnings', sessionId] });
    },
  });

  return {
    foreshadows,
    total,
    stats,
    warnings,
    isLoading,
    refetch,
    createForeshadow: createMutation.mutateAsync,
    updateForeshadow: updateMutation.mutateAsync,
    deleteForeshadow: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
