/**
 * Workspace Page Object Model
 * Page Object for the workspace page at /workspace/:sessionId
 */

import { Page, Locator, expect } from '@playwright/test';

export class WorkspacePage {
  readonly page: Page;
  readonly sessionId: string;

  // Progress section
  readonly progressLabel: Locator;
  readonly progressBar: Locator;
  readonly progressText: Locator;
  readonly currentTaskLabel: Locator;
  readonly currentTaskProvider: Locator;
  readonly waitingMessage: Locator;

  // Preview panel
  readonly previewPanel: Locator;
  readonly overviewTab: Locator;
  readonly tasksTab: Locator;
  readonly readerTab: Locator;

  // Chat panel
  readonly chatPanel: Locator;
  readonly chatInput: Locator;
  readonly sendButton: Locator;

  constructor(page: Page, sessionId?: string) {
    this.page = page;
    this.sessionId = sessionId || '';

    this.progressLabel = page.getByText(/任务进度/);
    this.progressBar = page.locator('[class*="progress"]');
    this.progressText = page.locator('text=/\\d+\\/\\d+/');
    this.currentTaskLabel = page.getByText(/▶ 正在执行/);
    this.currentTaskProvider = page.getByText(/🤖 使用模型/);
    this.waitingMessage = page.getByText(/等待任务启动/);

    this.previewPanel = page.locator('.min-w-0.border-r').first();
    this.overviewTab = page.getByRole('tab', { name: /概览/ });
    this.tasksTab = page.getByRole('tab', { name: /任务/ });
    this.readerTab = page.getByRole('tab', { name: /阅读/ });

    this.chatPanel = page.locator('.w-96.min-w-\\[320px\\]');
    this.chatInput = page.locator('textarea[placeholder*="输入"]');
    this.sendButton = page.getByRole('button', { name: /发送/ });
  }

  async goto(sessionId: string) {
    this.sessionId = sessionId;
    await this.page.goto(`/workspace/${sessionId}`);
    await this.page.waitForLoadState('networkidle');
  }

  async verifyPageLoaded() {
    await expect(this.progressLabel).toBeVisible();
    await expect(this.previewPanel).toBeVisible();
    await expect(this.chatPanel).toBeVisible();
  }

  async getProgressText() {
    return await this.progressText.textContent();
  }

  async getCurrentTask() {
    const text = await this.currentTaskLabel.textContent();
    return text?.replace('▶ 正在执行: ', '') || '';
  }

  async getCurrentTaskProvider() {
    const text = await this.currentTaskProvider.textContent();
    return text?.replace('🤖 使用模型: ', '') || '';
  }

  async isTaskRunning() {
    return await this.currentTaskLabel.isVisible();
  }

  async isWaiting() {
    return await this.waitingMessage.isVisible();
  }

  async clickOverviewTab() {
    await this.overviewTab.click();
  }

  async clickTasksTab() {
    await this.tasksTab.click();
  }

  async clickReaderTab() {
    await this.readerTab.click();
  }

  async waitForTaskStart(timeout = 30000) {
    await this.page.waitForFunction(
      () => {
        const taskLabel = document.body.innerText;
        return taskLabel.includes('正在执行') && !taskLabel.includes('等待任务启动');
      },
      { timeout }
    );
  }

  async waitForTaskCompletion(timeout = 120000) {
    await this.page.waitForFunction(
      () => {
        const taskLabel = document.body.innerText;
        return taskLabel.includes('已完成') || taskLabel.includes('failed');
      },
      { timeout }
    );
  }

  async takeScreenshot(path: string) {
    await this.page.screenshot({ path, fullPage: true });
  }
}
