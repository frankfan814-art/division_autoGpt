import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration for Creative AutoGPT
 *
 * Test Structure:
 * - critical/ : Core user flows that must work (create, start, approve, control)
 * - important/ : Important features (preview, history, export)
 * - pages/ : Page Object Models
 * - helpers/ : Test utilities and API helpers
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'playwright-results.json' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  timeout: 180000, // 3 minutes per test (LLM can be slow)

  expect: {
    timeout: 30000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: [
    {
      command: 'cd .. && PYTHONPATH=src python -m uvicorn creative_autogpt.api.main:app --host 0.0.0.0 --port 8000 --log-level warning',
      port: 8000,
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'VITE_API_BASE_URL=http://localhost:8000 npm run dev -- --host --port 4173',
      port: 4173,
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],

  // Output directories for artifacts
  outputDir: 'test-results',
});
