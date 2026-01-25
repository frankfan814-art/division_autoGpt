# 提示词系统指南

> Creative AutoGPT 提示词模板和风格注入系统

## 1. 提示词系统概览

提示词系统是 Creative AutoGPT 的核心组件之一，负责：
- 🤖 **智能提示词生成**：用户简单描述，LLM 自动扩展为专业提示词
- 🎯 **任务指令**：明确告诉 LLM 要做什么
- 🎨 **风格注入**：确保内容符合预设风格
- 📝 **上下文管理**：提供相关背景信息
- ✅ **质量控制**：通过约束确保输出质量

---

## 2. 智能提示词生成（PromptEnhancer）

> 🌟 **核心亮点**：让不懂提示词的用户也能轻松使用！

### 2.1 设计理念

传统方式要求用户提供详细的配置和提示词，门槛较高。我们引入 **PromptEnhancer（智能提示词增强器）**，让用户只需提供简单描述，系统自动生成专业的结构化提示词。

```
┌─────────────────────────────────────────────────────────────────────┐
│                    智能提示词生成流程                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  用户输入（简单）                     系统输出（完整）               │
│  ┌──────────────────┐               ┌──────────────────────────┐   │
│  │ "写一个玄幻小说   │               │ {                        │   │
│  │  主角是废材逆袭   │  ──────────▶  │   "style": "玄幻修仙",   │   │
│  │  100万字"        │   LLM扩展     │   "theme": "废材逆袭",   │   │
│  └──────────────────┘               │   "protagonist": {...},  │   │
│                                      │   "plot_elements": [...],│   │
│  门槛：⭐（超低）                    │   "style_elements": {...}│   │
│                                      │ }                        │   │
│                                      └──────────────────────────┘   │
│                                      门槛：⭐⭐⭐⭐⭐（专业级）      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 流程位置

PromptEnhancer 位于**整个流程的最前端**，作为预处理步骤：

```
┌─────────────────────────────────────────────────────────────────────┐
│                       完整执行流程                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ① 用户输入          ② 智能增强           ③ 用户确认              │
│  ┌─────────┐       ┌─────────────┐       ┌─────────────┐          │
│  │ 简单描述 │──────▶│PromptEnhancer│──────▶│ 预览&调整   │          │
│  │ (1-2句话)│       │ (DeepSeek)   │       │ (可选)     │          │
│  └─────────┘       └─────────────┘       └──────┬──────┘          │
│                                                  │                  │
│                                                  ▼                  │
│  ④ 任务规划         ⑤ 任务执行           ⑥ 质量评估              │
│  ┌─────────┐       ┌─────────────┐       ┌─────────────┐          │
│  │TaskPlanner│◀─────│ 完整配置    │       │  Evaluator  │          │
│  │ (规划)   │──────▶│ LoopEngine  │──────▶│  (评估)    │          │
│  └─────────┘       └─────────────┘       └─────────────┘          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 模块实现

**文件位置**: `src/creative_autogpt/prompts/enhancer.py`

```python
"""
智能提示词增强器
将用户的简单描述自动扩展为完整的结构化配置
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class EnhancedPrompt:
    """增强后的提示词配置"""
    style: str                      # 风格类型
    theme: str                      # 主题
    target_words: int               # 目标字数
    chapter_count: int              # 章节数
    
    protagonist: Dict[str, Any]     # 主角设定
    world_setting: Dict[str, Any]   # 世界观设定
    plot_elements: list             # 情节要素
    style_elements: Dict[str, Any]  # 风格元素
    
    constraints: list               # 约束条件
    special_requirements: list      # 特殊要求
    
    raw_input: str                  # 原始用户输入
    confidence: float               # 扩展置信度


class PromptEnhancer:
    """
    智能提示词增强器
    
    功能：
    1. 解析用户的自然语言描述
    2. 识别关键要素（风格、主题、人物等）
    3. 扩展为完整的结构化配置
    4. 支持用户确认和调整
    """
    
    def __init__(self, llm_client, config: Dict[str, Any] = None):
        self.llm_client = llm_client
        self.config = config or {}
        
        # 使用 DeepSeek 进行扩展（性价比高）
        self.enhancer_llm = "deepseek"
    
    async def enhance(
        self,
        user_input: str,
        mode: str = "novel"
    ) -> EnhancedPrompt:
        """
        将用户简单描述扩展为完整配置
        
        Args:
            user_input: 用户的简单描述
            mode: 写作模式 (novel/script/larp)
            
        Returns:
            EnhancedPrompt: 扩展后的完整配置
        """
        logger.info(f"Enhancing user input: {user_input[:100]}...")
        
        # 构建增强提示词
        enhance_prompt = self._build_enhance_prompt(user_input, mode)
        
        # 调用 LLM 进行扩展
        response = await self.llm_client.generate(
            prompt=enhance_prompt,
            task_type="prompt_enhance",
            llm=self.enhancer_llm,
            temperature=0.7
        )
        
        # 解析 LLM 响应
        enhanced = self._parse_response(response.content, user_input)
        
        logger.info(f"Enhancement complete. Style: {enhanced.style}, "
                    f"Theme: {enhanced.theme}, Confidence: {enhanced.confidence}")
        
        return enhanced
    
    def _build_enhance_prompt(self, user_input: str, mode: str) -> str:
        """构建增强用的提示词"""
        return f'''你是一位专业的小说策划专家。请根据用户的简单描述，扩展为完整的小说创作配置。

## 用户描述
{user_input}

## 写作模式
{mode}

## 你的任务
分析用户描述，推断并补充以下信息。如果用户没有明确说明，请根据描述合理推断。

请以 JSON 格式输出，包含以下字段：

```json
{{
  "style": "风格类型（玄幻/武侠/都市/科幻/言情等）",
  "theme": "核心主题（一句话概括）",
  "target_words": 目标字数（数字），
  "chapter_count": 章节数量（数字），
  
  "protagonist": {{
    "name": "主角姓名（可以为空，后续生成）",
    "gender": "性别",
    "age": "年龄范围",
    "personality": "性格特点",
    "background": "背景设定",
    "growth_arc": "成长弧线"
  }},
  
  "world_setting": {{
    "type": "世界类型",
    "era": "时代背景",
    "power_system": "力量体系（如修炼、魔法等）",
    "key_locations": ["关键地点1", "关键地点2"],
    "factions": ["势力1", "势力2"]
  }},
  
  "plot_elements": [
    "核心情节要素1",
    "核心情节要素2",
    "核心情节要素3"
  ],
  
  "style_elements": {{
    "tone": "整体基调（热血/轻松/沉重等）",
    "pacing": "节奏风格",
    "description_style": "描写风格",
    "dialogue_style": "对话风格"
  }},
  
  "constraints": [
    "创作约束1",
    "创作约束2"
  ],
  
  "special_requirements": [
    "用户特殊要求（从描述中提取）"
  ],
  
  "confidence": 0.0到1.0之间的数字，表示你对这个扩展的信心
}}
```

## 注意事项
1. 如果用户描述很简单，尽量合理推断补充
2. 保持与用户描述的一致性，不要偏离核心意图
3. confidence 字段：如果用户描述详细则接近1.0，如果需要大量推断则较低
4. 只输出 JSON，不要有其他文字
'''
    
    def _parse_response(
        self,
        response: str,
        raw_input: str
    ) -> EnhancedPrompt:
        """解析 LLM 响应"""
        import json
        
        # 提取 JSON
        try:
            # 尝试直接解析
            data = json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                raise ValueError("Failed to parse LLM response as JSON")
        
        return EnhancedPrompt(
            style=data.get("style", "玄幻"),
            theme=data.get("theme", ""),
            target_words=data.get("target_words", 100000),
            chapter_count=data.get("chapter_count", 50),
            protagonist=data.get("protagonist", {}),
            world_setting=data.get("world_setting", {}),
            plot_elements=data.get("plot_elements", []),
            style_elements=data.get("style_elements", {}),
            constraints=data.get("constraints", []),
            special_requirements=data.get("special_requirements", []),
            raw_input=raw_input,
            confidence=data.get("confidence", 0.5)
        )
    
    async def refine(
        self,
        enhanced: EnhancedPrompt,
        user_feedback: str
    ) -> EnhancedPrompt:
        """
        根据用户反馈调整配置
        
        Args:
            enhanced: 当前配置
            user_feedback: 用户的调整意见
            
        Returns:
            调整后的配置
        """
        refine_prompt = f'''当前配置：
{enhanced.__dict__}

用户反馈：
{user_feedback}

请根据用户反馈调整配置，输出完整的 JSON。'''
        
        response = await self.llm_client.generate(
            prompt=refine_prompt,
            task_type="prompt_refine",
            llm=self.enhancer_llm,
            temperature=0.5
        )
        
        return self._parse_response(response.content, enhanced.raw_input)
```

