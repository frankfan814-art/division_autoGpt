/**
 * PanelTabBar - 面板标签切换栏
 *
 * 用于在主面板中切换不同的视图：
 * - 📝 预览 (PreviewPanel)
 * - 📋 任务 (TaskListPanel)
 * - 📖 阅读 (ReaderPanel)
 * - ⚙️ 设定 (SettingsPanel)
 */

import { useLayoutStore, PanelTab } from '@/stores/layoutStore';

interface PanelTabBarProps {
  className?: string;
}

const tabs: { id: PanelTab; label: string; icon: string }[] = [
  { id: 'preview', label: '预览', icon: '📝' },
  { id: 'tasks', label: '任务', icon: '📋' },
  { id: 'reader', label: '阅读', icon: '📖' },
  { id: 'settings', label: '设定', icon: '⚙️' },
];

export const PanelTabBar = ({ className = '' }: PanelTabBarProps) => {
  const { activePanelTab, setActivePanelTab } = useLayoutStore();

  return (
    <div className={`flex items-center gap-1 px-3 py-2 ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setActivePanelTab(tab.id)}
          className={`
            px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2
            ${
              activePanelTab === tab.id
                ? 'bg-blue-100 text-blue-700 shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }
          `}
        >
          <span>{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
};
