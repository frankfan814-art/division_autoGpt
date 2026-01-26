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

    # 作者风格配置
    AUTHOR_STYLES = {
        "liucixin": {
            "name": "刘慈欣",
            "style_desc": "硬科幻风格，宏大的宇宙观，冷峻理性的笔触",
            "writing_features": [
                "用最朴素的语言描述最宏大的概念",
                "大量使用科学原理作为情节推动力",
                "善用比喻，将抽象概念具象化",
                "对话简练，信息密度高",
                "不煽情，不刻意渲染气氛",
                "注重逻辑推演的严密性"
            ],
            "example": "就像《三体》中用'黑暗森林'比喻宇宙文明关系，用'降维打击'描述毁灭方式",
        },
        "jiangnan": {
            "name": "江南",
            "style_desc": "热血青春风，细腻的情感描写，华丽的修辞",
            "writing_features": [
                "大量的比喻和排比",
                "情感描写细腻，擅长写孤独、热血、羁绊",
                "对话带有一定文艺腔",
                "善用留白和意境",
                "节奏先缓后急，高潮部分燃"
            ],
            "example": "就像《龙族》中路明非的孤独感，楚子航的热血，都是通过细节堆出来的",
        },
        "fenghuo": {
            "name": "我吃西红柿",
            "style_desc": "升级流爽文，节奏快，升级体系清晰",
            "writing_features": [
                "主角性格坚毅，目标明确",
                "升级体系量化，等级清晰",
                "战斗场面描写简洁有力",
                "不拖泥带水，该过就过",
                "善用伏笔，前后呼应"
            ],
            "example": "就像《盘龙》中，从初级战士到圣域，每一步都很清楚",
        },
        "tangjia": {
            "name": "唐家三少",
            "style_desc": "热血冒险，重视友情和团队",
            "writing_features": [
                "主角团队配合默契",
                "强调友情、信任、守护",
                "技能描写华丽",
                "对话口语化，贴近年轻人",
                "节奏明快，爽点多"
            ],
            "example": "就像《斗罗大陆》中史莱克七怪的配合，每个人都有独特作用",
        },
        "chenan": {
            "name": "陈安",
            "style_desc": "悬疑推理，逻辑严密",
            "writing_features": [
                "注重线索埋设",
                "推理过程严密",
                "细节描写精细",
                "对话简洁有力",
                "节奏张弛有度"
            ],
            "example": "推理小说的精髓在于线索的合理分布和逻辑的严密性",
        },
        "caocao": {
            "name": "猫腻",
            "style_desc": "权谋政治，文笔细腻",
            "writing_features": [
                "政治斗争描写细腻",
                "人物关系复杂",
                "文笔华丽但不浮夸",
                "善用反讽和黑色幽默",
                "节奏较慢，但细节丰富"
            ],
            "example": "就像《庆余年》中，每个角色都有自己的算计和立场",
        },
        "wuxing": {
            "name": "耳根",
            "style_desc": "仙侠玄幻，世界观宏大",
            "writing_features": [
                "世界观极其宏大",
                "修炼体系复杂完整",
                "主角性格坚毅狠辣",
                "战斗场面震撼",
                "动辄涉及因果轮回"
            ],
            "example": "就像《仙逆》中，主角从一个凡人一步步走到巅峰",
        },
        "zhuji": {
            "name": "辰东",
            "style_desc": "热血战斗，情节紧凑",
            "writing_features": [
                "战斗场面热血",
                "节奏紧凑，不拖沓",
                "善用悬念",
                "主角性格热血霸气",
                "情节反转多"
            ],
            "example": "就像《完美世界》中，战斗场面一个接一个，热血沸腾",
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

    def _get_author_style_guidance(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Get author style guidance for prompts"""
        author_style = (metadata.get("goal_author_style") if metadata else None) or ""
        if not author_style or author_style not in self.AUTHOR_STYLES:
            return ""

        style_config = self.AUTHOR_STYLES[author_style]

        guidance_text = f"\n### 📝 参考作者风格：{style_config['name']}\n"
        guidance_text += f"**风格特点**: {style_config['style_desc']}\n\n"
        guidance_text += "**写作特征**:\n"
        for feature in style_config['writing_features']:
            guidance_text += f"- {feature}\n"
        guidance_text += f"\n**参考**: {style_config['example']}\n"
        guidance_text += "\n请模仿这位作者的写作风格，但不要照搬具体情节和人物。\n"

        return guidance_text

    async def _get_examples_text(self, context: MemoryContext, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Get examples text for prompt"""
        try:
            from creative_autogpt.utils.example_retriever import get_retriever

            retriever = await get_retriever()
            if not retriever:
                return ""

            style = (metadata.get("goal_style") if metadata else None) or self.genre
            author_style = (metadata.get("goal_author_style") if metadata else None) or ""

            return await retriever.get_examples_for_prompt(
                style=style,
                author_style=author_style if author_style else None,
                max_examples=3,
            )

        except Exception as e:
            # 范例获取失败不影响主流程
            return ""

    async def build_prompt(
        self,
        task_type: str,
        context: MemoryContext,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for a novel task type"""
        metadata = metadata or {}

        # Get task-specific prompt (混合方案)
        if task_type == NovelTaskType.CREATIVE_BRAINSTORM.value:
            return self._build_brainstorm_prompt(context, metadata)

        elif task_type == NovelTaskType.STORY_CORE.value:
            return self._build_story_core_prompt(context, metadata)

        elif task_type == NovelTaskType.OUTLINE.value:
            return self._build_outline_prompt(context, metadata)

        elif task_type == NovelTaskType.CHARACTER_DESIGN.value:
            return self._build_character_prompt(context, metadata)

        elif task_type == NovelTaskType.WORLDVIEW_RULES.value:
            return self._build_worldview_prompt(context, metadata)

        elif task_type == NovelTaskType.CHAPTER_CONTENT.value:
            return await self._build_chapter_content_prompt(context, metadata)

        # elif task_type == NovelTaskType.BATCH_CHAPTER_GENERATION.value:  # ⚠️ 已禁用批量生成
        #     return self._build_batch_chapter_generation_prompt(context, metadata)

        # elif task_type == NovelTaskType.CHAPTER_POLISH.value:  # ⚠️ 已移除：使用 Qwen Long 直接生成高质量内容
        #     return self._build_chapter_polish_prompt(context, metadata)

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
        """Build prompt for enhanced story outline (包含事件、伏笔、章节规划)"""
        goal_length = metadata.get("goal_length", "30万字")
        chapter_count = metadata.get("chapter_count", 10)

        prompt = f"""## 🎯 任务: 创建完整的小说大纲（加强版）

### ⚠️ 这是整个创作的蓝图！所有细节都在这里设计好！

**目标规模**: {goal_length}
**预计章节数**: {chapter_count} 章

### 📋 前置信息
"""

        # Add relevant context - 只添加故事核心（前置任务）
        for result in context.recent_results:
            if result.get("task_type") == "故事核心":
                prompt += f"\n#### {result['task_type']}\n{result['content'][:800]}...\n"
                break

        prompt += f"""

### 🔥 核心要求：这是唯一的机会设计完整故事！

**为什么大纲如此重要？**
1. 这是所有章节创作的唯一蓝图
2. 所有伏笔必须在这里设计好
3. 人物关系必须在这里理清
4. 每章的内容必须在这里规划

**如果大纲设计有问题，后面生成的所有章节都会有问题！**

---

### 🚨 拒绝俗套要求

**绝对不要写**：
- ❌ 废柴逆袭流
- ❌ 退婚打脸流
- ❌ 秘境捡宝流
- ❌ 宗门大比流
- ❌ 主角最终成神/飞升的俗套结局

**必须创新**：
- ✅ 复杂的道德困境（不是简单的正邪对立）
- ✅ 意外的转折（读者猜不到的走向）
- ✅ 真实的人物动机（每个角色都有合理的行为逻辑）
- ✅ 独特的结局（不要大团圆，也不要故意悲剧）

---

### 📝 大纲必须包含的内容

#### 1. 故事结构
```
【开端】主角登场 + 初始状态 + 激励事件
    ↓
【发展】冲突升级 + 人物成长 + 秘密揭开
    ↓
【高潮】最大冲突 + 绝境时刻 + 最终抉择
    ↓
【结局】结局走向 + 主题升华 + 留白回味
```

#### 2. 完整事件链（时间线）
设计 20-50 个关键事件，按时间顺序排列：

```
事件1: [章节1] 主角遭遇激励事件...
事件2: [章节2] 主角开始行动...
事件3: [章节3] 第一次冲突...
...
事件N: [章节M] 最终决战...
```

**每个事件包含**：
- 触发条件
- 主要内容
- 结果影响
- 伏笔关联（如果有）

#### 3. 伏笔系统（⚠️ 重点！）

**主线伏笔**（5-10个，贯穿全书）：
| 伏笔名称 | 埋设章节 | 暗示内容 | 回收章节 | 揭示方式 | 影响 |
|---------|---------|---------|---------|---------|------|
| 伏笔1   | 第X章   | ...     | 第Y章   | ...     | ...  |
| ...     | ...     | ...     | ...     | ...     | ...  |

**支线伏笔**（3-5个）：
| 伏笔名称 | 埋设章节 | 暗示内容 | 回收章节 | 影响 |
|---------|---------|---------|---------|------|
| ...     | ...     | ...     | ...     | ...  |

**细节伏笔**（可以埋设的类型）：
- 人物身份的秘密
- 道具的特殊功能
- 表面的善意实际是阴谋
- 早期的对话有双关含义

#### 4. 章节规划（每章3000-5000字）

```
第1章: 【标题】核心内容（200字以内）
第2章: 【标题】核心内容
...
第{chapter_count}章: 【标题】核心内容
```

**每章包含**：
- 核心事件（发生了什么）
- 人物出场（谁出现，为什么）
- 伏笔埋设/回收（如果有）
- 情感节奏（紧张/缓和）
- 字数目标

#### 5. 人物关系网络

```
主角 ━━━━━ [关系1] ━━━━━ 配角A
  ├── [关系2] ━━━━━ 反派
  ├── [关系3] ━━━━━ 导师
  └── [关系4] ━━━━━ 恋爱对象

配角A ━━━━━ [关系5] ━━━━━ 反派
  └── [关系6] ━━━━━ 配角B
```

**标注**：
- 每段关系的性质（盟友/敌人/暧昧/利用）
- 关系的变化（第几章关系会改变）
- 隐藏的关系（表面A，实际B）

#### 6. 世界观要点（影响故事的关键设定）

列出影响剧情的核心设定：
```
设定1: [描述] → 如何影响剧情
设定2: [描述] → 如何制造冲突
设定3: [描述] → 如何限制主角
```

---

### ✅ 输出格式要求

请按以下结构输出大纲：

```markdown
# [小说标题] 大纲

## 一、故事简介
[200-300字，突出独特卖点]

## 二、故事结构
### 2.1 开端
...
### 2.2 发展
...
### 2.3 高潮
...
### 2.4 结局
...

## 三、完整事件链
### 3.1 主线事件时间线
1. [章节1] 事件名：描述
2. [章节2] 事件名：描述
...

### 3.2 关键转折点
转折点1（第X章）：...
转折点2（第Y章）：...
...

## 四、伏笔系统
### 4.1 主线伏笔
| 伏笔名称 | 埋设章节 | 暗示内容 | 回收章节 | 揭示方式 | 影响 |
|---------|---------|---------|---------|---------|------|
| ... | ... | ... | ... | ... | ... |

### 4.2 支线伏笔
| 伏笔名称 | 埋设章节 | 暗示内容 | 回收章节 | 影响 |
|---------|---------|---------|---------|------|
| ... | ... | ... | ... | ... |

### 4.3 伏笔回收计划
- 第1-3章埋设的主要伏笔将在第X章回收
- 第Y章的转折将揭示第Z章埋下的秘密
- ...

## 五、详细章节规划（⚠️ 必须为每一章提供完整大纲！）

### 🔴 章节规划要求
- **必须为所有 {chapter_count} 章提供详细大纲**
- **不能使用"..."省略任何章节**
- 每章都要有完整的内容规划

### 第1章：【标题】
- **核心事件**：（200字以内，本章发生了什么）
- **场景设定**：（在哪里发生）
- **人物出场**：（哪些人物首次出现，哪些人物有重要戏份）
- **情节推进**：（如何推进主线/支线）
- **冲突发展**：（本章的冲突是什么）
- **伏笔埋设**：（埋设哪些伏笔，如何暗示）
- **结尾悬念**：（章末如何吸引继续阅读）
- **情感节奏**：（紧张/缓和/铺垫）
- **字数目标**：（3000-5000字）

### 第2章：【标题】
- **核心事件**：
- **场景设定**：
- **人物出场**：
- **情节推进**：
- **冲突发展**：
- **伏笔埋设/回收**：
- **结尾悬念**：
- **情感节奏**：
- **字数目标**：

### 第3章：【标题】
（同上结构）

...（依此类推，直到第{chapter_count}章）

### 第{chapter_count}章：【标题】
- **核心事件**：
- **场景设定**：
- **人物出场**：
- **情节推进**：
- **冲突发展**：
- **伏笔回收**：（哪些伏笔在此章揭示）
- **结尾处理**：（如何为后续做铺垫）
- **情感节奏**：
- **字数目标**：

⚠️ **确认：以上已包含全部 {chapter_count} 章的完整规划，无任何省略！**

## 六、人物关系网络
### 主角关系
- vs 配角A：[关系性质，变化]
- vs 反派：[关系性质，变化]
...

### 次要关系
- 配角A vs 配角B：...
...

## 七、世界观要点
1. [设定名称]：[描述] → [剧情影响]
2. ...
```

---

### ⚠️ 最后检查

在输出之前，请确认：
1. ✅ 伏笔系统完整吗？（主线、支线都有）
2. ✅ 每个伏笔都有回收计划吗？
3. ✅ 事件链逻辑连贯吗？
4. ✅ 人物关系清晰吗？
5. ✅ 章节规划完整吗？
6. ✅ 拒绝俗套了吗？
7. ✅ 结局有新意吗？

**现在请开始创作完整大纲！**
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

    async def _build_chapter_content_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for chapter content generation（逐章生成，确保连贯性）"""
        chapter_index = metadata.get("chapter_index", 1)
        chapter_count = metadata.get("chapter_count", 10)
        is_first_chapter = metadata.get("is_first_chapter", False)

        prompt = f"""## 任务: 第{chapter_index}章内容生成（逐章生成模式）

### 🔥 连贯性优先级：最高

**这是逐章生成模式，每一章都必须与前面的章节保持连贯！**

---

### ⚠️ 人物名称一致性要求

**必须使用人物设计中确定的角色名称，绝对不要更换或创造新名字！**

从上下文中提取所有人物名称，确保：
- 主角名称保持一致（不要用林默、叶凡等俗套名字）
- 配角名称保持一致
- 地点、物品名称保持一致

如果人物设计中未提供具体名称，使用罕见的、自造的名字，绝对不要使用常见网文主角名！

---

### 📚 基础上下文（必须参考）

#### 1️⃣ 完整大纲（最重要的蓝图！）
"""

        # 添加完整大纲
        for result in context.recent_results:
            if result["task_type"] == "大纲":
                prompt += f"\n```markdown\n{result['content']}\n```\n"
                break

        prompt += "\n#### 2️⃣ 人物设计（确保人物名称一致！）\n\n"
        # 添加人物设计
        for result in context.recent_results:
            if result["task_type"] == "人物设计":
                prompt += f"{result['content'][:2000]}...\n\n"
                break

        prompt += "\n#### 3️⃣ 世界观规则（确保设定一致！）\n\n"
        # 添加世界观
        for result in context.recent_results:
            if result["task_type"] == "世界观规则":
                prompt += f"{result['content'][:1500]}...\n\n"
                break

        # 🔥 关键：添加前几章的内容用于连贯性
        if not is_first_chapter and chapter_index > 1:
            prompt += f"\n---\n\n### 🔥 前几章内容（连贯性关键！）\n\n"
            prompt += f"**以下是第{chapter_index-1}章的结尾部分，请确保本章自然衔接：**\n\n"

            # 查找前一章的内容
            previous_chapter_found = False
            for result in context.recent_results:
                if (result.get("task_type") == "章节内容" and
                    result.get("chapter_index") == chapter_index - 1):
                    # 获取前一章的结尾部分（最后800字）
                    content = result.get("content", "")
                    ending = content[-800:] if len(content) > 800 else content
                    prompt += f"```markdown\n...{ending}\n```\n\n"
                    previous_chapter_found = True
                    break

            if not previous_chapter_found:
                prompt += "⚠️ 未找到前一章内容，请确保本章能够自然开始。\n\n"

            prompt += "**连贯性要求：**\n"
            prompt += f"- 本章必须自然承接第{chapter_index-1}章的结尾\n"
            prompt += "- 人物状态要延续（位置、情绪、目标等）\n"
            prompt += "- 时间线要连续（不要突然跳跃）\n"
            prompt += "- 伏笔要呼应（前面埋下的伏笔要有关联）\n\n"

        prompt += f"""

---

### 📝 本章具体要求（第{chapter_index}章 / 共{chapter_count}章）

#### 从大纲中提取本章规划

**请务必按照大纲中"第{chapter_index}章"的规划来写！**

大纲中关于本章的规划包括：
- 核心事件
- 场景设定
- 人物出场
- 情节推进
- 冲突发展
- 伏笔埋设/回收
- 结尾悬念

---

### ✅ 创作要求（严格遵守！）

#### 🚨 关键约束

1. **人物名称一致性**
   - 主角名称必须从"人物设计"中提取，绝对不要创造新名字
   - 配角名称也要保持一致
   - 绝对不要使用林默、叶凡、萧炎等俗套名字

2. **剧情严格遵循大纲**
   - 本章必须按照大纲中的"章节规划"执行
   - 事件必须按照"事件链"发生
   - 伏笔必须在指定章节埋设/回收

3. **世界观一致**
   - 所有设定必须遵守"世界观规则"
   - 力量体系、地点名称、组织名称必须一致

4. **字数控制**
   - 本章 3000-5000 字
   - 不要写成流水账
   - 本章要有独立的内容和进展

#### 连贯性要点

{f'''
- **开头必须承接第{chapter_index-1}章**：不要突然开始新场景
- **人物状态延续**：人物的位置、情绪、目标要自然延续
- **时间线连续**：不要有时间跳跃
''' if not is_first_chapter else '- **这是第一章**：要开好头，设置好故事基调和悬念'}

#### 每章必须包含：

1. **开头**（200-500字）
   - {f'承接上一章（第{chapter_index-1}章）' if not is_first_chapter else '设置开场'}
   - 设置本章基调
   - 引入本章核心问题

2. **主体**（2000-3500字）
   - 2-4 个场景
   - 人物对话（占30-40%）
   - 行动描写
   - 心理活动
   - 伏笔埋设/回收（如果有）

3. **结尾**（300-800字）
   - 本章问题解决/升级
   - 引入下一章悬念
   - 情感节奏的收尾

#### 对话要求：

- **真实性**：每个角色说话符合其性格和背景
- **功能性**：对话推动剧情或展现人物关系
- **层次感**：有明说、暗示、潜台词
- **避免**：信息倾倒、直白表达、陈词滥调

#### 描写要求：

- **具象化**：用具体细节代替抽象描述
- **感官化**：视觉、听觉、触觉等多感官
- **节奏化**：紧张场景快节奏，反思场景慢节奏

---

### 🎨 风格指导

"""

        # 添加风格指导
        genre_guidance = self._get_genre_guidance(context, metadata)
        if genre_guidance:
            prompt += f"{genre_guidance}\n\n"

        # 添加作者风格指导
        author_style_guidance = self._get_author_style_guidance(metadata)
        if author_style_guidance:
            prompt += f"{author_style_guidance}\n\n"

        # 添加范例（如果有的话）
        examples_text = await self._get_examples_text(context, metadata)
        if examples_text:
            prompt += f"{examples_text}\n"

        prompt += f"""---

### 📋 输出格式

请直接输出第{chapter_index}章的完整内容：

```markdown
[本章内容，3000-5000字]
```

⚠️ **不需要输出章节标题**（如"第1章：xxx"），直接输出正文即可！

---

### ⚠️ 最后检查清单

在开始写作之前，请确认：

1. ✅ 我已经仔细阅读了完整大纲
2. ✅ 我已经理解了人物设计（主角名字、配角名字）
3. ✅ 我已经理解了世界观规则
4. ✅ 我知道本章要写什么内容（来自大纲的"章节规划"）
5. ✅ 我知道要在哪里埋设/回收伏笔
6. ✅ 我会保持人物名称、地点名称、组织名称的一致性
7. ✅ {f'我会确保本章自然承接第{chapter_index-1}章的结尾' if not is_first_chapter else '我会开个好头，设置好故事基调'}
8. ✅ 我会确保剧情连贯，不会前后矛盾

**现在，请开始生成第{chapter_index}章内容！**
"""
        return prompt

    # ⚠️ 已移除：使用 Qwen Long 直接生成高质量内容，无需单独润色步骤
    # def _build_chapter_polish_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
    #     """Build prompt for chapter polish"""
    #     chapter_index = metadata.get("chapter_index", 1)
    #     prompt = f"""## 任务: 第{chapter_index}章润色
    #     ... (完整方法已注释)
    #     """
    #     return prompt

    def _build_batch_chapter_generation_prompt(self, context: MemoryContext, metadata: Dict[str, Any]) -> str:
        """Build prompt for batch chapter generation (使用 qwen-long 一次性生成所有章节)"""
        chapter_count = metadata.get("chapter_count", 10)
        goal_style = metadata.get("goal_style", "科幻")

        prompt = f"""## 🎯 任务: 一次性生成所有章节内容（混合方案）

### 使用 qwen-long 的超大上下文能力，确保整体一致性！

**目标**: 生成 {chapter_count} 章完整内容（每章 3000-5000 字）

---

### 📚 完整上下文（按重要性排序）

#### 1️⃣ 完整大纲（最重要的蓝图！）
"""

        # 添加完整大纲
        for result in context.recent_results:
            if result["task_type"] == "大纲":
                prompt += f"""\n```markdown
{result['content']}
```\n"""
                break

        prompt += "\n#### 2️⃣ 人物设计（确保人物名称一致！）\n\n"
        # 添加人物设计
        for result in context.recent_results:
            if result["task_type"] == "人物设计":
                prompt += f"{result['content'][:2000]}...\n\n"
                break

        prompt += "\n#### 3️⃣ 世界观规则（确保设定一致！）\n\n"
        # 添加世界观
        for result in context.recent_results:
            if result["task_type"] == "世界观规则":
                prompt += f"{result['content'][:1500]}...\n\n"
                break

        prompt += f"""

---

### ✅ 创作要求（严格遵守！）

#### 🚨 关键约束

1. **人物名称一致性**
   - 主角名称必须从"人物设计"中提取，绝对不要创造新名字
   - 配角名称也要保持一致
   - 绝对不要使用林默、叶凡、萧炎等俗套名字

2. **剧情严格遵循大纲**
   - 每章必须按照大纲中的"章节规划"执行
   - 事件必须按照"事件链"发生
   - 伏笔必须在指定章节埋设/回收

3. **世界观一致**
   - 所有设定必须遵守"世界观规则"
   - 力量体系、地点名称、组织名称必须一致

4. **字数控制**
   - 每章 3000-5000 字
   - 不要写成流水账
   - 每章要有独立的内容和进展

---

### 📝 章节内容要求

#### 每章必须包含：

1. **开头**（200-500字）
   - 承接上一章（或开场）
   - 设置本章基调
   - 引入本章核心问题

2. **主体**（2000-3500字）
   - 2-4 个场景
   - 人物对话（占30-40%）
   - 行动描写
   - 心理活动
   - 伏笔埋设/回收（如果有）

3. **结尾**（300-800字）
   - 本章问题解决/升级
   - 引入下一章悬念
   - 情感节奏的收尾

#### 对话要求：

- **真实性**：每个角色说话符合其性格和背景
- **功能性**：对话推动剧情或展现人物关系
- **层次感**：有明说、暗示、潜台词
- **避免**：信息倾倒、直白表达、陈词滥调

#### 描写要求：

- **具象化**：用具体细节代替抽象描述
- **感官化**：视觉、听觉、触觉等多感官
- **节奏化**：紧张场景快节奏，反思场景慢节奏

---

### 🎨 风格指导（{goal_style}类型）

"""

        # 添加风格指导
        genre_guidance = self._get_genre_guidance(context, metadata)
        if genre_guidance:
            prompt += f"{genre_guidance}\n\n"

        prompt += f"""---

### 📋 输出格式

请按以下格式输出所有章节：

```markdown
# 第1章：[章节标题]

[本章内容，3000-5000字]

---

# 第2章：[章节标题]

[本章内容，3000-5000字]

---

# 第3章：[章节标题]

[本章内容，3000-5000字]

...

（共{chapter_count}章）
```

---

### ⚠️ 最后检查清单

在开始写作之前，请确认：

1. ✅ 我已经仔细阅读了完整大纲
2. ✅ 我已经理解了人物设计（主角名字、配角名字）
3. ✅ 我已经理解了世界观规则
4. ✅ 我知道每章要写什么内容（来自大纲的"章节规划"）
5. ✅ 我知道要在哪里埋设/回收伏笔
6. ✅ 我会保持人物名称、地点名称、组织名称的一致性
7. ✅ 我会确保剧情连贯，不会前后矛盾

**现在，请开始生成所有章节内容！**
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
