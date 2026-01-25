/**
 * Hook for exporting session content to various formats
 */

import { useMutation } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { useToast } from '@/components/ui/Toast';

export type ExportFormat = 'txt' | 'md' | 'docx' | 'pdf';

interface ExportParams {
  sessionId: string;
  format: ExportFormat;
  includeEvaluation?: boolean;
}

interface ExportResponse {
  download_url: string;
  filename: string;
  size: number;
}

export const useExport = () => {
  const toast = useToast();

  const exportMutation = useMutation({
    mutationFn: async ({ sessionId, format, includeEvaluation = false }: ExportParams) => {
      const response = await apiClient.post<{ data: ExportResponse }>(
        `/sessions/${sessionId}/export`,
        {
          format,
          include_evaluation: includeEvaluation,
        }
      );
      return response.data.data;
    },
    onSuccess: (data) => {
      // 触发下载
      const link = document.createElement('a');
      link.href = data.download_url;
      link.download = data.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast.success(`导出成功：${data.filename}`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '导出失败，请重试');
    },
  });

  return {
    exportSession: exportMutation.mutate,
    isExporting: exportMutation.isPending,
  };
};