### 2.4 使用示例

#### 最简单的使用方式

```python
from creative_autogpt import CreativeAutoGPT

# 初始化
app = CreativeAutoGPT()

# 用户只需一句话！
result = await app.create_novel(
    "写一个玄幻小说，主角是废材逆袭成仙帝，100万字"
)

# 系统自动：
# 1. 识别风格：玄幻修仙
# 2. 识别主题：废材逆袭
# 3. 识别字数：100万
# 4. 自动补充：人物设定、世界观、情节要素...
# 5. 生成完整配置
# 6. 开始创作
```

#### 带确认的使用方式

```python
from creative_autogpt.prompts.enhancer import PromptEnhancer

# 第一步：用户提供简单描述
user_input = "写个都市修仙，主角重生回到高中，要有系统金手指"

# 第二步：系统自动扩展
enhancer = PromptEnhancer(llm_client)
enhanced = await enhancer.enhance(user_input, mode="novel")

# 第三步：展示给用户确认
print("=" * 50)
print("📝 已为您生成以下配置：")
print("=" * 50)
print(f"🎨 风格：{enhanced.style}")
print(f"📖 主题：{enhanced.theme}")
print(f"📊 字数：{enhanced.target_words:,} 字")
print(f"📚 章节：{enhanced.chapter_count} 章")
print(f"\n👤 主角设定：")
print(f"   - 性格：{enhanced.protagonist.get('personality')}")
print(f"   - 背景：{enhanced.protagonist.get('background')}")
print(f"\n🌍 世界观：")
print(f"   - 类型：{enhanced.world_setting.get('type')}")
print(f"   - 力量体系：{enhanced.world_setting.get('power_system')}")
print(f"\n🎭 情节要素：")
for elem in enhanced.plot_elements:
    print(f"   • {elem}")
print(f"\n✨ 置信度：{enhanced.confidence * 100:.0f}%")
print("=" * 50)

# 第四步：用户可以调整
user_feedback = input("请输入调整意见（直接回车表示确认）：")
if user_feedback:
    enhanced = await enhancer.refine(enhanced, user_feedback)

# 第五步：开始创作
session = await app.start_session(config=enhanced.to_config())
```

#### 输出示例

用户输入：
```
"写一个玄幻小说，主角是废材逆袭成仙帝，100万字"
```

系统自动生成的配置：
```
══════════════════════════════════════════════════
📝 已为您生成以下配置：
══════════════════════════════════════════════════
🎨 风格：玄幻修仙
📖 主题：废材少年逆袭成为仙帝的热血成长故事
📊 字数：1,000,000 字
📚 章节：500 章

👤 主角设定：
   - 性格：坚韧不拔、心思缜密、重情重义
   - 背景：曾被视为废材的宗门弟子，意外获得机缘
   - 成长弧线：从被人嘲笑的废材到一步步证道成仙

🌍 世界观：
   - 类型：仙侠世界
   - 力量体系：炼气→筑基→金丹→元婴→化神→渡劫→大乘→仙帝
   - 关键地点：宗门、秘境、仙界

🎭 情节要素：
   • 废材逆袭
   • 奇遇机缘
   • 宗门斗争
   • 感情线
   • 最终证道

✨ 置信度：85%
══════════════════════════════════════════════════
```

### 2.5 置信度处理

根据 `confidence` 值决定是否需要用户确认：

```python
async def smart_create(user_input: str):
    """智能创建，根据置信度决定是否需要确认"""
    
    enhanced = await enhancer.enhance(user_input)
    
    if enhanced.confidence >= 0.8:
        # 高置信度：直接开始
        print("✅ 配置清晰，直接开始创作...")
        return await start_session(enhanced)
    
    elif enhanced.confidence >= 0.5:
        # 中等置信度：展示配置，快速确认
        print("📋 请确认以下配置：")
        show_summary(enhanced)
        if confirm("是否确认？(Y/n)"):
            return await start_session(enhanced)
        else:
            return await interactive_refine(enhanced)
    
    else:
        # 低置信度：需要更多信息
        print("❓ 需要更多信息来完善配置：")
        return await ask_clarifying_questions(enhanced)
```

### 2.6 Web UI 集成

