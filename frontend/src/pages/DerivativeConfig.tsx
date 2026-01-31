/**
 * DerivativeConfig page - 二创配置界面
 * 用于配置基于原作品的衍生创作（续写、改编、同人等）
 */

import { Link, useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import {
  useDerivativeCRUD,
  DerivativeConfig,
  DerivativeType,
  ToneStyle,
} from '@/hooks/useDerivative';

const derivativeTypes: { value: DerivativeType; label: string; description: string }[] = [
  { value: 'sequel', label: '续写', description: '在原作基础上继续故事发展' },
  { value: 'prequel', label: '前传', description: '讲述原作之前发生的故事' },
  { value: 'spinoff', label: '外传', description: '以配角为主角的衍生故事' },
  { value: 'adaptation', label: '改编', description: '改变原作背景或设定的重新创作' },
  { value: 'fanfic', label: '同人', description: '基于原作世界的粉丝创作' },
  { value: 'rewrite', label: '重写', description: '保留设定重新编写故事' },
];

const toneStyles: { value: ToneStyle; label: string }[] = [
  { value: 'serious', label: '严肃正剧' },
  { value: 'lighthearted', label: '轻松日常' },
  { value: 'dark', label: '黑暗向' },
  { value: 'comedy', label: '喜剧搞笑' },
  { value: 'romance', label: '爱情浪漫' },
  { value: 'epic', label: '史诗宏大' },
];

// 默认配置
const defaultConfig: DerivativeConfig = {
  type: 'sequel',
  title: '',
  target_chapter_count: 50,
  target_word_count: 150000,
  tone: 'serious',
  writing_style: '',
  original_elements: [],
  new_elements: [],
  keep_original_characters: true,
  new_character_count: 3,
  keep_original_worldview: true,
  world_changes: '',
  plot_direction: '',
  main_conflict: '',
  notes: '',
};

export const DerivativeConfigPage = () => {
  const { sessionId } = useParams<{ sessionId: string }>();

  const [config, setConfig] = useState<DerivativeConfig>(defaultConfig);
  const [tempElement, setTempElement] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  const {
    config: savedConfig,
    isLoading,
    hasConfig,
    refetch,
    createConfig,
    updateConfig,
    isCreating,
    isUpdating,
  } = useDerivativeCRUD(sessionId || '');

  // 加载已保存的配置
  useEffect(() => {
    if (savedConfig) {
      setConfig(savedConfig as DerivativeConfig);
    }
  }, [savedConfig]);

  // 检测配置变化
  useEffect(() => {
    if (savedConfig) {
      setHasChanges(JSON.stringify(config) !== JSON.stringify(savedConfig));
    } else {
      setHasChanges(JSON.stringify(config) !== JSON.stringify(defaultConfig));
    }
  }, [config, savedConfig]);

  const handleTypeSelect = (type: DerivativeType) => {
    setConfig({ ...config, type });
  };

  const handleToneSelect = (tone: ToneStyle) => {
    setConfig({ ...config, tone });
  };

  const addOriginalElement = () => {
    if (tempElement.trim()) {
      setConfig({
        ...config,
        original_elements: [...config.original_elements, tempElement.trim()],
      });
      setTempElement('');
    }
  };

  const removeOriginalElement = (index: number) => {
    setConfig({
      ...config,
      original_elements: config.original_elements.filter((_, i) => i !== index),
    });
  };

  const addNewElement = () => {
    if (tempElement.trim()) {
      setConfig({
        ...config,
        new_elements: [...config.new_elements, tempElement.trim()],
      });
      setTempElement('');
    }
  };

  const removeNewElement = (index: number) => {
    setConfig({
      ...config,
      new_elements: config.new_elements.filter((_, i) => i !== index),
    });
  };

  const handleSubmit = async () => {
    try {
      if (hasConfig) {
        await updateConfig(config);
        alert('二创配置已更新！');
      } else {
        await createConfig(config);
        alert('二创配置已保存！');
      }
      setHasChanges(false);
      refetch();
    } catch (error) {
      console.error('保存二创配置失败:', error);
      alert('保存失败，请重试');
    }
  };

  const handleReset = () => {
    if (savedConfig) {
      setConfig(savedConfig as DerivativeConfig);
    } else {
      setConfig(defaultConfig);
    }
    setHasChanges(false);
  };

  return (
    <MainLayout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">二创配置</h1>
            <p className="mt-2 text-gray-600">配置基于原作品的衍生创作参数</p>
          </div>
          <div className="flex gap-3">
            <Link to={`/dashboard/${sessionId}`}>
              <Button variant="secondary">返回概览</Button>
            </Link>
            {hasChanges && (
              <Button variant="secondary" onClick={handleReset}>
                重置更改
              </Button>
            )}
            <Button onClick={handleSubmit} disabled={!hasChanges || isCreating || isUpdating}>
              {isCreating || isUpdating ? '保存中...' : hasConfig ? '更新配置' : '保存配置'}
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-pulse text-gray-500">加载中...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 左侧：主要配置 */}
            <div className="lg:col-span-2 space-y-6">
              {/* 二创类型 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">二创类型</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {derivativeTypes.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => handleTypeSelect(type.value)}
                      className={`p-4 rounded-lg border-2 text-left transition-colors ${
                        config.type === type.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="font-medium text-gray-900 mb-1">{type.label}</div>
                      <div className="text-xs text-gray-500">{type.description}</div>
                    </button>
                  ))}
                </div>
              </Card>

              {/* 基础信息 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">基础信息</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      作品标题
                    </label>
                    <Input
                      type="text"
                      value={config.title}
                      onChange={(e) => setConfig({ ...config, title: e.target.value })}
                      placeholder="例如：XX续篇、XX前传..."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        目标章节数
                      </label>
                      <Input
                        type="number"
                        value={config.target_chapter_count}
                        onChange={(e) => setConfig({ ...config, target_chapter_count: parseInt(e.target.value) || 0 })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        目标字数（万）
                      </label>
                      <Input
                        type="number"
                        value={config.target_word_count / 10000}
                        onChange={(e) => setConfig({ ...config, target_word_count: (parseInt(e.target.value) || 0) * 10000 })}
                      />
                    </div>
                  </div>
                </div>
              </Card>

              {/* 风格设定 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">风格设定</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      作品基调
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {toneStyles.map((tone) => (
                        <button
                          key={tone.value}
                          type="button"
                          onClick={() => handleToneSelect(tone.value)}
                          className={`px-4 py-2 rounded-lg border transition-colors ${
                            config.tone === tone.value
                              ? 'border-blue-500 bg-blue-50 text-blue-700'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          {tone.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      写作风格描述
                    </label>
                    <Textarea
                      value={config.writing_style}
                      onChange={(e) => setConfig({ ...config, writing_style: e.target.value })}
                      placeholder="描述你想要的写作风格，例如：更注重心理描写、增加悬疑元素、采用多线叙事..."
                      rows={3}
                    />
                  </div>
                </div>
              </Card>

              {/* 内容配置 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">内容配置</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      保留的原作元素
                    </label>
                    <div className="flex gap-2 mb-2">
                      <Input
                        type="text"
                        value={tempElement}
                        onChange={(e) => setTempElement(e.target.value)}
                        placeholder="输入要保留的元素（如：某个角色、设定、情节）"
                        onKeyPress={(e) => e.key === 'Enter' && addOriginalElement()}
                      />
                      <Button type="button" onClick={addOriginalElement}>
                        添加
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {config.original_elements.map((element, index) => (
                        <Badge key={index} variant="primary" className="flex items-center gap-1">
                          {element}
                          <button
                            type="button"
                            onClick={() => removeOriginalElement(index)}
                            className="ml-1 text-blue-200 hover:text-white"
                          >
                            ×
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      新增元素
                    </label>
                    <div className="flex gap-2 mb-2">
                      <Input
                        type="text"
                        value={tempElement}
                        onChange={(e) => setTempElement(e.target.value)}
                        placeholder="输入要新增的元素"
                        onKeyPress={(e) => e.key === 'Enter' && addNewElement()}
                      />
                      <Button type="button" onClick={addNewElement}>
                        添加
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {config.new_elements.map((element, index) => (
                        <Badge key={index} variant="success" className="flex items-center gap-1">
                          {element}
                          <button
                            type="button"
                            onClick={() => removeNewElement(index)}
                            className="ml-1 text-green-200 hover:text-white"
                          >
                            ×
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </Card>

              {/* 人物和世界观 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">人物和世界观</h2>
                <div className="space-y-4">
                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={config.keep_original_characters}
                        onChange={(e) => setConfig({ ...config, keep_original_characters: e.target.checked })}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">保留原作主要人物</span>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      计划新增人物数量
                    </label>
                    <Input
                      type="number"
                      value={config.new_character_count}
                      onChange={(e) => setConfig({ ...config, new_character_count: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={config.keep_original_worldview}
                        onChange={(e) => setConfig({ ...config, keep_original_worldview: e.target.checked })}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">保留原作世界观</span>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      世界观变更说明
                    </label>
                    <Textarea
                      value={config.world_changes}
                      onChange={(e) => setConfig({ ...config, world_changes: e.target.value })}
                      placeholder="描述世界观上的变化，例如：时代背景改变、地理范围扩展..."
                      rows={2}
                    />
                  </div>
                </div>
              </Card>

              {/* 剧情设定 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">剧情设定</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      故事发展方向
                    </label>
                    <Textarea
                      value={config.plot_direction}
                      onChange={(e) => setConfig({ ...config, plot_direction: e.target.value })}
                      placeholder="描述故事的主要发展方向和情节走向..."
                      rows={3}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      主要冲突
                    </label>
                    <Textarea
                      value={config.main_conflict}
                      onChange={(e) => setConfig({ ...config, main_conflict: e.target.value })}
                      placeholder="描述故事的核心冲突和矛盾..."
                      rows={2}
                    />
                  </div>
                </div>
              </Card>

              {/* 备注 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">备注</h2>
                <Textarea
                  value={config.notes}
                  onChange={(e) => setConfig({ ...config, notes: e.target.value })}
                  placeholder="其他补充说明、注意事项等..."
                  rows={3}
                />
              </Card>
            </div>

            {/* 右侧：配置预览和提示 */}
            <div className="space-y-6">
              {/* 配置预览 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">配置预览</h2>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">类型</span>
                    <span className="font-medium">{derivativeTypes.find(t => t.value === config.type)?.label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">基调</span>
                    <span className="font-medium">{toneStyles.find(t => t.value === config.tone)?.label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">章节</span>
                    <span className="font-medium">{config.target_chapter_count} 章</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">字数</span>
                    <span className="font-medium">{(config.target_word_count / 10000).toFixed(0)} 万字</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">保留原人物</span>
                    <span className="font-medium">{config.keep_original_characters ? '是' : '否'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">新增人物</span>
                    <span className="font-medium">{config.new_character_count} 个</span>
                  </div>
                </div>
              </Card>

              {/* 提示信息 */}
              <Card className="p-6 bg-blue-50 border-blue-200">
                <h2 className="text-lg font-bold text-blue-900 mb-3">💡 提示</h2>
                <ul className="space-y-2 text-sm text-blue-800">
                  <li>• 二创将基于原作的人物和世界观进行</li>
                  <li>• 建议保留原作核心设定以保证连贯性</li>
                  <li>• 新增元素应与原作风格协调</li>
                  <li>• 配置完成后可随时修改</li>
                </ul>
              </Card>

              {/* 配置检查 */}
              <Card className="p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-3">配置检查</h2>
                <div className="space-y-2 text-sm">
                  <div className={`flex items-center gap-2 ${config.title ? 'text-green-600' : 'text-gray-400'}`}>
                    <span>{config.title ? '✓' : '○'}</span>
                    <span>作品标题</span>
                  </div>
                  <div className={`flex items-center gap-2 ${config.plot_direction ? 'text-green-600' : 'text-gray-400'}`}>
                    <span>{config.plot_direction ? '✓' : '○'}</span>
                    <span>剧情方向</span>
                  </div>
                  <div className={`flex items-center gap-2 ${config.main_conflict ? 'text-green-600' : 'text-gray-400'}`}>
                    <span>{config.main_conflict ? '✓' : '○'}</span>
                    <span>核心冲突</span>
                  </div>
                  <div className={`flex items-center gap-2 ${config.original_elements.length > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                    <span>{config.original_elements.length > 0 ? '✓' : '○'}</span>
                    <span>保留元素 ({config.original_elements.length})</span>
                  </div>
                </div>
              </Card>

              {/* 状态提示 */}
              {hasConfig && !hasChanges && (
                <Card className="p-4 bg-green-50 border-green-200">
                  <div className="flex items-center gap-2 text-green-800">
                    <span className="text-lg">✓</span>
                    <span className="text-sm font-medium">配置已保存</span>
                  </div>
                </Card>
              )}

              {hasChanges && (
                <Card className="p-4 bg-yellow-50 border-yellow-200">
                  <div className="flex items-center gap-2 text-yellow-800">
                    <span className="text-lg">⚠️</span>
                    <span className="text-sm font-medium">有未保存的更改</span>
                  </div>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
};
