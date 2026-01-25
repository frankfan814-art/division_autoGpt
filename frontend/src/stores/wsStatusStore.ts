/**
 * WebSocket connection status store
 */

import { create } from 'zustand';

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

interface WebSocketStatusState {
  status: ConnectionStatus;
  reconnectAttempts: number;
  lastError: string | null;

  // Actions
  setStatus: (status: ConnectionStatus) => void;
  setReconnectAttempts: (attempts: number) => void;
  setLastError: (error: string | null) => void;
  reset: () => void;
}

export const useWebSocketStatusStore = create<WebSocketStatusState>((set) => ({
  status: 'disconnected',
  reconnectAttempts: 0,
  lastError: null,

  setStatus: (status) => set({ status }),

  setReconnectAttempts: (attempts) => set({ reconnectAttempts: attempts }),

  setLastError: (error) => set({ lastError: error }),

  reset: () =>
    set({
      status: 'disconnected',
      reconnectAttempts: 0,
      lastError: null,
    }),
}));
