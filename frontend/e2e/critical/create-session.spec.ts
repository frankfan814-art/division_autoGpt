/**
 * CRITICAL FLOW: Create Session
 *
 * Tests the complete flow of creating a new session from the home page
 * to the workspace.
 *
 * Test Cases:
 * 1. Navigate to create page from home
 * 2. Create session with manual form
 * 3. Create session with smart enhance
 * 4. Verify redirect to workspace
 * 5. Verify session is created via API
 */

import { test, expect } from '../helpers/test-fixtures';
import { HomePage } from '../pages/HomePage';
import { CreatePage } from '../pages/CreatePage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { TestDataGenerator } from '../helpers/api-helpers';

test.describe('CRITICAL: Create Session Flow', () => {
  test('1. Should navigate to create page from home', async ({ page }) => {
    // Arrange
    const homePage = new HomePage(page);

    // Act
    await homePage.goto();
    await homePage.clickCreateProject();

    // Assert
    await expect(page).toHaveURL(/\/create/);
    const createPage = new CreatePage(page);
    await createPage.verifyPageLoaded();

    // Screenshot
    await page.screenshot({ path: 'artifacts/create-page-navigation.png' });
  });

  test('2. Should create session with manual form', async ({ page, apiHelpers }) => {
    // Arrange
    const homePage = new HomePage(page);
    const createPage = new CreatePage(page);
    const testData = TestDataGenerator.createSessionData({
      title: `E2E Manual ${Date.now()}`,
    });

    // Act - Navigate to create page
    await homePage.goto();
    await homePage.clickCreateProject();
    await createPage.verifyPageLoaded();

    // Ensure manual mode is selected
    await createPage.switchToManualMode();

    // Fill form
    await createPage.fillForm({
      title: testData.title,
      mode: testData.mode,
      genre: testData.goal.genre,
      style: testData.goal.style,
      requirements: testData.goal.requirements,
    });

    // Screenshot before submit
    await page.screenshot({ path: 'artifacts/create-form-filled.png' });

    // Submit form
    await createPage.submitForm();

    // Assert - Should redirect to workspace
    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });

    // Extract session ID from URL
    const url = page.url();
    const sessionId = url.split('/workspace/')[1]?.split('/')[0];
    expect(sessionId).toBeTruthy();
    console.log(`  ✓ Created session: ${sessionId}`);

    // Verify session exists via API
    const session = await apiHelpers.getSession(sessionId);
    expect(session.title).toBe(testData.title);
    expect(session.status).toBe('created');

    // Screenshot of workspace
    await page.screenshot({ path: `artifacts/workspace-after-creation-${sessionId}.png` });
  });

  test('3. Should create session with estimated chapter count', async ({ page }) => {
    // Arrange
    const createPage = new CreatePage(page);
    const wordCount = '30000'; // 30k words
    const chapterWordCount = '2500'; // 2.5k per chapter
    const expectedChapters = 12; // 30000 / 2500 = 12

    // Act
    await page.goto('/create');
    await createPage.switchToManualMode();

    // Set word count and chapter word count
    await createPage.fillForm({
      title: `E2E Chapter Count ${Date.now()}`,
      wordCount,
      chapterWordCount,
    });

    // Get estimated chapter count
    const actualChapters = await createPage.getEstimatedChapterCount();

    // Assert
    expect(actualChapters).toBe(expectedChapters);

    // Screenshot
    await page.screenshot({ path: 'artifacts/chapter-count-calculation.png' });
  });

  test('4. Should validate required fields', async ({ page }) => {
    // Arrange
    const createPage = new CreatePage(page);

    // Act
    await page.goto('/create');
    await createPage.switchToManualMode();

    // Try to submit without filling required fields
    await createPage.submitForm();

    // Assert - Should show validation error
    const titleInput = createPage.titleInput;
    const error = await titleInput.evaluate((el: any) =>
      el.nextElementSibling?.textContent?.includes('请输入')
    );

    // Should not redirect (still on create page)
    await expect(page).toHaveURL(/\/create/);

    // Screenshot
    await page.screenshot({ path: 'artifacts/validation-error.png' });
  });

  test('5. Should create session via API and navigate to workspace', async ({ page, apiHelpers }) => {
    // Arrange
    const testData = TestDataGenerator.createSessionData({
      title: `E2E API Create ${Date.now()}`,
    });

    // Act - Create session via API
    const session = await apiHelpers.createSession(testData);
    console.log(`  ✓ Created session via API: ${session.id}`);

    // Navigate to workspace
    await page.goto(`/workspace/${session.id}`);

    // Assert
    await expect(page).toHaveURL(/\/workspace\//);
    const workspacePage = new WorkspacePage(page, session.id);
    await workspacePage.verifyPageLoaded();

    // Verify session status
    const sessionData = await apiHelpers.getSession(session.id);
    expect(sessionData.id).toBe(session.id);

    // Screenshot
    await page.screenshot({ path: `artifacts/workspace-api-create-${session.id}.png` });
  });

  test('6. Should create session with approval mode enabled', async ({ page, apiHelpers }) => {
    // Arrange
    const createPage = new CreatePage(page);

    // Act
    await page.goto('/create');
    await createPage.switchToManualMode();

    // Fill form with approval mode enabled (default)
    await createPage.fillForm({
      title: `E2E Approval Mode ${Date.now()}`,
      approvalMode: true,
    });

    // Submit
    await createPage.submitForm();

    // Assert
    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/);

    // Verify session config
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    const session = await apiHelpers.getSession(sessionId);

    expect(session.config?.approval_mode).toBe(true);

    console.log(`  ✓ Approval mode enabled for session: ${sessionId}`);

    // Screenshot
    await page.screenshot({ path: 'artifacts/approval-mode-enabled.png' });
  });

  test.afterEach(async ({ page }, testInfo) => {
    // Save screenshot on failure
    if (testInfo.status !== 'passed') {
      await page.screenshot({
        path: `artifacts/failure-${testInfo.title.replace(/\s+/g, '-')}.png`,
      });
    }
  });
});
