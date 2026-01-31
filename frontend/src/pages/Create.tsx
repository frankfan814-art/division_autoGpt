/**
 * Create page with smart prompt enhancement
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select } from '@/components/ui/Select';
import { useSessions } from '@/hooks/useSession';
import { useToast } from '@/components/ui/Toast';
import apiClient, { charactersApi } from '@/api/client';

const modeOptions = [
  { value: 'novel', label: '小说创作' },
  { value: 'story', label: '短篇故事' },
  { value: 'script', label: '剧本创作' },
];

// 🔥 二创类型选项
const derivativeTypeOptions = [
  { value: 'sequel', label: '续写', description: '在原作基础上继续故事发展' },
  { value: 'prequel', label: '前传', description: '讲述原作之前发生的故事' },
  { value: 'spinoff', label: '外传', description: '以配角为主角的衍生故事' },
  { value: 'adaptation', label: '改编', description: '改变原作背景或设定的重新创作' },
  { value: 'fanfic', label: '同人', description: '基于原作世界的粉丝创作' },
  { value: 'rewrite', label: '重写', description: '保留设定重新编写故事' },
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

export const Create = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { createSession, isCreating } = useSessions();
  // 🔥 获取所有会话，用于二创模式下选择原作
  const { sessions: allSessions } = useSessions({ status: 'completed' });  // 只获取已完成的

  const [useSmartCreate, setUseSmartCreate] = useState(false);
  const [userInput, setUserInput] = useState('我在大宋送外卖，送成了首富。历史穿越。爽文。历史穿越文。'); // 🔥 默认创作想法
  const [isEnhancing, setIsEnhancing] = useState(false);

  const [title, setTitle] = useState('');
  const [mode, setMode] = useState('novel');
  const [authorStyle, setAuthorStyle] = useState(''); // 作者风格
  const [chapterWordCount, setChapterWordCount] = useState('2500'); // 每章字数，默认2500
  const [wordCount, setWordCount] = useState('10000'); // 🔥 默认1万字
  const [approvalMode, setApprovalMode] = useState(true); // 默认开启审核模式
  const [genre, setGenre] = useState('');
  const [style, setStyle] = useState('');
  const [requirements, setRequirements] = useState('');

  // 🔥 二创模式相关状态
  const [isDerivativeMode, setIsDerivativeMode] = useState(false); // 是否开启二创模式
  const [derivativeType, setDerivativeType] = useState('sequel'); // 二创类型
  const [originalWork, setOriginalWork] = useState(''); // 原作名称
  const [keepOriginalCharacters, setKeepOriginalCharacters] = useState(true); // 保留原作人物
  const [keepOriginalWorldview, setKeepOriginalWorldview] = useState(true); // 保留原作世界观
  const [originalElements, setOriginalElements] = useState<string[]>([]); // 保留元素列表
  const [newElements, setNewElements] = useState<string[]>([]); // 新增元素列表
  const [tempElement, setTempElement] = useState(''); // 临时输入元素

  // 🔥 导入功能相关状态
  const [importMode, setImportMode] = useState(false); // 导入模式
  const [isParsing, setIsParsing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // 🔥 原作选择方式：select=从已完成小说选择, manual=手动输入
  const [originalWorkInputMode, setOriginalWorkInputMode] = useState<'select' | 'manual'>('select');
  const [isLoadingOriginalData, setIsLoadingOriginalData] = useState(false); // 正在加载原作数据

  // 动态计算章节数
  const calculatedChapterCount = Math.ceil(parseInt(wordCount) / parseInt(chapterWordCount || '2500'));

  const [errors, setErrors] = useState<Record<string, string>>({});

  // 🔥 解析导入的 .md 文件
  const parseImportFile = async (file: File): Promise<void> => {
    setIsParsing(true);
    try {
      const text = await file.text();

      // 提取项目标题
      const titleMatch = text.match(/#?\s*(.+?)\s+项目概览|项目名称[：:]\s*(.+)/i);
      if (titleMatch) {
        setTitle(titleMatch[1]?.trim() || titleMatch[2]?.trim() || file.name.replace('.md', ''));
      } else {
        setTitle(file.name.replace('.md', ''));
      }

      // 提取类型/流派
      const genreMatch = text.match(/类型[：:]\s*(.+)/i);
      if (genreMatch) {
        setGenre(genreMatch[1].trim());
      }

      // 提取写作风格
      const styleMatch = text.match(/写作风格[：:]\s*(.+)/i);
      if (styleMatch) {
        setStyle(styleMatch[1].trim());
      }

      // 提取目标字数和章节数
      const wordCountMatch = text.match(/目标字数[：:]\s*(\d+)/i);
      if (wordCountMatch) {
        const count = parseInt(wordCountMatch[1]);
        // 找最接近的预设值
        const options = [5000, 10000, 30000, 50000, 100000, 200000, 500000, 1000000];
        const closest = options.reduce((prev, curr) =>
          Math.abs(curr - count) < Math.abs(prev - count) ? curr : prev
        );
        setWordCount(String(closest));
      }

      const chapterCountMatch = text.match(/章节数[：:]\s*(\d+)/i);
      if (chapterCountMatch) {
        const chapters = parseInt(chapterCountMatch[1]);
        // 反推每章字数
        const newChapterWordCount = Math.max(500, Math.floor(100000 / chapters));
        setChapterWordCount(String(newChapterWordCount));
      }

      // 提取人物信息作为保留元素
      const characters: string[] = [];
      const charMatches = text.matchAll(/[-*]\s*\*\*([^*]+)\*\*[：:]\s*([^*]+)/gi);
      for (const match of charMatches) {
        characters.push(match[1].trim());
      }
      if (characters.length > 0) {
        setOriginalElements(characters.slice(0, 5)); // 最多取5个
        setKeepOriginalCharacters(true);
      }

      // 提取世界观/门派信息
      const worldview: string[] = [];
      const worldviewMatches = text.matchAll(/世界观[：:]\s*([^\n]+)/gi);
      for (const match of worldviewMatches) {
        worldview.push(match[1].trim());
      }
      if (worldview.length > 0) {
        setKeepOriginalWorldview(true);
      }

      // 提取创作要求
      const requirementsMatch = text.match(/创作要求[：:]\s*([^#]+)/i);
      if (requirementsMatch) {
        setRequirements(requirementsMatch[1].trim());
      }

      // 自动启用二创模式
      setIsDerivativeMode(true);
      setOriginalWork(file.name.replace('.md', ''));

      toast.success('文件解析成功！已自动填充表单并启用二创模式');
      setImportMode(false);
    } catch (error) {
      console.error('解析文件失败:', error);
      toast.error('文件解析失败，请检查文件格式');
    } finally {
      setIsParsing(false);
    }
  };

  // 🔥 处理文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.md')) {
        toast.warning('请选择 .md 格式的文件');
        return;
      }
      parseImportFile(file);
    }
  };

  // 🔥 自动填充原作数据：当用户从下拉框选择原作时，自动填充保留元素和基本信息
  useEffect(() => {
    const autoFillOriginalData = async () => {
      // 只有在下拉框模式且选择了原作时才自动填充
      if (originalWorkInputMode === 'select' && originalWork) {
        setIsLoadingOriginalData(true);
        try {
          // 获取原作会话的详细信息
          const session = allSessions.find((s: any) => s.id === originalWork);
          if (!session) {
            toast.warning('未找到原作信息');
            return;
          }

          // 1. 填充基本信息
          if (session.goal?.genre) {
            setGenre(session.goal.genre);
          }
          if (session.goal?.style) {
            setStyle(session.goal.style);
          }
          if (session.goal?.requirements) {
            setRequirements(session.goal.requirements);
          }
          if (session.goal?.author_style) {
            setAuthorStyle(session.goal.author_style);
          }

          // 2. 获取人物列表，自动填充到保留元素
          try {
            const charactersData = await charactersApi.list(originalWork);
            const characterElements: string[] = [];

            if (charactersData.characters && Array.isArray(charactersData.characters)) {
              charactersData.characters.forEach((char: any) => {
                // 添加角色名称
                if (char.name) {
                  characterElements.push(`角色: ${char.name}`);
                }
                // 如果有关键关系，也添加进去
                if (char.relationships && Object.keys(char.relationships).length > 0) {
                  const relationText = Object.entries(char.relationships)
                    .map(([target, relation]) => `${char.name}→${target}: ${relation}`)
                    .join('; ');
                  if (relationText) {
                    characterElements.push(`关系: ${relationText}`);
                  }
                }
              });
            }

            // 设置保留元素
            if (characterElements.length > 0) {
              setOriginalElements(characterElements);
            }
          } catch (charError) {
            console.warn('获取人物信息失败:', charError);
            // 人物获取失败不影响其他信息的使用
          }

          // 3. 获取任务结果，提取世界观和伏笔信息
          try {
            const tasksData = await apiClient.get(`/sessions/${originalWork}/tasks`);
            if (tasksData.data && Array.isArray(tasksData.data)) {
              const worldviewElements: string[] = [];
              const foreshadowElements: string[] = [];

              tasksData.data.forEach((task: any) => {
                // 提取世界观任务结果
                if (task.task_type === 'worldview' && task.result) {
                  try {
                    const result = typeof task.result === 'string' ? JSON.parse(task.result) : task.result;
                    if (result.worldview_rules) {
                      worldviewElements.push(`世界观规则: ${result.worldview_rules}`);
                    }
                    if (result.power_system) {
                      worldviewElements.push(`力量体系: ${result.power_system}`);
                    }
                    if (result.factions) {
                      worldviewElements.push(`势力设定: ${result.factions}`);
                    }
                  } catch (e) {
                    // 忽略解析错误
                  }
                }

                // 提取伏笔任务结果
                if (task.task_type === 'foreshadow' && task.result) {
                  try {
                    const result = typeof task.result === 'string' ? JSON.parse(task.result) : task.result;
                    if (result.foreshadows && Array.isArray(result.foreshadows)) {
                      result.foreshadows.forEach((fs: any) => {
                        if (fs.name) {
                          foreshadowElements.push(`伏笔: ${fs.name}`);
                        }
                      });
                    }
                  } catch (e) {
                    // 忽略解析错误
                  }
                }
              });

              // 将世界观和伏笔添加到保留元素
              const additionalElements = [...worldviewElements, ...foreshadowElements];
              if (additionalElements.length > 0) {
                setOriginalElements((prev) => [...prev, ...additionalElements]);
              }
            }
          } catch (taskError) {
            console.warn('获取任务信息失败:', taskError);
            // 任务获取失败不影响其他信息的使用
          }

          toast.success(`已自动填充原作《${session.title}》的设定信息`);
        } catch (error) {
          console.error('自动填充失败:', error);
          toast.error('自动填充原作信息失败，请手动填写');
        } finally {
          setIsLoadingOriginalData(false);
        }
      }
    };

    autoFillOriginalData();
  }, [originalWork, originalWorkInputMode, allSessions]);

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
      // 🔥 构建二创配置
      const derivativeConfig = isDerivativeMode ? {
        type: derivativeType,
        original_work: originalWork,
        keep_original_characters: keepOriginalCharacters,
        keep_original_worldview: keepOriginalWorldview,
        original_elements: originalElements,
        new_elements: newElements,
      } : undefined;

      const session = await createSession({
        title,
        mode,
        goal: {
          genre,
          style,
          requirements,
          author_style: authorStyle, // 作者风格
          chapter_count: calculatedChapterCount,
          chapter_word_count: parseInt(chapterWordCount),
          word_count: parseInt(wordCount),
        },
        config: {
          approval_mode: approvalMode,
          // 🔥 添加二创模式配置
          ...(isDerivativeMode && {
            is_derivative: true,
            derivative_config: derivativeConfig,
          }),
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
            {importMode
              ? '📂 选择之前导出的项目文件，快速创建二创项目'
              : useSmartCreate
              ? '💡 描述您的创作想法，AI将为您智能生成完整配置'
              : '填写项目信息，开始AI辅助创作之旅'
            }
          </p>

          <div className="mt-4 flex gap-2">
            <Button
              type="button"
              variant={importMode ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setImportMode(true)}
            >
              📂 导入项目
            </Button>
            <Button
              type="button"
              variant={useSmartCreate ? 'secondary' : 'primary'}
              size="sm"
              onClick={() => {
                setImportMode(false);
                setUseSmartCreate(false);
              }}
            >
              📝 手动填写
            </Button>
            <Button
              type="button"
              variant={useSmartCreate ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => {
                setImportMode(false);
                setUseSmartCreate(true);
              }}
            >
              ✨ 智能生成
            </Button>
          </div>
        </div>

        {/* 🔥 导入模式 */}
        {importMode && (
          <div className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
            <div className="text-center py-8">
              <div className="text-5xl mb-4">📂</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">导入项目文件</h3>
              <p className="text-gray-600 mb-6">
                选择之前导出的 .md 文件，系统将自动解析并填充项目信息
              </p>

              <input
                ref={fileInputRef}
                type="file"
                accept=".md"
                onChange={handleFileSelect}
                className="hidden"
              />

              <div className="flex justify-center gap-3">
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  isLoading={isParsing}
                >
                  选择文件
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setImportMode(false)}
                >
                  取消
                </Button>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg text-sm text-blue-800">
                <p className="font-medium mb-2">💡 支持的信息提取：</p>
                <ul className="text-left space-y-1 ml-4">
                  <li>• 项目标题和类型</li>
                  <li>• 写作风格和创作要求</li>
                  <li>• 目标字数和章节数</li>
                  <li>• 人物和世界观信息</li>
                </ul>
              </div>
            </div>
          </div>
        )}

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

          {/* 🔥 二创模式开关 */}
          <div className="border-t pt-6">
            <label className="flex items-center gap-3 cursor-pointer mb-4">
              <input
                type="checkbox"
                checked={isDerivativeMode}
                onChange={(e) => setIsDerivativeMode(e.target.checked)}
                className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-2 focus:ring-purple-500"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">🎨 二创模式</span>
                <p className="text-xs text-gray-500 mt-0.5">
                  基于现有作品进行二次创作，将自动跳过创意脑暴阶段
                </p>
              </div>
            </label>

            {/* 二创配置选项 */}
            {isDerivativeMode && (
              <div className="mt-4 pl-6 space-y-4 border-l-2 border-purple-200">
                {/* 原作选择 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    选择原作 <span className="text-red-500">*</span>
                  </label>

                  {/* 选择方式切换 */}
                  <div className="flex gap-2 mb-2">
                    <button
                      type="button"
                      onClick={() => setOriginalWorkInputMode('select')}
                      className={`px-3 py-1 text-sm rounded-lg border transition-colors ${
                        originalWorkInputMode === 'select'
                          ? 'border-purple-500 bg-purple-50 text-purple-700'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      📚 从已完成作品选择
                    </button>
                    <button
                      type="button"
                      onClick={() => setOriginalWorkInputMode('manual')}
                      className={`px-3 py-1 text-sm rounded-lg border transition-colors ${
                        originalWorkInputMode === 'manual'
                          ? 'border-purple-500 bg-purple-50 text-purple-700'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      ✏️ 手动输入原作名称
                    </button>
                  </div>

                  {/* 下拉框：从已完成作品选择 */}
                  {originalWorkInputMode === 'select' && (
                    <div>
                      {allSessions.length === 0 ? (
                        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 text-center">
                          <p className="text-sm text-gray-500 mb-2">暂无已完成的小说</p>
                          <p className="text-xs text-gray-400">请先完成一部小说，或选择"手动输入"方式</p>
                        </div>
                      ) : (
                        <select
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 disabled:bg-gray-100 disabled:cursor-wait"
                          value={originalWork}
                          onChange={(e) => setOriginalWork(e.target.value)}
                          required={isDerivativeMode}
                          disabled={isLoadingOriginalData}
                        >
                          <option value="">请选择原作...</option>
                          {allSessions.map((session: any) => {
                            const wordCountText = session.goal?.word_count
                              ? (session.goal.word_count >= 10000
                                  ? `${session.goal.word_count / 10000}万字`
                                  : `${session.goal.word_count}字`)
                              : '';
                            return (
                              <option key={session.id} value={session.id}>
                                {session.title}
                                {session.goal?.genre && ` (${session.goal.genre})`}
                                {wordCountText && ` - ${wordCountText}`}
                              </option>
                            );
                          })}
                        </select>
                      )}
                      {isLoadingOriginalData && (
                        <div className="mt-2 flex items-center gap-2 text-sm text-purple-600">
                          <div className="animate-spin w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full"></div>
                          <span>正在加载原作设定...</span>
                        </div>
                      )}
                      <p className="mt-1 text-xs text-gray-500">
                        💡 选择已完成的作品作为原作，系统会自动提取其设定
                      </p>
                    </div>
                  )}

                  {/* 手动输入：原作名称 */}
                  {originalWorkInputMode === 'manual' && (
                    <div>
                      <Input
                        type="text"
                        value={originalWork}
                        onChange={(e) => setOriginalWork(e.target.value)}
                        placeholder="例如：我在都市修仙，太精彩了"
                        required={isDerivativeMode}
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        💡 手动输入原作名称，适合基于外部作品创作
                      </p>
                    </div>
                  )}
                </div>

                {/* 二创类型 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    二创类型
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {derivativeTypeOptions.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setDerivativeType(option.value)}
                        className={`p-3 text-sm rounded-lg border-2 text-left transition-colors ${
                          derivativeType === option.value
                            ? 'border-purple-500 bg-purple-50 text-purple-700'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="font-medium">{option.label}</div>
                        <div className="text-xs text-gray-500 mt-0.5">{option.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 保留选项 */}
                <div className="flex gap-6">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={keepOriginalCharacters}
                      onChange={(e) => setKeepOriginalCharacters(e.target.checked)}
                      className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-2 focus:ring-purple-500"
                    />
                    <span className="text-sm text-gray-700">保留原作人物</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={keepOriginalWorldview}
                      onChange={(e) => setKeepOriginalWorldview(e.target.checked)}
                      className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-2 focus:ring-purple-500"
                    />
                    <span className="text-sm text-gray-700">保留原作世界观</span>
                  </label>
                </div>

                {/* 保留元素 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    保留原作元素
                    {originalWorkInputMode === 'select' && originalElements.length > 0 && (
                      <span className="ml-2 text-xs text-green-600 font-normal">
                        ✓ 已从原作自动提取
                      </span>
                    )}
                  </label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      value={tempElement}
                      onChange={(e) => setTempElement(e.target.value)}
                      placeholder="输入要保留的元素（如：某个角色、设定、情节）"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          if (tempElement.trim()) {
                            setOriginalElements([...originalElements, tempElement.trim()]);
                            setTempElement('');
                          }
                        }
                      }}
                    />
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => {
                        if (tempElement.trim()) {
                          setOriginalElements([...originalElements, tempElement.trim()]);
                          setTempElement('');
                        }
                      }}
                    >
                      添加
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {originalElements.map((element, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm"
                      >
                        {element}
                        <button
                          type="button"
                          onClick={() => setOriginalElements(originalElements.filter((_, i) => i !== index))}
                          className="ml-1 text-purple-400 hover:text-purple-900"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* 新增元素 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    新增元素
                  </label>
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      value={tempElement}
                      onChange={(e) => setTempElement(e.target.value)}
                      placeholder="输入要新增的元素"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          if (tempElement.trim()) {
                            setNewElements([...newElements, tempElement.trim()]);
                            setTempElement('');
                          }
                        }
                      }}
                    />
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => {
                        if (tempElement.trim()) {
                          setNewElements([...newElements, tempElement.trim()]);
                          setTempElement('');
                        }
                      }}
                    >
                      添加
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {newElements.map((element, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm"
                      >
                        {element}
                        <button
                          type="button"
                          onClick={() => setNewElements(newElements.filter((_, i) => i !== index))}
                          className="ml-1 text-green-400 hover:text-green-900"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Genre */}
          <Input
            label="类型/流派"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            placeholder="例如：科幻、奇幻、都市..."
          />

          {/* Author Style */}
          <Select
            label="参考作者风格（可选）"
            options={authorStyleOptions}
            value={authorStyle}
            onChange={(e) => setAuthorStyle(e.target.value)}
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
