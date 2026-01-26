# E2E Test Architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PLAYWRIGHT TEST RUNNER                   │
│                     (playwright.config.ts)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ├──► ┌──────────────────────────────────────┐
                         │    │         CRITICAL TESTS               │
                         │    │  ┌─────────────────────────────────┐  │
                         │    │  │ create-session.spec.ts         │  │
                         │    │  │ sessions-list-resume.spec.ts   │  │
                         │    │  │ start-execution.spec.ts        │  │
                         │    │  │ task-approval.spec.ts          │  │
                         │    │  │ session-control.spec.ts        │  │
                         │    │  └─────────────────────────────────┘  │
                         │    └──────────────┬───────────────────────┘
                         │                   │
                         ├──► ┌───────────────┴───────────────────────┐
                         │    │         IMPORTANT TESTS              │
                         │    │  ┌─────────────────────────────────┐  │
                         │    │  │ task-history.spec.ts            │  │
                         │    │  │ preview-content.spec.ts         │  │
                         │    │  │ export-functionality.spec.ts    │  │
                         │    │  └─────────────────────────────────┘  │
                         │    └──────────────┬───────────────────────┘
                         │                   │
                         ├──► ┌───────────────┴───────────────────────┐
                         │    │         SMOKE TESTS                   │
                         │    │  ┌─────────────────────────────────┐  │
                         │    │  │ smoke.spec.ts                   │  │
                         │    │  └─────────────────────────────────┘  │
                         │    └──────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────────┐
         │         PAGE OBJECT LAYER             │
         │  ┌─────────────────────────────────┐  │
         │  │ HomePage.ts                     │  │
         │  │ CreatePage.ts                   │  │
         │  │ SessionsPage.ts                 │  │
         │  │ WorkspacePage.ts                │  │
         │  │ TaskApprovalDialog.ts           │  │
         │  └─────────────────────────────────┘  │
         └───────────────┬───────────────────────┘
                         │
         ┌───────────────┴───────────────────────┐
         │         HELPER LAYER                  │
         │  ┌─────────────────────────────────┐  │
         │  │ api-helpers.ts                  │  │
         │  │   - ApiHelpers                  │  │
         │  │   - TestDataGenerator           │  │
         │  │                                 │  │
         │  │ test-setup.ts                   │  │
         │  │   - TestSetup                   │  │
         │  │   - setupTests()                │  │
         │  │   - teardownTests()             │  │
         │  └─────────────────────────────────┘  │
         └───────────────┬───────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────────┐
         │         APPLICATION LAYER              │
         │  ┌─────────────────────────────────┐  │
         │  │         Frontend (React)        │  │
         │  │  http://localhost:4173          │  │
         │  └───────────────┬─────────────────┘  │
         │                  │                     │
         │  ┌───────────────┴─────────────────┐  │
         │  │         Backend (FastAPI)       │  │
         │  │  http://localhost:8000          │  │
         │  └─────────────────────────────────┘  │
         └───────────────────────────────────────┘
```

## Test Flow Diagram

```
┌──────────┐
│   Test   │
└────┬─────┘
     │
     ├─► Setup
     │   ├─► Create API Helpers
     │   ├─► Generate Test Data
     │   └─► Cleanup Old Sessions
     │
     ├─► Arrange
     │   ├─► Initialize Page Objects
     │   ├─► Navigate to Page
     │   └─► Set Up Test State
     │
     ├─► Act
     │   ├─► Perform User Actions
     │   ├─► Fill Forms
     │   ├─► Click Buttons
     │   ├─► Send WebSocket Events
     │   └─► Wait for Responses
     │
     ├─► Assert
     │   ├─► Verify Page Navigation
     │   ├─► Check API Responses
     │   ├─► Validate UI Elements
     │   └─► Confirm State Changes
     │
     ├─► Cleanup
     │   ├─► Delete Test Sessions
     │   ├─► Stop Running Processes
     │   └─► Clear Test Data
     │
     └─► Report
         ├─► Screenshot on Failure
         ├─► Video Recording
         ├─► Trace Files
         └─► HTML Report
```

## Page Object Hierarchy

```
Page (Playwright)
    │
    ├─► HomePage
    │   ├─► pageTitle: Locator
    │   ├─► createProjectButton: Locator
    │   ├─► viewSessionsButton: Locator
    │   ├─► goto()
    │   ├─► verifyPageLoaded()
    │   └─► clickCreateProject()
    │
    ├─► CreatePage
    │   ├─► pageTitle: Locator
    │   ├─► titleInput: Locator
    │   ├─► genreInput: Locator
    │   ├─► styleInput: Locator
    │   ├─► createButton: Locator
    │   ├─► goto()
    │   ├─► fillForm()
    │   └─► submitForm()
    │
    ├─► SessionsPage
    │   ├─► pageTitle: Locator
    │   ├─► sessionCards: Locator
    │   ├─► statusFilter: Locator
    │   ├─► goto()
    │   ├─► filterByStatus()
    │   └─► getSessionCount()
    │
    ├─► WorkspacePage
    │   ├─► progressLabel: Locator
    │   ├─► progressBar: Locator
    │   ├─► currentTaskLabel: Locator
    │   ├─► goto(sessionId)
    │   ├─► waitForTaskStart()
    │   └─► takeScreenshot()
    │
    └─► TaskApprovalDialog
        ├─► dialog: Locator
        ├─► taskTypeBadge: Locator
        ├─► approveButton: Locator
        ├─► rejectButton: Locator
        ├─► waitForVisible()
        ├─► approve()
        └─► reject()
