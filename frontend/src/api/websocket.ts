/**
 * WebSocket client for real-time communication
 */

import { WebSocketMessage } from '@/types';
import { useWebSocketStatusStore } from '@/stores/wsStatusStore';
import logger from '@/utils/logger';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/ws';

export type WebSocketEventHandler = (data: any) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private clientId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private eventHandlers: Map<string, Set<WebSocketEventHandler>> = new Map();
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;

  connect() {
    // Prevent multiple connections
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      logger.debug('WebSocket already connected or connecting');
      return;
    }

    const statusStore = useWebSocketStatusStore.getState();
    statusStore.setStatus('connecting');

    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      logger.debug('WebSocket connected');
      this.reconnectAttempts = 0;
      statusStore.setStatus('connected');
      statusStore.setReconnectAttempts(0);

      // Send init message
      this.send({ event: 'connect' });

      // Start heartbeat
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        logger.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      logger.debug('WebSocket disconnected');
      statusStore.setStatus('disconnected');
      this.stopHeartbeat();
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      logger.error('WebSocket error:', error);
      statusStore.setStatus('error');
      statusStore.setLastError('连接错误');
    };
  }

  private handleMessage(message: WebSocketMessage) {
    const { event } = message;
    
    // Ignore internal/heartbeat events
    if (event === 'pong' || event === 'connected') {
      return;
    }
    
    const handlers = this.eventHandlers.get(event);

    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          logger.error(`Error in ${event} handler:`, error);
        }
      });
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error('Max reconnect attempts reached');
      const statusStore = useWebSocketStatusStore.getState();
      statusStore.setLastError('无法连接到服务器，请刷新页面重试');
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
    const statusStore = useWebSocketStatusStore.getState();
    statusStore.setReconnectAttempts(this.reconnectAttempts + 1);

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ event: 'ping' });
      }
    }, 3000); // 3 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    const statusStore = useWebSocketStatusStore.getState();
    statusStore.reset();
  }

  send(data: any): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      return true;
    }
    logger.warn('WebSocket not ready, readyState:', this.ws?.readyState);
    return false;
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  subscribe(event: string, handler: WebSocketEventHandler): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.eventHandlers.get(event)?.delete(handler);
    };
  }

  getSessionId(): string | null {
    return this.clientId;
  }
}

// Global WebSocket client instance
let globalWsClient: WebSocketClient | null = null;

export const getWebSocketClient = (): WebSocketClient => {
  if (!globalWsClient) {
    globalWsClient = new WebSocketClient();
    globalWsClient.connect();
  }
  return globalWsClient;
};

export default getWebSocketClient;
