# E2E Tests for Creative AutoGPT

This directory contains end-to-end tests for the Creative AutoGPT application using Playwright.

## Test Structure

```
e2e/
├── critical/                  # CRITICAL - Core user flows
│   ├── create-session.spec.ts
│   ├── sessions-list-resume.spec.ts
│   ├── start-execution.spec.ts
│   ├── task-approval.spec.ts
│   └── session-control.spec.ts
├── important/                 # IMPORTANT - Key features
│   ├── task-history.spec.ts
│   ├── preview-content.spec.ts
│   └── export-functionality.spec.ts
├── smoke/                     # SMOKE - Quick health checks
│   └── smoke.spec.ts
├── pages/                     # Page Object Models
│   ├── HomePage.ts
│   ├── CreatePage.ts
│   ├── SessionsPage.ts
│   ├── WorkspacePage.ts
│   └── TaskApprovalDialog.ts
├── helpers/                   # Test utilities
│   ├── api-helpers.ts
│   └── test-setup.ts
├── full-workflow.spec.ts      # Legacy test (will be refactored)
└── artifacts/                 # Screenshots, videos, traces

```

## Page Object Model

All page interactions go through Page Object classes located in `pages/`:

- `HomePage` - Home page at `/`
- `CreatePage` - Create project page at `/create`
- `SessionsPage` - Sessions list at `/sessions`
- `WorkspacePage` - Workspace at `/workspace/:sessionId`
- `TaskApprovalDialog` - Task approval modal

## Running Tests

### Run all tests
```bash
npm run test:e2e
```

### Run specific test file
```bash
npx playwright test e2e/critical/create-session.spec.ts
```

### Run with UI (interactive mode)
```bash
npm run test:e2e:ui
```

### Run in headed mode (see browser)
```bash
npm run test:e2e:headed
```

### Run with debug mode
```bash
npm run test:e2e:debug
```

### Run specific test suite
```bash
# Run only critical tests
npx playwright test --grep "CRITICAL"

# Run only smoke tests
npx playwright test e2e/smoke/
```

### Run specific browsers
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## Test Priorities

### CRITICAL (Must Pass)
These are core user flows that MUST work for the application to be usable:
1. Create session flow
2. Sessions list and resume
3. Start execution
4. Task approval
5. Session control (pause/resume/stop)

### IMPORTANT (Should Pass)
Important features that users expect:
1. Task history viewing
2. Preview/reader functionality
3. Export functionality

### SMOKE (Fast Health Check)
Quick tests to verify the application is not completely broken:
1. API health
2. Page loads
3. Basic navigation
4. WebSocket connectivity

## Writing Tests

### Test Template

```typescript
import { test, expect } from '@playwright/test';
import { HomePage } from '../pages/HomePage';
import { ApiHelpers, TestDataGenerator } from '../helpers/api-helpers';

test.describe('Feature Name', () => {
  let apiHelpers: ApiHelpers;
  let testSessionIds: string[] = [];

  test.beforeAll(async ({ request }) => {
    apiHelpers = new ApiHelpers(request);
  });

  test.afterAll(async ({ request }) => {
    // Cleanup
    for (const sessionId of testSessionIds) {
      await apiHelpers.deleteSession(sessionId);
    }
  });

  test('should do something', async ({ page }) => {
    // Arrange
    const homePage = new HomePage(page);

    // Act
    await homePage.goto();
    await homePage.clickCreateProject();

    // Assert
    await expect(page).toHaveURL(/\/create/);
  });
});
```

### Best Practices

1. **Use Page Objects** - Always use Page Object classes, never interact with selectors directly in tests
2. **Wait for API Responses** - Use `waitForResponse()` or `waitForLoadState()` instead of arbitrary timeouts
3. **Cleanup After Tests** - Always delete test sessions in `afterAll` or `afterEach`
4. **Use Descriptive Names** - Test names should describe what is being tested
5. **Add Screenshots** - Take screenshots at key points for debugging
6. **Handle Flaky Tests** - If a test is flaky, mark it with `test.skip()` or `test.fixme()` until fixed

## Artifacts

Test artifacts are stored in:
- `playwright-report/` - HTML test report
- `test-results/` - Videos, traces, screenshots
- `artifacts/` - Custom screenshots saved by tests

View HTML report:
```bash
npx playwright show-report
```

## CI/CD Integration

Tests run automatically on pull requests. Configuration in `.github/workflows/`.

### Environment Variables

- `CI` - Set to `true` in CI environment
- `BASE_URL` - Override default base URL (default: `http://localhost:4173`)
- `API_BASE_URL` - Backend API URL (default: `http://localhost:8000`)

## Troubleshooting

### Tests timeout
- Increase timeout in `playwright.config.ts`
- Check if backend is running
- Check API key configuration in `.env`

### WebSocket connection fails
- Verify backend is running on port 8000
- Check firewall settings
- Look for console errors in browser

### Can't find elements
- Use Playwright Inspector: `npx playwright test --debug`
- Check if selectors are correct
- Wait for elements to be ready

### Tests are flaky
- Run with retries: `npx playwright test --retries=3`
- Check for race conditions
- Use explicit waits instead of `waitForTimeout`

## Data-testid Attributes

Components should have `data-testid` attributes for reliable testing:

```tsx
<button data-testid="create-project-button">Create</button>
<input data-testid="title-input" />
<div data-testid="task-card" data-task-id="123">
```

Currently, tests use text content and aria labels. Adding `data-testid` attributes would improve test reliability.

## API Testing

The `api-helpers.ts` file provides utilities for API testing:

```typescript
const apiHelpers = new ApiHelpers(request);

// Create session
const session = await apiHelpers.createSession(data);

// Get session
const session = await apiHelpers.getSession(sessionId);

// Delete session
await apiHelpers.deleteSession(sessionId);

// Cleanup test sessions
await apiHelpers.cleanupTestSessions();
```

## Future Improvements

- [ ] Add `data-testid` attributes to all components
- [ ] Add visual regression tests
- [ ] Add performance tests
- [ ] Add accessibility tests
- [ ] Add mobile-specific tests
- [ ] Add network throttling tests
