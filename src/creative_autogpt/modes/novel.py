"""
Novel Mode - Writing mode for novels and long-form fiction

Implements the standard novel creation pipeline with:
- Style definition
- Theme confirmation
- Outline generation
- Character design
- World-building
- Chapter generation
- Quality evaluation
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from creative_autogpt.modes.base import Mode, WritingMode, register_mode
from creative_autogpt.core.task_planner import TaskDefinition, NovelTaskType
from creative_autogpt.core.vector_memory import MemoryContext


@register_mode
class NovelMode(Mode):
    """
    Writing mode for novels

    Supports:
    - Various genres (xuanhuan, wuxia, urban, scifi, etc.)
    - Long-form structure (up to millions of characters)
    - Complex character relationships
    - Multi-arc storylines
    """

    mode_type = WritingMode.NOVEL
    name = "Novel Mode"
    description = "Writing mode for novels and long-form fiction"

    # Genre-specific configurations
    GENRE_CONFIGS = {
        "玄幻": {
            "style": "宏大世界观，修炼升级体系",
            "themes": ["成长", "复仇", "守护", "探索"],
            "elements": ["灵力", "功法", "法宝", "宗门", "秘境"],
        },
        "武侠": {
            "style": "江湖恩怨，侠义精神",
            "themes": ["义气", "情仇", "门派", "传承"],
            "elements": ["武功", "内力", "兵器", "秘籍", "门派"],
        },
        "都市": {
            "style": "现代都市背景，贴近现实",
            "themes": ["奋斗", "情感", "商战", "悬疑"],
            "elements": ["职场", "家庭", "友情", "爱情"],
        },
        "科幻": {
            "style": "未来科技，宇宙探索",
            "themes": ["科技", "人性", "文明", "探索"],
            "elements": ["AI", "太空", "基因", "能源"],
        },
        "悬疑": {
            "style": "层层悬念，逻辑推理",
            "themes": ["解谜", "真相", "人性", "犯罪"],
            "elements": ["线索", "推理", "反转", "伏笔"],
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.genre = config.get("genre", "玄幻") if config else "玄幻"
        self.genre_config = self.GENRE_CONFIGS.get(self.genre, {})

    async def build_prompt(
        self,
        task_type: str,
        context: MemoryContext,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for a novel task type"""
        metadata = metadata or {}

        # Get task-specific prompt
        if task_type == NovelTaskType.STYLE_ELEMENTS.value:
            return self._build_style_prompt(metadata)

        elif task_type == NovelTaskType.THEME_CONFIRMATION.value:
            return self._build_theme_prompt(context, metadata)

        elif task_type == NovelTaskType.MARKET_POSITIONING.value:
            return self._build_market_prompt(context, metadata)

        elif task_type == NovelTaskType.OUTLINE.value:
            return self._build_outline_prompt(context, metadata)

        elif task_type == NovelTaskType.CHARACTER_DESIGN.value:
            return self._build_character_prompt(context, metadata)

        elif task_type == NovelTaskType.WORLDVIEW_RULES.value:
            return self._build_worldview_prompt(context, metadata)

        elif task_type == NovelTaskType.EVENTS.value:
            return self._build_events_prompt(context, metadata)

        elif task_type == NovelTaskType.SCENES_ITEMS_CONFLICTS.value:
            return self._build_scenes_prompt(context, metadata)

        elif task_type == NovelTaskType.FORESHADOW_LIST.value:
            return self._build_foreshadow_prompt(context, metadata)

        elif task_type == NovelTaskType.CONSISTENCY_CHECK.value:
            return self._build_consistency_prompt(context, metadata)

        elif task_type == NovelTaskType.CHAPTER_OUTLINE.value:
            return self._build_chapter_outline_prompt(context, metadata)

        elif task_type == NovelTaskType.SCENE_GENERATION.value:
            return self._build_scene_generation_prompt(context, metadata)

        elif task_type == NovelTaskType.CHAPTER_CONTENT.value:
            return self._build_chapter_content_prompt(context, metadata)

        elif task_type == NovelTaskType.CHAPTER_POLISH.value:
            return self._build_chapter_polish_prompt(context, metadata)

        elif task_type == NovelTaskType.EVALUATION.value:
            return self._build_evaluation_prompt(context, metadata)

        elif task_type == NovelTaskType.REVISION.value:
            return self._build_revision_prompt(context, metadata)

        else:
            return self._build_generic_prompt(task_type, context, metadata)

    def _build_style_prompt(self, metadata: Dict[str, Any]) -> str:
        """Build prompt for style elements definition"""
        genre = metadata.get("goal_style") or metadata.get("genre", self.genre)
        genre_config = self.GENRE_CONFIGS.get(genre, {})

        prompt = f"""## 任务: 定义小说风格元素

请为一部{genre}小说定义详细的风格元素。

### 类型特征
"""

        if genre_config.get("style"):
            prompt += f"风格特点: {genre_config['style']}\n"

        if genre_config.get("themes"):
            prompt += f"常见主题: {', '.join(genre_config['themes'])}\n"

        if genre_config.get("elements"):
            prompt += f"核心元素: {', '.join(genre_config['elements'])}\n"

        prompt += """
### 输出要求

请以JSON格式输出风格元素配置:

```json
{
  "narrative_style": "叙述风格描述",
  "language_style": "语言风格描述",
  "pacing": "节奏控制",
  "tone": "基调氛围",
  "key_elements": ["元素1", "元素2", ...],
  "avoid_elements": ["避免的元素1", "避免的元素2", ...],
  "target_audience": "目标读者",
  "similar_works": ["类似作品1", "类似作品2", ...]
}
```

请直接输出JSON，不需要其他内容。
"""
        return prompt

    def _build_theme_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for theme confirmation"""
        goal_theme = metadata.get("goal_theme", "成长与冒险")

        prompt = f"""## 任务: 确认小说主题

