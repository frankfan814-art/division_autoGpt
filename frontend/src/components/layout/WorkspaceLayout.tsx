/**
 * WorkspaceLayout component for workspace pages
 *
 * 简化后的布局 - 只包含全局 Header
 * 侧边栏、面板等布局由 Workspace 内部的 ResizablePanels 管理
 */

import { Outlet } from 'react-router-dom';
import { Header } from './Header';

export const WorkspaceLayout = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <div className="flex-1 overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
};