```
┌─────────────────────────────────────────────────────────────────────┐
│                    新建项目                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  描述你想写的小说：                                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 写一个玄幻小说，主角是废材逆袭成仙帝，100万字                  │   │
│  │                                                               │   │
│  │                                                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  💡 提示：用简单的话描述即可，系统会自动扩展为完整配置               │
│                                                                      │
│                              [🚀 智能生成配置]                       │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ✨ 为您生成的配置（可编辑）：                                        │
│                                                                      │
│  风格：[玄幻修仙    ▼]    字数：[1000000] 字    章节：[500] 章       │
│                                                                      │
│  主题：[废材少年逆袭成为仙帝的热血成长故事________________]          │
│                                                                      │
│  ▼ 高级设置（点击展开）                                              │
│                                                                      │
│                    [📝 手动模式]  [✅ 确认开始创作]                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.7 为什么使用 DeepSeek？

**成本分析**：

| 模型 | 单次扩展成本 | 说明 |
|------|-------------|------|
| Qwen | ~￥0.05 | 价格适中 |
| **DeepSeek** | **~￥0.001** | **极低成本** ⭐ |
| Doubao | ~￥0.02 | 中等 |

使用 DeepSeek 进行提示词扩展的原因：
1. **成本极低**：一次扩展不到 1 分钱
2. **逻辑能力强**：结构化输出准确
3. **响应快**：提示词扩展不需要长上下文

### 2.8 配置选项

```yaml
# config/prompt_enhancer.yaml

prompt_enhancer:
  enabled: true                    # 是否启用智能扩展
  llm: deepseek                    # 使用的 LLM
  
  auto_confirm_threshold: 0.8      # 高于此值自动确认
  require_confirm_threshold: 0.5   # 高于此值快速确认，低于需详细交互
  
  temperature: 0.7                 # 创造性参数
  max_retries: 2                   # 解析失败重试次数
  
  # 默认值（当用户未指定时）
  defaults:
    target_words: 100000
    chapter_count: 50
    words_per_chapter: 2000
