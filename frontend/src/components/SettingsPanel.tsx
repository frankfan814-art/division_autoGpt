/**
 * SettingsPanel - 设定面板
 *
 * 显示和编辑用户的创作设定
 * 包括：目标字数、章节数、类型/流派、写作风格、创作要求等
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select } from '@/components/ui/Select';
import { useSession } from '@/hooks/useSession';
import { useToast } from '@/components/ui/Toast';
import apiClient from '@/api/client';
import logger from '@/utils/logger';

interface SettingsPanelProps {
  sessionId: string;
}

const modeOptions = [
  { value: 'novel', label: '小说创作' },
  { value: 'story', label: '短篇故事' },
  { value: 'script', label: '剧本创作' },
];

const authorStyleOptions = [
  { value: '', label: '不限制（默认）' },
  { value: 'liucixin', label: '刘慈欣 - 硬科幻，宏大的宇宙观' },
  { value: 'jiangnan', label: '江南 - 热血青春，细腻情感' },
  { value: 'fenghuo', label: '我吃西红柿 - 升级流，爽文' },
  { value: 'tangjia', label: '唐家三少 - 热血冒险，友情羁绊' },
  { value: 'chenan', label: '陈安 - 悬疑推理，逻辑严密' },
  { value: 'caocao', label: '猫腻 - 权谋政治，文笔细腻' },
  { value: 'wuxing', label: '耳根 - 仙侠玄幻，世界观宏大' },
  { value: 'zhuji', label: '辰东 - 热血战斗，情节紧凑' },
];

export const SettingsPanel = ({ sessionId }: SettingsPanelProps) => {
  const { session, isLoading } = useSession(sessionId);
  const toast = useToast();

  // 编辑状态
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // 表单状态
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState('novel');
  const [genre, setGenre] = useState('');
  const [style, setStyle] = useState('');
  const [authorStyle, setAuthorStyle] = useState('');
  const [requirements, setRequirements] = useState('');
  const [wordCount, setWordCount] = useState('10000');
  const [chapterWordCount, setChapterWordCount] = useState('2500');
  const [approvalMode, setApprovalMode] = useState(true);

  // 从会话数据加载设定
  useEffect(() => {
    if (session) {
      const goal = session.goal || {};
      const config = session.config || {};

      setTitle(session.title || '');
      setMode(session.mode || 'novel');
      setGenre(goal.genre || '');
      setStyle(goal.style || '');
      setAuthorStyle(goal.author_style || '');
      setRequirements(goal.requirements || '');
      setWordCount(String(goal.word_count || 10000));
      setChapterWordCount(String(goal.chapter_word_count || 2500));
      setApprovalMode(config.approval_mode !== false); // 默认开启
    }
  }, [session]);

  // 动态计算章节数
  const calculatedChapterCount = Math.ceil(parseInt(wordCount || '0') / parseInt(chapterWordCount || '2500'));

  // 重置到原始值
  const handleReset = () => {
    if (session) {
      const goal = session.goal || {};
      const config = session.config || {};

      setTitle(session.title || '');
      setMode(session.mode || 'novel');
      setGenre(goal.genre || '');
      setStyle(goal.style || '');
      setAuthorStyle(goal.author_style || '');
      setRequirements(goal.requirements || '');
      setWordCount(String(goal.word_count || 10000));
      setChapterWordCount(String(goal.chapter_word_count || 2500));
      setApprovalMode(config.approval_mode !== false);
    }
    setIsEditing(false);
  };

  // 保存设定
  const handleSave = async () => {
    if (!sessionId) return;

    setIsSaving(true);
    try {
      await apiClient.patch(`/sessions/${sessionId}`, {
        title,
        mode,
        goal: {
          genre,
          style,
          author_style: authorStyle,
          requirements,
          word_count: parseInt(wordCount),
          chapter_count: calculatedChapterCount,
          chapter_word_count: parseInt(chapterWordCount),
        },
        config: {
          approval_mode: approvalMode,
        },
      });

      toast.success('设定已保存！');
      setIsEditing(false);
    } catch (error: any) {
      logger.error('Failed to save settings:', error);
      toast.error(error.response?.data?.detail || '保存失败，请重试');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        加载中...
      </div>
    );
  }

  if (!session) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        未找到会话信息
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 头部 */}
      <div className="flex-shrink-0 px-6 py-4 border-b flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">项目设定</h2>
          <p className="text-sm text-gray-500 mt-1">
            查看和编辑您的创作设定，确保内容与预期一致
          </p>
        </div>
        {!isEditing ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsEditing(true)}
          >
            ✏️ 编辑设定
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleReset}
              disabled={isSaving}
            >
              取消
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSave}
              isLoading={isSaving}
            >
              保存
            </Button>
          </div>
        )}
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-2xl space-y-6">
          {/* 基本信息 */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <span>📋</span> 基本信息
            </h3>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                项目标题
              </label>
              {isEditing ? (
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="例如：我的科幻小说"
                />
              ) : (
                <div className="px-3 py-2 bg-white border rounded-lg text-gray-900">
                  {title || '未设置'}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                创作模式
              </label>
              {isEditing ? (
                <Select
                  options={modeOptions}
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                />
              ) : (
                <div className="px-3 py-2 bg-white border rounded-lg text-gray-900">
                  {modeOptions.find(o => o.value === mode)?.label || mode}
                </div>
              )}
            </div>
          </div>

          {/* 规模设定 */}
          <div className="bg-blue-50 rounded-lg p-4 space-y-4">
            <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <span>📏</span> 规模设定
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  目标字数
                </label>
                {isEditing ? (
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
                ) : (
                  <div className="px-3 py-2 bg-white border rounded-lg text-gray-900">
                    {parseInt(wordCount).toLocaleString()} 字
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  每章字数
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    value={chapterWordCount}
                    onChange={(e) => setChapterWordCount(e.target.value)}
                    min="500"
                    max="10000"
                    step="100"
                  />
                ) : (
                  <div className="px-3 py-2 bg-white border rounded-lg text-gray-900">
                    {parseInt(chapterWordCount).toLocaleString()} 字/章
                  </div>
                )}
              </div>
            </div>

            <div className="px-3 py-2 bg-blue-100 rounded-lg">
              <p className="text-sm text-blue-800">
                📖 预计章节数：<strong>{calculatedChapterCount}</strong> 章
              </p>
            </div>
          </div>

          {/* 风格设定 */}
          <div className="bg-green-50 rounded-lg p-4 space-y-4">
            <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <span>🎨</span> 风格设定
            </h3>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                类型/流派
              </label>
              {isEditing ? (
                <Input
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  placeholder="例如：科幻、奇幻、都市..."
                />
              ) : (
                <div className="px-3 py-2 bg-white border rounded-lg text-gray-900">
                  {genre || '未设置'}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                参考作者风格
              </label>
              {isEditing ? (
                <Select
                  options={authorStyleOptions}
                  value={authorStyle}
                  onChange={(e) => setAuthorStyle(e.target.value)}
                />
              ) : (
                <div className="px-3 py-2 bg-white border rounded-lg text-gray-900">
                  {authorStyleOptions.find(o => o.value === authorStyle)?.label || '不限制'}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                写作风格
              </label>
              {isEditing ? (
                <Input
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  placeholder="例如：悬疑、轻松、严肃..."
                />
              ) : (
                <div className="px-3 py-2 bg-white border rounded-lg text-gray-900">
                  {style || '未设置'}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                创作要求
              </label>
              {isEditing ? (
                <Textarea
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  placeholder="描述您的创作要求、故事背景、角色设定等..."
                  rows={4}
                />
              ) : (
                <div className="px-3 py-2 bg-white border rounded-lg text-gray-900 whitespace-pre-wrap">
                  {requirements || '未设置'}
                </div>
              )}
            </div>
          </div>

          {/* 执行配置 */}
          <div className="bg-orange-50 rounded-lg p-4 space-y-4">
            <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <span>⚙️</span> 执行配置
            </h3>

            <div>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={approvalMode}
                  onChange={(e) => setApprovalMode(e.target.checked)}
                  disabled={!isEditing}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
                <div>
                  <span className="text-sm font-medium text-gray-700">每步审核模式</span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    开启后，每个任务完成后会等待您的审核通过才继续下一步
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* 偏离检测 */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-yellow-800 flex items-center gap-2 mb-2">
              <span>⚠️</span> 设定偏离检测
            </h3>
            <p className="text-xs text-yellow-700">
              如果您发现生成的内容与您的设定有偏离，可以在这里查看和调整原始设定。
              系统会根据这些设定进行一致性检查，确保内容符合您的预期。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
