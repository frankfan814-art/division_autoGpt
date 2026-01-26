/**
 * Session hook for session management
 */

import { useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sessionsApi } from '@/api/client';
import { useSessionStore } from '@/stores/sessionStore';
import { SessionCreateRequest, Session } from '@/types';

export const useSessions = (params?: { status?: string; page?: number; page_size?: number }) => {
  const queryClient = useQueryClient();
  const { setSessions, addSession, updateSession, removeSession, setLoading, setError } = useSessionStore();

  // Fetch sessions list
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['sessions', params],
    queryFn: () => sessionsApi.list(params),
    staleTime: 5000,
  });

  // Update store when data changes
  useEffect(() => {
    if (data?.items) {
      setSessions(data.items);
    }
    setLoading(isLoading);
    setError(error?.message || null);
  }, [data, isLoading, error, setSessions, setLoading, setError]);

  // Create session mutation
  const createMutation = useMutation({
    mutationFn: (data: SessionCreateRequest) => sessionsApi.create(data),
    onSuccess: (session) => {
      addSession(session);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  // Update session mutation
  const updateMutation = useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string; data: Partial<Session> }) =>
      sessionsApi.update(sessionId, data),
    onSuccess: (session) => {
      updateSession(session.id, session);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['session', session.id] });
    },
  });

  // Delete session mutation
  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.delete(sessionId),
    onSuccess: (_, sessionId) => {
      removeSession(sessionId);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
    onError: (error) => {
      console.error('删除会话失败:', error);
    },
  });

  // Pause session mutation
  const pauseMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.pause(sessionId),
    onSuccess: (result, sessionId) => {
      if (result?.status) {
        updateSession(sessionId, { status: result.status });
      }
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  // Resume session mutation
  const resumeMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.resume(sessionId),
    onSuccess: (result, sessionId) => {
      if (result?.status) {
        updateSession(sessionId, { status: result.status });
      }
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  // Stop session mutation
  const stopMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.stop(sessionId),
    onSuccess: (result, sessionId) => {
      if (result?.status) {
        updateSession(sessionId, { status: result.status });
      }
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  // Restore session mutation
  const restoreMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.restore(sessionId),
    onSuccess: (_, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });

  // Get resumable sessions
  const { data: resumableSessions = [] } = useQuery({
    queryKey: ['resumable-sessions'],
    queryFn: () => sessionsApi.listResumable(),
    refetchInterval: 10000, // 每10秒刷新一次
  });

  return {
    sessions: data?.items || [],
    total: data?.total || 0,
    page: data?.page || 1,
    pageSize: data?.page_size || 10,
    isLoading,
    error: error?.message || null,
    refetch,
    resumableSessions,

    createSession: createMutation.mutateAsync,
    updateSession: updateMutation.mutateAsync,
    deleteSession: deleteMutation.mutateAsync,
    pauseSession: pauseMutation.mutateAsync,
    resumeSession: resumeMutation.mutateAsync,
    stopSession: stopMutation.mutateAsync,
    restoreSession: restoreMutation.mutateAsync,

    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isPausing: pauseMutation.isPending,
    isResuming: resumeMutation.isPending,
    isStopping: stopMutation.isPending,
    isRestoring: restoreMutation.isPending,
  };
};

export const useSession = (sessionId: string) => {
  const { setCurrentSession, setLoading, setError } = useSessionStore();

  const { data: session, isLoading, error, refetch } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId),
    enabled: !!sessionId,
    refetchInterval: 2000,
  });

  useEffect(() => {
    if (session) {
      setCurrentSession(session);
    }
    setLoading(isLoading);
    setError(error?.message || null);
  }, [session, isLoading, error, setCurrentSession, setLoading, setError]);

  // Export session
  const exportSession = useCallback(async (format: string = 'txt', includeMetadata: boolean = true) => {
    try {
      const blob = await sessionsApi.export(sessionId, format, includeMetadata);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session-${sessionId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export failed:', err);
      throw err;
    }
  }, [sessionId]);

  return {
    session,
    isLoading,
    error: error?.message || null,
    refetch,
    exportSession,
  };
};
