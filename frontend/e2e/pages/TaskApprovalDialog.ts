/**
 * Task Approval Dialog Object Model
 * Page Object for the task approval modal dialog
 */

import { Page, Locator, expect } from '@playwright/test';

export class TaskApprovalDialog {
  readonly page: Page;
  readonly dialog: Locator;
  readonly title: Locator;
  readonly taskTypeBadge: Locator;
  readonly llmInfo: Locator;
  readonly scoreLabel: Locator;
  readonly passStatus: Locator;
  readonly taskDescription: Locator;
  readonly taskResult: Locator;
  readonly feedbackTextarea: Locator;
  readonly approveButton: Locator;
  readonly rejectButton: Locator;
  readonly regenerateButton: Locator;
  readonly ideaSelectionGrid: Locator;
  readonly selectedIdeaButtons: Locator;

  constructor(page: Page) {
    this.page = page;
    this.dialog = page.locator('.fixed.inset-0.bg-black');
    this.title = page.getByRole('heading', { name: /任务结果预览/ });
    this.taskTypeBadge = page.locator('[class*="badge"]');
    this.llmInfo = page.getByText(/🤖/);
    this.scoreLabel = page.locator('text=/评分: \\d+\\/100/');
    this.passStatus = page.locator('text=/✓ 通过|✗ 未通过/');
    this.taskDescription = page.getByText(/任务描述/);
    this.taskResult = page.locator('.bg-gray-50.rounded-lg pre');
    this.feedbackTextarea = page.locator('textarea[placeholder*="反馈"]');
    this.approveButton = page.getByRole('button', { name: /✓ 接受并继续|确认选择/ });
    this.rejectButton = page.getByRole('button', { name: /✗ 拒绝并跳过/ });
    this.regenerateButton = page.getByRole('button', { name: /🔄 重新生成/ });
    this.ideaSelectionGrid = page.locator('.grid.grid-cols-2');
    this.selectedIdeaButtons = page.locator('button.border-blue-500');
  }

  async isVisible() {
    return await this.dialog.isVisible();
  }

  async waitForVisible(timeout = 10000) {
    await expect(this.dialog).toBeVisible({ timeout });
  }

  async waitForHidden(timeout = 10000) {
    await expect(this.dialog).toBeHidden({ timeout });
  }

  async getTaskType() {
    return await this.taskTypeBadge.textContent();
  }

  async getScore() {
    const text = await this.scoreLabel.textContent();
    const match = text?.match(/评分: (\d+)\/100/);
    return match ? parseInt(match[1]) : 0;
  }

  async isPassing() {
    const text = await this.passStatus.textContent();
    return text?.includes('✓ 通过') || false;
  }

  async getResult() {
    return await this.taskResult.textContent();
  }

  async selectIdea(ideaNumber: number) {
    const ideaButton = this.page.locator(`button:has-text("点子 ${ideaNumber}")`);
    await ideaButton.click();
  }

  async fillFeedback(feedback: string) {
    await this.feedbackTextarea.fill(feedback);
  }

  async approve() {
    await this.approveButton.click();
  }

  async reject() {
    await this.rejectButton.click();
  }

  async regenerate() {
    await this.regenerateButton.click();
  }

  async approveWithFeedback(feedback: string) {
    await this.fillFeedback(feedback);
    await this.approve();
  }

  async hasIdeaSelection() {
    return await this.ideaSelectionGrid.isVisible();
  }
}
