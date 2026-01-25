/**
 * Chat hook for user feedback management
 */

import { useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { useChatStore } from '@/stores/chatStore';
import { ChatFeedback } from '@/types';

const FEEDBACK_API_URL = '/sessions/:sessionId/feedback';

export const useChat = (sessionId: string | null) => {
  const { messages, addMessage, clearMessages, setEnabled, setError } = useChatStore();

  // Send feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: async (feedback: ChatFeedback) => {
      if (!sessionId) throw new Error('No session ID provided');
      const url = FEEDBACK_API_URL.replace(':sessionId', sessionId);
      const response = await apiClient.post(url, feedback);
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Add user message to chat
      addMessage({
        role: 'user',
        content: variables.message,
        timestamp: new Date().toISOString(),
      });
    },
    onError: (error) => {
      setError(error.message);
    },
  });

  // Send quick feedback mutation
  const quickFeedbackMutation = useMutation({
    mutationFn: async ({ feedbackId, taskId }: { feedbackId: string; taskId?: string }) => {
      if (!sessionId) throw new Error('No session ID provided');
      const url = `/sessions/${sessionId}/tasks/${taskId || 'current'}/quick-feedback`;
      const response = await apiClient.post(url, { quick_feedback_id: feedbackId });
      return response.data;
    },
    onSuccess: () => {
      // Quick feedback is acknowledged
    },
    onError: (error) => {
      setError(error.message);
    },
  });

  const sendMessage = useCallback(async (message: string, scope?: 'current_task' | 'chapter' | 'all') => {
    if (!message.trim()) return;

    try {
      await feedbackMutation.mutateAsync({
        message,
        scope,
      });
    } catch (err) {
      console.error('Failed to send feedback:', err);
      throw err;
    }
  }, [feedbackMutation]);

  const sendQuickFeedback = useCallback(async (feedbackId: string, taskId?: string) => {
    try {
      await quickFeedbackMutation.mutateAsync({ feedbackId, taskId });
    } catch (err) {
      console.error('Failed to send quick feedback:', err);
      throw err;
    }
  }, [quickFeedbackMutation]);

  const clearHistory = useCallback(() => {
    clearMessages();
  }, [clearMessages]);

  const setChatEnabled = useCallback((enabled: boolean) => {
    setEnabled(enabled);
  }, [setEnabled]);

  return {
    messages,
    sendMessage,
    sendQuickFeedback,
    clearHistory,
    setChatEnabled,
    isLoading: feedbackMutation.isPending || quickFeedbackMutation.isPending,
    error: feedbackMutation.error?.message || quickFeedbackMutation.error?.message || null,
  };
};
