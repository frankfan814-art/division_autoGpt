/**
 * API client for backend communication
 */

import axios from 'axios';
import type { Session, SessionCreateRequest, Task, TaskProgress, HealthResponse } from '@/types';
import logger from '@/utils/logger';

// API基础路径 - 开发环境通过Vite代理转发到后端
// 生产环境需要配置 VITE_API_BASE_URL 环境变量为完整的后端地址
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // 默认超时 5 分钟（AI 生成可能需要较长时间）
  timeout: 300000,
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
    logger.error('API error:', error.response?.data || error.message);
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

  // 获取可恢复的会话列表
  listResumable: async (): Promise<Session[]> => {
    const response = await apiClient.get<Session[]>('/sessions/resumable/list');
    return response.data;
  },

  // 恢复会话
  restore: async (sessionId: string): Promise<any> => {
    const response = await apiClient.post(`/sessions/${sessionId}/restore`);
    return response.data;
  },

  // 获取会话恢复信息
  getRestoreInfo: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/sessions/${sessionId}/restore-info`);
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
