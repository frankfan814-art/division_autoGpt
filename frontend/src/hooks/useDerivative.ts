/**
 * useDerivative hook - 二创配置管理
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { derivativeApi } from '@/api/client';

export type DerivativeType = 'sequel' | 'prequel' | 'spinoff' | 'adaptation' | 'fanfic' | 'rewrite';
export type ToneStyle = 'serious' | 'lighthearted' | 'dark' | 'comedy' | 'romance' | 'epic';

export interface DerivativeConfig {
  type: DerivativeType;
  title: string;
  target_chapter_count: number;
  target_word_count: number;
  tone: ToneStyle;
  writing_style: string;
  original_elements: string[];
  new_elements: string[];
  keep_original_characters: boolean;
  new_character_count: number;
  keep_original_worldview: boolean;
  world_changes: string;
  plot_direction: string;
  main_conflict: string;
  notes: string;
}

export interface DerivativeConfigUpdate {
  type?: DerivativeType;
  title?: string;
  target_chapter_count?: number;
  target_word_count?: number;
  tone?: ToneStyle;
  writing_style?: string;
  original_elements?: string[];
  new_elements?: string[];
  keep_original_characters?: boolean;
  new_character_count?: number;
  keep_original_worldview?: boolean;
  world_changes?: string;
  plot_direction?: string;
  main_conflict?: string;
  notes?: string;
}

// 获取二创配置
export const useDerivativeConfig = (sessionId: string) => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['derivativeConfig', sessionId],
    queryFn: () => derivativeApi.getConfig(sessionId),
    enabled: !!sessionId,
  });

  return {
    config: data?.config || null,
    isLoading,
    error,
    refetch,
    hasConfig: !!data?.config,
  };
};

// 创建二创配置
export const useCreateDerivativeConfig = (sessionId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DerivativeConfig) =>
      derivativeApi.createConfig(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['derivativeConfig', sessionId] });
    },
  });
};

// 更新二创配置
export const useUpdateDerivativeConfig = (sessionId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DerivativeConfigUpdate) =>
      derivativeApi.updateConfig(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['derivativeConfig', sessionId] });
    },
  });
};

// 删除二创配置
export const useDeleteDerivativeConfig = (sessionId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => derivativeApi.deleteConfig(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['derivativeConfig', sessionId] });
    },
  });
};

// 开始生成二创作品
export const useGenerateDerivative = (sessionId: string) => {
  return useMutation({
    mutationFn: () => derivativeApi.generate(sessionId),
  });
};

// 组合 Hook：二创配置管理的完整功能
export const useDerivativeCRUD = (sessionId: string) => {
  const { config, isLoading, refetch, hasConfig } = useDerivativeConfig(sessionId);

  const createMutation = useMutation({
    mutationFn: (data: DerivativeConfig) =>
      derivativeApi.createConfig(sessionId, data),
    onSuccess: () => {
      refetch();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: DerivativeConfigUpdate) =>
      derivativeApi.updateConfig(sessionId, data),
    onSuccess: () => {
      refetch();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => derivativeApi.deleteConfig(sessionId),
    onSuccess: () => {
      refetch();
    },
  });

  const generateMutation = useMutation({
    mutationFn: () => derivativeApi.generate(sessionId),
  });

  return {
    config,
    isLoading,
    hasConfig,
    refetch,
    createConfig: createMutation.mutateAsync,
    updateConfig: updateMutation.mutateAsync,
    deleteConfig: deleteMutation.mutateAsync,
    generate: generateMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isGenerating: generateMutation.isPending,
  };
};
