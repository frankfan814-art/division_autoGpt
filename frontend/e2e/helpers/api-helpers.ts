/**
 * API Helper Functions
 * Utility functions for API interactions during tests
 */

import { APIRequestContext, expect } from '@playwright/test';

const BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export interface CreateSessionData {
  title: string;
  mode?: string;
  goal: {
    genre?: string;
    style?: string;
    requirements?: string;
    chapter_count?: number;
    chapter_word_count?: number;
    word_count?: number;
  };
  config?: {
    approval_mode?: boolean;
  };
}

export interface Session {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export class ApiHelpers {
  constructor(private request: APIRequestContext) {}

  async checkHealth() {
    const response = await this.request.get(`${BASE_URL}/health`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createSession(data: CreateSessionData): Promise<Session> {
    const response = await this.request.post(`${BASE_URL}/sessions`, {
      data,
    });
    expect(response.ok()).toBeTruthy();
    const session = await response.json();
    expect(session).toHaveProperty('id');
    return session as Session;
  }

  async getSession(sessionId: string): Promise<Session> {
    const response = await this.request.get(`${BASE_URL}/sessions/${sessionId}`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getSessions(params?: { page?: number; page_size?: number; status?: string }) {
    const url = new URL(`${BASE_URL}/sessions`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, String(value));
      });
    }
    const response = await this.request.get(url.toString());
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async deleteSession(sessionId: string) {
    const response = await this.request.delete(`${BASE_URL}/sessions/${sessionId}`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getSessionProgress(sessionId: string) {
    const response = await this.request.get(`${BASE_URL}/sessions/${sessionId}/progress`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async startSession(sessionId: string) {
    const response = await this.request.post(`${BASE_URL}/sessions/${sessionId}/start`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async pauseSession(sessionId: string) {
    const response = await this.request.post(`${BASE_URL}/sessions/${sessionId}/pause`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async resumeSession(sessionId: string) {
    const response = await this.request.post(`${BASE_URL}/sessions/${sessionId}/resume`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async stopSession(sessionId: string) {
    const response = await this.request.post(`${BASE_URL}/sessions/${sessionId}/stop`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getStyles() {
    const response = await this.request.get(`${BASE_URL}/prompts/styles`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getTemplates() {
    const response = await this.request.get(`${BASE_URL}/prompts/templates`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async smartEnhance(input: string, currentConfig: any = null) {
    const response = await this.request.post(`${BASE_URL}/prompts/smart-enhance`, {
      data: {
        input,
        current_config: currentConfig,
      },
    });
    return response;
  }

  /**
   * Clean up test sessions
   * Deletes all sessions with "E2E", "test", or "测试" in the title
   */
  async cleanupTestSessions() {
    const data = await this.getSessions({ page_size: 100 });
    const testSessions = (data.sessions || []).filter(
      (s: Session) =>
        s.title?.toLowerCase().includes('e2e') ||
        s.title?.toLowerCase().includes('test') ||
        s.title?.includes('测试')
    );

    for (const session of testSessions) {
      try {
        await this.deleteSession(session.id);
        console.log(`  Deleted test session: ${session.id} - ${session.title}`);
      } catch (error) {
        console.error(`  Failed to delete session ${session.id}:`, error);
      }
    }

    return testSessions.length;
  }
}

// Test data generators
export const TestDataGenerator = {
  createSessionData(overrides?: Partial<CreateSessionData>): CreateSessionData {
    return {
      title: 'E2E Test Novel',
      mode: 'novel',
      goal: {
        genre: '玄幻',
        style: '修仙',
        requirements: 'E2E automated test session',
        chapter_count: 3,
        chapter_word_count: 2500,
        word_count: 10000,
        ...overrides?.goal,
      },
      config: {
        approval_mode: true,
        ...overrides?.config,
      },
      ...overrides,
    };
  },

  randomTitle(): string {
    return `E2E Test ${Date.now()}`;
  },

  randomGenre(): string {
    const genres = ['玄幻', '科幻', '奇幻', '都市', '悬疑', '历史'];
    return genres[Math.floor(Math.random() * genres.length)];
  },

  randomStyle(): string {
    const styles = ['修仙', '硬核', '轻松', '严肃', '幽默'];
    return styles[Math.floor(Math.random() * styles.length)];
  },
};