### 目标主题
{goal_theme}

### 已确认的风格
"""

        # Add recent style information if available
        for result in context.recent_results:
            if result["task_type"] == "风格元素":
                prompt += f"\n{result['content'][:500]}...\n"
                break

        prompt += f"""

### 输出要求

请确认并细化小说的核心主题，包括:

1. **核心主题**: 一句话概括小说的核心思想
2. **主题层次**: 主要主题、次要主题
3. **价值取向**: 小说的价值观导向
4. **情感基调": 主要的情感色彩
5. **现实意义**: 小说的现实寓意

请以清晰的结构输出主题确认结果。
"""
        return prompt

    def _build_market_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for market positioning"""
        prompt = """## 任务: 市场定位分析

### 已确认信息
"""

        # Add theme information
        for result in context.recent_results:
            if result["task_type"] == "主题确认":
                prompt += f"\n主题:\n{result['content'][:500]}...\n"
                break

        prompt += """

### 输出要求

请分析小说的市场定位:

1. **目标读者**: 年龄、性别、阅读偏好
2. **平台定位**: 适合的平台（起点、晋江、番茄等）
3. **同类竞品**: 3-5部同类作品分析
4. **差异化**: 本作品的独特卖点
5. **更新策略**: 建议的更新节奏和字数
6. **变现潜力**: 付费、IP改编等潜力分析

请以结构化格式输出分析结果。
"""
        return prompt

    def _build_outline_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for story outline generation"""
        goal_length = metadata.get("goal_length", "100万字")

        prompt = f"""## 任务: 创建小说大纲

### 目标规模
{goal_length}

### 前置信息
"""

        # Add relevant context
        for result in context.recent_results[:3]:
            prompt += f"\n#### {result['task_type']}\n{result['content'][:300]}...\n"

        prompt += """

### 输出要求

请创建完整的故事大纲，包括:

1. **故事简介**: 200-300字简介
2. **主线剧情**: 开端、发展、高潮、结局
3. **分卷规划**: 建议的分卷（每卷20-50万字）
4. **核心冲突**: 主要矛盾和冲突点
5. **关键转折**: 故事的关键转折点
6. **结局方向**: 预期的结局走向

请以清晰的层级结构输出大纲。
"""
        return prompt

    def _build_character_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for character design"""
        prompt = """## 任务: 设计人物角色

### 故事大纲
"""

        # Add outline information
        for result in context.recent_results:
            if result["task_type"] == "大纲":
                prompt += f"\n{result['content'][:800]}...\n"
                break

        prompt += """

### 输出要求

请设计主要人物角色，包括:

**主角:**
- 姓名、年龄、外貌
- 性格特点
- 背景设定
- 核心动机
- 能力/特长
- 性格缺陷
- 成长弧线

**重要配角:**
- 3-5个重要配角
- 每个角色的角色定位
- 与主角的关系

**人物关系图:**
- 主要人物之间的关系网络

请以结构化格式输出人物设计。
"""
        return prompt

    def _build_worldview_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for worldview building"""
        genre = metadata.get("genre", self.genre)

        prompt = f"""## 任务: 构建世界观设定

