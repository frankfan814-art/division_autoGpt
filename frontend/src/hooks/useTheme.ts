/**
 * useTheme Hook
 *
 * 深色模式切换 Hook
 */

import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'creative-autogpt-theme';

function getSystemTheme(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getStoredTheme(): Theme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }
  return 'system';
}

function getAppliedTheme(themeSetting: Theme): 'light' | 'dark' {
  if (themeSetting === 'system') {
    return getSystemTheme();
  }
  return themeSetting;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => getStoredTheme());
  const [appliedTheme, setAppliedTheme] = useState<'light' | 'dark'>(() =>
    getAppliedTheme(getStoredTheme())
  );

  // 设置主题
  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem(THEME_STORAGE_KEY, newTheme);

    const resolvedTheme = getAppliedTheme(newTheme);
    setAppliedTheme(resolvedTheme);

    // 更新 DOM
    const root = document.documentElement;
    if (resolvedTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  };

  // 监听系统主题变化
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      const newTheme = e.matches ? 'dark' : 'light';
      setAppliedTheme(newTheme);

      const root = document.documentElement;
      if (newTheme === 'dark') {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // 初始化主题
  useEffect(() => {
    const root = document.documentElement;
    const resolvedTheme = getAppliedTheme(theme);

    setAppliedTheme(resolvedTheme);

    if (resolvedTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, []);

  return {
    theme,
    appliedTheme,
    setTheme,
    isDark: appliedTheme === 'dark',
  };
}
