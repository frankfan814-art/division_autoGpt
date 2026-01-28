/**
 * Home page
 */

import { Link, useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { SessionCard } from '@/components/SessionCard';
import { ExportDialog } from '@/components/ExportDialog';
import { useSessions } from '@/hooks/useSession';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useState } from 'react';
import { Session } from '@/types';

export const Home = () => {
  const navigate = useNavigate();
  const { sessions, isLoading, deleteSession } = useSessions({ page: 1, page_size: 5 });
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportSessionId, setExportSessionId] = useState<string | null>(null);

  const recentSessions = sessions.slice(0, 3);

  const handleExport = (id: string) => {
    setExportSessionId(id);
    setExportDialogOpen(true);
  };

  // WebSocket real-time updates for session list
  useWebSocket({
    onSessionUpdate: () => {
      // Sessions will be updated via store automatically
    },
  });

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        {/* Hero Section */}
        <div className="text-center py-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Creative AutoGPT
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            智能小说创作助手 - 让AI帮你创作精彩故事
          </p>
          <div className="flex justify-center gap-4">
            <Link to="/create">
              <Button size="lg">创建新项目</Button>
            </Link>
            <Link to="/sessions">
              <Button variant="secondary" size="lg">查看会话列表</Button>
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 py-12">
          <div className="bg-white p-6 rounded-lg border shadow-sm">
            <div className="text-3xl mb-3">🤖</div>
            <h3 className="text-lg font-semibold mb-2">智能多模型路由</h3>
            <p className="text-gray-600 text-sm">
              自动选择最适合的LLM处理不同任务，优化创作质量和效率
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg border shadow-sm">
            <div className="text-3xl mb-3">📝</div>
            <h3 className="text-lg font-semibold mb-2">实时预览反馈</h3>
            <p className="text-gray-600 text-sm">
              实时查看创作进度，提供即时反馈，引导AI创作方向
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg border shadow-sm">
            <div className="text-3xl mb-3">✅</div>
            <h3 className="text-lg font-semibold mb-2">质量评估系统</h3>
            <p className="text-gray-600 text-sm">
              内置多维度质量评估，确保内容符合创作标准
            </p>
          </div>
        </div>

        {/* Recent Sessions */}
        <div className="py-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">最近项目</h2>
            <Link to="/sessions" className="text-blue-600 hover:text-blue-700 text-sm">
              查看全部 →
            </Link>
          </div>

          {isLoading ? (
            <div className="grid gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-gray-100 rounded-lg h-40 animate-pulse" />
              ))}
            </div>
          ) : recentSessions.length > 0 ? (
            <div className="grid gap-4">
              {recentSessions.map((session: Session) => (
                <SessionCard
                  key={session.id}
                  session={session}
                  onContinue={(id) => navigate(`/workspace/${id}`)}
                  onView={(id) => navigate(`/workspace/${id}`)}
                  onRead={(id) => navigate(`/workspace/${id}`)}
                  onExport={handleExport}
                  onDelete={deleteSession}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-white rounded-lg border">
              <div className="text-5xl mb-4">📝</div>
              <p className="text-gray-500 mb-4">暂无项目，创建第一个项目吧！</p>
              <Link to="/create">
                <Button>创建新项目</Button>
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Export Dialog */}
      {exportSessionId && (
        <ExportDialog
          sessionId={exportSessionId}
          isOpen={exportDialogOpen}
          onClose={() => {
            setExportDialogOpen(false);
            setExportSessionId(null);
          }}
        />
      )}
    </MainLayout>
  );
};
