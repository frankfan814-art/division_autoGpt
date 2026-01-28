/**
 * Hook for exporting session content to various formats
 */

import { useMutation } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { useToast } from '@/components/ui/Toast';
import logger from '@/utils/logger';

export type ExportFormat = 'txt' | 'md' | 'json' | 'full';

interface ExportParams {
  sessionId: string;
  format: ExportFormat;
  includeMetadata?: boolean;
}

export const useExport = () => {
  const toast = useToast();

  const exportMutation = useMutation({
    mutationFn: async ({ sessionId, format, includeMetadata = true }: ExportParams) => {
      // 🔥 后端返回 FileResponse（Blob），需要特殊处理
      const response = await apiClient.post(
        `/sessions/${sessionId}/export`,
        {
          format,
          include_metadata: includeMetadata,
        },
        {
          responseType: 'blob',  // 关键：告诉 axios 返回的是 Blob
        }
      );

      // 🔥 从响应头获取文件名
      const contentDisposition = response.headers['content-disposition'];
      let filename = `export.${format === 'full' ? 'md' : format}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // 🔥 创建 Blob URL 并触发下载
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // 释放 URL 对象
      window.URL.revokeObjectURL(url);

      return { filename, size: blob.size };
    },
    onSuccess: (data) => {
      toast.success(`导出成功：${data.filename}`);
    },
    onError: (error: any) => {
      logger.error('Export error:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '导出失败，请重试';
      toast.error(errorMessage);
    },
  });

  return {
    exportSession: exportMutation.mutate,
    isExporting: exportMutation.isPending,
  };
};
