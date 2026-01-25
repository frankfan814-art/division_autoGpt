/**
 * Export Dialog for session content export
 */

import { useState } from 'react';
import { Button } from './ui/Button';
import { Select } from './ui/Select';
import { ExportFormat, useExport } from '@/hooks/useExport';

interface ExportDialogProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

const formatOptions = [
  { value: 'txt', label: '纯文本 (.txt)' },
  { value: 'md', label: 'Markdown (.md)' },
  { value: 'docx', label: 'Word 文档 (.docx)' },
  { value: 'pdf', label: 'PDF 文档 (.pdf)' },
];

export const ExportDialog = ({ sessionId, isOpen, onClose }: ExportDialogProps) => {
  const [format, setFormat] = useState<ExportFormat>('txt');
  const [includeEvaluation, setIncludeEvaluation] = useState(false);
  const { exportSession, isExporting } = useExport();

  if (!isOpen) return null;

  const handleExport = () => {
    exportSession({ sessionId, format, includeEvaluation });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">导出内容</h2>

        <div className="space-y-4">
          <Select
            label="导出格式"
            options={formatOptions}
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
          />

          <div className="flex items-center">
            <input
              type="checkbox"
              id="include-evaluation"
              checked={includeEvaluation}
              onChange={(e) => setIncludeEvaluation(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="include-evaluation" className="ml-2 text-sm text-gray-700">
              包含质量评估信息
            </label>
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={isExporting}
            >
              取消
            </Button>
            <Button
              onClick={handleExport}
              isLoading={isExporting}
            >
              📥 导出
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