```

---

## 3. 实时预览与聊天反馈系统 🆕

> 🌟 **核心理念**：每一步都让用户看见、每一步都可以调整！

### 3.1 设计目标

1. **实时预览**：每个任务执行完成后，立即展示结果给用户
2. **聊天窗口**：用户可以随时通过自然语言提意见
3. **智能转换**：用户意见自动转换为专业提示词
4. **作用域隔离**：修改只影响当前任务，不影响其他任务

### 3.2 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         实时交互执行系统                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      任务执行流水线                                  │   │
│   │                                                                      │   │
│   │   Task 1        Task 2        Task 3        Task 4                  │   │
│   │   大纲生成  ──▶  人物设计  ──▶  事件规划  ──▶  章节撰写             │   │
│   │      │             │             │             │                    │   │
│   │      ▼             ▼             ▼             ▼                    │   │
│   │   ┌─────┐      ┌─────┐      ┌─────┐      ┌─────┐                   │   │
│   │   │预览 │      │预览 │      │预览 │      │预览 │  ← 每步都预览     │   │
│   │   └──┬──┘      └──┬──┘      └──┬──┘      └──┬──┘                   │   │
│   │      │             │             │             │                    │   │
│   │      ▼             ▼             ▼             ▼                    │   │
│   │   ┌─────┐      ┌─────┐      ┌─────┐      ┌─────┐                   │   │
│   │   │确认/ │      │确认/ │      │确认/ │      │确认/ │  ← 可单独调整   │   │
│   │   │调整  │      │调整  │      │调整  │      │调整  │                 │   │
│   │   └─────┘      └─────┘      └─────┘      └─────┘                   │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                     ▲                                        │
│                                     │                                        │
│   ┌─────────────────────────────────┼───────────────────────────────────┐   │
│   │                          聊天反馈窗口                                │   │
│   │                                 │                                    │   │
│   │    用户输入："这个主角性格太软了，要更霸气一点"                       │   │
│   │                                 │                                    │   │
│   │                                 ▼                                    │   │
│   │    ┌─────────────────────────────────────────────────────────────┐  │   │
│   │    │              FeedbackTransformer (意见转换器)               │  │   │
│   │    │                                                             │  │   │
│   │    │  输入: 用户自然语言                                         │  │   │
│   │    │  输出: 结构化修改指令 + 专业提示词补丁                       │  │   │
│   │    │                                                             │  │   │
│   │    │  转换结果:                                                  │  │   │
│   │    │  {                                                          │  │   │
│   │    │    "target": "character.protagonist.personality",           │  │   │
│   │    │    "action": "modify",                                      │  │   │
│   │    │    "prompt_patch": "主角性格调整为：霸气侧漏、睥睨天下...",  │  │   │
│   │    │    "scope": "current_task_only"  ← 只影响当前任务           │  │   │
│   │    │  }                                                          │  │   │
│   │    └─────────────────────────────────────────────────────────────┘  │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 作用域隔离机制

**核心原则**：用户的修改意见只影响当前任务，不会污染其他任务。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          作用域隔离示意图                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   全局配置 (Global Config)                                                   │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │  style: "玄幻"  |  protagonist: {...}  |  world: {...}               │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│          ┌──────────────────┼──────────────────┐                            │
│          ▼                  ▼                  ▼                            │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                      │
│   │  Task 1     │   │  Task 2     │   │  Task 3     │                      │
│   │  大纲生成    │   │  人物设计   │   │  事件规划    │                      │
│   │             │   │             │   │             │                      │
│   │ 用户反馈:   │   │ 用户反馈:   │   │ 用户反馈:   │                      │
│   │ "章节太少"  │   │ "主角更霸气" │   │ (无)        │                      │
│   │             │   │             │   │             │                      │
│   │ 本地补丁:   │   │ 本地补丁:   │   │ 本地补丁:   │                      │
│   │ +10章节     │   │ 性格调整    │   │ (空)        │                      │
│   │             │   │             │   │             │                      │
│   │ 最终结果:   │   │ 最终结果:   │   │ 最终结果:   │                      │
│   │ 原配置+补丁 │   │ 原配置+补丁 │   │ 原配置      │  ← Task 3 不受影响   │
│   └─────────────┘   └─────────────┘   └─────────────┘                      │
│                                                                              │
│   ❌ 错误做法: 用户说"主角更霸气"后修改全局配置，导致后续任务都变了           │
│   ✅ 正确做法: 只在 Task 2 的执行上下文中应用补丁，Task 3 使用原始配置        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 核心实现

**文件位置**: `src/creative_autogpt/interaction/feedback_handler.py`

```python
"""
实时反馈处理系统
处理用户在任务执行过程中的实时反馈
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class FeedbackScope(Enum):
    """反馈作用域"""
    CURRENT_TASK = "current_task"      # 只影响当前任务
    CURRENT_AND_FUTURE = "future"      # 影响当前及后续任务
    GLOBAL = "global"                  # 影响全局配置（需用户二次确认）


@dataclass
class FeedbackPatch:
    """反馈转换后的补丁"""
    target: str                        # 目标路径 (如 "character.protagonist.personality")
    action: str                        # 操作类型 (modify/add/remove/regenerate)
    prompt_patch: str                  # 注入到提示词的补丁内容
    scope: FeedbackScope               # 作用域
    original_feedback: str             # 原始用户反馈
    confidence: float                  # 转换置信度


@dataclass
class TaskPreview:
    """任务预览"""
    task_id: str
    task_type: str
    task_name: str
    content: str                       # 生成的内容
    summary: str                       # 内容摘要（方便快速查看）
    key_points: List[str]              # 关键点列表
    word_count: int
    quality_score: float               # 质量评分
    status: str                        # pending_review / approved / needs_revision
    
    # 用户反馈相关
    feedbacks: List[FeedbackPatch] = field(default_factory=list)
    revision_count: int = 0


class FeedbackTransformer:
    """
    反馈转换器
    将用户的自然语言反馈转换为结构化的修改指令
    """
    
    TRANSFORM_PROMPT = '''你是一个专业的小说创作助手。请将用户的反馈意见转换为结构化的修改指令。

## 当前任务信息
任务类型: {task_type}
任务内容摘要: {task_summary}

## 用户反馈
{user_feedback}

## 转换要求
1. 分析用户反馈的核心意图
2. 确定修改目标（哪部分内容需要修改）
3. 生成专业的提示词补丁
4. 判断作用域（是否只影响当前任务）

## 输出格式 (JSON)
```json
{{
  "target": "修改目标路径 (如 character.protagonist.personality)",
  "action": "modify|add|remove|regenerate",
  "prompt_patch": "注入到提示词的专业描述，用于指导 LLM 进行修改",
  "scope": "current_task|future|global",
  "key_changes": ["变化点1", "变化点2"],
  "confidence": 0.0-1.0
}}
```

## 重要规则
1. 默认 scope 为 "current_task"，除非用户明确说"后面都要这样"
2. prompt_patch 要专业、详细、可执行
3. 如果用户反馈模糊，confidence 要低
'''
    
    def __init__(self, llm_client, config: Dict[str, Any] = None):
        self.llm_client = llm_client
        self.config = config or {}
        self.transformer_llm = "deepseek"  # 使用 DeepSeek 进行转换
    
    async def transform(
        self,
        feedback: str,
        task_context: Dict[str, Any]
    ) -> FeedbackPatch:
        """
        将用户反馈转换为结构化补丁
        
        Args:
            feedback: 用户的自然语言反馈
            task_context: 当前任务上下文
            
        Returns:
            FeedbackPatch: 结构化的修改补丁
        """
        logger.info(f"🔄 Transforming feedback: {feedback[:50]}...")
        
        prompt = self.TRANSFORM_PROMPT.format(
            task_type=task_context.get("task_type", "unknown"),
            task_summary=task_context.get("summary", ""),
            user_feedback=feedback
        )
        
        response = await self.llm_client.generate(
            prompt=prompt,
            task_type="feedback_transform",
            llm=self.transformer_llm,
            temperature=0.3  # 低温度，保证准确性
        )
        
        patch = self._parse_response(response.content, feedback)
        
        logger.info(
            f"✅ Feedback transformed: target={patch.target}, "
            f"scope={patch.scope.value}, confidence={patch.confidence:.0%}"
        )
        
        return patch
    
    def _parse_response(self, response: str, original: str) -> FeedbackPatch:
        """解析 LLM 响应"""
        import json
        import re
        
        try:
            # 提取 JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(response)
            
            return FeedbackPatch(
                target=data.get("target", "general"),
                action=data.get("action", "modify"),
                prompt_patch=data.get("prompt_patch", ""),
                scope=FeedbackScope(data.get("scope", "current_task")),
                original_feedback=original,
                confidence=data.get("confidence", 0.5)
            )
        except Exception as e:
            logger.warning(f"Failed to parse feedback response: {e}")
            # 返回默认补丁
            return FeedbackPatch(
                target="general",
                action="modify",
                prompt_patch=f"用户要求: {original}",
                scope=FeedbackScope.CURRENT_TASK,
                original_feedback=original,
                confidence=0.3
            )


class TaskPreviewManager:
    """
    任务预览管理器
    管理每个任务的预览、反馈和状态
    """
    
    def __init__(self, llm_client, config: Dict[str, Any] = None):
        self.llm_client = llm_client
        self.config = config or {}
        self.transformer = FeedbackTransformer(llm_client)
        
        # 任务预览缓存
        self.previews: Dict[str, TaskPreview] = {}
    
    async def create_preview(
        self,
        task_id: str,
        task_type: str,
        task_name: str,
        content: str,
        quality_score: float = 0.0
    ) -> TaskPreview:
        """
        为任务创建预览
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            task_name: 任务名称
            content: 生成的内容
            quality_score: 质量评分
            
        Returns:
            TaskPreview: 任务预览对象
        """
        # 生成摘要和关键点
        summary, key_points = await self._generate_summary(content, task_type)
        
        preview = TaskPreview(
            task_id=task_id,
            task_type=task_type,
            task_name=task_name,
            content=content,
            summary=summary,
            key_points=key_points,
            word_count=len(content),
            quality_score=quality_score,
            status="pending_review"
        )
        
        self.previews[task_id] = preview
        
        logger.info(f"📋 Preview created for task {task_id}: {summary[:50]}...")
        
        return preview
    
    async def _generate_summary(
        self,
        content: str,
        task_type: str
    ) -> tuple[str, List[str]]:
        """生成内容摘要和关键点"""
        
        prompt = f'''请为以下{task_type}内容生成简洁摘要和关键点。

内容:
{content[:2000]}  # 限制长度

请输出:
1. 一句话摘要（50字以内）
2. 3-5个关键点

格式:
摘要: ...
关键点:
- ...
- ...
'''
        
        response = await self.llm_client.generate(
            prompt=prompt,
            task_type="summarize",
            llm="deepseek",
            temperature=0.3
        )
        
        # 简单解析
        lines = response.content.strip().split('\n')
        summary = ""
        key_points = []
        
        for line in lines:
            if line.startswith("摘要:"):
                summary = line.replace("摘要:", "").strip()
            elif line.startswith("- "):
                key_points.append(line[2:].strip())
        
        return summary or content[:50] + "...", key_points or ["内容已生成"]
    
    async def add_feedback(
        self,
        task_id: str,
        feedback: str
    ) -> FeedbackPatch:
        """
        添加用户反馈
        
        Args:
            task_id: 任务ID
            feedback: 用户反馈
            
        Returns:
            FeedbackPatch: 转换后的补丁
        """
        preview = self.previews.get(task_id)
        if not preview:
            raise ValueError(f"Task {task_id} not found")
        
        # 转换反馈为补丁
        patch = await self.transformer.transform(
            feedback=feedback,
            task_context={
                "task_type": preview.task_type,
                "summary": preview.summary,
                "content": preview.content[:1000]
            }
        )
        
        # 添加到预览
        preview.feedbacks.append(patch)
        preview.status = "needs_revision"
        
        return patch
    
    def approve_preview(self, task_id: str) -> bool:
        """用户确认预览"""
        preview = self.previews.get(task_id)
        if preview:
            preview.status = "approved"
            return True
        return False
    
    def get_pending_patches(self, task_id: str) -> List[FeedbackPatch]:
        """获取待应用的补丁"""
        preview = self.previews.get(task_id)
        if preview:
            return [p for p in preview.feedbacks if p.scope == FeedbackScope.CURRENT_TASK]
        return []
```

### 3.5 执行引擎集成

修改 `LoopEngine` 以支持实时预览和反馈：

```python
class InteractiveLoopEngine(LoopEngine):
    """
    支持实时交互的执行引擎
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preview_manager = TaskPreviewManager(self.llm_client)
        self.interaction_mode = kwargs.get("interaction_mode", "preview_each")
        # interaction_mode: 
        #   - "preview_each": 每步都预览
        #   - "preview_key": 只预览关键步骤
        #   - "auto": 自动执行，出问题才暂停
    
    async def _execute_task_with_preview(self, task: Dict[str, Any]) -> Any:
        """
        执行任务并生成预览
        """
        task_id = task["task_id"]
        
        # 1. 检查是否有待应用的补丁（来自之前的反馈）
        patches = self.preview_manager.get_pending_patches(task_id)
        
        # 2. 构建 Prompt（应用补丁）
        prompt = await self.mode.build_prompt(task, self.memory)
        if patches:
            prompt = self._apply_patches_to_prompt(prompt, patches)
        
        # 3. 执行 LLM 生成
        result = await self.llm_client.generate(
            prompt=prompt,
            task_type=task["task_type"],
            llm=self._route_to_llm(task["task_type"])
        )
        
        # 4. 评估质量
        evaluation = await self.evaluator.evaluate(
            task_type=task["task_type"],
            content=result.content
        )
        
        # 5. 创建预览
        preview = await self.preview_manager.create_preview(
            task_id=task_id,
            task_type=task["task_type"],
            task_name=task.get("name", task["task_type"]),
            content=result.content,
            quality_score=evaluation.score
        )
        
        # 6. 推送预览到前端（WebSocket）
        await self._push_preview_to_frontend(preview)
        
        # 7. 等待用户确认（如果是预览模式）
        if self.interaction_mode == "preview_each":
            await self._wait_for_user_confirmation(task_id)
        
        # 8. 检查是否需要重写（用户反馈后）
        preview = self.preview_manager.previews[task_id]
        if preview.status == "needs_revision":
            result = await self._revise_with_feedback(task, result, preview.feedbacks)
        
        return result
    
    def _apply_patches_to_prompt(
        self,
        prompt: str,
        patches: List[FeedbackPatch]
    ) -> str:
        """
        将补丁应用到提示词
        
        关键：只应用 scope=CURRENT_TASK 的补丁
        """
        if not patches:
            return prompt
        
        patch_section = "\n\n## 用户特别要求（仅本次任务生效）\n"
        for patch in patches:
            patch_section += f"- {patch.prompt_patch}\n"
        
        # 在提示词末尾添加补丁
        return prompt + patch_section
    
    async def _revise_with_feedback(
        self,
        task: Dict[str, Any],
        original_result: Any,
        feedbacks: List[FeedbackPatch]
    ) -> Any:
        """
        根据用户反馈修订内容
        """
        revision_prompt = f'''请根据以下反馈修改内容。

## 原始内容
{original_result.content}

## 用户反馈
{chr(10).join([f"- {f.prompt_patch}" for f in feedbacks])}

## 要求
1. 保持原有内容的整体结构
2. 只修改用户提到的部分
3. 确保修改后内容连贯
'''
        
        result = await self.llm_client.generate(
            prompt=revision_prompt,
            task_type=f"{task['task_type']}_revision",
            llm=self._route_to_llm(task["task_type"]),
            temperature=0.7
        )
        
        return result
