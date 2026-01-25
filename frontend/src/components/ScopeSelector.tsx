/**
 * ScopeSelector component for choosing feedback scope
 */

import { useState } from 'react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';

export interface ScopeOption {
  id: 'current_task' | 'future' | 'global';
  label: string;
  description: string;
  isDefault?: boolean;
  warning?: string;
}

export interface ScopeSelectorProps {
  /** 是否显示选择器 */
  isOpen: boolean;
  /** 选项列表 */
  options: ScopeOption[];
  /** 默认选中 */
  defaultScope?: string;
  /** 选择回调 */
  onSelect: (scope: string) => void;
  /** 取消回调 */
  onCancel?: () => void;
}

const DEFAULT_OPTIONS: ScopeOption[] = [
  {
    id: 'current_task',
    label: '仅当前任务',
    description: '只修改当前任务的内容，不影响其他部分',
    isDefault: true,
  },
  {
    id: 'future',
    label: '当前及后续任务',
    description: '修改当前任务，并影响后续相关内容的生成',
    warning: '会影响后续内容的连贯性',
  },
  {
    id: 'global',
    label: '全局设定',
    description: '修改整体创作设定，可能需要重新规划大纲',
    warning: '需要重新规划，可能影响已生成的内容',
  },
];

export const ScopeSelector = ({
  isOpen,
  options = DEFAULT_OPTIONS,
  defaultScope,
  onSelect,
  onCancel,
}: ScopeSelectorProps) => {
  const [selected, setSelected] = useState<string>(
    defaultScope || options.find(o => o.isDefault)?.id || options[0]?.id
  );

  const handleConfirm = () => {
    onSelect(selected);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel || (() => {})}
      title="🎯 这个修改应该影响哪些内容？"
      size="md"
    >
      <div className="space-y-3">
        {options.map((option) => (
          <label
            key={option.id}
            className={`block relative rounded-lg border-2 p-4 cursor-pointer transition-all ${
              selected === option.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300 bg-white'
            }`}
          >
            <input
              type="radio"
              name="scope"
              value={option.id}
              checked={selected === option.id}
              onChange={() => setSelected(option.id)}
              className="sr-only"
            />
            <div className="flex items-start">
              <div className={`flex-shrink-0 w-5 h-5 rounded-full border-2 mt-0.5 mr-3 flex items-center justify-center ${
                selected === option.id
                  ? 'border-blue-500 bg-blue-500'
                  : 'border-gray-300'
              }`}>
                {selected === option.id && (
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 12 12">
                    <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              <div className="flex-1">
                <div className="font-semibold text-gray-900 mb-1">
                  {option.label}
                </div>
                <div className="text-sm text-gray-600">
                  {option.description}
                </div>
                {option.warning && (
                  <div className="mt-2 flex items-start gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm">
                    <span className="text-yellow-600 flex-shrink-0">⚠️</span>
                    <span className="text-yellow-700">{option.warning}</span>
                  </div>
                )}
              </div>
            </div>
          </label>
        ))}
      </div>

      <div className="flex justify-end gap-2 mt-6">
        {onCancel && (
          <Button variant="ghost" onClick={onCancel}>
            取消
          </Button>
        )}
        <Button variant="primary" onClick={handleConfirm}>
          确认
        </Button>
      </div>
    </Modal>
  );
};
