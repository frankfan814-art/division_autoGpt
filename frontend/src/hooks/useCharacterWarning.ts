/**
 * Character warning hook for character consistency tracking
 */

import { useQuery } from '@tanstack/react-query';
import { charactersApi } from '@/api/client';

export interface CharacterConsistencyIssue {
  character_id: string;
  character_name: string;
  issue_type: 'voice_profile_missing' | 'personality_drift' | 'relationship_inconsistent' | 'appearance_mismatch';
  severity: 'warning' | 'error';
  message: string;
  chapter_indices?: number[];
  details?: any;
}

export const useCharacterWarnings = (sessionId: string) => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['character-warnings', sessionId],
    queryFn: () => charactersApi.getStats(sessionId),
    enabled: !!sessionId,
    staleTime: 30000,
    refetchInterval: 60000, // 每分钟刷新一次
  });

  // 从统计数据中提取一致性警告
  const warnings: CharacterConsistencyIssue[] = data?.consistency_issues || [];

  return {
    warnings,
    total: warnings.length,
    isLoading,
    error: error?.message || null,
    refetch,

    // 额外的统计数据
    stats: data || {
      total_characters: 0,
      by_role: {},
      consistency_issues: [],
    },
  };
};