```

### 3.6 Web UI 设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Creative AutoGPT - 实时创作                                       [_][□][×]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │        任务进度                  │  │          内容预览                 │ │
│  │                                  │  │                                  │ │
│  │  ✅ 1. 大纲生成    [已确认]     │  │  📖 第一章：废材少年              │ │
│  │  ✅ 2. 人物设计    [已确认]     │  │  ──────────────────────────────  │ │
│  │  🔄 3. 事件规划    [预览中] ◀── │  │                                  │ │
│  │  ⏳ 4. 第一章      [等待中]     │  │  林轩站在宗门演武场中央，周围     │ │
│  │  ⏳ 5. 第二章      [等待中]     │  │  是无数嘲讽的目光。他紧握双拳，   │ │
│  │                                  │  │  心中暗暗发誓...                 │ │
│  │  总进度: ████████░░ 40%         │  │                                  │ │
│  │                                  │  │  【摘要】主角林轩在宗门受辱，    │ │
│  └─────────────────────────────────┘  │  获得神秘传承，开始逆袭之路。    │ │
│                                        │                                  │ │
│  ┌─────────────────────────────────┐  │  【关键点】                       │ │
│  │     💬 聊天反馈窗口              │  │  • 主角被嘲笑为废材              │ │
│  │  ─────────────────────────────  │  │  • 获得神秘老者传承              │ │
│  │                                  │  │  • 隐藏实力，蛰伏等待            │ │
│  │  🤖 请查看当前生成的内容，       │  │                                  │ │
│  │     有什么需要调整的吗？         │  │  质量评分: ⭐⭐⭐⭐ 4.2/5        │ │
│  │                                  │  │                                  │ │
│  │  👤 主角的反应太软弱了，         │  └──────────────────────────────────┘ │
│  │     我想要他更霸气一点，         │                                       │
│  │     即使被嘲笑也要冷笑回去       │  ┌──────────────────────────────────┐ │
│  │                                  │  │        操作按钮                   │ │
│  │  🤖 收到！我会调整主角的性格     │  │                                  │ │
│  │     表现，让他更霸气。这个修改   │  │  [✅ 确认通过]  [🔄 重新生成]    │ │
│  │     只会影响当前的事件规划，     │  │                                  │ │
│  │     不会影响之前和之后的内容。   │  │  [⏭️ 跳过此步]  [⏸️ 暂停执行]    │ │
│  │                                  │  │                                  │ │
│  │  ┌────────────────────────────┐ │  └──────────────────────────────────┘ │
│  │  │ 输入你的反馈或建议...      │ │                                       │
│  │  └────────────────────────────┘ │                                       │
│  │                        [发送 ↵] │                                       │
│  └─────────────────────────────────┘                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.7 作用域选择交互

当用户的反馈可能影响多个任务时，系统会询问：

```
┌─────────────────────────────────────────────────────────────────────┐
│                     🎯 作用域确认                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  您的反馈: "主角性格要更霸气"                                        │
│                                                                      │
│  这个修改应该影响哪些内容？                                          │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ○ 只影响当前任务（事件规划）                                  │   │
│  │   → 只修改当前正在预览的内容                                 │   │
│  │                                                              │   │
│  │ ○ 影响当前和后续任务                                         │   │
│  │   → 当前任务和之后的章节都会应用这个修改                     │   │
│  │                                                              │   │
│  │ ○ 修改全局设定                                               │   │
│  │   → 更新主角的基础人设，影响整个项目                        │   │
│  │   ⚠️ 这可能导致已完成的内容与新设定不一致                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│                              [确认选择]  [取消]                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.8 配置选项