### 类型
{genre}

### 故事大纲
"""

        # Add outline information
        for result in context.recent_results:
            if result["task_type"] == "大纲":
                prompt += f"\n{result['content'][:800]}...\n"
                break

        prompt += """

### 输出要求

请构建完整的世界观设定:

**基础设定:**
- 世界类型（现实/架空/未来等）
- 时代背景
- 地理环境

**力量体系:** (如适用)
- 能量类型
- 等级划分
- 修炼/成长方式
- 限制和代价

**社会结构:**
- 政治体系
- 经济体系
- 文化特色
- 势力划分

**特殊设定:**
- 独特的规则或现象
- 重要地点
- 关键物品

请以结构化格式输出世界观设定。
"""
        return prompt

    def _build_events_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for event design"""
        prompt = """## 任务: 设计情节事件

### 故事大纲
"""

        # Add outline information
        for result in context.recent_results:
            if result["task_type"] == "大纲":
                prompt += f"\n{result['content'][:800]}...\n"
                break

        prompt += """

### 输出要求

请设计主要情节事件链:

**主线事件:**
- 按时间顺序列出10-20个关键事件
- 每个事件包括: 触发条件、主要内容、结果影响、伏笔关联

**支线事件:**
- 3-5条支线
- 每条支线的起承转合

**冲突设计:**
- 主要冲突点
- 冲突升级路径
- 冲突解决方式

请以清晰的时间线格式输出事件设计。
"""
        return prompt

    def _build_scenes_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for scene and item design"""
        prompt = """## 任务: 设计场景、物品和冲突

### 相关信息
"""

        # Add relevant context
        for result in context.recent_results[:3]:
            prompt += f"\n#### {result['task_type']}\n{result['content'][:400]}...\n"

        prompt += """

### 输出要求

**重要场景:**
- 5-10个关键场景
- 每个场景的环境描述
- 氛围营造要点
- 与剧情的关联

**重要物品:**
- 5-10个关键物品
- 每个物品的描述
- 功能和象征意义
- 获取/使用方式

**冲突场景:**
- 主要对峙场景
- 冲突的表现形式
- 场景的转折点

请以结构化格式输出设计结果。
"""
        return prompt

    def _build_foreshadow_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for foreshadow planning"""
        prompt = """## 任务: 规划伏笔元素

### 故事大纲和事件
"""

        # Add relevant context
        for result in context.recent_results:
            if result["task_type"] in ["大纲", "事件"]:
                prompt += f"\n#### {result['task_type']}\n{result['content'][:400]}...\n"

        prompt += """

### 输出要求

请规划故事的伏笔系统:

**主线伏笔:**
- 5-10个主线伏笔
- 每个伏笔的: 埋设位置、暗示内容、回收时机、影响范围

**支线伏笔:**
- 3-5个支线伏笔
- 埋设和回收计划

**细节伏笔:**
- 可以埋藏伏笔的细节类型
- 隐藏技巧

请以表格形式列出伏笔规划，包含章节位置信息。
"""
        return prompt

    def _build_consistency_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for consistency check"""
        prompt = """## 任务: 一致性检查

### 所有设定
"""

        # Add all relevant context
        for result in context.recent_results:
            prompt += f"\n#### {result['task_type']}\n{result['content'][:300]}...\n"

        prompt += """

### 输出要求

请检查所有设定的一致性:

**检查项:**
1. 人物设定是否自洽
2. 世界观规则是否统一
3. 事件逻辑是否合理
4. 时间线是否连贯
5. 力量体系是否平衡
6. 伏笔是否可落实

**输出格式:**
- 发现的问题列表
- 问题的严重程度
- 修改建议
- 需要调整的设定

