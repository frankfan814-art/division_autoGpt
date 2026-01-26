/**
 * App root component
 */

import { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { Home } from './pages/Home';
import { Create } from './pages/Create';
import { Sessions } from './pages/Sessions';
import { WorkspaceLayout } from './components/layout/WorkspaceLayout';
import { Overview } from './pages/Workspace/Overview';
import { Tasks } from './pages/Workspace/Tasks';
import { Preview } from './pages/Workspace/Preview';
import { Reader } from './pages/Workspace/Reader';
import { Workspace } from './pages/Workspace/Workspace';
import { ToastContainer } from './components/ui/Toast';
import { WebSocketStatus } from './components/WebSocketStatus';
import { ErrorBoundary } from './components/ErrorBoundary';

// Create react-query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Suspense fallback={<div className="flex items-center justify-center h-screen">加载中...</div>}>
          <Routes>
            {/* Main routes */}
            <Route path="/" element={<Home />} />
            <Route path="/create" element={<Create />} />
            <Route path="/sessions" element={<Sessions />} />

            {/* Workspace routes */}
            <Route path="/workspace/:sessionId" element={<WorkspaceLayout />}>
              <Route index element={<Workspace />} />
              <Route path="overview" element={<Overview />} />
              <Route path="tasks" element={<Tasks />} />
              <Route path="preview" element={<Preview />} />
              {/* Reader is accessed directly from session list, not in sidebar */}
              <Route path="reader" element={<Reader />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <ToastContainer />
          <WebSocketStatus />
        </Suspense>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