```yaml
# config/interaction.yaml

interaction:
  # 预览模式
  preview_mode: "preview_each"    # preview_each / preview_key / auto
  
  # 需要预览的任务类型（preview_key 模式下生效）
  key_tasks:
    - outline
    - character_design
    - chapter_content
  
  # 聊天反馈
  feedback:
    enabled: true
    transformer_llm: deepseek     # 用于转换的 LLM
    
    # 默认作用域
    default_scope: current_task   # current_task / future / global
    
    # 是否询问作用域
    ask_scope: true               # 当可能影响多个任务时询问
    ask_scope_threshold: 0.6      # 置信度低于此值时询问
  
  # 预览超时
  preview_timeout: 300            # 5分钟无响应自动通过
  auto_approve_on_timeout: true   # 超时后自动通过还是暂停
  
  # 质量门槛
  quality_threshold: 3.5          # 低于此分数强制预览
```

---

## 4. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                   Prompt Manager                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Prompt 构建流程                           │ │
│  │                                                        │ │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐             │ │
│  │  │PromptEn-│   │ 模板    │   │ 上下文  │             │ │
│  │  │ hancer  │──▶│ Template│──▶│ Context │             │ │
│  │  │(智能扩展)│   └─────────┘   └─────────┘             │ │
│  │  └─────────┘        │             │                   │ │
│  │       │             │             │                   │ │
│  │       │             ▼             ▼                   │ │
│  │       │       ┌─────────┐   ┌─────────┐              │ │
│  │       └──────▶│ 风格    │──▶│ 最终    │              │ │
│  │               │ Style   │   │ Prompt  │              │ │
│  │               └─────────┘   └─────────┘              │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 提示词模板

### 5.1 模板结构
│   └── scifi.yaml         # 科幻风格
└── examples/              # 示例库
    └── chapter_examples.yaml
```

---

### 3.2 系统提示词

**prompts/base/system.txt**

```text
你是一位经验丰富的专业小说作家，精通各种文学体裁和写作技巧。

你的核心能力：
1. 创作能力：能够创作引人入胜的故事情节
2. 文学素养：文笔优美，善于运用修辞手法
3. 结构把控：擅长规划故事结构和节奏
4. 人物塑造：能够塑造立体生动的人物形象
5. 一致性维护：确保故事前后逻辑一致

你的工作原则：
- 严格遵循用户提供的风格要求
- 保持世界观、人物设定的一致性
- 输出内容必须原创，避免套路化
- 注重细节描写，让场景更加真实
- 控制输出长度，符合字数要求
```

---

### 3.3 任务模板示例

#### 大纲生成模板

**prompts/tasks/outline.jinja2**

```jinja2
# 任务：生成小说大纲

## 基本信息
- 风格：{{ style }}
- 主题：{{ theme }}
- 目标字数：{{ target_words }}
- 章节数：{{ chapter_count }}

{% if additional_requirements %}
## 额外要求
{{ additional_requirements }}
{% endif %}

## 大纲要求

请创作一个 {{ style }} 风格的小说大纲，遵循以下结构：

### 1. 故事概要（100-200字）
简述整个故事的核心情节和主题思想。

### 2. 分卷规划（{{ chapter_count }} 章分为 3-5 卷）
- 第一卷：起始（章节范围、主要情节、字数占比）
- 第二卷：发展（章节范围、主要情节、字数占比）
- 第三卷：高潮（章节范围、主要情节、字数占比）
- 第N卷：结局（章节范围、主要情节、字数占比）

### 3. 主要情节线（3-5条）
- 主线：[情节描述]
- 支线1：[情节描述]
- 支线2：[情节描述]

### 4. 关键转折点（5-10个）
列出故事中的重要转折，标注出现章节。

### 5. 伏笔设置
规划需要埋设的伏笔及其回收时机。

## 风格要求
{{ style_elements | safe }}

## 注意事项
1. 情节要有起承转合，张弛有度
2. 伏笔要合理埋设，后续回收
3. 避免常见套路，追求创新
4. 确保逻辑自洽，前后一致
5. 控制节奏，避免拖沓或仓促

请输出符合以上要求的完整大纲。
```

---

#### 章节生成模板

**prompts/tasks/chapter.jinja2**

```jinja2
# 任务：生成第 {{ chapter_number }} 章内容

## 章节信息
- 章节标题：{{ chapter_title }}
- 目标字数：{{ target_words }} 字
- 风格：{{ style }}

## 情节要点
{{ plot_points }}

## 涉及人物
{% for character in characters %}
- {{ character.name }}：{{ character.role }}
  - 性格：{{ character.personality }}
  - 当前状态：{{ character.current_state }}
{% endfor %}

## 前情提要
{{ previous_summary }}

## 上下文记忆
{% if relevant_context %}
### 相关设定
{{ relevant_context.settings }}

### 相关伏笔
{{ relevant_context.foreshadows }}

### 相关事件
{{ relevant_context.events }}
{% endif %}

## 创作要求

