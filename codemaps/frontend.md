# Frontend Architecture - React/TypeScript Client

**Last Updated:** 2025-01-25
**Framework:** React 18 + TypeScript + Vite
**Entry Point:** frontend/src/main.tsx → App.tsx

## Directory Structure

```
frontend/src/
├── main.tsx                  # Vite entry point
├── App.tsx                   # Root component
├── vite-env.d.ts             # Vite type definitions
├── index.css                 # Global styles
│
├── types/
│   └── index.ts              # TypeScript type definitions
│
├── stores/                   # Zustand state management
│   ├── sessionStore.ts       # Session CRUD state
│   ├── taskStore.ts          # Task progress state
│   ├── wsStatusStore.ts      # WebSocket connection state
│   ├── previewStore.ts       # Task result preview
│   └── chatStore.ts          # User feedback/chat
│
├── components/
│   ├── layout/
│   │   ├── MainLayout.tsx    # App shell with header/sidebar
│   │   ├── Header.tsx        # Top navigation bar
│   │   ├── Sidebar.tsx       # Session list sidebar
│   │   └── WorkspaceLayout.tsx # Main workspace
│   │
│   ├── ui/                   # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Textarea.tsx
│   │   ├── Select.tsx
│   │   ├── Modal.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Progress.tsx
│   │   ├── Toast.tsx
│   │   ├── ThemeToggle.tsx
│   │   └── index.ts          # UI exports
│   │
│   ├── SessionCard.tsx       # Session display card
│   ├── TaskCard.tsx          # Task progress card
│   ├── PreviewPanel.tsx      # Task result preview panel
│   ├── TaskApproval.tsx      # Approve/reject modal
│   ├── ExportDialog.tsx      # Export options modal
│   └── WebSocketStatus.tsx   # Connection status indicator
│
└── utils/
    ├── api.ts                # HTTP client (fetch wrapper)
    ├── websocket.ts          # WebSocket client
    └── formatting.ts         # Date/time formatters
```

## Technology Stack

**Core:**
- React 18.3+ - UI framework
- TypeScript 5.6+ - Type safety
- Vite 6.0+ - Build tool and dev server

**State Management:**
- Zustand 5+ - Lightweight state management
- zustand/middleware - Persist middleware for localStorage

**Styling:**
- Tailwind CSS 3.4+ - Utility-first CSS
- PostCSS - CSS processing
- tailwindcss-animate - Animation utilities

**UI Components:**
- Radix UI - Headless component primitives (via shadcn/ui patterns)
- Lucide React - Icon library

**Testing:**
- Vitest - Unit testing
- Playwright - E2E testing
- React Testing Library - Component testing

## State Management (Zustand Stores)

### Session Store (stores/sessionStore.ts)

**Purpose:** Manage writing sessions

**State:**
```typescript
{
  sessions: Session[]           // All sessions
  currentSession: Session | null  // Active session
  isLoading: boolean
  error: string | null
}
```

**Actions:**
```typescript
fetchSessions()                // GET /api/sessions
createSession(title, goal)     // POST /api/sessions
selectSession(id)              // Set current session
updateSession(id, updates)     // PUT /api/sessions/{id}
deleteSession(id)              // DELETE /api/sessions/{id}
exportSession(id, format)      // POST /api/sessions/{id}/export
```

**Persistence:** localStorage (via zustand/persist)

### Task Store (stores/taskStore.ts)

**Purpose:** Track task execution progress

**State:**
```typescript
{
  tasks: Task[]                // All tasks for current session
  currentTask: Task | null     // Currently executing task
  progress: Progress           // { total, completed, percentage }
  isExecuting: boolean
}
```

**Actions:**
```typescript
setTasks(tasks)                // Update task list
updateTask(id, updates)        // Update single task
setCurrentTask(task)           // Set running task
setProgress(progress)          // Update progress stats
reset()                        // Clear state
```

**Integration:** Updated via WebSocket events

### WebSocket Status Store (stores/wsStatusStore.ts)

**Purpose:** Track WebSocket connection state

**State:**
```typescript
{
  connected: boolean
  connecting: boolean
  error: string | null
  reconnectAttempts: number
}
```

**Actions:**
```typescript
setConnected(connected)
setConnecting(connecting)
setError(error)
incrementReconnectAttempts()
resetReconnectAttempts()
```

**UI Indicator:** WebSocketStatus component shows status with colored dot

### Preview Store (stores/previewStore.ts)

**Purpose:** Manage task result preview

**State:**
```typescript
{
  isVisible: boolean
  taskId: string | null
  content: string | null
  evaluation: Evaluation | null
  taskType: string | null
}
```

**Actions:**
```typescript
showPreview(taskId, content, evaluation, taskType)
hidePreview()
updateContent(content)
```

**Integration:** Triggered by task completion events

### Chat Store (stores/chatStore.ts)

**Purpose:** User feedback and chat interface

**State:**
```typescript
{
  messages: Message[]          // Chat history
  feedback: string | null      // Current user feedback
}
```

