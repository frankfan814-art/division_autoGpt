/**
 * API client for backend communication
 */

import axios from 'axios';
import type { Session, SessionCreateRequest, Task, TaskProgress, HealthResponse } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API error:', error.response?.data || error.message);
    return Promise.reject(error.response?.data || error.message);
  }
);

// Sessions API
export const sessionsApi = {
  list: async (params?: { status?: string; page?: number; page_size?: number }) => {
    const response = await apiClient.get<any>('/sessions', { params });
    return response.data;
  },

  get: async (sessionId: string): Promise<Session> => {
    const response = await apiClient.get<Session>(`/sessions/${sessionId}`);
    return response.data;
  },

  create: async (data: SessionCreateRequest): Promise<Session> => {
    const response = await apiClient.post<Session>('/sessions', data);
    return response.data;
  },

  update: async (sessionId: string, data: Partial<Session>): Promise<Session> => {
    const response = await apiClient.patch<Session>(`/sessions/${sessionId}`, data);
    return response.data;
  },

  delete: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/sessions/${sessionId}`);
  },

  getProgress: async (sessionId: string): Promise<TaskProgress> => {
    const response = await apiClient.get<TaskProgress>(`/sessions/${sessionId}/progress`);
    return response.data;
  },

  getTasks: async (
    sessionId: string,
    params?: { task_type?: string; chapter_index?: number }
  ): Promise<Task[]> => {
    const response = await apiClient.get<Task[]>(`/sessions/${sessionId}/tasks`, { params });
    return response.data;
  },

  pause: async (sessionId: string): Promise<any> => {
    const response = await apiClient.post(`/sessions/${sessionId}/pause`);
    return response.data;
  },

  resume: async (sessionId: string): Promise<any> => {
    const response = await apiClient.post(`/sessions/${sessionId}/resume`);
    return response.data;
  },

  stop: async (sessionId: string): Promise<any> => {
    const response = await apiClient.post(`/sessions/${sessionId}/stop`);
    return response.data;
  },

  export: async (sessionId: string, format: string = 'txt', include_metadata: boolean = true): Promise<Blob> => {
    const response = await apiClient.post(
      `/sessions/${sessionId}/export`,
      { format, include_metadata },
      { responseType: 'blob' }
    );
    return response.data;
  },
};

// Health API
export const healthApi = {
  check: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },
};

export default apiClient;
