import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }],
  ],
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  timeout: 120000, // 2 minutes per test
  expect: {
    timeout: 30000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd .. && PYTHONPATH=src uvicorn creative_autogpt.api.main:app --host 0.0.0.0 --port 8000',
      port: 8000,
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'VITE_API_BASE_URL=http://localhost:8000 npm run dev -- --host --port 4173',
      port: 4173,
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