```

## Data Flow

```
┌──────────────┐
│ Test Data    │
│ Generator    │
└──────┬───────┘
       │
       ├─► Create Session Data
       │   { title, mode, goal, config }
       │
       ▼
┌──────────────┐
│  API Helpers │
└──────┬───────┘
       │
       ├─► POST /sessions
       │   └─► Returns: { id, status, ... }
       │
       ├─► GET /sessions/:id
       │   └─► Returns: Session object
       │
       ├─► POST /sessions/:id/start
       ├─► POST /sessions/:id/pause
       ├─► POST /sessions/:id/resume
       └─► DELETE /sessions/:id
```

## WebSocket Events

```
Client (Test)                    Server (Backend)
     │                                  │
     ├───── subscribe ─────────────────►│
     │                                  │
     ├───── start ─────────────────────►│
     │                                  │
     │◀──── subscribed ─────────────────┤
     │                                  │
     │◀──── started ────────────────────┤
     │                                  │
     │◀──── task_start ─────────────────┤
     │                                  │
     │◀──── task_complete ──────────────┤
     │                                  │
     ├───── approve_task ──────────────►│
     │   { action: 'approve' }          │
     │                                  │
     │◀──── task_start (next) ──────────┤
     │                                  │
     │◀──── completed ───────────────────┤
     │                                  │
     ├───── stop ──────────────────────►│
     │                                  │
```

## Artifacts Output

```
test-results/
├── chromium/                    # Browser-specific results
│   ├── test-1/
│   │   ├── screenshot.png       # Failure screenshots
│   │   ├── video.webm           # Test recording
│   │   └── trace.zip            # Execution trace
│   └── ...
├── firefox/
└── webkit/

playwright-report/               # HTML report
├── index.html
├── data.json
└── ...

artifacts/                       # Custom screenshots
├── create-page-navigation.png
├── workspace-loaded.png
├── task-approval-dialog.png
└── ...

playwright-results.json          # JSON report
playwright-results.xml           # JUnit XML
```

## CI/CD Integration

```
┌────────────────┐
│ Pull Request   │
└────────┬───────┘
         │
         ▼
┌─────────────────────────────┐
│  GitHub Actions Trigger     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Install Dependencies       │
│  - npm ci                   │
│  - npx playwright install   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Start Servers              │
│  - Backend (uvicorn)        │
│  - Frontend (vite)          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Run E2E Tests              │
│  - Smoke tests              │
│  - Critical tests           │
│  - Important tests          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Upload Artifacts           │
│  - Screenshots              │
│  - Videos                   │
│  - Traces                   │
│  - HTML Report              │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Report Results             │
│  - Comment on PR            │
│  - Check status pass/fail   │
└─────────────────────────────┘
```

## Key Patterns

### 1. Test Structure
```typescript
test.describe('Feature Name', () => {
  test.beforeAll(async ({ request }) => {
    // Setup: Create API helpers, cleanup old data
  });

  test.afterAll(async ({ request }) => {
    // Teardown: Delete test sessions
  });

  test('should do something', async ({ page }) => {
    // Arrange: Setup test state
    // Act: Perform actions
    // Assert: Verify outcomes
  });
});
```

### 2. Page Object Usage
```typescript
const pageObject = new PageObjectClass(page);
await pageObject.goto();
await pageObject.performAction();
await expect(pageObject.element).toBeVisible();
```

### 3. API-First Testing
```typescript
const session = await apiHelpers.createSession(data);
await page.goto(`/workspace/${session.id}`);
// Test with real session
await apiHelpers.deleteSession(session.id);
```

### 4. Proper Waiting
```typescript
// ✅ Good - Wait for condition
await page.waitForResponse(resp => resp.url().includes('/api/sessions'));
await expect(element).toBeVisible();

// ❌ Bad - Arbitrary timeout
await page.waitForTimeout(5000);
```

### 5. Cleanup
```typescript
test.afterAll(async () => {
  for (const sessionId of testSessionIds) {
    await apiHelpers.stopSession(sessionId);
    await apiHelpers.deleteSession(sessionId);
  }
});
```

---

**Document Version**: 1.0
**Last Updated**: 2025-01-25
**Status**: ✅ Complete
