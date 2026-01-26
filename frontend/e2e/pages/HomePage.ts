/**
 * Home Page Object Model
 * Page Object for the home page at /
 */

import { Page, Locator, expect } from '@playwright/test';

export class HomePage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly createProjectButton: Locator;
  readonly viewSessionsButton: Locator;
  readonly recentSessionsSection: Locator;
  readonly viewAllLink: Locator;
  readonly emptyState: Locator;
  readonly featureCards: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.getByRole('heading', { name: 'Creative AutoGPT' }).first();
    this.createProjectButton = page.getByRole('link', { name: /创建新项目|创建/i });
    this.viewSessionsButton = page.getByRole('link', { name: /查看会话列表|查看全部/i });
    this.recentSessionsSection = page.getByRole('heading', { name: /最近项目/i });
    this.viewAllLink = page.getByRole('link', { name: /查看全部 →/ });
    this.emptyState = page.getByText(/暂无项目，创建第一个项目吧/i);
    this.featureCards = page.locator('.grid.md\\:grid-cols-3');
  }

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async verifyPageLoaded() {
    await expect(this.pageTitle).toBeVisible();
    await expect(this.createProjectButton).toBeVisible();
    await expect(this.viewSessionsButton).toBeVisible();
  }

  async clickCreateProject() {
    await this.createProjectButton.first().click();
  }

  async clickViewSessions() {
    await this.viewSessionsButton.click();
  }

  async clickViewAllSessions() {
    await this.viewAllLink.click();
  }

  async hasRecentSessions() {
    const count = await this.page.locator('[class*="session"]').count();
    return count > 0;
  }

  async isEmpty() {
    return await this.emptyState.isVisible();
  }

  async getFeatureCardCount() {
    return await this.featureCards.locator('> div').count();
  }
}
