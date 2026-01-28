/**
 * ResizablePanels - 可调整大小的面板容器
 *
 * 使用 react-resizable-panels 实现可拖拽调整大小的面板布局
 */

import {
  Panel,
  Group,
  Separator,
} from 'react-resizable-panels';
import { useLayoutStore } from '@/stores/layoutStore';

interface ResizablePanelsProps {
  /** 侧边栏内容 */
  sidebar: React.ReactNode;
  /** 主面板内容 */
  main: React.ReactNode;
  /** 聊天面板内容 */
  chat: React.ReactNode;
  /** 面板标签栏内容（放在主面板顶部） */
  panelTabs?: React.ReactNode;
}

/**
 * 调整手柄组件
 */
function ResizeHandle() {
  return (
    <Separator
      className="
        relative flex items-center justify-center w-1
        hover:bg-blue-200 transition-colors
        data-[separator-active]:bg-blue-300
      "
    >
      <div className="rounded-full bg-gray-300 w-1 h-8" />
    </Separator>
  );
}

/**
 * 可调整大小的面板容器
 */
export const ResizablePanels = ({
  sidebar,
  main,
  chat,
  panelTabs,
}: ResizablePanelsProps) => {
  const {
    panelLayout,
    setSidebarWidth,
    setChatPanelWidth,
    toggleSidebar,
    toggleChatPanel,
  } = useLayoutStore();

  // 侧边栏折叠/展开
  const handleToggleSidebar = () => {
    toggleSidebar();
  };

  // 聊天面板折叠/展开
  const handleToggleChat = () => {
    toggleChatPanel();
  };

  // 侧边栏宽度变化
  const handleSidebarResize = (size: { asPercentage: number; inPixels: number }) => {
    setSidebarWidth(size.inPixels);
  };

  // 聊天面板宽度变化
  const handleChatResize = (size: { asPercentage: number; inPixels: number }) => {
    setChatPanelWidth(size.inPixels);
  };

  return (
    <div className="h-full w-full flex flex-col">
      {/* 面板标签栏（如果有） */}
      {panelTabs && (
        <div className="flex-shrink-0 border-b bg-gray-50">
          {panelTabs}
        </div>
      )}

      {/* 主面板区域 */}
      <div className="flex-1 min-h-0">
        <Group
          orientation="horizontal"
          className="h-full"
        >
          {/* 侧边栏 */}
          {!panelLayout.sidebarCollapsed ? (
            <>
              <Panel
                defaultSize={panelLayout.sidebarWidth}
                minSize={180}
                maxSize={400}
                onResize={handleSidebarResize}
                className="min-w-0"
              >
                {sidebar}
              </Panel>
              <ResizeHandle />
            </>
          ) : (
            <div className="w-0" />
          )}

          {/* 主内容区 */}
          <Panel
            defaultSize={50}
            minSize={30}
            className="min-w-0 flex flex-col"
          >
            {main}
          </Panel>

          {/* 聊天面板 */}
          {!panelLayout.chatPanelCollapsed ? (
            <>
              <ResizeHandle />
              <Panel
                defaultSize={panelLayout.chatPanelWidth}
                minSize={280}
                maxSize={500}
                onResize={handleChatResize}
                className="min-w-0"
              >
                {chat}
              </Panel>
            </>
          ) : null}
        </Group>
      </div>

      {/* 折叠/展开控制按钮 */}
      <div className="absolute left-0 top-1/2 -translate-y-1/2 z-10 flex flex-col gap-2">
        {panelLayout.sidebarCollapsed && (
          <button
            onClick={handleToggleSidebar}
            className="ml-1 p-1 bg-white border rounded shadow hover:bg-gray-50"
            title="展开侧边栏"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>

      {!panelLayout.chatPanelCollapsed && (
        <button
          onClick={handleToggleChat}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 mr-1 p-1 bg-white border rounded shadow hover:bg-gray-50"
          title="折叠聊天面板"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      )}

      {panelLayout.chatPanelCollapsed && (
        <button
          onClick={handleToggleChat}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 mr-1 p-1 bg-white border rounded shadow hover:bg-gray-50"
          title="展开聊天面板"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>
      )}
    </div>
  );
};
