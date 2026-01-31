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

  // 跳过章节
  skipChapter: async (sessionId: string, chapterIndex: number): Promise<any> => {
    const response = await apiClient.post(`/sessions/${sessionId}/skip-chapter/${chapterIndex}`);
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

// Chapters API - 章节重写和版本管理
export const chaptersApi = {
  // 重写章节
  rewrite: async (
    sessionId: string,
    chapterIndex: number,
    reason?: string,
    feedback?: string,
    maxRetries: number = 3
  ): Promise<any> => {
    const response = await apiClient.post(`/chapters/${sessionId}/rewrite`, null, {
      params: { chapter_index: chapterIndex, reason, feedback, max_retries: maxRetries }
    });
    return response.data;
  },

  // 获取所有章节版本概览
  listVersions: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/chapters/${sessionId}/versions`);
    return response.data;
  },

  // 获取指定章节的所有版本
  getChapterVersions: async (sessionId: string, chapterIndex: number): Promise<any> => {
    const response = await apiClient.get(`/chapters/${sessionId}/chapters/${chapterIndex}/versions`);
    return response.data;
  },

  // 恢复到指定版本
  restoreVersion: async (sessionId: string, chapterIndex: number, versionId: string): Promise<any> => {
    const response = await apiClient.post(`/chapters/${sessionId}/chapters/${chapterIndex}/versions/${versionId}/restore`);
    return response.data;
  },

  // 获取版本详情
  getVersionDetail: async (sessionId: string, chapterIndex: number, versionId: string): Promise<any> => {
    const response = await apiClient.get(`/chapters/${sessionId}/chapters/${chapterIndex}/versions/${versionId}`);
    return response.data;
  },

  // 获取章节上下文信息
  getChapterContext: async (sessionId: string, chapterIndex: number): Promise<any> => {
    const response = await apiClient.get(`/chapters/${sessionId}/chapters/${chapterIndex}/context`);
    return response.data;
  },

  // 手动编辑并保存章节内容
  manualEdit: async (
    sessionId: string,
    chapterIndex: number,
    content: string,
    editReason?: string
  ): Promise<any> => {
    const response = await apiClient.post(
      `/chapters/${sessionId}/chapters/${chapterIndex}/manual-edit`,
      { content, edit_reason: editReason }
    );
    return response.data;
  },
};

// Characters API - 人物管理
export const charactersApi = {
  // 获取人物列表
  list: async (sessionId: string, role?: string): Promise<any> => {
    const response = await apiClient.get(`/characters/${sessionId}`, {
      params: role ? { role } : {}
    });
    return response.data;
  },

  // 获取人物详情
  getDetail: async (sessionId: string, characterId: string): Promise<any> => {
    const response = await apiClient.get(`/characters/${sessionId}/${characterId}`);
    return response.data;
  },

  // 获取人物统计
  getStats: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/characters/${sessionId}/stats`);
    return response.data;
  },

  // 创建人物
  create: async (sessionId: string, data: any): Promise<any> => {
    const response = await apiClient.post(`/characters/${sessionId}`, data);
    return response.data;
  },

  // 更新人物
  update: async (sessionId: string, characterId: string, data: any): Promise<any> => {
    const response = await apiClient.put(`/characters/${sessionId}/${characterId}`, data);
    return response.data;
  },

  // 删除人物
  delete: async (sessionId: string, characterId: string): Promise<any> => {
    const response = await apiClient.delete(`/characters/${sessionId}/${characterId}`);
    return response.data;
  },
};

// Foreshadows API - 伏笔追踪
export const foreshadowsApi = {
  // 获取伏笔列表
  list: async (sessionId: string, status?: string, importance?: string): Promise<any> => {
    const response = await apiClient.get(`/foreshadows/${sessionId}`, {
      params: { status, importance }
    });
    return response.data;
  },

  // 获取伏笔统计
  getStats: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/foreshadows/${sessionId}/stats`);
    return response.data;
  },

  // 获取伏笔警告
  getWarnings: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/foreshadows/${sessionId}/warnings`);
    return response.data;
  },

  // 获取伏笔详情
  getDetail: async (sessionId: string, elementId: string): Promise<any> => {
    const response = await apiClient.get(`/foreshadows/${sessionId}/${elementId}`);
    return response.data;
  },

  // 创建伏笔
  create: async (sessionId: string, data: any): Promise<any> => {
    const response = await apiClient.post(`/foreshadows/${sessionId}`, data);
    return response.data;
  },

  // 更新伏笔
  update: async (sessionId: string, elementId: string, data: any): Promise<any> => {
    const response = await apiClient.put(`/foreshadows/${sessionId}/${elementId}`, data);
    return response.data;
  },

  // 删除伏笔
  delete: async (sessionId: string, elementId: string): Promise<any> => {
    const response = await apiClient.delete(`/foreshadows/${sessionId}/${elementId}`);
    return response.data;
  },
};

// Derivative API - 二创配置
export const derivativeApi = {
  // 获取二创配置
  getConfig: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/derivative/${sessionId}`);
    return response.data;
  },

  // 创建二创配置
  createConfig: async (sessionId: string, data: any): Promise<any> => {
    const response = await apiClient.post(`/derivative/${sessionId}`, data);
    return response.data;
  },

  // 更新二创配置
  updateConfig: async (sessionId: string, data: any): Promise<any> => {
    const response = await apiClient.put(`/derivative/${sessionId}`, data);
    return response.data;
  },

  // 删除二创配置
  deleteConfig: async (sessionId: string): Promise<any> => {
    const response = await apiClient.delete(`/derivative/${sessionId}`);
    return response.data;
  },

  // 开始生成二创作品
  generate: async (sessionId: string): Promise<any> => {
    const response = await apiClient.post(`/derivative/${sessionId}/generate`);
    return response.data;
  },
};

export default apiClient;
