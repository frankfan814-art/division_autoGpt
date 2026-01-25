/**
 * ThemeToggle Component
 *
 * 深色模式切换组件
 */

import { Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const themes: { value: 'light' | 'dark' | 'system'; icon: React.ReactNode; label: string }[] = [
    { value: 'light', icon: <Sun className="w-4 h-4" />, label: '浅色' },
    { value: 'dark', icon: <Moon className="w-4 h-4" />, label: '深色' },
    { value: 'system', icon: <Monitor className="w-4 h-4" />, label: '跟随系统' },
  ];

  const currentIndex = themes.findIndex((t) => t.value === theme);
  const nextTheme = themes[(currentIndex + 1) % themes.length];

  return (
    <div className="relative group">
      {/* 按钮 */}
      <button
        onClick={() => setTheme(nextTheme.value)}
        className="btn-ghost !p-2 rounded-lg"
        title={`当前: ${themes[currentIndex].label}，点击切换到 ${nextTheme.label}`}
        aria-label={`切换主题，当前: ${themes[currentIndex].label}`}
      >
        {themes[currentIndex].icon}
      </button>

      {/* 提示 */}
      <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
        {themes[currentIndex].label}
      </div>
    </div>
  );
}
