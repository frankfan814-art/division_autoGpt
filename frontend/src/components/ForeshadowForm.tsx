/**
 * ForeshadowForm component - 伏笔表单组件
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import {
  Foreshadow,
  ForeshadowCreateInput,
  ForeshadowUpdateInput,
  ForeshadowType,
  ForeshadowImportance,
} from '@/hooks/useForeshadow';

interface ForeshadowFormProps {
  foreshadow?: Partial<Foreshadow>;
  onSubmit: (data: Partial<Foreshadow> | ForeshadowCreateInput | ForeshadowUpdateInput) => void;
  onCancel: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
}

const typeOptions: { value: ForeshadowType; label: string }[] = [
  { value: 'plot', label: '剧情' },
  { value: 'character', label: '人物' },
  { value: 'worldview', label: '世界观' },
  { value: 'dialogue', label: '对话' },
];

const importanceOptions: { value: ForeshadowImportance; label: string }[] = [
  { value: 'critical', label: '关键' },
  { value: 'major', label: '重要' },
  { value: 'minor', label: '次要' },
];

export const ForeshadowForm = ({
  foreshadow,
  onSubmit,
  onCancel,
  submitLabel = '保存',
  isSubmitting = false,
}: ForeshadowFormProps) => {
  const [formData, setFormData] = useState<Partial<Foreshadow>>({
    name: '',
    type: 'plot',
    importance: 'minor',
    description: '',
    plant_chapter: undefined,
    payoff_chapter: undefined,
  });

  useEffect(() => {
    if (foreshadow) {
      setFormData({
        name: foreshadow.name || '',
        type: foreshadow.type || 'plot',
        importance: foreshadow.importance || 'minor',
        description: foreshadow.description || '',
        plant_chapter: foreshadow.plant_chapter,
        payoff_chapter: foreshadow.payoff_chapter,
      });
    }
  }, [foreshadow]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 基本信息 */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">基本信息</h3>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            伏笔名称 <span className="text-red-500">*</span>
          </label>
          <Input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="输入伏笔名称"
            required
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              伏笔类型 <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value as ForeshadowType })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              {typeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              重要性 <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.importance}
              onChange={(e) => setFormData({ ...formData, importance: e.target.value as ForeshadowImportance })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              {importanceOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">描述</label>
          <Textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="描述伏笔的内容和作用..."
            rows={3}
          />
        </div>
      </div>

      {/* 章节规划 */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">章节规划</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">埋设章节</label>
            <Input
              type="number"
              value={formData.plant_chapter || ''}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  plant_chapter: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              placeholder="预计埋设的章节号"
              min="1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">回收章节</label>
            <Input
              type="number"
              value={formData.payoff_chapter || ''}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  payoff_chapter: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              placeholder="预计回收的章节号"
              min="1"
            />
          </div>
        </div>

        {formData.plant_chapter && formData.payoff_chapter && formData.payoff_chapter <= formData.plant_chapter && (
          <p className="text-sm text-red-600">
            ⚠️ 回收章节应大于埋设章节
          </p>
        )}
      </div>

      {/* 提交按钮 */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          取消
        </Button>
        <Button
          type="submit"
          disabled={isSubmitting || Boolean(formData.payoff_chapter && formData.plant_chapter && formData.payoff_chapter <= formData.plant_chapter)}
        >
          {isSubmitting ? '保存中...' : submitLabel}
        </Button>
      </div>
    </form>
  );
};
