/**
 * CharacterForm component - 人物表单组件
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Badge } from '@/components/ui/Badge';
import { Character } from '@/hooks/useCharacter';

interface CharacterFormProps {
  character?: Partial<Character>;
  onSubmit: (data: Partial<Character>) => void;
  onCancel: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
}

const roleOptions = [
  { value: 'protagonist', label: '主角' },
  { value: 'supporting', label: '配角' },
  { value: 'antagonist', label: '反派' },
  { value: 'minor', label: '路人' },
];

const genderOptions = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
  { value: 'other', label: '其他' },
];

export const CharacterForm = ({
  character,
  onSubmit,
  onCancel,
  submitLabel = '保存',
  isSubmitting = false,
}: CharacterFormProps) => {
  const [formData, setFormData] = useState<Partial<Character>>({
    name: '',
    role: 'minor',
    age: undefined,
    gender: undefined,
    appearance: '',
    personality: {
      traits: [],
      description: '',
    },
    background: '',
    goals: {
      main: '',
      sub_goals: [],
    },
    voice_profile: {
      voice: 'calm',
      speech_pattern: 'normal',
      catchphrases: [],
    },
  });

  const [traitInput, setTraitInput] = useState('');
  const [subGoalInput, setSubGoalInput] = useState('');
  const [catchphraseInput, setCatchphraseInput] = useState('');

  useEffect(() => {
    if (character) {
      setFormData({
        name: character.name || '',
        role: character.role || 'minor',
        age: character.age,
        gender: character.gender,
        appearance: character.appearance || '',
        personality: character.personality || { traits: [], description: '' },
        background: character.background || '',
        goals: character.goals || { main: '', sub_goals: [] },
        voice_profile: character.voice_profile || { voice: 'calm', speech_pattern: 'normal', catchphrases: [] },
      });
    }
  }, [character]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const addTrait = () => {
    if (traitInput.trim()) {
      setFormData({
        ...formData,
        personality: {
          ...formData.personality,
          traits: [...(formData.personality?.traits || []), traitInput.trim()],
        },
      });
      setTraitInput('');
    }
  };

  const removeTrait = (index: number) => {
    setFormData({
      ...formData,
      personality: {
        ...formData.personality,
        traits: formData.personality?.traits?.filter((_, i) => i !== index) || [],
      },
    });
  };

  const addSubGoal = () => {
    if (subGoalInput.trim()) {
      setFormData({
        ...formData,
        goals: {
          ...formData.goals,
          sub_goals: [...(formData.goals?.sub_goals || []), subGoalInput.trim()],
        },
      });
      setSubGoalInput('');
    }
  };

  const removeSubGoal = (index: number) => {
    setFormData({
      ...formData,
      goals: {
        ...formData.goals,
        sub_goals: formData.goals?.sub_goals?.filter((_, i) => i !== index) || [],
      },
    });
  };

  const addCatchphrase = () => {
    if (catchphraseInput.trim()) {
      setFormData({
        ...formData,
        voice_profile: {
          ...formData.voice_profile,
          catchphrases: [...(formData.voice_profile?.catchphrases || []), catchphraseInput.trim()],
        },
      });
      setCatchphraseInput('');
    }
  };

  const removeCatchphrase = (index: number) => {
    setFormData({
      ...formData,
      voice_profile: {
        ...formData.voice_profile,
        catchphrases: formData.voice_profile?.catchphrases?.filter((_, i) => i !== index) || [],
      },
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 基本信息 */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">基本信息</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              姓名 <span className="text-red-500">*</span>
            </label>
            <Input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="输入人物姓名"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              角色类型 <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as Character['role'] })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              {roleOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">年龄</label>
            <Input
              type="number"
              value={formData.age || ''}
              onChange={(e) => setFormData({ ...formData, age: e.target.value ? parseInt(e.target.value) : undefined })}
              placeholder="输入年龄"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">性别</label>
            <select
              value={formData.gender || ''}
              onChange={(e) => setFormData({ ...formData, gender: e.target.value as Character['gender'] })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">未指定</option>
              {genderOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">外貌描写</label>
          <Textarea
            value={formData.appearance}
            onChange={(e) => setFormData({ ...formData, appearance: e.target.value })}
            placeholder="描述人物的外貌特征..."
            rows={2}
          />
        </div>
      </div>

      {/* 性格设定 */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">性格设定</h3>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">性格标签</label>
          <div className="flex gap-2 mb-2">
            <Input
              type="text"
              value={traitInput}
              onChange={(e) => setTraitInput(e.target.value)}
              placeholder="输入性格特征（如：冷静、勇敢...）"
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTrait())}
            />
            <Button type="button" onClick={addTrait}>
              添加
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.personality?.traits?.map((trait, index) => (
              <Badge key={index} variant="primary" className="flex items-center gap-1">
                {trait}
                <button
                  type="button"
                  onClick={() => removeTrait(index)}
                  className="ml-1 text-blue-200 hover:text-white"
                >
                  ×
                </button>
              </Badge>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">性格描述</label>
          <Textarea
            value={formData.personality?.description || ''}
            onChange={(e) => setFormData({
              ...formData,
              personality: { ...formData.personality, description: e.target.value }
            })}
            placeholder="详细描述人物的性格特点..."
            rows={3}
          />
        </div>
      </div>

      {/* 背景和目标 */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">背景和目标</h3>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">背景故事</label>
          <Textarea
            value={formData.background}
            onChange={(e) => setFormData({ ...formData, background: e.target.value })}
            placeholder="描述人物的背景经历..."
            rows={3}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">核心目标</label>
          <Textarea
            value={formData.goals?.main || ''}
            onChange={(e) => setFormData({
              ...formData,
              goals: { ...formData.goals, main: e.target.value }
            })}
            placeholder="描述人物的核心目标或动机..."
            rows={2}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">次要目标</label>
          <div className="flex gap-2 mb-2">
            <Input
              type="text"
              value={subGoalInput}
              onChange={(e) => setSubGoalInput(e.target.value)}
              placeholder="输入次要目标"
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addSubGoal())}
            />
            <Button type="button" onClick={addSubGoal}>
              添加
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.goals?.sub_goals?.map((goal, index) => (
              <Badge key={index} variant="secondary" className="flex items-center gap-1">
                {goal}
                <button
                  type="button"
                  onClick={() => removeSubGoal(index)}
                  className="ml-1 text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* 语言风格 */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-900">对话风格</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">语调</label>
            <select
              value={formData.voice_profile?.voice || 'calm'}
              onChange={(e) => setFormData({
                ...formData,
                voice_profile: { ...formData.voice_profile, voice: e.target.value }
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="calm">冷静</option>
              <option value="energetic">活力</option>
              <option value="formal">正式</option>
              <option value="casual">随意</option>
              <option value="aggressive">强势</option>
              <option value="gentle">温和</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">说话方式</label>
            <select
              value={formData.voice_profile?.speech_pattern || 'normal'}
              onChange={(e) => setFormData({
                ...formData,
                voice_profile: { ...formData.voice_profile, speech_pattern: e.target.value }
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="normal">正常</option>
              <option value="direct">直爽</option>
              <option value="polite">礼貌</option>
              <option value="formal">正式</option>
              <option value="casual">随意</option>
              <option value="aggressive">粗鲁</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">口头禅/习惯用语</label>
          <div className="flex gap-2 mb-2">
            <Input
              type="text"
              value={catchphraseInput}
              onChange={(e) => setCatchphraseInput(e.target.value)}
              placeholder="输入口头禅"
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCatchphrase())}
            />
            <Button type="button" onClick={addCatchphrase}>
              添加
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.voice_profile?.catchphrases?.map((phrase, index) => (
              <Badge key={index} variant="default" className="flex items-center gap-1">
                "{phrase}"
                <button
                  type="button"
                  onClick={() => removeCatchphrase(index)}
                  className="ml-1 text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* 提交按钮 */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          取消
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? '保存中...' : submitLabel}
        </Button>
      </div>
    </form>
  );
};
