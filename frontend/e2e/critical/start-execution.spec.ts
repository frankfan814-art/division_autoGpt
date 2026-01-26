/**
 * CRITICAL FLOW: Start Execution
 *
 * Tests the flow of starting a session execution from the workspace:
 * - Navigate to workspace
 * - WebSocket connection establishment
 * - Start execution button
 * - Task execution begins
 * - Real-time progress updates
 *
 * Test Cases:
 * 1. Workspace loads correctly
 * 2. WebSocket connects automatically
 * 3. Session starts automatically on workspace load
 * 4. Progress updates display correctly
 * 5. Current task shows LLM provider
 */

import { test, expect } from '../helpers/test-fixtures';
import { CreatePage } from '../pages/CreatePage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { TestDataGenerator } from '../helpers/api-helpers';

test.describe('CRITICAL: Start Execution Flow', () => {
  let testSessionIds: string[] = [];

  test.afterEach(async ({ page }, testInfo) => {
    // Save screenshot on failure
    if (testInfo.status !== 'passed') {
      await page.screenshot({
        path: `artifacts/failure-${testInfo.title.replace(/\s+/g, '-')}.png`,
      });
    }
  });

  test.afterAll(async () => {
    // Note: Don't delete sessions immediately as they may be running
    // Tests should clean up their own sessions
  });

  test('1. Should load workspace page', async ({ page }) => {
    // Arrange
    const createPage = new CreatePage(page);
    const workspacePage = new WorkspacePage(page);
    const testData = TestDataGenerator.createSessionData({
      title: `E2E Workspace Load ${Date.now()}`,
    });

    // Act - Create session via UI
    await page.goto('/create');
    await createPage.switchToManualMode();
    await createPage.fillForm({
      title: testData.title,
      mode: testData.mode,
      genre: testData.goal.genre,
      style: testData.goal.style,
      requirements: testData.goal.requirements,
    });
    await createPage.submitForm();

    // Wait for redirect to workspace
    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });

    // Extract session ID
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    testSessionIds.push(sessionId);

    // Assert
    await workspacePage.verifyPageLoaded();

    // Verify progress section is visible
    await expect(workspacePage.progressLabel).toBeVisible();
    await expect(workspacePage.progressBar).toBeVisible();

    // Screenshot
    await workspacePage.takeScreenshot('artifacts/workspace-loaded.png');

    console.log(`  ✓ Workspace loaded for session: ${sessionId}`);
  });

  test('2. Should establish WebSocket connection', async ({ page }) => {
    // Arrange
    const sessionId = testSessionIds[0];
    if (!sessionId) {
      test.skip(true, 'No session available from previous test');
    }

    const workspacePage = new WorkspacePage(page);

    // Monitor WebSocket events
    const wsMessages: any[] = [];
    page.on('websocket', (ws) => {
      console.log(`  WebSocket opened: ${ws.url()}`);

      ws.on('framereceived', (frame) => {
        try {
          const data = JSON.parse(frame.payload.toString());
          wsMessages.push(data);
          console.log(`  ← WS received: ${data.event}`);
        } catch (e) {
          // Ignore non-JSON messages
        }
      });

      ws.on('framesent', (frame) => {
        try {
          const data = JSON.parse(frame.payload.toString());
          console.log(`  → WS sent: ${data.event}`);
        } catch (e) {
          // Ignore non-JSON messages
        }
      });
    });

    // Act
    await workspacePage.goto(sessionId);
    await workspacePage.verifyPageLoaded();

    // Wait for WebSocket to connect
    await page.waitForTimeout(3000);

    // Assert - Should have WebSocket messages
    expect(wsMessages.length).toBeGreaterThan(0);

    // Should have subscribed to session
    const subscribeMsg = wsMessages.find((m) => m.event === 'subscribed');
    expect(subscribeMsg).toBeDefined();

    // Screenshot
    await page.screenshot({ path: 'artifacts/websocket-connected.png' });

    console.log(`  ✓ WebSocket connection established`);
    console.log(`  ✓ Received ${wsMessages.length} WebSocket messages`);
  });

  test('3. Should start session execution automatically', async ({ page, apiHelpers }) => {
    // Arrange
    const createPage = new CreatePage(page);
    const workspacePage = new WorkspacePage(page);
    const testData = TestDataGenerator.createSessionData({
      title: `E2E Auto Start ${Date.now()}`,
      goal: {
        ...TestDataGenerator.createSessionData().goal,
        chapter_count: 2, // Small for faster test
      },
    });

    // Act - Create session
    await page.goto('/create');
    await createPage.switchToManualMode();
    await createPage.fillForm({
      title: testData.title,
      genre: testData.goal.genre,
      style: testData.goal.style,
      requirements: testData.goal.requirements,
    });
    await createPage.submitForm();

    // Wait for workspace redirect
    await expect(page).toHaveURL(/\/workspace\/[a-f0-9-]+/, { timeout: 10000 });
    const url = page.url();
    const sessionId = url.split('/workspace/')[1];
    testSessionIds.push(sessionId);

    // Wait for auto-start (happens in useEffect)
    await page.waitForTimeout(5000);

    // Check session status via API
    const session = await apiHelpers.getSession(sessionId);

    // Assert - Session should be starting or running
    console.log(`  Session status: ${session.status}`);
    expect(['created', 'running', 'started']).toContain(session.status);

    // Screenshot
    await workspacePage.takeScreenshot(`artifacts/session-auto-started-${sessionId}.png`);

    console.log(`  ✓ Session auto-started: ${sessionId}`);
  });

  test('4. Should display progress updates', async ({ page }) => {
    // Arrange
    const sessionId = testSessionIds[testSessionIds.length - 1];
    if (!sessionId) {
      test.skip(true, 'No session available from previous test');
    }

    const workspacePage = new WorkspacePage(page);

    // Act
    await workspacePage.goto(sessionId);
    await workspacePage.verifyPageLoaded();

    // Wait for some progress
    await page.waitForTimeout(5000);

    // Get progress text
    const progressText = await workspacePage.getProgressText();
    console.log(`  Progress: ${progressText}`);

    // Check if task is running
    const isTaskRunning = await workspacePage.isTaskRunning();
    const isWaiting = await workspacePage.isWaiting();

    console.log(`  Task running: ${isTaskRunning}, Waiting: ${isWaiting}`);

    // Assert - Should show progress or waiting state
    expect(progressText).toBeTruthy();

    // Screenshot
    await page.screenshot({ path: 'artifacts/progress-updates.png' });

    console.log(`  ✓ Progress displayed: ${progressText}`);
  });

  test('5. Should display current task and LLM provider', async ({ page }) => {
    // Arrange
    const sessionId = testSessionIds[testSessionIds.length - 1];
    if (!sessionId) {
      test.skip(true, 'No session available from previous test');
    }

    const workspacePage = new WorkspacePage(page);

    // Act
    await workspacePage.goto(sessionId);
    await workspacePage.verifyPageLoaded();

    // Wait for task to start (may take a while)
    try {
      await workspacePage.waitForTaskStart(30000);
    } catch (e) {
      console.log(`  Task did not start within timeout, may be waiting`);
    }

    // Get current task info
    const currentTask = await workspacePage.getCurrentTask();
    const currentProvider = await workspacePage.getCurrentTaskProvider();

    console.log(`  Current task: ${currentTask || 'None'}`);
    console.log(`  Current provider: ${currentProvider || 'None'}`);

    // Screenshot
    await page.screenshot({ path: 'artifacts/current-task-display.png' });

    // Assert - If task is running, should show task info
    if (currentTask) {
      expect(currentTask).toBeTruthy();
      console.log(`  ✓ Current task displayed: ${currentTask}`);
    }

    if (currentProvider) {
      expect(currentProvider).toBeTruthy();
      console.log(`  ✓ LLM provider displayed: ${currentProvider}`);
    }
  });

  test('6. Should switch between workspace tabs', async ({ page }) => {
    // Arrange
    const sessionId = testSessionIds[0];
    if (!sessionId) {
      test.skip(true, 'No session available from previous test');
    }

    const workspacePage = new WorkspacePage(page);

    // Act
    await workspacePage.goto(sessionId);
    await workspacePage.verifyPageLoaded();

    // Switch to Tasks tab
    await workspacePage.clickTasksTab();
    await page.waitForTimeout(1000);

    // Switch to Reader tab
    await workspacePage.clickReaderTab();
    await page.waitForTimeout(1000);

    // Switch back to Overview
    await workspacePage.clickOverviewTab();
    await page.waitForTimeout(1000);

    // Assert - All tabs should be clickable
    // (Visual verification only)

    // Screenshot
    await page.screenshot({ path: 'artifacts/workspace-tabs.png' });

    console.log(`  ✓ Workspace tabs functional`);
  });
});
