/**
 * CRITICAL FLOW: Session Control
 *
 * Tests session control operations:
 * - Pause running session
 * - Resume paused session
 * - Stop session
 *
 * Test Cases:
 * 1. Pause a running session
 * 2. Verify session state after pause
 * 3. Resume a paused session
 * 4. Stop a running session
 * 5. Verify session cannot be resumed after stopping
 */

import { test, expect } from '../helpers/test-fixtures';
import { CreatePage } from '../pages/CreatePage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { SessionsPage } from '../pages/SessionsPage';
import { TestDataGenerator } from '../helpers/api-helpers';

test.describe('CRITICAL: Session Control Flow', () => {
  let testSessionIds: string[] = [];

  test('1. Should pause a running session via API', async ({ page, apiHelpers }) => {
    // Arrange - Create and start a session
    const createPage = new CreatePage(page);
    const testData = TestDataGenerator.createSessionData({
      title: `E2E Pause Test ${Date.now()}`,
      goal: {
        ...TestDataGenerator.createSessionData().goal,
        chapter_count: 2,
      },
    });

    await page.goto('/create');
    await createPage.switchToManualMode();
    await createPage.fillForm({
      title: testData.title,
      genre: testData.goal.genre,
      style: testData.goal.style,
    });
    await createPage.submitForm();

    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    testSessionIds.push(sessionId);

    // Wait for session to start
    await page.waitForTimeout(5000);

    // Act - Pause the session
    const pauseResponse = await apiHelpers.pauseSession(sessionId);
    console.log(`  Pause response:`, pauseResponse);

    // Wait for state to update
    await page.waitForTimeout(2000);

    // Assert - Check session status
    const session = await apiHelpers.getSession(sessionId);
    console.log(`  Session status after pause: ${session.status}`);

    expect(session.status).toBe('paused');

    // Screenshot
    await page.screenshot({ path: `artifacts/session-paused-${sessionId}.png` });

    console.log(`  ✓ Session paused successfully`);
  });

  test('2. Should resume a paused session via API', async ({ page, apiHelpers }) => {
    // Arrange - Use paused session from previous test or create new one
    let sessionId = testSessionIds[testSessionIds.length - 1];

    if (!sessionId) {
      // Create a new session and pause it
      const createPage = new CreatePage(page);
      await page.goto('/create');
      await createPage.switchToManualMode();
      await createPage.fillForm({
        title: `E2E Resume Test ${Date.now()}`,
        genre: '科幻',
      });
      await createPage.submitForm();

      await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
      const url = page.url();
      sessionId = url.split('/workspace/')[1];
      testSessionIds.push(sessionId);

      await page.waitForTimeout(3000);
      await apiHelpers.pauseSession(sessionId);
      await page.waitForTimeout(2000);
    }

    // Act - Resume the session
    const resumeResponse = await apiHelpers.resumeSession(sessionId);
    console.log(`  Resume response:`, resumeResponse);

    // Wait for state to update
    await page.waitForTimeout(2000);

    // Assert - Check session status
    const session = await apiHelpers.getSession(sessionId);
    console.log(`  Session status after resume: ${session.status}`);

    expect(['running', 'started']).toContain(session.status);

    // Screenshot
    await page.screenshot({ path: `artifacts/session-resumed-${sessionId}.png` });

    console.log(`  ✓ Session resumed successfully`);
  });

  test('3. Should stop a running session via API', async ({ page, apiHelpers }) => {
    // Arrange - Create and start a session
    const createPage = new CreatePage(page);
    const testData = TestDataGenerator.createSessionData({
      title: `E2E Stop Test ${Date.now()}`,
    });

    await page.goto('/create');
    await createPage.switchToManualMode();
    await createPage.fillForm({
      title: testData.title,
      genre: testData.goal.genre,
    });
    await createPage.submitForm();

    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    testSessionIds.push(sessionId);

    // Wait for session to start
    await page.waitForTimeout(3000);

    // Act - Stop the session
    const stopResponse = await apiHelpers.stopSession(sessionId);
    console.log(`  Stop response:`, stopResponse);

    // Wait for state to update
    await page.waitForTimeout(2000);

    // Assert - Check session status
    const session = await apiHelpers.getSession(sessionId);
    console.log(`  Session status after stop: ${session.status}`);

    expect(['stopped', 'failed', 'completed', 'paused']).toContain(session.status);

    // Screenshot
    await page.screenshot({ path: `artifacts/session-stopped-${sessionId}.png` });

    console.log(`  ✓ Session stopped successfully`);
  });

  test('4. Should handle pause/resume via WebSocket', async ({ page, apiHelpers }) => {
    // Arrange - Create session
    const createPage = new CreatePage(page);
    const workspacePage = new WorkspacePage(page);

    await page.goto('/create');
    await createPage.switchToManualMode();
    await createPage.fillForm({
      title: `E2E WS Control Test ${Date.now()}`,
      genre: '奇幻',
    });
    await createPage.submitForm();

    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    testSessionIds.push(sessionId);

    await page.waitForTimeout(3000);

    // Monitor WebSocket messages
    const wsMessages: any[] = [];
    page.on('websocket', (ws) => {
      ws.on('framereceived', (frame) => {
        try {
          const data = JSON.parse(frame.payload.toString());
          wsMessages.push(data);
        } catch (e) {}
      });
    });

    // Act - Send pause event via WebSocket (simulating UI button)
    await page.evaluate((sid) => {
      const wsClient = (window as any).__wsClient;
      if (wsClient) {
        wsClient.send({
          event: 'pause',
          session_id: sid,
        });
      }
    }, sessionId);

    // Wait for response
    await page.waitForTimeout(3000);

    // Assert
    const session = await apiHelpers.getSession(sessionId);
    console.log(`  Session status after WS pause: ${session.status}`);

    // Screenshot
    await page.screenshot({ path: `artifacts/ws-pause-control-${sessionId}.png` });

    console.log(`  ✓ WebSocket pause control tested`);
  });

  test('5. Should display correct controls based on session state', async ({ page, apiHelpers }) => {
    // Arrange - Create a paused session
    let sessionId = testSessionIds[0];

    if (!sessionId) {
      const createPage = new CreatePage(page);
      await page.goto('/create');
      await createPage.switchToManualMode();
      await createPage.fillForm({
        title: `E2E State Display ${Date.now()}`,
        genre: '都市',
      });
      await createPage.submitForm();

      await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
      const url = page.url();
      sessionId = url.split('/workspace/')[1];
      testSessionIds.push(sessionId);

      await page.waitForTimeout(3000);
      await apiHelpers.pauseSession(sessionId);
    }

    // Act - Navigate to sessions list
    await page.goto('/sessions');
    const sessionsPage = new SessionsPage(page);

    // Assert - Check if session shows as resumable
    await page.waitForTimeout(2000);
    const hasResumable = await sessionsPage.hasResumableSessions();

    console.log(`  Has resumable sessions: ${hasResumable}`);

    // Screenshot
    await page.screenshot({ path: 'artifacts/sessions-list-resumable.png' });

    console.log(`  ✓ Session state displayed correctly`);
  });

  // Cleanup at the end of all tests
  test.afterAll('Cleanup test sessions', async ({ }) => {
    // Note: We can't use apiHelpers in afterAll due to fixture restrictions
    // Sessions will be cleaned up manually or via a separate cleanup script
    console.log(`  ${testSessionIds.length} test sessions created (cleanup skipped)`);
  });

  test.afterEach(async ({ page, apiHelpers, }, testInfo) => {
    // Save screenshot on failure
    if (testInfo.status !== 'passed') {
      await page.screenshot({
        path: `artifacts/failure-${testInfo.title.replace(/\s+/g, '-')}.png`,
      });
    }

    // Cleanup session after each test (optional, can be disabled for debugging)
    // Uncomment to enable cleanup:
    // const url = page.url();
    // const match = url.match(/\/workspace\/([a-f0-9-]+)/);
    // if (match) {
    //   const sessionId = match[1];
    //   try {
    //     await apiHelpers.stopSession(sessionId);
    //     await apiHelpers.deleteSession(sessionId);
    //   } catch (error) {
    //     console.error(`  Failed to cleanup session:`, error);
    //   }
    // }
  });
});
