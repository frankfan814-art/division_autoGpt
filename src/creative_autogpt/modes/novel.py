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

from typing import Any, Dict, Optional


from creative_autogpt.modes.base import Mode, WritingMode, register_mode
from creative_autogpt.core.task_planner import NovelTaskType
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
            "style": "未来科技，宇宙探索，带有黑色幽默和心理深度",
            "themes": ["科技", "人性", "文明", "探索"],
            "elements": ["AI", "太空", "基因", "能源"],
            "writing_guidance": {
                "tone": "在硬核科幻设定中融入黑色幽默，通过讽刺和反讽揭示社会现象",
                "psychology": "深入探索科技对人性的影响，增加心理描画的层次感",
                "narrative": "可使用多重视角（如AI日志、公司内部文档）增强故事层次",
                "dialogue": "对话应体现理性与情感的冲突，避免过于直白的表达"
            }
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

    def _get_genre_guidance(self, context: MemoryContext, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Get genre-specific writing guidance for prompts"""
        # 优先从元数据获取类型，更可靠
        genre = (metadata.get("goal_style") if metadata else None) or self.genre
        genre_config = self.GENRE_CONFIGS.get(genre, {})
        guidance = genre_config.get("writing_guidance", {})

        if not guidance:
            return ""

        guidance_text = "\n### 风格特定写作指导\n"
        if guidance.get("tone"):
            guidance_text += f"**基调**: {guidance['tone']}\n"
        if guidance.get("psychology"):
            guidance_text += f"**心理描写**: {guidance['psychology']}\n"
        if guidance.get("narrative"):
            guidance_text += f"**叙事技巧**: {guidance['narrative']}\n"
        if guidance.get("dialogue"):
            guidance_text += f"**对话风格**: {guidance['dialogue']}\n"

        return guidance_text

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

        # 注：一致性检查已合并到综合评估任务中
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

        elif task_type == NovelTaskType.CREATIVE_BRAINSTORM.value:
            return self._build_brainstorm_prompt(context, metadata)

        elif task_type == NovelTaskType.STORY_CORE.value:
            return self._build_story_core_prompt(context, metadata)

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

        # 添加类型特定的写作指导
        if genre_config.get("writing_guidance"):
            prompt += "\n### 写作指导\n"
            guidance = genre_config["writing_guidance"]
            if guidance.get("tone"):
                prompt += f"**基调**: {guidance['tone']}\n"
            if guidance.get("psychology"):
                prompt += f"**心理描写**: {guidance['psychology']}\n"
            if guidance.get("narrative"):
                prompt += f"**叙事技巧**: {guidance['narrative']}\n"
            if guidance.get("dialogue"):
                prompt += f"**对话风格**: {guidance['dialogue']}\n"

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

### ⚠️ 重要要求：避免俗套！

**请务必创新**：
- 拒绝老套路：不要"废柴逆袭"、"退婚打脸"、"秘境捡宝"
- 冲突要复杂：不要简单的正邪对立，要有道德困境
- 节奏要独特：不要千篇一律的"升级-打脸-升级"循环
- 结局要意外：不要主角最终成神这种套路

### 输出要求

请创建完整的故事大纲，包括:

1. **故事简介**: 200-300字简介（突出独特卖点）
2. **主线剧情**: 开端、发展、高潮、结局（每个转折都要有新意）
3. **分卷规划**: 建议的分卷（每卷20-50万字）
4. **核心冲突**: 主要矛盾和冲突点（要有多层次的冲突）
5. **关键转折**: 故事的关键转折点（至少3个意外转折）
6. **结局方向**: 预期的结局走向（不要大团圆俗套）

请以清晰的层级结构输出大纲。
"""
        return prompt

    def _build_character_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for character design"""
        prompt = """## 🚨🚨🚨 最高优先级要求：主角名称必须独特！🚨🚨🚨

在生成人物之前，必须遵守以下命名规则：

### ❌ 绝对禁止使用的名字（违规立即作废）
**常见网文主角名（绝对禁止）**：
林默、叶凡、萧炎、林动、楚羽、苏铭、方寒、宁川、江尘、秦羽、唐三、罗峰、楚枫、陈北玄、牧童、宋慈、顾慎为等

**历史名人（绝对禁止）**：
李白、杜甫、苏轼、诸葛亮、关羽、曹操、刘备、孙权、岳飞、文天祥等

**神话人物（绝对禁止）**：
哪吒、杨戬、二郎神、太白金星、玉皇大帝、如来佛祖、观音菩萨等

### ✅ 正确的命名方式
**方法1：罕见姓氏 + 有寓意的名字**
- 陆沉舟、楚未央、顾青寒、谢安澜、萧九歌、夜七杀、墨千山、白无忧
- 江南烟、北宫寒、西门雪、东方玉、独孤败、司马长风、皇甫静

**方法2：完全自造的名字**
- 从诗词、成语、自然现象中提取元素组合
- 确保不会让人联想到其他任何作品

**方法3：使用复姓或三字名**
- 欧阳、上官、皇甫、司马、独孤、宇文、长孙等
- 配合有寓意的字，如欧阳云、上官婉、皇甫谧

### ⚠️ 违规后果
如果使用了上述禁止名字，整个设计将被拒绝，需要重新设计！

---

## 任务: 设计人物角色

### 故事大纲
"""

        # Add outline information
        for result in context.recent_results:
            if result["task_type"] == "大纲":
                prompt += f"\n{result['content'][:800]}...\n"
                break

        prompt += """

### 输出要求

请设计主要人物角色，每个角色都必须有深度和立体感：

**主角:**
- **姓名**（🚨🚨�️ 必须独特，绝对不要使用上述禁用名字！🚨🚨�️）
- 年龄、外貌特征
- 性格特点（至少3个正面特质和1-2个致命缺陷）
- 背景设定（家庭、成长经历、关键转折点）
- 核心动机（内在驱动力和外在目标）
- 能力/特长（以及局限性）
- 性格缺陷（致命弱点，会导致冲突）
- 成长弧线（起点、转折、终点）
- 说话风格和口头禅

**重要配角（每个配角都需要完整小传）:**
- 3-5个重要配角
- 每个配角的完整小传，包括：
  - 姓名（🚨 同样必须独特，不要使用禁用名字！）
  - 背景故事：他们的过去经历了什么？为什么成为现在这样？
  - 核心动机：他们真正想要什么？为什么？
  - 性格特点：优点和缺点都要有
  - 与主角的关系：复杂的关系网络（不仅仅是朋友/敌人）
  - 自身的故事线：配角应该有自己的目标和成长
  - 对话风格：独特的说话方式，反映其性格和背景

**配角对话指导原则:**
- 每个角色的对话必须符合其性格、背景和教育水平
- 通过对话展示人物的情感变化和内心冲突
- 避免直白的信息倾倒，用自然的对话传达信息
- 增加对话的层次感，有些话明说，有些话暗示

**人物关系图:**
- 主要人物之间复杂的关系网络
- 包括明面的关系和隐藏的矛盾

请以结构化格式输出人物设计，确保每个配角都有足够的深度。
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

    # 注：一致性检查已合并到综合评估任务中，_build_consistency_prompt 方法已移除

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

### 重要提示：信息量均衡与节奏控制

**避免常见问题:**
- ❌ 信息过载：不要在单一章节中堆积过多背景介绍和细节
- ❌ 信息不足：确保每个章节都有足够的内容支撑情节推进
- ❌ 节奏不一致：避免部分章节过快、部分章节过慢

**信息量均衡原则:**
- 每个章节应该有1-2个核心信息点或情节推进
- 背景信息应分散到多个章节，通过对话和行动自然展现
- 避免在章节开头大段的说明性文字
- 通过情节发展自然带出世界观和设定信息

**节奏控制要点:**
- 紧张情节之后适当放缓，给读者缓冲时间
- 平滑过渡，避免突兀的节奏跳跃
- 每章都应有小高潮，章末留悬念吸引继续阅读

### 输出要求

请为第{chapter_index}章创建详细大纲:

1. **章节标题**: 吸引人的标题
2. **核心目标**: 本章要达成什么情节目标？（1-2个即可）
3. **场景划分**: 3-5个场景，每个场景的信息量要均衡
4. **出场人物**: 本章出场的人物及其作用
5. **情节推进**: 推进的主线/支线（明确推进了什么）
6. **冲突发展**: 本章的冲突（新冲突或旧冲突升级）
7. **伏笔埋设/回收**: 本章涉及的伏笔
8. **结尾悬念**: 章末的悬念点
9. **信息密度评估**: 预估本章的信息量是否适中（过低/适中/过高）

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

### 重要提示：对话真实性

**避免常见问题:**
- ❌ 对话生硬：不符合人物性格和背景
- ❌ 信息倾倒：通过大段对话说明背景
- ❌ 陈词滥调：使用过于直白或套路化的表达
- ❌ 缺乏层次：对话只有表意，没有潜台词

**对话真实性原则:**
- 每个角色的对话必须符合其性格、背景和教育水平
- 通过对话展示人物的情感变化和内心冲突，而非直接陈述
- 增加对话的层次感：有些话明说，有些话暗示，有些话不说
- 避免过于直白的表达，增加对话的微妙感和真实感
- 使用角色独特的说话方式、口头禅和语言习惯
"""

        # 添加风格特定的写作指导
        genre_guidance = self._get_genre_guidance(context, metadata)
        if genre_guidance:
            prompt += f"\n{genre_guidance}\n"

        prompt += """
### 输出要求

请生成详细的场景内容:

1. **场景描述**: 环境、氛围（具象生动，避免抽象描述）
2. **人物动作**: 人物的行为和互动（通过行动展现性格）
3. **对话**: 符合人物性格的自然对话（关键！）
4. **心理描写**: 人物内心活动（通过内心独白展现复杂情感）
5. **感官细节**: 视觉、听觉、触觉等具体细节
6. **节奏控制**: 快慢节奏的把握（紧张场景快节奏，反思场景慢节奏）

请直接输出场景内容，1500-2500字。
"""
        return prompt

    def _build_chapter_content_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for chapter content generation"""
        chapter_index = metadata.get("chapter_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章内容生成

### ⚠️ 人物名称一致性要求

**必须使用人物设计中确定的角色名称，绝对不要更换或创造新名字！**

从上下文中提取所有人物名称，确保：
- 主角名称保持一致（不要用林默、叶凡等俗套名字）
- 配角名称保持一致
- 地点、物品名称保持一致

如果人物设计中未提供具体名称，使用罕见的、自造的名字，绝对不要使用常见网文主角名！

---

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

### 重要提示：节奏一致性与信息量控制

**避免常见问题:**
- ❌ 节奏不一致：场景之间节奏跳跃过大
- ❌ 信息过载：在同一章节中堆砌过多内容
- ❌ 信息不足：章节内容稀疏，缺乏实质推进
- ❌ 过渡生硬：场景转换缺乏平滑过渡

**节奏一致性原则:**
- 平衡紧张场景和缓和场景的比例
- 场景之间要有平滑的过渡，避免突兀跳跃
- 在紧张情节之后适当放缓节奏
- 保持整章的节奏基调一致，不要忽快忽慢

**信息量控制:**
- 每个章节聚焦1-2个核心情节目标
- 确保每个场景都对主线或支线有实质推进
- 避免在单一场景中塞入过多信息点
- 通过情节发展自然带出信息，而非说明性文字

### 输出要求

请将各场景整合成完整的章节内容:

1. **结构完整**: 开头、发展、结尾（三段式结构）
2. **过渡自然**: 场景之间的平滑过渡（关键！）
3. **节奏协调**: 整章节奏一致，快慢有致
4. **信息均衡**: 每个场景的信息量要均衡，不要过载或不足
5. **字数控制**: 3000-5000字
6. **悬念设置**: 章末留悬念，吸引读者继续阅读
7. **对话自然**: 确保所有对话都符合人物性格
8. **心理描写**: 通过内心独白展现人物复杂情感

请直接输出章节内容，不需要章节标题。
"""
        return prompt

    def _build_chapter_polish_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for chapter polish"""
        chapter_index = metadata.get("chapter_index", 1)

        prompt = f"""## 任务: 第{chapter_index}章润色

### ⚠️ 人物名称一致性要求

**在润色过程中，必须保持所有人物名称一致！**

- 绝对不要更改人物名称
- 绝对不要使用林默、叶凡、萧炎等常见网文主角名
- 如果发现人物名称不一致，必须修正为原始名称
- 确保主角、配角的所有称呼都保持一致

---

### 原始内容
"""

        # Add chapter content
        for result in context.recent_results:
            if result.get("task_type") == "章节内容" and result.get("chapter_index") == chapter_index:
                prompt += f"\n{result['content'][:2000]}...\n"
                break

        prompt += """

### 重要提示：对话优化与心理描写

**对话优化要点:**
- 检查每句对话是否符合人物性格和背景
- 增加对话的层次感：明说、暗示、潜台词
- 避免陈词滥调和过于直白的表达
- 确保对话推动情节或展现人物关系
- 优化对话的节奏感，长短句结合

**心理描写要点:**
- 增加更多关于主角和配角的内心独白
- 通过内心活动展现人物复杂情感和冲突
- 使用细节和动作暗示人物心理状态
- 通过梦境、幻觉等方式展示潜意识
- 避免直接陈述情感，用具体感受替代
"""

        # 添加风格特定的写作指导
        genre_guidance = self._get_genre_guidance(context, metadata)
        if genre_guidance:
            prompt += f"\n{genre_guidance}\n"

        prompt += """
### 输出要求

请对章节内容进行润色:

1. **语言优化**: 更优美、精准的表达（具象生动，避免抽象）
2. **对话优化**: 确保对话自然、符合人物性格（关键！）
3. **心理描写**: 增加内心独白，展现人物复杂情感（关键！）
4. **节奏调整**: 改善节奏感，保持整体节奏一致
5. **细节增强**: 增加生动的感官细节
6. **情感渲染**: 增强情感表达的真实感
7. **保持原意**: 不改变原有情节和结构

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

    def _build_brainstorm_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for creative brainstorm"""
        genre = metadata.get("goal_style") or metadata.get("genre", self.genre)
        goal_idea = metadata.get("goal_idea", "")

        prompt = f"""## 任务: 创意脑暴

### 小说类型
{genre}

### 创意方向
{goal_idea if goal_idea else "请自由发挥创意"}

### ⚠️ 重要要求：避免雷同！

**务必创新**：
- 避免使用常见的套路和俗套情节
- 拒绝陈词滥调：不要"废柴逆袭"、"退婚流"等老套路
- 创造独特的设定和冲突
- 每个点子都要有自己的"灵魂"

**追求差异化**：
- 🔄 如果看到3个以上点子风格相似，请重新构思
- 🎭 人物动机要复杂，非黑即白的人物不够有趣
- ⚡ 冲突要新颖，不要千篇一律的"复仇"或"打脸"
- 💫 情感钩子要独特，让读者产生新的情感体验

### 输出要求

请产生 **3-5 个完全不同** 的故事点子，每个点子包括：

**点子 1 / 点子 2 / ...**
1. **核心概念** (一句话概括)
2. **独特卖点** (为什么这个创意与众不同？)
3. **核心冲突** (主角想要什么？什么在阻止他？)
4. **情感钩子** (读者为什么会关心？)
5. **世界观亮点** (如果适用，简要说明独特的设定元素)

请确保每个点子都有鲜明的个性，不要雷同！
"""
        return prompt

    def _build_story_core_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for story core definition"""
        prompt = """## 任务: 确定故事核心

### 创意脑暴结果
"""

        # Add brainstorm result
        for result in context.recent_results:
            if result["task_type"] == "创意脑暴":
                prompt += f"\n{result['content'][:1000]}...\n"
                break

        prompt += """

### 输出要求

从上面的创意点子中选择一个最有潜力的，确定故事核心。

**故事核心必须包含**：

1. **主角是谁？**
   - 姓名（避免常见名字如林默、叶凡、萧炎等）
   - 初始状态（平凡/特殊/困境）

2. **主角想要什么？** (外在目标)
   - 明确的目标

3. **什么在阻止他？** (核心冲突)
   - 内在阻碍
   - 外在阻碍

4. **为什么读者会在意？** (情感钩子)
   - 普世的情感需求

5. **一句话概括**
   - 格式：[主角] + [想要] + [但] + [所以] + [最终]

⚠️ **避免雷同**：
- 主角名字要独特，避免使用常见网文主角名
- 核心冲突要新颖，不要千篇一律
- 确保这个故事之前没人讲过

请直接输出故事核心，不需要其他内容。
"""
        return prompt
