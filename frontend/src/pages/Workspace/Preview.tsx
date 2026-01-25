/**
 * Preview page for workspace
 */

import { useParams } from 'react-router-dom';
import { PreviewPanel } from '@/components/PreviewPanel';

export const Preview = () => {
  const { sessionId } = useParams<{ sessionId: string }>();

  return (
    <div className="h-full">
      <PreviewPanel sessionId={sessionId || null} />
    </div>
  );
};
