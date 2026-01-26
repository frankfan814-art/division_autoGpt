/**
 * Custom Test Fixtures
 * Extends Playwright test with custom fixtures
 */

import { test as base, APIRequestContext } from '@playwright/test';
import { ApiHelpers } from './api-helpers';

// Define our custom fixtures
type MyFixtures = {
  apiHelpers: ApiHelpers;
};

// Extend base test with custom fixtures
export const test = base.extend<MyFixtures>({
  // Create apiHelpers fixture - this will be created fresh for each test
  apiHelpers: async ({ request }, use) => {
    const helpers = new ApiHelpers(request);
    await use(helpers);
  },
});

// Re-export everything from the original test
export { expect } from '@playwright/test';
