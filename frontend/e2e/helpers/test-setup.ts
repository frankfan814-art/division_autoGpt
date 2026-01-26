/**
 * Test Setup Utilities
 *
 * Helper functions for test setup and teardown
 */

import { Page, APIRequestContext } from '@playwright/test';
import { ApiHelpers, TestDataGenerator } from './api-helpers';

export interface TestContext {
  page: Page;
  request: APIRequestContext;
  apiHelpers: ApiHelpers;
  testSessionIds: string[];
}

export class TestSetup {
  private apiHelpers: ApiHelpers;
  private testSessionIds: string[] = [];

  constructor(request: APIRequestContext) {
    this.apiHelpers = new ApiHelpers(request);
  }

  /**
   * Create a test session with default or custom data
   */
  async createTestSession(overrides?: {
    title?: string;
    genre?: string;
    style?: string;
    approvalMode?: boolean;
  }) {
    const session = await this.apiHelpers.createSession(
      TestDataGenerator.createSessionData({
        title: overrides?.title || `E2E Test ${Date.now()}`,
        goal: {
          ...TestDataGenerator.createSessionData().goal,
          genre: overrides?.genre,
          style: overrides?.style,
        },
        config: {
          approval_mode: overrides?.approvalMode ?? true,
        },
      })
    );

    this.testSessionIds.push(session.id);
    return session;
  }

  /**
   * Create a test session via UI
   */
  async createSessionViaUI(
    page: Page,
    data: {
      title?: string;
      genre?: string;
      style?: string;
      requirements?: string;
    }
  ) {
    const { CreatePage } = await import('../pages/CreatePage');

    const createPage = new CreatePage(page);
    await page.goto('/create');
    await createPage.switchToManualMode();

    await createPage.fillForm({
      title: data.title || `E2E UI Test ${Date.now()}`,
      genre: data.genre || '玄幻',
      style: data.style || '修仙',
      requirements: data.requirements || 'E2E test session',
    });

    await createPage.submitForm();

    // Wait for redirect to workspace
    await page.waitForURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });

    // Extract session ID from URL
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];

    this.testSessionIds.push(sessionId);

    return { sessionId };
  }

  /**
   * Cleanup all test sessions
   */
  async cleanupAllSessions() {
    for (const sessionId of this.testSessionIds) {
      try {
        // Stop if running
        await this.apiHelpers.stopSession(sessionId).catch(() => {});
        // Delete
        await this.apiHelpers.deleteSession(sessionId);
        console.log(`  Cleaned up session: ${sessionId}`);
      } catch (error) {
        console.error(`  Failed to cleanup session ${sessionId}:`, error);
      }
    }
    this.testSessionIds = [];
  }

  /**
   * Cleanup only specified sessions
   */
  async cleanupSessions(sessionIds: string[]) {
    for (const sessionId of sessionIds) {
      try {
        await this.apiHelpers.stopSession(sessionId).catch(() => {});
        await this.apiHelpers.deleteSession(sessionId);
      } catch (error) {
        console.error(`  Failed to cleanup session ${sessionId}:`, error);
      }
    }
  }

  /**
   * Get all test session IDs created by this setup
   */
  getTestSessionIds(): string[] {
    return [...this.testSessionIds];
  }

  /**
   * Wait for session to reach a specific status
   */
  async waitForSessionStatus(
    sessionId: string,
    targetStatus: string,
    timeout = 60000
  ): Promise<boolean> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const session = await this.apiHelpers.getSession(sessionId);
      if (session.status === targetStatus) {
        return true;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    return false;
  }

  /**
   * Take a screenshot with a descriptive name
   */
  async screenshot(page: Page, name: string) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const path = `artifacts/${name}-${timestamp}.png`;
    await page.screenshot({ path, fullPage: true });
    return path;
  }
}

/**
 * Setup before all tests in a file
 */
export async function setupTests(request: APIRequestContext) {
  const setup = new TestSetup(request);

  // Cleanup any existing test sessions before starting
  try {
    const cleanedCount = await setup['apiHelpers'].cleanupTestSessions();
    if (cleanedCount > 0) {
      console.log(`  Cleaned up ${cleanedCount} existing test sessions`);
    }
  } catch (error) {
    console.log('  No existing test sessions to cleanup');
  }

  return setup;
}

/**
 * Teardown after all tests in a file
 */
export async function teardownTests(setup: TestSetup) {
  await setup.cleanupAllSessions();
}
