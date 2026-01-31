/**
 * Hooks index
 */

export { useWebSocket } from './useWebSocket';
export type { UseWebSocketOptions } from './useWebSocket';

export { useSession, useSessions } from './useSession';

export { useTasks, useTaskProgress, useFilteredTasks } from './useTask';

export { useChat } from './useChat';

export { usePreview } from './usePreview';

// 🔥 新增：章节版本管理 hooks
export { useChapters, useChapterVersions, useChapterVersionDetail } from './useChapter';
export type { ChapterVersion, ChapterInfo } from './useChapter';
