/**
 * Character hook for character management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { charactersApi } from '@/api/client';
import logger from '@/utils/logger';

export interface Character {
  id: string;
  name: string;
  role: 'protagonist' | 'antagonist' | 'supporting' | 'minor';
  age?: number;
  gender?: 'male' | 'female' | 'other';
  appearance?: string;
  personality?: {
    traits?: string[];
    description?: string;
  };
  background?: string;
  goals?: {
    main?: string;
    sub_goals?: string[];
  };
  voice_profile?: {
    voice?: string;
    speech_pattern?: string;
    catchphrases?: string[];
  };
  relationships_count?: number;
  arc_stages?: number;
  appearances?: number;
}

export interface CharacterDetail extends Character {
  relationships?: Array<{
    character_id: string;
    type: string;
    description: string;
  }>;
  development_arcs?: Array<{
    stage: string;
    chapters: number[];
    description: string;
  }>;
}

export const useCharacters = (sessionId: string, role?: string) => {
  const queryClient = useQueryClient();

  // 获取人物列表
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['characters', sessionId, role],
    queryFn: () => charactersApi.list(sessionId, role),
    enabled: !!sessionId,
  });

  // 获取人物统计
  const { data: stats } = useQuery({
    queryKey: ['character-stats', sessionId],
    queryFn: () => charactersApi.getStats(sessionId),
    enabled: !!sessionId,
  });

  // 新增人物
  const createMutation = useMutation({
    mutationFn: (data: Partial<Character>) => charactersApi.create(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['character-stats', sessionId] });
    },
    onError: (error) => {
      logger.error('创建人物失败:', error);
    },
  });

  // 更新人物
  const updateMutation = useMutation({
    mutationFn: ({ characterId, data }: { characterId: string; data: Partial<Character> }) =>
      charactersApi.update(sessionId, characterId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['character-stats', sessionId] });
    },
    onError: (error) => {
      logger.error('更新人物失败:', error);
    },
  });

  // 删除人物
  const deleteMutation = useMutation({
    mutationFn: (characterId: string) => charactersApi.delete(sessionId, characterId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['character-stats', sessionId] });
    },
    onError: (error) => {
      logger.error('删除人物失败:', error);
    },
  });

  return {
    characters: data?.characters || [],
    total: data?.total || 0,
    isLoading,
    error: error?.message || null,
    refetch,
    stats: stats?.stats || {
      total_characters: 0,
      role_counts: {},
      total_relationships: 0,
      total_appearances: 0,
      consistency_issues: [],
    },

    createCharacter: createMutation.mutateAsync,
    updateCharacter: updateMutation.mutateAsync,
    deleteCharacter: deleteMutation.mutateAsync,

    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

export const useCharacter = (sessionId: string, characterId: string) => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['character', sessionId, characterId],
    queryFn: () => charactersApi.getDetail(sessionId, characterId),
    enabled: !!sessionId && !!characterId,
  });

  return {
    character: data?.character as CharacterDetail | undefined,
    isLoading,
    error: error?.message || null,
    refetch,
  };
};