### 1. 内容要求
- 严格围绕情节要点展开
- 保持人物性格一致
- 自然衔接前后章节
- 推进主要情节线

### 2. 文笔要求
{{ style_elements.writing_style }}

### 3. 结构要求
- 开头：自然引入，吸引读者（{{ (target_words * 0.1) | int }} 字左右）
- 发展：情节推进，冲突展开（{{ (target_words * 0.6) | int }} 字左右）
- 高潮：情节高潮，情绪饱满（{{ (target_words * 0.2) | int }} 字左右）
- 结尾：留下悬念或铺垫（{{ (target_words * 0.1) | int }} 字左右）

### 4. 细节要求
- 环境描写：{{ style_elements.environment_description }}
- 人物描写：{{ style_elements.character_description }}
- 对话风格：{{ style_elements.dialogue_style }}
- 心理描写：{{ style_elements.psychological_description }}

## 禁止事项
- ❌ 不要出现与已有设定冲突的内容
- ❌ 不要使用现代网络用语（除非是现代题材）
- ❌ 不要突然改变人物性格
- ❌ 不要重复之前章节的描写
- ❌ 不要超出或严重不足目标字数（允许±10%）

请开始创作第 {{ chapter_number }} 章的完整内容。
```

---

## 4. 风格系统

### 4.1 风格配置文件

**prompts/styles/xuanhuan.yaml**

```yaml
# 玄幻风格配置

style_name: 玄幻修仙
category: fantasy

# 核心元素
core_elements:
  - 修炼体系
  - 境界划分
  - 法宝丹药
  - 宗门势力
  - 天地灵气

# 文笔风格
writing_style: |
  文笔要求：
  - 恢弘大气，展现修仙世界的磅礴
  - 善用古典意象，如"紫气东来"、"仙鹤白云"
  - 战斗场面要写得酣畅淋漓
  - 修炼场景要有代入感
  - 适当使用文言词汇，但不要过度

# 环境描写
environment_description: |
  - 仙山洞府：云雾缭绕，灵气充沛
  - 修炼圣地：天地异象，法则显化
  - 战斗场景：灵力激荡，虚空震颤
  - 示例：紫气东来三万里，霞光万道照青山

# 人物描写
character_description: |
  - 外貌：仙风道骨，气质超凡
  - 气质：清冷孤傲 / 温文尔雅 / 霸道无双
  - 实力：通过境界、灵力波动体现
  - 示例：白衣胜雪，剑眉星目，周身灵气环绕

# 对话风格
dialogue_style: |
  - 高阶修士：言简意赅，话语间透露威压
  - 普通弟子：恭敬有礼，称呼得当
  - 战斗时：简洁有力，充满杀意或气势
  - 示例：
    * "区区金丹，也敢在本座面前放肆？"
    * "晚辈见过前辈，恳请前辈指点。"

# 心理描写
psychological_description: |
  - 修炼感悟：与天地交融，感悟大道
  - 战斗心理：冷静分析，寻找破绽
  - 情感波动：即使动情也要保持超然
  - 示例：他心神一动，似有所悟，天地间的灵气仿佛在此刻变得格外清晰

# 常用词汇
vocabulary:
  realms:        # 境界
    - 炼气
    - 筑基
    - 金丹
    - 元婴
    - 化神
    - 合体
    - 渡劫
    - 大乘
    
  skills:        # 功法术法
    - 剑诀
    - 遁术
    - 神通
    - 秘法
    - 禁术
    
  items:         # 物品
    - 灵石
    - 丹药
    - 法宝
    - 符箓
    - 阵法
    
  places:        # 地点
    - 洞府
    - 秘境
    - 遗迹
    - 仙府
    - 灵脉

# 情节模式
plot_patterns:
  opening:
    - 废材逆袭
    - 奇遇崛起
    - 宗门试炼
    
  conflict:
    - 宗门之争
    - 争夺宝物
    - 仇人寻仇
    - 正邪对抗
    
  climax:
    - 突破境界
    - 生死对决
    - 机缘造化
    
# 禁止内容
forbidden:
  - 现代化用语（手机、电脑等）
  - 科技元素（除非是修真科技）
  - 过度白话的对话
  - 违背世界观的内容
```

---

### 4.2 使用风格

```python
from creative_autogpt.prompts.style_manager import StyleManager

# 加载风格
style_mgr = StyleManager()
xuanhuan_style = style_mgr.load_style("xuanhuan")

# 应用风格
prompt = template.render(
    style_elements=xuanhuan_style,
    chapter_number=1,
    ...
)
```

---

## 5. 上下文管理

### 5.1 上下文检索

```python
from creative_autogpt.core.vector_memory import VectorMemoryManager

memory = VectorMemoryManager()

# 检索相关上下文
relevant_context = memory.retrieve(
    query=f"第{chapter_number}章相关内容",
    filters={
        "task_type": ["character", "event", "setting"],
        "relevance": "high"
    },
    top_k=10
)

# 构建上下文字符串
context_str = "\n\n".join([
    f"### {ctx.type}\n{ctx.content}"
    for ctx in relevant_context
])
```

---

### 5.2 动态上下文窗口

```python
from creative_autogpt.prompts.context_manager import ContextWindowManager

ctx_mgr = ContextWindowManager(
    max_tokens=8000,        # 最大上下文长度
    priority_order=[        # 优先级
        "current_chapter",
        "main_characters",
        "recent_events",
        "world_settings",
        "foreshadows"
    ]
)

# 智能裁剪上下文
optimized_context = ctx_mgr.optimize(
    all_contexts=all_available_contexts,
    task_type="chapter",
    llm="qwen"              # 根据模型调整
)
```

---

## 6. Few-Shot 示例

### 6.1 示例库

**prompts/examples/chapter_examples.yaml**

```yaml
# 章节示例库

examples:
  - style: 玄幻
    scene: 突破境界
    input: |
      李逍遥即将突破金丹期，在洞府中闭关修炼。
    output: |
      洞府之中，李逍遥盘膝而坐，周身灵气如同潮水般涌动。
      
      三年苦修，今朝终于到了突破的关键时刻。他深吸一口气，
      引导体内真元按照《玄天心法》的路线运转。
      
      丹田之中，金色的真元如同旋涡般急速旋转，渐渐凝聚成
      一颗金色的圆珠。这便是传说中的金丹！
      
      "凝！"
      
      李逍遥轻喝一声，所有真元瞬间收缩，金丹的雏形骤然凝实。
      与此同时，天地灵气疯狂涌入，洞府上空乌云密布，雷劫将至！
      
  - style: 玄幻
    scene: 战斗场景
    input: |
      李逍遥与敌人在山谷中激战。
    output: |
      "剑来！"
      
      随着李逍遥一声轻喝，飞剑化作一道流光刺向对手。
      
      敌人冷笑一声，单手结印："雕虫小技！"一道火墙凭空
      出现，挡住了飞剑的去路。
      
      然而李逍遥嘴角微扬，这一剑不过是虚招。真正的杀招
      是藏在暗处的第二剑！
      
      "爆！"
      
      火墙之后，一道更加凌厉的剑气破空而出，直取敌人要害。
      对方脸色大变，仓促之间只来得及侧身避让......