**Actions:**
```typescript
addMessage(message)
setFeedback(text)
submitFeedback(sessionId)      // Send via WebSocket
clear()
```

## Component Architecture

### Layout Components

#### MainLayout (components/layout/MainLayout.tsx)

**Purpose:** App shell with header and sidebar

**Structure:**
```
<div className="min-h-screen bg-background">
  <Header />
  <div className="flex">
    <Sidebar />
    <main>{children}</main>
  </div>
</div>
```

**Features:**
- Responsive layout (mobile hamburger menu)
- Theme toggle (dark/light mode)
- Global error boundary

#### Header (components/layout/Header.tsx)

**Elements:**
- Logo/title
- Theme toggle button
- Connection status indicator
- User menu (future)

#### Sidebar (components/layout/Sidebar.tsx)

**Purpose:** Session list and navigation

**Features:**
- SessionCard for each session
- "New Session" button
- Session status badges
- Active session highlighting
- Filter/search (future)

**State Integration:** Uses sessionStore

#### WorkspaceLayout (components/layout/WorkspaceLayout.tsx)

**Purpose:** Main workspace for active session

**Layout:**
```
┌────────────────────────────────────────┐
│ Session Info                           │
├────────────────────┬───────────────────┤
│ Task List          │ Preview Panel     │
│ (TaskCard items)   │ (Right panel)     │
└────────────────────┴───────────────────┘
```

**Features:**
- Breadcrumb navigation
- Session controls (start, pause, stop)
- Split view (tasks + preview)

### UI Components

**Design System:** shadcn/ui inspired

| Component | Purpose | Props |
|-----------|---------|-------|
| Button | Clickable actions | variant (default, ghost, outline), size |
| Input | Text input | placeholder, onChange, value |
| Textarea | Multi-line input | rows, placeholder |
| Select | Dropdown selection | options, value, onChange |
| Modal | Dialog overlay | isOpen, onClose, children |
| Card | Content container | title, children, footer |
| Badge | Status labels | variant (default, success, warning) |
| Progress | Progress bar | value (0-100), label |
| Toast | Notifications | message, type (info, success, error) |
| ThemeToggle | Dark/light mode | toggle |

**Styling:** Tailwind CSS utility classes

### Feature Components

#### SessionCard (components/SessionCard.tsx)

**Purpose:** Display session in list

**Props:**
```typescript
{
  session: Session
  isActive: boolean
  onClick: () => void
  onDelete: () => void
}
```

**Display:**
- Session title
- Status badge (created, running, paused, completed)
- Progress bar
- Task count (X/Y completed)
- Creation date
- Delete button (hover)

#### TaskCard (components/TaskCard.tsx)

**Purpose:** Display task with controls

**Props:**
```typescript
{
  task: Task
  isActive: boolean
  onApprove?: () => void
  onReject?: () => void
}
```

**Display:**
- Task type (e.g., "章节大纲", "章节内容")
- Status indicator (pending, running, completed, failed)
- Chapter index (if applicable)
- Retry count
- Approval buttons (if approval mode enabled)

**Interactions:**
- Click → Show preview
- Approve → Continue execution
- Reject → Trigger rewrite

#### PreviewPanel (components/PreviewPanel.tsx)

**Purpose:** Display task result content

**Props:**
```typescript
{
  taskId: string
  content: string
  evaluation: Evaluation | null
  taskType: string
  onClose: () => void
}
```

**Layout:**
```
┌─────────────────────────────┐
│ Task Type          [Close]  │
├─────────────────────────────┤
│ Content (formatted text)    │
│                              │
├─────────────────────────────┤
│ Evaluation Score: 85%       │
│ - Coherence: 90%            │
│ - Creativity: 80%           │
│ Suggestions: [...]          │
└─────────────────────────────┘
```

**Features:**
- Markdown rendering (if applicable)
- Evaluation breakdown
- Copy to clipboard
- Download as file

#### TaskApproval (components/TaskApproval.tsx)

**Purpose:** Modal for approving/rejecting task results

**Props:**
```typescript
{
  task: Task
  result: string
  evaluation: Evaluation
  onApprove: () => void
  onReject: (feedback: string) => void
  isOpen: boolean
}
```

**Layout:**
```
┌─────────────────────────────┐
│ Review Task Result          │
├─────────────────────────────┤
│ [Preview content]           │
│                              │
│ Evaluation Score: 0.85      │
│                              │
├─────────────────────────────┤
│ [Approve]  [Reject]         │
│                              │
│ Feedback: [Textarea]         │
└─────────────────────────────┘
```

#### ExportDialog (components/ExportDialog.tsx)

**Purpose:** Export session content

**Props:**
```typescript
{
  session: Session
  isOpen: boolean
  onClose: () => void
}
```

**Options:**
- Format: TXT, JSON, Markdown
- Include metadata: Yes/No
- Chapter range: All or specific chapters
- Download button

#### WebSocketStatus (components/WebSocketStatus.tsx)

**Purpose:** Display connection status

**Visual:**
- Green dot = Connected
- Yellow dot = Connecting
- Red dot = Disconnected
- Reconnect attempt count

