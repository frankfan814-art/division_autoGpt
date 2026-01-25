/**
 * Preview store for managing content preview
 */

import { create } from 'zustand';

interface PreviewState {
  // Content preview
  outline: string | null;
  currentChapter: number;
  chapters: Map<number, string>; // chapter_index -> content

  // Preview settings
  showMetadata: boolean;
  showEvaluation: boolean;

  // UI state
  isLoading: boolean;
  error: string | null;

  // Actions
  setOutline: (outline: string | null) => void;
  setCurrentChapter: (chapterIndex: number | ((prev: number) => number)) => void;
  setChapterContent: (chapterIndex: number, content: string) => void;
  getChapterContent: (chapterIndex: number) => string | undefined;
  clearChapters: () => void;
  setShowMetadata: (show: boolean) => void;
  setShowEvaluation: (show: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const usePreviewStore = create<PreviewState>((set, get) => ({
  outline: null,
  currentChapter: 1,
  chapters: new Map(),
  showMetadata: true,
  showEvaluation: true,
  isLoading: false,
  error: null,

  setOutline: (outline) => set({ outline }),

  setCurrentChapter: (chapterIndex) => set((state) => ({
    currentChapter: typeof chapterIndex === 'function' ? chapterIndex(state.currentChapter) : chapterIndex
  })),

  setChapterContent: (chapterIndex, content) =>
    set((state) => {
      const newChapters = new Map(state.chapters);
      newChapters.set(chapterIndex, content);
      return { chapters: newChapters };
    }),

  getChapterContent: (chapterIndex) => {
    return get().chapters.get(chapterIndex);
  },

  clearChapters: () => set({ chapters: new Map() }),

  setShowMetadata: (show) => set({ showMetadata: show }),

  setShowEvaluation: (show) => set({ showEvaluation: show }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),
}));
