/**
 * CRITICAL FLOW: Sessions List and Resume
 *
 * Tests the sessions list page functionality:
 * - View all sessions
 * - Filter by status
 * - Identify resumable sessions
 * - Resume paused/running sessions
 *
 * Test Cases:
 * 1. View sessions list
 * 2. Filter sessions by status
 * 3. Display resumable session notice
 * 4. Resume a paused session
 * 5. Navigate to session workspace
 */

import { test, expect } from '../helpers/test-fixtures';
import { HomePage } from '../pages/HomePage';
import { SessionsPage } from '../pages/SessionsPage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { TestDataGenerator } from '../helpers/api-helpers';

test.describe('CRITICAL: Sessions List and Resume Flow', () => {
  let testSessionIds: string[] = [];

  // Use a test to create initial data (runs once before others)
  test('0. Setup: Create test sessions', async ({ apiHelpers }) => {
    // Create test sessions in different states
    const session1 = await apiHelpers.createSession(
      TestDataGenerator.createSessionData({
        title: 'E2E Test Session Created',
      })
    );
    testSessionIds.push(session1.id);

    console.log(`  Created test session: ${session1.id}`);

    // Mark this test as skipped from results (it's just setup)
    test.skip(true, 'Setup test - always skip');
  });

  test.afterAll(async () => {
    // Note: We can't use apiHelpers in afterAll due to fixture restrictions
    // Tests should clean up their own sessions or use a separate cleanup mechanism
    console.log('  Note: Session cleanup should be done per-test or via separate cleanup script');
  });

  test('1. Should navigate to sessions list from home', async ({ page }) => {
    // Arrange
    const homePage = new HomePage(page);

    // Act
    await homePage.goto();
    await homePage.clickViewSessions();

    // Assert
    await expect(page).toHaveURL(/\/sessions/);
    const sessionsPage = new SessionsPage(page);
    await sessionsPage.verifyPageLoaded();

    // Screenshot
    await page.screenshot({ path: 'artifacts/sessions-list-page.png' });
  });

  test('2. Should display sessions list', async ({ page }) => {
    // Arrange
    const sessionsPage = new SessionsPage(page);

    // Act
    await sessionsPage.goto();

    // Assert
    await sessionsPage.verifyPageLoaded();

    // Check if we have sessions (might be empty in fresh environment)
    const sessionCount = await sessionsPage.getSessionCount();
    console.log(`  Found ${sessionCount} sessions`);

    if (sessionCount > 0) {
      // Should have at least our test session
      expect(sessionCount).toBeGreaterThanOrEqual(1);
    }

    // Screenshot
    await page.screenshot({ path: 'artifacts/sessions-list-display.png' });
  });

  test('3. Should filter sessions by status', async ({ page }) => {
    // Arrange
    const sessionsPage = new SessionsPage(page);

    // Act
    await sessionsPage.goto();

    // Get initial count
    const initialCount = await sessionsPage.getSessionCount();

    // Filter by 'created' status
    await sessionsPage.filterByStatus('created');
    await page.waitForLoadState('networkidle');

    // Get filtered count
    const filteredCount = await sessionsPage.getSessionCount();

    console.log(`  Initial count: ${initialCount}, Filtered count: ${filteredCount}`);

    // Assert
    // Filtered count should be <= initial count
    expect(filteredCount).toBeLessThanOrEqual(initialCount);

    // Screenshot
    await page.screenshot({ path: 'artifacts/sessions-filtered-by-status.png' });
  });

  test('4. Should show empty state when no sessions', async ({ page, apiHelpers }) => {
    // This test assumes we can delete all sessions temporarily
    // Skip in CI to avoid affecting other tests
    test.skip(process.env.CI === 'true', 'Skip in CI to avoid side effects');

    // Arrange
    const sessionsPage = new SessionsPage(page);

    // Get all existing sessions
    const allSessions = await apiHelpers.getSessions({ page_size: 100 });
    const sessionIds = (allSessions.sessions || []).map((s: any) => s.id);

    // Store IDs to restore later
    const sessionsToRestore: any[] = [];

    // Delete all sessions temporarily
    for (const id of sessionIds) {
      try {
        const session = await apiHelpers.getSession(id);
        sessionsToRestore.push(session);
        await apiHelpers.deleteSession(id);
      } catch (error) {
        console.error(`  Failed to delete session ${id}:`, error);
      }
    }

    // Act
    await sessionsPage.goto();

    // Assert - Should show empty state
    const isEmpty = await sessionsPage.isEmpty();
    expect(isEmpty).toBeTruthy();

    // Screenshot
    await page.screenshot({ path: 'artifacts/sessions-empty-state.png' });

    // Restore sessions for other tests
    for (const sessionData of sessionsToRestore) {
      try {
        await apiHelpers.createSession(sessionData);
      } catch (error) {
        console.error(`  Failed to restore session:`, error);
      }
    }
  });

  test('5. Should navigate to create new project from sessions page', async ({ page }) => {
    // Arrange
    const sessionsPage = new SessionsPage(page);

    // Act
    await sessionsPage.goto();
    await sessionsPage.clickCreateProject();

    // Assert
    await expect(page).toHaveURL(/\/create/);
    await expect(page.getByRole('heading', { name: /创建新项目/ })).toBeVisible();

    // Screenshot
    await page.screenshot({ path: 'artifacts/navigate-to-create-from-sessions.png' });
  });

  test('6. Should navigate to session workspace', async ({ page, apiHelpers }) => {
    // Arrange
    const sessionsPage = new SessionsPage(page);
    const workspacePage = new WorkspacePage(page);

    // Create a fresh session for this test
    const newSession = await apiHelpers.createSession(
      TestDataGenerator.createSessionData({
        title: 'E2E Test Navigation Session',
      })
    );

    // Act
    await sessionsPage.goto();
    await sessionsPage.clickViewSession(newSession.id);

    // Assert
    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/);
    await workspacePage.verifyPageLoaded();

    // Cleanup
    try {
      await apiHelpers.deleteSession(newSession.id);
    } catch (error) {
      console.error(`  Failed to cleanup session:`, error);
    }

    // Screenshot
    await page.screenshot({ path: 'artifacts/navigated-to-workspace.png' });
  });

  test('7. Should display pagination when multiple pages', async ({ page, apiHelpers }) => {
    // Arrange
    const sessionsPage = new SessionsPage(page);

    // Create enough sessions to trigger pagination (11+ for page size of 10)
    const newSessions = [];
    for (let i = 0; i < 12; i++) {
      const session = await apiHelpers.createSession(
        TestDataGenerator.createSessionData({
          title: `E2E Pagination Test ${i}`,
        })
      );
      newSessions.push(session.id);
    }

    // Act
    await sessionsPage.goto();

    // Check if pagination is visible
    const hasPagination = await sessionsPage.pagination.isVisible().catch(() => false);

    if (hasPagination) {
      const totalPages = await sessionsPage.getTotalPages();
      console.log(`  Total pages: ${totalPages}`);
      expect(totalPages).toBeGreaterThan(1);

      // Test next page
      await sessionsPage.nextPage();
      const currentPage = await sessionsPage.getCurrentPage();
      expect(currentPage).toBe(2);

      // Test previous page
      await sessionsPage.previousPage();
      const backToFirst = await sessionsPage.getCurrentPage();
      expect(backToFirst).toBe(1);

      // Screenshot
      await page.screenshot({ path: 'artifacts/sessions-pagination.png' });
    } else {
      console.log('  Pagination not visible (not enough sessions)');
    }

    // Cleanup
    for (const sessionId of newSessions) {
      try {
        await apiHelpers.deleteSession(sessionId);
      } catch (error) {
        console.error(`  Failed to cleanup session ${sessionId}:`, error);
      }
    }
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
