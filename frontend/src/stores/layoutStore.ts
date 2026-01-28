/**
 * Layout Store - 管理工作区布局状态
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type PanelTab = 'preview' | 'tasks' | 'reader' | 'settings';
export type LayoutMode = 'split' | 'stack';

/**
 * 面板布局配置
 */
export interface PanelLayout {
  sidebarWidth: number;        // 侧边栏宽度 (px)
  sidebarCollapsed: boolean;   // 侧边栏是否折叠
  chatPanelWidth: number;      // 聊天面板宽度 (px)
  chatPanelCollapsed: boolean; // 聊天面板是否折叠
  layoutMode: LayoutMode;      // 布局模式 (并排/堆叠)
}

/**
 * 布局状态
 */
interface LayoutState {
  panelLayout: PanelLayout;
  activePanelTab: PanelTab;
}

/**
 * 布局操作
 */
interface LayoutActions {
  // 面板布局操作
  updatePanelLayout: (layout: Partial<PanelLayout>) => void;
  setSidebarWidth: (width: number) => void;
  setChatPanelWidth: (width: number) => void;
  toggleSidebar: () => void;
  toggleChatPanel: () => void;
  setLayoutMode: (mode: LayoutMode) => void;

  // 面板标签操作
  setActivePanelTab: (tab: PanelTab) => void;

  // 重置布局
  resetLayout: () => void;
}

/**
 * 默认布局配置
 */
const defaultPanelLayout: PanelLayout = {
  sidebarWidth: 240,
  sidebarCollapsed: false,
  chatPanelWidth: 320,
  chatPanelCollapsed: false,
  layoutMode: 'split',
};

type LayoutStore = LayoutState & LayoutActions;

/**
 * 布局 Store
 */
export const useLayoutStore = create<LayoutStore>()(
  persist(
    (set) => ({
      // 初始状态
      panelLayout: defaultPanelLayout,
      activePanelTab: 'preview',

      // 更新面板布局
      updatePanelLayout: (layout: Partial<PanelLayout>) =>
        set((state) => ({
          panelLayout: { ...state.panelLayout, ...layout },
        })),

      // 设置侧边栏宽度
      setSidebarWidth: (width: number) =>
        set((state) => ({
          panelLayout: { ...state.panelLayout, sidebarWidth: width },
        })),

      // 设置聊天面板宽度
      setChatPanelWidth: (width: number) =>
        set((state) => ({
          panelLayout: { ...state.panelLayout, chatPanelWidth: width },
        })),

      // 切换侧边栏折叠状态
      toggleSidebar: () =>
        set((state) => ({
          panelLayout: {
            ...state.panelLayout,
            sidebarCollapsed: !state.panelLayout.sidebarCollapsed,
          },
        })),

      // 切换聊天面板折叠状态
      toggleChatPanel: () =>
        set((state) => ({
          panelLayout: {
            ...state.panelLayout,
            chatPanelCollapsed: !state.panelLayout.chatPanelCollapsed,
          },
        })),

      // 设置布局模式
      setLayoutMode: (mode: LayoutMode) =>
        set((state) => ({
          panelLayout: { ...state.panelLayout, layoutMode: mode },
        })),

      // 设置当前激活的面板标签
      setActivePanelTab: (tab: PanelTab) =>
        set({ activePanelTab: tab }),

      // 重置布局
      resetLayout: () =>
        set({
          panelLayout: defaultPanelLayout,
          activePanelTab: 'preview',
        }),
    }),
    {
      name: 'creative-autogpt-layout-storage', // localStorage key
      partialize: (state) => ({
        panelLayout: state.panelLayout,
        activePanelTab: state.activePanelTab,
      }),
    }
  )
);
