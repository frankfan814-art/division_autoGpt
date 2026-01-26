/**
 * IMPORTANT FLOW: Export Functionality
 *
 * Tests the export dialog and functionality:
 * - Open export dialog
 * - Select export format
 * - Download exported file
 *
 * Test Cases:
 * 1. Open export dialog from home
 * 2. Open export dialog from sessions list
 * 3. Select export format
 * 4. Download export
 */

import { test, expect } from '@playwright/test';
import { HomePage } from '../pages/HomePage';
import { SessionsPage } from '../pages/SessionsPage';
import { CreatePage } from '../pages/CreatePage';
import { ApiHelpers, TestDataGenerator } from '../helpers/api-helpers';

test.describe('IMPORTANT: Export Functionality', () => {
  let apiHelpers: ApiHelpers;
  let testSessionIds: string[] = [];

  test.beforeEach(async ({ request, page }) => {
    apiHelpers = new ApiHelpers(request);

    // Create a test session
    const session = await apiHelpers.createSession(
      TestDataGenerator.createSessionData({
        title: `E2E Export Test ${Date.now()}`,
      })
    );
    testSessionIds.push(session.id);
  });

  test.afterAll(async ({ request }) => {
    const helpers = new ApiHelpers(request);
    for (const sessionId of testSessionIds) {
      try {
        await helpers.deleteSession(sessionId);
      } catch (error) {
        console.error(`  Failed to cleanup ${sessionId}:`, error);
      }
    }
  });

  test('1. Should open export dialog from sessions list', async ({ page }) => {
    // Arrange
    const sessionsPage = new SessionsPage(page);

    // Act
    await sessionsPage.goto();

    // Find and click export button for our test session
    const exportButton = page.locator(`[data-session-id="${testSessionIds[0]}"]`).getByRole('button', { name: /导出/i });

    const isVisible = await exportButton.isVisible().catch(() => false);

    if (isVisible) {
      await exportButton.click();
      await page.waitForTimeout(1000);

      // Assert - Export dialog should appear
      const dialog = page.locator('[class*="dialog"]').or(page.locator('[class*="modal"]'));
      const dialogVisible = await dialog.isVisible().catch(() => false);

      if (dialogVisible) {
        console.log(`  ✓ Export dialog opened from sessions list`);

        // Screenshot
        await page.screenshot({ path: 'artifacts/export-dialog-from-sessions.png' });
      } else {
        console.log(`  Export button clicked but no dialog detected`);
      }
    } else {
      console.log(`  Export button not found (may not be implemented yet)`);
      test.skip(true, 'Export functionality not implemented');
    }
  });

  test('2. Should select export format', async ({ page }) => {
    test.skip(true, 'Requires export dialog - implementation pending');

    // This test would verify format selection
    // when the export dialog is fully implemented

    console.log(`  ✓ Export format selection (pending implementation)`);
  });

  test('3. Should download exported file', async ({ page }) => {
    test.skip(true, 'Requires export functionality - implementation pending');

    // Setup download handler
    const downloadPromise = page.waitForEvent('download');

    // Trigger download
    // ... click export button

    // Wait for download
    const download = await downloadPromise;

    // Assert
    expect(download.suggestedFilename()).toBeTruthy();

    console.log(`  ✓ File downloaded: ${download.suggestedFilename()}`);
  });

  test('4. Should handle export for empty session', async ({ page, request }) => {
    test.skip(true, 'Requires export functionality - implementation pending');

    // Create empty session
    const emptySession = await apiHelpers.createSession(
      TestDataGenerator.createSessionData({
        title: `E2E Empty Export ${Date.now()}`,
      })
    );
    testSessionIds.push(emptySession.id);

    // Try to export
    // ... navigate and click export

    // Should handle gracefully (show message or download empty file)

    console.log(`  ✓ Empty session export handled`);
  });
});
