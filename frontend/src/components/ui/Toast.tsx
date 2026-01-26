/**
 * Toast notification component
 */

import { useEffect } from 'react';
import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = `toast_${Date.now()}_${Math.random()}`;
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }));
    
    // Auto remove after duration (default 5 seconds)
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, toast.duration || 5000);
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));

export const useToast = () => {
  const { addToast } = useToastStore();

  return {
    success: (message: string, duration?: number) =>
      addToast({ type: 'success', message, duration: duration ?? 10000 }),  // 🔥 默认10秒
    error: (message: string, duration?: number) =>
      addToast({ type: 'error', message, duration: duration ?? 15000 }),  // 🔥 默认15秒（错误信息需要更长时间阅读）
    warning: (message: string, duration?: number) =>
      addToast({ type: 'warning', message, duration: duration ?? 12000 }),  // 🔥 默认12秒
    info: (message: string, duration?: number) =>
      addToast({ type: 'info', message, duration: duration ?? 10000 }),  // 🔥 默认10秒
  };
};

const typeConfig: Record<ToastType, { icon: string; className: string }> = {
  success: { icon: '✅', className: 'bg-green-50 border-green-500 text-green-900' },
  error: { icon: '❌', className: 'bg-red-50 border-red-500 text-red-900' },
  warning: { icon: '⚠️', className: 'bg-yellow-50 border-yellow-500 text-yellow-900' },
  info: { icon: 'ℹ️', className: 'bg-blue-50 border-blue-500 text-blue-900' },
};

export const ToastContainer = () => {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => {
        const config = typeConfig[toast.type];
        return (
          <ToastItem
            key={toast.id}
            toast={toast}
            config={config}
            onClose={() => removeToast(toast.id)}
          />
        );
      })}
    </div>
  );
};

interface ToastItemProps {
  toast: Toast;
  config: { icon: string; className: string };
  onClose: () => void;
}

const ToastItem = ({ toast, config, onClose }: ToastItemProps) => {
  useEffect(() => {
    // Add enter animation
    const timer = setTimeout(() => {
      const el = document.getElementById(`toast-${toast.id}`);
      el?.classList.add('toast-enter');
    }, 10);
    return () => clearTimeout(timer);
  }, [toast.id]);

  return (
    <div
      id={`toast-${toast.id}`}
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border-l-4 shadow-lg transition-all duration-300 transform translate-x-full ${config.className}`}
      style={{ minWidth: '300px', maxWidth: '500px' }}
    >
      <span className="text-xl flex-shrink-0">{config.icon}</span>
      <p className="flex-1 text-sm font-medium">{toast.message}</p>
      <button
        onClick={onClose}
        className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  );
};
