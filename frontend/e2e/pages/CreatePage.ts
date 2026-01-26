/**
 * Create Page Object Model
 * Page Object for the create project page at /create
 */

import { Page, Locator, expect } from '@playwright/test';

export class CreatePage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly manualModeButton: Locator;
  readonly smartModeButton: Locator;

  // Manual form fields
  readonly titleInput: Locator;
  readonly modeSelect: Locator;
  readonly chapterWordCountInput: Locator;
  readonly wordCountSelect: Locator;
  readonly approvalModeCheckbox: Locator;
  readonly genreInput: Locator;
  readonly styleInput: Locator;
  readonly requirementsTextarea: Locator;
  readonly createButton: Locator;
  readonly cancelButton: Locator;

  // Smart create fields
  readonly smartCreateTextarea: Locator;
  readonly generateConfigButton: Locator;

  readonly estimatedChapterCount: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.getByRole('heading', { name: /创建新项目/ });
    this.manualModeButton = page.getByRole('button', { name: /📝 手动填写/ });
    this.smartModeButton = page.getByRole('button', { name: /✨ 智能生成/ });

    // Manual form
    this.titleInput = page.getByLabel(/项目标题|标题/i);
    this.modeSelect = page.getByLabel(/创作模式/);
    this.chapterWordCountInput = page.locator('input[type="number"]').first();
    this.wordCountSelect = page.locator('select').first();
    this.approvalModeCheckbox = page.locator('input[type="checkbox"]').first();
    this.genreInput = page.getByLabel(/类型|流派/i);
    this.styleInput = page.getByLabel(/写作风格|风格/i);
    this.requirementsTextarea = page.getByLabel(/创作要求|要求/i);
    this.createButton = page.getByRole('button', { name: /创建项目/ });
    this.cancelButton = page.getByRole('button', { name: /取消/ });

    // Smart create
    this.smartCreateTextarea = page.getByLabel(/您的创作想法/);
    this.generateConfigButton = page.getByRole('button', { name: /✨ 生成配置/ });

    this.estimatedChapterCount = page.getByText(/📖 预计章节数/);
  }

  async goto() {
    await this.page.goto('/create');
    await this.page.waitForLoadState('networkidle');
  }

  async verifyPageLoaded() {
    await expect(this.pageTitle).toBeVisible();
  }

  async switchToManualMode() {
    await this.manualModeButton.click();
  }

  async switchToSmartMode() {
    await this.smartModeButton.click();
  }

  async fillForm(data: {
    title: string;
    mode?: string;
    genre?: string;
    style?: string;
    requirements?: string;
    chapterWordCount?: string;
    wordCount?: string;
    approvalMode?: boolean;
  }) {
    if (data.title) {
      await this.titleInput.fill(data.title);
    }
    if (data.mode) {
      await this.modeSelect.selectOption(data.mode);
    }
    if (data.genre) {
      await this.genreInput.fill(data.genre);
    }
    if (data.style) {
      await this.styleInput.fill(data.style);
    }
    if (data.requirements) {
      await this.requirementsTextarea.fill(data.requirements);
    }
    if (data.chapterWordCount) {
      await this.chapterWordCountInput.fill(data.chapterWordCount);
    }
    if (data.wordCount) {
      await this.wordCountSelect.selectOption(data.wordCount);
    }
    if (data.approvalMode !== undefined) {
      const isChecked = await this.approvalModeCheckbox.isChecked();
      if (isChecked !== data.approvalMode) {
        await this.approvalModeCheckbox.click();
      }
    }
  }

  async submitForm() {
    await this.createButton.click();
  }

  async getEstimatedChapterCount() {
    const text = await this.estimatedChapterCount.textContent();
    const match = text?.match(/预计章节数：(\d+) 章/);
    return match ? parseInt(match[1]) : 0;
  }

  async isInSmartMode() {
    return await this.smartCreateTextarea.isVisible();
  }
}
