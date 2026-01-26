/**
 * Preview page - 查看所有任务结果（大纲、人物、章节等）
 * 从会话列表点击"查看"进入，或在侧边栏点击"预览"
 */

import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { PreviewPanel } from '@/components/PreviewPanel';
import { useTasks } from '@/hooks/useTask';
import { useTaskStore } from '@/stores/taskStore';

export const Preview = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const setCurrentSession = useTaskStore((state) => state.setCurrentSession);

  // 🔥 主动加载任务数据（从会话列表点击"查看"进入时需要）
  useTasks(sessionId!);

  // 🔥 设置当前会话到 taskStore
  useEffect(() => {
    if (sessionId) {
      console.log('🔄 Preview: Setting current session:', sessionId);
      setCurrentSession(sessionId);
    }
  }, [sessionId, setCurrentSession]);

  return (
    <div className="h-full">
      <PreviewPanel sessionId={sessionId || null} />
    </div>
  );
};
