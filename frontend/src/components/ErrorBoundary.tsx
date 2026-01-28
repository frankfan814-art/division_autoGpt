/**
 * Error Boundary Component - 捕获React渲染错误，防止页面空白
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import logger from '@/utils/logger';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error('🚨 ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      // 默认的错误显示
      return (
        <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
          <h2 className="text-lg font-semibold text-red-800 mb-2">
            😵 页面渲染出错了
          </h2>
          <p className="text-sm text-red-700 mb-4">
            请尝试刷新页面，如果问题持续存在，请联系开发者。
          </p>
          <details className="bg-white p-3 rounded border">
            <summary className="cursor-pointer text-sm font-medium text-red-600">
              查看错误详情
            </summary>
            <pre className="mt-2 text-xs text-gray-700 overflow-auto max-h-40">
              {this.state.error?.toString()}
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            刷新页面
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
