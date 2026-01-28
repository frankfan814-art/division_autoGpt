/**
 * 日志配置
 *
 * 使用 loglevel 库进行日志管理
 * - 生产环境: 只显示 warn 和 error
 * - 开发环境: 显示所有级别
 */

import log from 'loglevel';

// 设置日志级别
const isDevelopment = import.meta.env.MODE === 'development';

if (isDevelopment) {
  log.setLevel('debug');
} else {
  log.setLevel('warn');
}

// 扩展 loglevel，添加更友好的方法
const logger = log;

// 可选：添加自定义格式
const originalFactory = log.methodFactory;
log.methodFactory = (methodName, logLevel, loggerName) => {
  const rawMethod = originalFactory(methodName, logLevel, loggerName);

  return (...args: any[]) => {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${methodName.toUpperCase()}]`;

    if (methodName === 'error' || methodName === 'warn') {
      // 在生产环境也保留错误和警告的堆栈信息
      console.error(prefix, ...args);
    } else {
      rawMethod(prefix, ...args);
    }
  };
};

// 设置新的工厂方法
log.setLevel(log.getLevel());

export default logger;
