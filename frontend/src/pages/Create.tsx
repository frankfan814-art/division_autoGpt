/**
 * Create page with smart prompt enhancement
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select } from '@/components/ui/Select';
import { useSessions } from '@/hooks/useSession';
import { useToast } from '@/components/ui/Toast';
import apiClient from '@/api/client';

const modeOptions = [
  { value: 'novel', label: '小说创作' },
  { value: 'story', label: '短篇故事' },
  { value: 'script', label: '剧本创作' },
];

export const Create = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { createSession, isCreating } = useSessions();

  const [useSmartCreate, setUseSmartCreate] = useState(false);
  const [userInput, setUserInput] = useState('');
  const [isEnhancing, setIsEnhancing] = useState(false);

  const [title, setTitle] = useState('');
  const [mode, setMode] = useState('novel');
  const [chapterWordCount, setChapterWordCount] = useState('2500'); // 每章字数，默认2500
  const [wordCount, setWordCount] = useState('50000'); // 默认5万字
  const [approvalMode, setApprovalMode] = useState(true); // 默认开启审核模式
  const [genre, setGenre] = useState('');
  const [style, setStyle] = useState('');
  const [requirements, setRequirements] = useState('');

  // 动态计算章节数
  const calculatedChapterCount = Math.ceil(parseInt(wordCount) / parseInt(chapterWordCount || '2500'));

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!title.trim()) {
      newErrors.title = '请输入项目标题';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 智能提示词增强
  const handleSmartEnhance = async () => {
    if (!userInput.trim()) {
      toast.warning('请输入您的创作想法');
      return;
    }

    setIsEnhancing(true);
    try {
      const response = await apiClient.post('/prompts/smart-enhance', {
        input: userInput,
        current_config: null,
      });

      const { config } = response.data;
      
      // 填充表单
      if (config.title) setTitle(config.title);
      if (config.genre) setGenre(config.genre);
      if (config.style) setStyle(config.style);
      if (config.requirements) setRequirements(config.requirements);
      if (config.chapter_word_count) setChapterWordCount(String(config.chapter_word_count));
      
      toast.success('智能分析完成，已为您填充表单！');
      setUseSmartCreate(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || '智能分析失败，请重试');
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    try {
      const session = await createSession({
        title,
        mode,
        goal: {
          genre,
          style,
          requirements,
          chapter_count: calculatedChapterCount,
          chapter_word_count: parseInt(chapterWordCount),
          word_count: parseInt(wordCount),
        },
        config: {
          approval_mode: approvalMode,
        },
      });

      toast.success('项目创建成功！');
      navigate(`/workspace/${session.id}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建项目失败，请重试');
    }
  };

  return (
    <MainLayout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">创建新项目</h1>
          <p className="text-gray-600 mt-2">
            {useSmartCreate 
              ? '💡 描述您的创作想法，AI将为您智能生成完整配置' 
              : '填写项目信息，开始AI辅助创作之旅'
            }
          </p>
          
          <div className="mt-4 flex gap-2">
            <Button
              type="button"
              variant={useSmartCreate ? 'secondary' : 'primary'}
              size="sm"
              onClick={() => setUseSmartCreate(false)}
            >
              📝 手动填写
            </Button>
            <Button
              type="button"
              variant={useSmartCreate ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setUseSmartCreate(true)}
            >
              ✨ 智能生成
            </Button>
          </div>
        </div>

        {useSmartCreate ? (
          <div className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
            <div>
              <Textarea
                label="您的创作想法"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                placeholder="例如：我想写一个关于时间旅行的科幻小说，主角是一个物理学家，意外发现了穿越时空的方法..."
                rows={8}
              />
              <p className="mt-1 text-sm text-gray-500">描述越详细，AI生成的配置越准确</p>
            </div>
            
            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setUseSmartCreate(false)}
              >
                返回手动填写
              </Button>
              <Button
                type="button"
                onClick={handleSmartEnhance}
                isLoading={isEnhancing}
              >
                ✨ 生成配置
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
            {/* Title */}
            <Input
              label="项目标题"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：我的科幻小说"
              error={errors.title}
              required
            />

          {/* Mode */}
          <Select
            label="创作模式"
            options={modeOptions}
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          />

          {/* Chapter Word Count */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              每章字数
            </label>
            <input
              type="number"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={chapterWordCount}
              onChange={(e) => setChapterWordCount(e.target.value)}
              min="500"
              max="10000"
              step="100"
            />
            <p className="mt-1 text-xs text-gray-500">建议范围：500-5000字/章</p>
          </div>

          {/* Word Count */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              目标字数
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={wordCount}
              onChange={(e) => setWordCount(e.target.value)}
            >
              <option value="5000">5千字（超短篇）</option>
              <option value="10000">1万字（短篇）</option>
              <option value="30000">3万字（中短篇）</option>
              <option value="50000">5万字（中篇）</option>
              <option value="100000">10万字（长篇）</option>
              <option value="200000">20万字（长篇）</option>
              <option value="500000">50万字（超长篇）</option>
              <option value="1000000">100万字（网文连载）</option>
            </select>
            {/* 动态显示计算出的章节数 */}
            <p className="mt-2 text-sm text-blue-600 font-medium">
              📖 预计章节数：{calculatedChapterCount} 章 （{parseInt(wordCount).toLocaleString()}字 ÷ {parseInt(chapterWordCount).toLocaleString()}字/章）
            </p>
          </div>

          {/* Approval Mode */}
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={approvalMode}
                onChange={(e) => setApprovalMode(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">每步审核模式</span>
                <p className="text-xs text-gray-500 mt-0.5">
                  开启后，每个任务完成后会等待您的审核通过才继续下一步（推荐）
                </p>
              </div>
            </label>
          </div>

          {/* Genre */}
          <Input
            label="类型/流派"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            placeholder="例如：科幻、奇幻、都市..."
          />

          {/* Style */}
          <Input
            label="写作风格"
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            placeholder="例如：悬疑、轻松、严肃..."
          />

          {/* Requirements */}
          <Textarea
            label="创作要求"
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
            placeholder="描述您的创作要求、故事背景、角色设定等..."
            rows={5}
          />

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate('/')}
              >
                取消
              </Button>
              <Button
                type="submit"
                isLoading={isCreating}
              >
                创建项目
              </Button>
            </div>
          </form>
        )}
      </div>
    </MainLayout>
  );
};
