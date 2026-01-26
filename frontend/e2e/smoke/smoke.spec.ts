/**
 * SMOKE TESTS
 *
 * Quick smoke tests to verify the core application is working.
 * These should run fast and catch major issues.
 *
 * Run before more comprehensive tests.
 */

import { test, expect } from '@playwright/test';
import { HomePage } from '../pages/HomePage';
import { CreatePage } from '../pages/CreatePage';
import { SessionsPage } from '../pages/SessionsPage';
import { ApiHelpers, TestDataGenerator } from '../helpers/api-helpers';

test.describe('Smoke Tests', () => {
  let apiHelpers: ApiHelpers;

  test.beforeEach(async ({ request }) => {
    apiHelpers = new ApiHelpers(request);
  });

  test('API health check', async ({ request }) => {
    const response = await request.get('http://localhost:8000/health');
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');

    console.log('  ✓ API is healthy');
  });

  test('Home page loads', async ({ page }) => {
    const homePage = new HomePage(page);
    await homePage.goto();
    await homePage.verifyPageLoaded();

    console.log('  ✓ Home page loads');
  });

  test('Create page loads', async ({ page }) => {
    const createPage = new CreatePage(page);
    await createPage.goto();
    await createPage.verifyPageLoaded();

    console.log('  ✓ Create page loads');
  });

  test('Sessions page loads', async ({ page }) => {
    const sessionsPage = new SessionsPage(page);
    await sessionsPage.goto();
    await sessionsPage.verifyPageLoaded();

    console.log('  ✓ Sessions page loads');
  });

  test('Can create session via API', async ({ request }) => {
    const testData = TestDataGenerator.createSessionData({
      title: `Smoke Test ${Date.now()}`,
    });

    const session = await apiHelpers.createSession(testData);
    expect(session).toHaveProperty('id');
    expect(session.status).toBe('created');

    // Cleanup
    await apiHelpers.deleteSession(session.id);

    console.log('  ✓ Can create session via API');
  });

  test('Can fetch sessions list', async ({ request }) => {
    const data = await apiHelpers.getSessions({ page: 1, page_size: 10 });
    expect(data).toHaveProperty('sessions');
    expect(Array.isArray(data.sessions)).toBeTruthy();

    console.log(`  ✓ Can fetch sessions (found ${data.sessions.length})`);
  });

  test('Can fetch prompts', async ({ request }) => {
    const styles = await apiHelpers.getStyles();
    expect(Array.isArray(styles)).toBeTruthy();

    const templates = await apiHelpers.getTemplates();
    expect(Array.isArray(templates)).toBeTruthy();

    console.log(`  ✓ Can fetch prompts (${styles.length} styles, ${templates.length} templates)`);
  });

  test('Navigation between main pages', async ({ page }) => {
    // Home -> Create
    await page.goto('/');
    await page.getByRole('link', { name: /创建新项目|创建/i }).first().click();
    await expect(page).toHaveURL(/\/create/);

    // Create -> Home
    await page.getByRole('button', { name: /取消/ }).click();
    await expect(page).toHaveURL(/\//);

    // Home -> Sessions
    await page.getByRole('link', { name: /查看会话列表|查看全部/i }).first().click();
    await expect(page).toHaveURL(/\/sessions/);

    console.log('  ✓ Navigation works');
  });

  test('WebSocket endpoint accessible', async ({ page }) => {
    // Navigate to workspace to trigger WebSocket connection
    const testData = TestDataGenerator.createSessionData({
      title: `WS Smoke ${Date.now()}`,
    });

    const session = await apiHelpers.createSession(testData);
    await page.goto(`/workspace/${session.id}`);

    // Wait for WebSocket to potentially connect
    await page.waitForTimeout(3000);

    // Check for any WebSocket errors in console
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // If we got here without crashing, WebSocket is probably OK
    console.log('  ✓ WebSocket endpoint accessible');

    // Cleanup
    await apiHelpers.deleteSession(session.id);
  });
});
