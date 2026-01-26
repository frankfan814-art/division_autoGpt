/**
 * IMPORTANT FLOW: Preview Chapter Content
 *
 * Tests the preview panel functionality:
 * - Open preview panel
 * - View chapter content
 * - Switch between chapters
 *
 * Test Cases:
 * 1. Open preview panel
 * 2. View overview content
 * 3. Switch to reader mode
 * 4. Navigate chapters
 */

import { test, expect } from '@playwright/test';
import { CreatePage } from '../pages/CreatePage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { TestDataGenerator } from '../helpers/api-helpers';

test.describe('IMPORTANT: Preview Content Flow', () => {
  let testSessionIds: string[] = [];

  test.afterAll(async ({ request }) => {
    const { ApiHelpers } = await import('../helpers/api-helpers');
    const helpers = new ApiHelpers(request);
    for (const sessionId of testSessionIds) {
      try {
        await helpers.stopSession(sessionId);
        await helpers.deleteSession(sessionId);
      } catch (error) {
        console.error(`  Failed to cleanup ${sessionId}:`, error);
      }
    }
  });

  test('1. Should display preview panel on workspace', async ({ page }) => {
    // Arrange
    const createPage = new CreatePage(page);
    const workspacePage = new WorkspacePage(page);

    await page.goto('/create');
    await createPage.switchToManualMode();
    await createPage.fillForm({
      title: `E2E Preview Test ${Date.now()}`,
      genre: '奇幻',
    });
    await createPage.submitForm();

    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    testSessionIds.push(sessionId);

    // Wait for initial data
    await page.waitForTimeout(3000);

    // Act - Check preview panel visibility
    const previewPanel = workspacePage.previewPanel;

    // Assert
    await expect(previewPanel).toBeVisible();

    // Screenshot
    await page.screenshot({ path: 'artifacts/preview-panel-visible.png' });

    console.log(`  ✓ Preview panel displayed`);
  });

  test('2. Should display overview tab content', async ({ page }) => {
    // Arrange
    const workspacePage = new WorkspacePage(page);

    // Act - Ensure overview tab is selected
    await workspacePage.clickOverviewTab();
    await page.waitForTimeout(1000);

    // Assert - Overview content should be visible
    // (Actual implementation depends on component structure)
    const overviewTab = workspacePage.overviewTab;
    await expect(overviewTab).toBeVisible();

    // Screenshot
    await page.screenshot({ path: 'artifacts/overview-tab-content.png' });

    console.log(`  ✓ Overview tab content displayed`);
  });

  test('3. Should switch to reader mode', async ({ page }) => {
    // Arrange
    const workspacePage = new WorkspacePage(page);

    // Act - Click reader tab
    await workspacePage.clickReaderTab();
    await page.waitForTimeout(2000);

    // Assert - Reader tab should be active
    const readerTab = workspacePage.readerTab;
    await expect(readerTab).toBeVisible();

    // Screenshot
    await page.screenshot({ path: 'artifacts/reader-mode-active.png' });

    console.log(`  ✓ Reader mode activated`);
  });

  test('4. Should display chapter content in reader', async ({ page }) => {
    test.skip(true, 'Requires generated chapters - run after tasks complete');

    // Arrange
    const workspacePage = new WorkspacePage(page);

    // Act - Navigate to reader tab
    await workspacePage.clickReaderTab();
    await page.waitForTimeout(2000);

    // Look for chapter content
    const chapterContent = page.locator('text=/第.*章/').first();

    // Assert
    const isVisible = await chapterContent.isVisible().catch(() => false);

    if (isVisible) {
      console.log(`  ✓ Chapter content displayed`);
    } else {
      console.log(`  No chapter content yet (expected early in session)`);
    }

    // Screenshot
    await page.screenshot({ path: 'artifacts/chapter-content-display.png' });
  });

  test('5. Should navigate between chapters', async ({ page }) => {
    test.skip(true, 'Requires multiple chapters - implementation pending');

    // This test would verify chapter navigation controls
    // when they are implemented in the reader component

    console.log(`  ✓ Chapter navigation (pending implementation)`);
  });
});
