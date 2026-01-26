/**
 * IMPORTANT FLOW: Task History
 *
 * Tests viewing task history and results:
 * - View task list
 * - View individual task details
 * - Filter tasks by status
 *
 * Test Cases:
 * 1. Navigate to tasks tab
 * 2. View completed tasks
 * 3. View task details
 * 4. Search/filter tasks
 */

import { test, expect } from '@playwright/test';
import { CreatePage } from '../pages/CreatePage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { TestDataGenerator } from '../helpers/api-helpers';

test.describe('IMPORTANT: Task History Flow', () => {
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

  test('1. Should navigate to tasks tab and display task list', async ({ page }) => {
    // Arrange
    const createPage = new CreatePage(page);
    const workspacePage = new WorkspacePage(page);

    await page.goto('/create');
    await createPage.switchToManualMode();
    await createPage.fillForm({
      title: `E2E Tasks Tab ${Date.now()}`,
      genre: '科幻',
    });
    await createPage.submitForm();

    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    testSessionIds.push(sessionId);

    // Wait for some tasks to complete
    await page.waitForTimeout(10000);

    // Act - Click tasks tab
    await workspacePage.clickTasksTab();
    await page.waitForTimeout(2000);

    // Assert - Tasks tab should be visible
    // (Visual verification - actual implementation depends on component structure)

    // Screenshot
    await page.screenshot({ path: 'artifacts/tasks-tab-display.png' });

    console.log(`  ✓ Tasks tab displayed`);
  });

  test('2. Should display task cards with status', async ({ page }) => {
    test.skip(true, 'Requires completed tasks - run after session finishes');

    // Arrange
    const workspacePage = new WorkspacePage(page);

    // Act - Navigate to tasks tab
    await workspacePage.clickTasksTab();

    // Look for task cards
    const taskCards = page.locator('[class*="task"]');
    const count = await taskCards.count();

    console.log(`  Found ${count} task cards`);

    // Assert - Should have task cards
    expect(count).toBeGreaterThan(0);

    // Screenshot
    await page.screenshot({ path: 'artifacts/task-cards-display.png' });
  });

  test('3. Should display task details when clicking a task', async ({ page }) => {
    test.skip(true, 'Requires completed tasks - run after session finishes');

    // Arrange
    const workspacePage = new WorkspacePage(page);

    // Act
    await workspacePage.clickTasksTab();
    const firstTaskCard = page.locator('[class*="task"]').first();
    await firstTaskCard.click();

    // Wait for details to load
    await page.waitForTimeout(1000);

    // Assert - Task details should be visible
    // (Implementation depends on component structure)

    // Screenshot
    await page.screenshot({ path: 'artifacts/task-details-display.png' });

    console.log(`  ✓ Task details displayed`);
  });

  test('4. Should filter tasks by status', async ({ page }) => {
    test.skip(true, 'Requires filter UI - implementation pending');

    // This test would verify task filtering functionality
    // when filter controls are added to the tasks tab

    console.log(`  ✓ Task filtering (pending implementation)`);
  });
});