```

---

### 6.2 使用示例

```python
from creative_autogpt.prompts.few_shot import FewShotManager

# 加载示例
few_shot = FewShotManager()

# 获取相关示例
examples = few_shot.get_examples(
    style="玄幻",
    scene_type="突破境界",
    count=2
)

# 添加到 Prompt
prompt = f"""
参考以下优秀示例：

{examples}

现在请创作...
"""
```

---

## 7. 约束与质量控制

### 7.1 通用约束

**prompts/base/constraints.txt**

```text
# 通用约束条件

## 格式约束
1. 不要输出任何解释性文字，直接输出内容
2. 不要添加"以下是..."、"根据要求..."等前缀
3. 不要在结尾添加总结或评论

## 内容约束
1. 严格遵守字数要求（允许±10%浮动）
2. 不得出现与已有设定冲突的内容
3. 保持人物性格、能力的一致性
4. 确保时间线逻辑合理

## 质量约束
1. 避免过度使用重复词汇和句式
2. 场景描写要具体生动，避免空洞
3. 对话要符合人物身份和性格
4. 情节推进要自然流畅

## 创新约束
1. 避免常见网文套路
2. 人物刻画要立体，避免脸谱化
3. 情节要有新意，避免老套
```

---

### 7.2 动态约束

```python
# 根据任务动态添加约束
def build_constraints(task_type, context):
    constraints = load_base_constraints()
    
    if task_type == "chapter":
        # 章节特殊约束
        if context.get("has_battle"):
            constraints.append("战斗场面要详细描写，不要一笔带过")
        
        if context.get("is_plot_critical"):
            constraints.append("这是关键情节章节，必须重点刻画")
    
    return "\n".join(constraints)
```

---

## 8. 提示词优化技巧

### 8.1 明确性原则

❌ **模糊**
```text
写一个玄幻小说的开头。
```

✅ **明确**
```text
创作一个玄幻修仙小说的第一章：
- 主角：16岁少年，天赋平凡
- 情节：意外获得传承玉佩
- 字数：3000字
- 风格：轻松诙谐，不要过于严肃
```

---

### 8.2 结构化原则

❌ **无结构**
```text
写一个人物，包括名字、性格、背景、能力等信息。
```

✅ **结构化**
```text
请按以下格式设计人物：

## 基本信息
- 姓名：
- 年龄：
- 性别：

## 性格特点
- 核心性格：
- 行为习惯：

## 背景故事
- 出身：
- 经历：

## 能力设定
- 主要能力：
- 当前境界：
```

---

### 8.3 示例引导

```text
请参考以下示例的写作风格：

【示例】
夕阳西下，余晖洒在青石板路上，给古朴的小镇披上了一层金色的纱衣。
李逍遥背着药篓，哼着小曲，悠然走在回家的路上。

【要求】
请用类似的风格，描写主角清晨出门的场景。
```

---

## 9. 调试与优化

### 9.1 查看最终 Prompt

```python
from creative_autogpt.prompts.manager import PromptManager

prompt_mgr = PromptManager()

# 生成 Prompt
final_prompt = prompt_mgr.build_prompt(
    task_type="chapter",
    context={...},
    debug=True      # 开启调试模式
)

# 打印查看
print("=" * 80)
print("最终 Prompt:")
print("=" * 80)
print(final_prompt)
print("=" * 80)
print(f"Token 数: {count_tokens(final_prompt)}")
```

---

### 9.2 A/B 测试

```python
# 测试不同的 Prompt 版本
results = []

for prompt_version in ["v1", "v2", "v3"]:
    result = await llm_client.generate(
        prompt=load_prompt(version=prompt_version),
        task_type="chapter"
    )
    
    evaluation = evaluate_result(result)
    results.append({
        "version": prompt_version,
        "score": evaluation.score,
        "quality": evaluation.quality
    })

# 选择最佳版本
best = max(results, key=lambda x: x["score"])
print(f"最佳版本: {best['version']}, 评分: {best['score']}")
```

---

### 9.3 Token 优化

```python
from creative_autogpt.prompts.optimizer import PromptOptimizer

optimizer = PromptOptimizer()

# 压缩 Prompt（保持语义）
optimized_prompt = optimizer.compress(
    original_prompt=long_prompt,
    target_tokens=4000,
    strategy="smart"    # smart: 智能压缩, truncate: 截断
)

print(f"原始: {len(long_prompt)} tokens")
print(f"压缩后: {len(optimized_prompt)} tokens")
print(f"压缩率: {(1 - len(optimized_prompt)/len(long_prompt))*100:.1f}%")
```

---

## 10. 最佳实践

### 10.1 模板设计

✅ **DO**
- 使用 Jinja2 模板，支持条件和循环
- 分层组织（基础层、任务层、风格层）
- 提供默认值，处理缺失参数
- 添加注释说明每个部分的作用

❌ **DON'T**
- 硬编码所有内容
- 将所有逻辑放在一个大模板里
- 忽略参数验证
- 缺少示例和说明

---

### 10.2 上下文管理

✅ **DO**
- 根据任务类型选择性加载上下文
- 使用向量检索获取最相关内容
- 动态调整上下文长度
- 优先加载关键信息

❌ **DON'T**
- 盲目加载所有上下文
- 忽略 token 限制
- 加载无关信息
- 上下文过时不更新

---

### 10.3 风格一致性

✅ **DO**
- 使用配置文件统一管理风格
- 每个任务都注入相同的风格元素
- 提供风格示例供 LLM 参考
- 定期检查风格一致性

❌ **DON'T**
- 每次手动描述风格要求
- 不同任务使用不同风格定义
- 忽略风格验证
- 风格描述过于模糊

---

## 11. 参考资源

- [核心模块文档](../architecture/CORE_MODULES.md)
- [多 LLM 使用指南](./MULTI_LLM_GUIDE.md)
- [提示词工程最佳实践](https://platform.openai.com/docs/guides/prompt-engineering)

---

*版本: 1.0*  
*最后更新: 2026-01-23*
