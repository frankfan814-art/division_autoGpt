/**
 * Sessions Page Object Model
 * Page Object for the sessions list page at /sessions
 */

import { Page, Locator, expect } from '@playwright/test';

export class SessionsPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly createProjectButton: Locator;
  readonly statusFilter: Locator;
  readonly sessionCards: Locator;
  readonly emptyState: Locator;
  readonly resumableNotice: Locator;
  readonly pagination: Locator;
  readonly previousPageButton: Locator;
  readonly nextPageButton: Locator;
  readonly currentPageIndicator: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.getByRole('heading', { name: /会话列表/ });
    this.createProjectButton = page.getByRole('link', { name: /创建新项目/ });
    this.statusFilter = page.getByLabel(/全部状态/);
    this.sessionCards = page.locator('[class*="session"]');
    this.emptyState = page.getByText(/暂无项目/);
    this.resumableNotice = page.getByText(/发现.*个可恢复的会话/);
    this.pagination = page.locator('text=/第.*页/');
    this.previousPageButton = page.getByRole('button', { name: /上一页/ });
    this.nextPageButton = page.getByRole('button', { name: /下一页/ });
    this.currentPageIndicator = page.locator('text=/第 \\d+\\/\\d+ 页/');
  }

  async goto() {
    await this.page.goto('/sessions');
    await this.page.waitForLoadState('networkidle');
  }

  async verifyPageLoaded() {
    await expect(this.pageTitle).toBeVisible();
  }

  async clickCreateProject() {
    await this.createProjectButton.click();
  }

  async filterByStatus(status: string) {
    await this.statusFilter.selectOption(status);
    await this.page.waitForLoadState('networkidle');
  }

  async getSessionCount() {
    return await this.sessionCards.count();
  }

  async isEmpty() {
    return await this.emptyState.isVisible();
  }

  async hasResumableSessions() {
    return await this.resumableNotice.isVisible();
  }

  async getResumableCount() {
    const text = await this.resumableNotice.textContent();
    const match = text?.match(/发现 (\d+) 个可恢复的会话/);
    return match ? parseInt(match[1]) : 0;
  }

  async clickRestoreSession(sessionId?: string) {
    // Find restore button for a specific session or the first one
    const restoreButton = sessionId
      ? this.page.locator(`[data-session-id="${sessionId}"]`).getByRole('button', { name: /恢复|继续/i })
      : this.page.getByRole('button', { name: /恢复|继续/i }).first();

    await restoreButton.click();
  }

  async clickContinueSession(sessionId?: string) {
    await this.clickRestoreSession(sessionId);
  }

  async clickViewSession(sessionId?: string) {
    const viewButton = sessionId
      ? this.page.locator(`[data-session-id="${sessionId}"]`).getByRole('button', { name: /查看/i })
      : this.page.getByRole('button', { name: /查看/i }).first();

    await viewButton.click();
  }

  async getCurrentPage() {
    const text = await this.currentPageIndicator.textContent();
    const match = text?.match(/第 (\d+)\/\d+ 页/);
    return match ? parseInt(match[1]) : 1;
  }

  async getTotalPages() {
    const text = await this.currentPageIndicator.textContent();
    const match = text?.match(/第 \d+\/(\d+) 页/);
    return match ? parseInt(match[1]) : 1;
  }

  async nextPage() {
    await this.nextPageButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async previousPage() {
    await this.previousPageButton.click();
    await this.page.waitForLoadState('networkidle');
  }
}