**Auto-reconnect:** Implements exponential backoff

## WebSocket Integration

### WebSocket Client (utils/websocket.ts)

**Class:**
```typescript
class WebSocketClient {
  private ws: WebSocket | null
  private url: string
  private reconnectAttempts: number
  private maxReconnectAttempts: number
  private reconnectDelay: number

  connect(url: string)
  disconnect()
  send(event: string, data: any)
  on(event: string, handler: Function)
  off(event: string, handler: Function)
}
```

**Event Handling:**
```typescript
ws.on('connected', () => { /* ... */ })
ws.on('progress', (data) => { /* Update taskStore */ })
ws.on('task_complete', (data) => { /* Show preview */ })
ws.on('error', (error) => { /* Show toast */ })
```

**Auto-Reconnect:**
- Exponential backoff: 1s, 2s, 4s, 8s, 16s
- Max attempts: 5
- Manual reconnect button after max attempts

### Event Flow

```
Component → WebSocketClient.send(event, data)
    ↓
WebSocket → Backend (websocket.py)
    ↓
Backend processes → WebSocket broadcast
    ↓
WebSocketClient.on('event') → Update Zustand store
    ↓
Component re-renders with new state
```

**Example: Task Progress**
```typescript
// Backend sends
ws.send(JSON.stringify({
  event: 'progress',
  data: { total_tasks: 10, completed_tasks: 5, percentage: 50 }
}))

// Frontend receives
ws.on('progress', (data) => {
  taskStore.setProgress(data)
})
```

## API Client

### HTTP Client (utils/api.ts)

**Wrapper around fetch:**
```typescript
async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T>

// Convenience methods
get<T>(endpoint: string)
post<T>(endpoint: string, data: any)
put<T>(endpoint: string, data: any)
delete<T>(endpoint: string)
```

**Error Handling:**
- Try/catch with toast notifications
- Parse error messages from backend
- Update store error state

**Usage Example:**
```typescript
const sessions = await api.get<Session[]>('/api/sessions')
sessionStore.setSessions(sessions)
```

## Type Definitions

### Core Types (types/index.ts)

```typescript
// Session
interface Session {
  id: string
  title: string
  mode: string
  status: SessionStatus
  goal: Goal
  config: Config
  created_at: string
  updated_at: string
  total_tasks: number
  completed_tasks: number
}

// Task
interface Task {
  task_id: string
  task_type: string
  description: string
  status: TaskStatus
  result?: string
  evaluation?: Evaluation
  chapter_index?: number
  retry_count: number
}

// Evaluation
interface Evaluation {
  passed: boolean
  score: number
  dimension_scores: Record<string, DimensionScore>
  reasons: string[]
  suggestions: string[]
}

// Enums
enum SessionStatus {
  CREATED = 'created',
  RUNNING = 'running',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

enum TaskStatus {
  PENDING = 'pending',
  READY = 'ready',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed'
}
```

## Routing

**Current:** No client-side routing (single-page app)

**Future:** React Router for:
- `/sessions` - Session list
- `/sessions/:id` - Session detail
- `/settings` - Settings page
- `/export/:id` - Export page

## Styling Strategy

**Tailwind CSS Configuration:**

```javascript
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        // ... CSS variables for theming
      }
    }
  },
  plugins: [require('tailwindcss-animate')]
}
```

**Dark Mode:**
- CSS variables via `data-theme` attribute
- ThemeToggle component switches `data-theme` between 'light' and 'dark'
- Tailwind's `dark:` modifier for conditional styles

**Responsive Design:**
- Mobile-first approach
- Breakpoints: `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`
- Sidebar collapses on mobile
- Grid layouts adapt to screen size

## Performance Optimizations

**Code Splitting:**
- Vite automatic code splitting
- Lazy loading for large components (future)

**State Management:**
- Zustand's shallow comparison for selective updates
- Memoized selectors via `useStore()` hook

**Rendering:**
- React.memo for expensive components
- useMemo/useCallback for event handlers
- Virtualization for long lists (future: react-window)

**WebSocket:**
- Throttled progress updates (max 10/sec)
- Batch state updates

## Testing Strategy

**Unit Tests (Vitest):**
- Store logic (reducers, actions)
- Utility functions
- Component logic (hooks)

**Component Tests (RTL):**
- User interactions
- Props rendering
- Event handling

**E2E Tests (Playwright):**
- Critical user flows
- WebSocket integration
- Session creation → execution → export

## Key Frontend Patterns

1. **Container/Presentational:** Components separated into logic (stores) and UI
2. **Composition:** Layout components compose smaller components
3. **Hooks:** Custom hooks for WebSocket, API calls
4. **State Machines:** Task status transitions tracked in store
5. **Event-Driven:** WebSocket events drive state updates
6. **Optimistic UI:** UI updates immediately, validated by server

---

**Related Codemaps:**
- [Architecture Overview](architecture.md) - System-wide architecture
- [Backend Structure](backend.md) - API and server logic
- [Data Models](data.md) - Shared type definitions