请以清晰的结构输出检查结果。
"""
        return prompt

    def _build_chapter_outline_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for chapter outline"""
        chapter_index = metadata.get("chapter_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章大纲

### 全局设定
"""

        # Add global context
        for result in context.recent_results[:3]:
            prompt += f"{result['task_type']}: {result['content'][:200]}...\n"

        prompt += f"""

### 输出要求

请为第{chapter_index}章创建详细大纲:

1. **章节标题**: 吸引人的标题
2. **主要内容**: 本章要讲述的内容
3. **场景划分**: 3-5个场景
4. **出场人物**: 本章出场的人物
5. **情节推进**: 推进的主线/支线
6. **冲突发展**: 本章的冲突
7. **伏笔埋设/回收**: 本章涉及的伏笔
8. **结尾悬念**: 章末的悬念点

请以结构化格式输出章节大纲。
"""
        return prompt

    def _build_scene_generation_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for scene generation"""
        chapter_index = metadata.get("chapter_index", 1)
        scene_index = metadata.get("scene_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章场景{scene_index}生成

### 章节大纲
"""

        # Add chapter outline
        for result in context.recent_results:
            if result.get("chapter_index") == chapter_index:
                prompt += f"\n{result['content'][:500]}...\n"
                break

        prompt += """

### 输出要求

请生成详细的场景内容:

1. **场景描述**: 环境、氛围
2. **人物动作**: 人物的行为和互动
3. **对话**: 人物对话
4. **心理描写**: 人物内心活动
5. **感官细节**: 视觉、听觉等细节
6. **节奏控制**: 快慢节奏的把握

请直接输出场景内容，1500-2500字。
"""
        return prompt

    def _build_chapter_content_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for chapter content generation"""
        chapter_index = metadata.get("chapter_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章内容生成

### 相关信息
"""

        # Add relevant context
        chapter_scenes = []
        for result in context.recent_results:
            if result.get("chapter_index") == chapter_index:
                chapter_scenes.append(result)

        for scene in chapter_scenes:
            prompt += f"\n{scene.get('task_type', '场景')}\n{scene['content'][:400]}...\n"

        prompt += f"""

### 输出要求

请将各场景整合成完整的章节内容:

1. **结构完整**: 开头、发展、结尾
2. **过渡自然**: 场景之间的过渡
3. **节奏协调**: 快慢节奏把握
4. **字数控制**: 3000-5000字
5. **悬念设置**: 章末留悬念

请直接输出章节内容，不需要章节标题。
"""
        return prompt

    def _build_chapter_polish_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for chapter polish"""
        chapter_index = metadata.get("chapter_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章润色

### 原始内容
"""

        # Add chapter content
        for result in context.recent_results:
            if result.get("task_type") == "章节内容" and result.get("chapter_index") == chapter_index:
                prompt += f"\n{result['content'][:2000]}...\n"
                break

        prompt += """

### 输出要求

请对章节内容进行润色:

1. **语言优化**: 更优美的表达
2. **节奏调整**: 改善节奏感
3. **细节增强**: 增加生动细节
4. **情感渲染**: 增强情感表达
5. **保持原意**: 不改变原有情节

请直接输出润色后的内容。
"""
        return prompt

    def _build_evaluation_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for content evaluation"""
        chapter_index = metadata.get("chapter_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章质量评估

### 章节内容
"""

        # Add chapter content
        for result in context.recent_results:
            if result.get("task_type") == "章节润色" and result.get("chapter_index") == chapter_index:
                prompt += f"\n{result['content'][:3000]}\n"
                break

        prompt += """

### 评估维度

请从以下维度评估（0-100分）:

1. **连贯性**: 逻辑是否连贯
2. **创意性**: 内容是否有新意
3. **文笔质量**: 文字是否优美
4. **一致性**: 是否与前面设定一致
5. **吸引力**: 是否吸引读者继续阅读

请输出JSON格式的评估结果。
"""
        return prompt

    def _build_revision_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for content revision"""
        chapter_index = metadata.get("chapter_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章修订

### 当前内容
"""

        # Add chapter content
        for result in context.recent_results:
            if result.get("chapter_index") == chapter_index and result.get("task_type") in ["章节润色", "评估"]:
                prompt += f"\n{result['content'][:2000]}\n"
                break

        prompt += """

### 评估反馈
"""

        # Add evaluation feedback
        for result in context.recent_results:
            if result.get("evaluation"):
                prompt += f"\n{result['evaluation'][:500]}\n"
                break

        prompt += """

### 输出要求

请根据评估反馈修订内容，解决发现的问题。
保持原有结构和情节，仅改进需要修正的部分。

请直接输出修订后的内容。
"""
        return prompt

    def _build_generic_prompt(
        self,
        task_type: str,
        context: MemoryContext,
        metadata: Dict[str, Any],
    ) -> str:
        """Build generic prompt for unknown task types"""
        prompt = f"""## 任务: {task_type}

### 相关上下文
"""

        # Add context
        for result in context.recent_results[:3]:
            prompt += f"\n{result['task_type']}: {result['content'][:200]}...\n"

        prompt += f"""

### 元数据
{metadata}

### 输出要求
请完成任务，直接输出结果。
"""
        return prompt
