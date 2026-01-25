/**
 * WebSocket connection status indicator
 */

import { useWebSocketStatusStore } from '@/stores/wsStatusStore';

export const WebSocketStatus = () => {
  const { status, reconnectAttempts, lastError } = useWebSocketStatusStore();

  if (status === 'connected') {
    return null; // Don't show when connected
  }

  const statusConfig = {
    connecting: {
      color: 'bg-yellow-500',
      text: '正在连接...',
      icon: '🔄',
    },
    disconnected: {
      color: 'bg-orange-500',
      text: reconnectAttempts > 0 ? `重连中 (${reconnectAttempts}/5)` : '已断开连接',
      icon: '⚠️',
    },
    error: {
      color: 'bg-red-500',
      text: lastError || '连接错误',
      icon: '❌',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className={`${config.color} text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 animate-pulse`}>
        <span>{config.icon}</span>
        <span className="text-sm font-medium">{config.text}</span>
      </div>
    </div>
  );
};
