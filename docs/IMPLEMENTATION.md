# 技术实现文档

> Creative AutoGPT 详细技术实现规范

## 1. 代码结构

### 1.1 项目目录结构

```
creative_autogpt/
├── src/
│   └── creative_autogpt/
│       ├── __init__.py
│       ├── core/                    # 核心模块
│       │   ├── __init__.py
│       │   ├── loop_engine.py       # 执行引擎
│       │   ├── task_planner.py      # 任务规划
│       │   ├── evaluator.py         # 质量评估
│       │   └── vector_memory.py     # 向量记忆
│       ├── modes/                   # 写作模式
│       │   ├── __init__.py
│       │   ├── base.py              # 基础模式
│       │   ├── novel.py             # 小说模式
│       │   ├── script.py            # 剧本模式
│       │   └── larp.py              # 剧本杀模式
│       ├── plugins/                 # 插件系统
│       │   ├── __init__.py
│       │   ├── base.py              # 插件基类
│       │   ├── character.py         # 人物插件
│       │   ├── worldview.py         # 世界观插件
│       │   ├── event.py             # 事件插件
│       │   └── manager.py           # 插件管理器
│       ├── prompts/                 # 提示词系统
│       │   ├── __init__.py
│       │   ├── manager.py           # 提示词管理器
│       │   ├── enhancer.py          # 🆕 智能提示词增强器
│       │   ├── templates/           # 模板文件
│       │   └── styles/              # 风格配置
│       ├── utils/                   # 工具类
│       │   ├── __init__.py
│       │   ├── llm_client.py        # LLM客户端
│       │   ├── cache.py             # 缓存
│       │   ├── logger.py            # 日志
│       │   └── validators.py        # 验证器
│       ├── storage/                 # 存储层
│       │   ├── __init__.py
│       │   ├── session.py           # 会话存储
│       │   ├── vector_store.py      # 向量存储
│       │   └── file_store.py        # 文件存储
│       └── api/                     # API层
│           ├── __init__.py
│           ├── main.py              # FastAPI主文件
│           ├── routes/              # 路由
│           │   ├── sessions.py
│           │   ├── tasks.py
│           │   └── websocket.py
│           ├── schemas/             # 数据模型
│           │   ├── session.py
│           │   ├── task.py
│           │   └── response.py
│           └── dependencies.py      # 依赖注入
│
├── prompts/                         # 提示词模板
│   ├── base/
│   │   ├── system.txt
│   │   └── constraints.txt
│   ├── tasks/
│   │   ├── outline.jinja2
│   │   ├── character.jinja2
│   │   └── chapter.jinja2
│   └── styles/
│       ├── xuanhuan.yaml
│       └── wuxia.yaml
│
├── frontend/                        # 前端代码
│   ├── src/
│   │   ├── pages/                   # 页面
│   │   ├── components/              # 组件
│   │   ├── stores/                  # 状态管理
│   │   ├── api/                     # API调用
│   │   └── utils/                   # 工具函数
│   ├── public/
│   └── package.json
│
├── tests/                           # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/                         # 脚本
│   ├── init_db.py
│   ├── migrate.py
│   └── analyze_llm_usage.py
│
├── data/                            # 数据目录（gitignore）
│   ├── sessions/
│   ├── chroma/
│   └── exports/
│
├── logs/                            # 日志（gitignore）
│
├── docs/                            # 文档
│
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 2. 核心模块实现

### 2.1 LoopEngine (执行引擎)

**文件**: `src/creative_autogpt/core/loop_engine.py`

```python
"""
核心执行引擎
负责协调所有模块完成小说创作
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import asyncio

from creative_autogpt.modes.base import Mode
from creative_autogpt.core.task_planner import TaskPlanner
from creative_autogpt.core.evaluator import EvaluationEngine
from creative_autogpt.core.vector_memory import VectorMemoryManager
from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.storage.session import SessionStorage


class LoopEngine:
    """写作 Agent 的核心执行引擎"""
    
    def __init__(
        self,
        session_id: str,
        mode: Mode,
        llm_client: MultiLLMClient,
        memory: VectorMemoryManager,
        evaluator: EvaluationEngine,
        storage: SessionStorage,
        config: Dict[str, Any] = None
    ):
        self.session_id = session_id
        self.mode = mode
        self.llm_client = llm_client
        self.memory = memory
        self.evaluator = evaluator
        self.storage = storage
        self.config = config or {}
        
        # 任务规划器
        self.planner = TaskPlanner(mode=mode, config=config)
        
        # 执行状态
        self.is_running = False
        self.is_paused = False
        self.current_task = None
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_time": 0,
        }
    
    async def run(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        主执行循环
        
        Args:
            goal: 创作目标，包含风格、主题、字数等
            
        Returns:
            执行结果
        """
        logger.info(f"Session {self.session_id} starting execution")
        logger.debug(f"Goal: {goal}")
        
        try:
            # 1. 生成任务计划
            tasks = await self.planner.plan(goal)
            self.stats["total_tasks"] = len(tasks)
            logger.info(f"Generated {len(tasks)} tasks")
            
            # 保存任务队列
            await self.storage.save_tasks(tasks)
            
            # 2. 执行任务队列
            self.is_running = True
            
            for task in tasks:
                if not self.is_running:
                    logger.info("Execution stopped by user")
                    break
                
                if self.is_paused:
                    logger.info("Execution paused, waiting...")
                    await self._wait_for_resume()
                
                # 执行单个任务
                await self._execute_task(task)
            
            # 3. 生成最终报告
            result = await self._generate_final_report()
            
            logger.info(f"Session {self.session_id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Session {self.session_id} failed: {str(e)}")
            raise
        finally:
            self.is_running = False
    
    async def _execute_task(self, task: Dict[str, Any]) -> None:
        """
        执行单个任务
        
        Args:
            task: 任务信息
        """
        self.current_task = task
        task_id = task["task_id"]
        task_type = task["task_type"]
        
        logger.info(f"Executing task {task_id}: {task_type}")
        
        try:
            # 1. 构建 Prompt
            prompt = await self.mode.build_prompt(task, self.memory)
            
            # 2. 调用 LLM 生成内容
            llm_name = self._route_to_llm(task_type)
            result = await self.llm_client.generate(
                prompt=prompt,
                task_type=task_type,
                llm=llm_name,
                **task.get("llm_params", {})
            )
            
            # 3. 评估结果质量
            evaluation = await self.evaluator.evaluate(
                task_type=task_type,
                content=result.content,
                criteria=task.get("evaluation_criteria"),
                llm_client=self.llm_client
            )
            
            # 4. 判断是否需要重写
            if not evaluation.passed:
                result = await self._attempt_rewrite(
                    task=task,
                    result=result,
                    evaluation=evaluation
                )
            
            # 5. 保存结果到记忆
            await self.memory.store(
                content=result.content,
                task_id=task_id,
                task_type=task_type,
                metadata={
                    "evaluation": evaluation.to_dict(),
                    "llm_used": llm_name,
                    "tokens_used": result.tokens_used
                }
            )
            
            # 6. 保存到存储
            await self.storage.save_task_result(
                task_id=task_id,
                result=result,
                evaluation=evaluation
            )
            
            # 7. 更新统计
            self.stats["completed_tasks"] += 1
            await self._update_progress()
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            self.stats["failed_tasks"] += 1
            
            # 保存错误信息
            await self.storage.save_task_error(
                task_id=task_id,
                error=str(e)
            )
            
            # 根据配置决定是否继续
            if not self.config.get("continue_on_error", False):
                raise
    
    def _route_to_llm(self, task_type: str) -> str:
        """
        根据任务类型路由到合适的 LLM
        
        Args:
            task_type: 任务类型
            
        Returns:
            LLM 名称
        """
        routing_map = {
            # 规划类 → Qwen
            "outline": "qwen",
            "style_elements": "qwen",
            "character_design": "qwen",
            "worldview": "qwen",
            
            # 逻辑类 → DeepSeek
            "events": "deepseek",
            "scenes": "deepseek",
            "evaluation": "deepseek",
            "consistency_check": "deepseek",
            
            # 创作类 → Doubao
            "chapter_content": "doubao",
            "revision": "doubao",
            "polish": "doubao",
        }
        
        return routing_map.get(task_type, "doubao")  # 默认 Doubao
    
    async def _attempt_rewrite(
        self,
        task: Dict[str, Any],
        result: Any,
        evaluation: Any,
        max_retries: int = 3
    ) -> Any:
        """
        尝试重写不合格的内容
        
        Args:
            task: 任务信息
            result: 原始结果
            evaluation: 评估结果
            max_retries: 最大重试次数
            
        Returns:
            重写后的结果
        """
        logger.warning(f"Task {task['task_id']} failed evaluation, attempting rewrite")
        
        for attempt in range(max_retries):
            logger.info(f"Rewrite attempt {attempt + 1}/{max_retries}")
            
            # 构建改进后的 Prompt
            improved_prompt = await self.mode.build_improved_prompt(
                task=task,
                previous_result=result.content,
                evaluation_feedback=evaluation.feedback
            )
            
            # 重新生成
            llm_name = self._route_to_llm(task["task_type"])
            new_result = await self.llm_client.generate(
                prompt=improved_prompt,
                task_type=task["task_type"],
                llm=llm_name,
                temperature=self.config.get("rewrite_temperature", 0.8)
            )
            
            # 重新评估
            new_evaluation = await self.evaluator.evaluate(
                task_type=task["task_type"],
                content=new_result.content,
                criteria=task.get("evaluation_criteria"),
                llm_client=self.llm_client
            )
            
            if new_evaluation.passed:
                logger.info(f"Rewrite successful on attempt {attempt + 1}")
                return new_result
        
        # 所有重试失败，返回最好的结果
        logger.warning(f"All rewrite attempts failed for task {task['task_id']}")
        return result
    
    async def _update_progress(self) -> None:
        """更新执行进度"""
        progress = {
            "total_tasks": self.stats["total_tasks"],
            "completed_tasks": self.stats["completed_tasks"],
            "failed_tasks": self.stats["failed_tasks"],
            "percentage": (
                self.stats["completed_tasks"] / self.stats["total_tasks"] * 100
                if self.stats["total_tasks"] > 0 else 0
            )
        }
        
        # 保存进度
        await self.storage.update_progress(progress)
        
        # 发送 WebSocket 事件
        await self._emit_event("progress_updated", progress)
    
    async def _wait_for_resume(self) -> None:
        """等待恢复执行"""
        while self.is_paused and self.is_running:
            await asyncio.sleep(1)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """发送 WebSocket 事件（需要实现）"""
        # TODO: 实现 WebSocket 事件发送
        pass
    
    async def _generate_final_report(self) -> Dict[str, Any]:
        """生成最终报告"""
        return {
            "session_id": self.session_id,
            "status": "completed",
            "stats": self.stats,
            "summary": await self._generate_summary()
        }
    
    async def _generate_summary(self) -> str:
        """生成创作总结"""
        # TODO: 使用 LLM 生成整体总结
        return f"Session {self.session_id} completed with {self.stats['completed_tasks']} tasks"
    
    # === 控制方法 ===
    
    def pause(self) -> None:
        """暂停执行"""
        logger.info(f"Session {self.session_id} pausing")
        self.is_paused = True
    
    def resume(self) -> None:
        """恢复执行"""
        logger.info(f"Session {self.session_id} resuming")
        self.is_paused = False
    
    def stop(self) -> None:
        """停止执行"""
        logger.info(f"Session {self.session_id} stopping")
        self.is_running = False
        self.is_paused = False
```

---

### 2.2 PromptEnhancer (智能提示词增强器) 🆕

> 让不懂提示词的用户也能轻松使用系统！

**文件**: `src/creative_autogpt/prompts/enhancer.py`

```python
"""
智能提示词增强器
将用户的简单描述自动扩展为完整的结构化配置

设计目标：
- 用户只需一句话描述，系统自动生成专业级配置
- 降低使用门槛，让非技术用户也能轻松创作
- 使用 DeepSeek 进行扩展（成本极低，约 ¥0.001/次）
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from loguru import logger
import json
import re


@dataclass
class EnhancedPrompt:
    """增强后的提示词配置"""
    # 基本信息
    style: str                      # 风格类型（玄幻/武侠/都市/科幻等）
    theme: str                      # 主题（一句话概括）
    target_words: int               # 目标字数
    chapter_count: int              # 章节数
    
    # 人物设定
    protagonist: Dict[str, Any]     # 主角设定
    
    # 世界观
    world_setting: Dict[str, Any]   # 世界观设定
    
    # 情节与风格
    plot_elements: list             # 情节要素
    style_elements: Dict[str, Any]  # 风格元素
    
    # 约束
    constraints: list               # 约束条件
    special_requirements: list      # 特殊要求
    
    # 元信息
    raw_input: str                  # 原始用户输入
    confidence: float               # 扩展置信度（0-1）
    
    def to_config(self) -> Dict[str, Any]:
        """转换为 LoopEngine 可用的配置"""
        return {
            "style": self.style,
            "theme": self.theme,
            "structure": {
                "target_words": self.target_words,
                "chapter_count": self.chapter_count,
                "words_per_chapter": self.target_words // self.chapter_count
            },
            "characters": {
                "protagonist": self.protagonist
            },
            "world": self.world_setting,
            "plot": {
                "elements": self.plot_elements
            },
            "style_config": self.style_elements,
            "constraints": self.constraints,
            "requirements": self.special_requirements
        }


class PromptEnhancer:
    """
    智能提示词增强器
    
    核心功能：
    1. 解析用户的自然语言描述
    2. 识别关键要素（风格、主题、人物等）
    3. 扩展为完整的结构化配置
    4. 支持用户确认和迭代调整
    
    使用示例:
        enhancer = PromptEnhancer(llm_client)
        
        # 简单使用：用户一句话
        enhanced = await enhancer.enhance("写一个玄幻小说，主角废材逆袭，100万字")
        
        # 用户可以查看配置并调整
        if enhanced.confidence < 0.8:
            enhanced = await enhancer.refine(enhanced, "主角要是女的")
        
        # 转换为系统配置
        config = enhanced.to_config()
    """
    
    # 扩展提示词模板
    ENHANCE_PROMPT_TEMPLATE = '''你是一位专业的小说策划专家。请根据用户的简单描述，扩展为完整的小说创作配置。

## 用户描述
{user_input}

## 写作模式
{mode}

## 你的任务
分析用户描述，推断并补充以下信息。如果用户没有明确说明，请根据描述合理推断。

请以 JSON 格式输出：
```json
{{
  "style": "风格类型",
  "theme": "核心主题（一句话）",
  "target_words": 目标字数,
  "chapter_count": 章节数,
  
  "protagonist": {{
    "name": "姓名（可为空）",
    "gender": "性别",
    "age": "年龄范围",
    "personality": "性格特点",
    "background": "背景设定",
    "growth_arc": "成长弧线"
  }},
  
  "world_setting": {{
    "type": "世界类型",
    "era": "时代背景",
    "power_system": "力量体系",
    "key_locations": ["地点1", "地点2"],
    "factions": ["势力1", "势力2"]
  }},
  
  "plot_elements": ["情节要素1", "情节要素2", "情节要素3"],
  
  "style_elements": {{
    "tone": "整体基调",
    "pacing": "节奏风格",
    "description_style": "描写风格",
    "dialogue_style": "对话风格"
  }},
  
  "constraints": ["创作约束1", "创作约束2"],
  "special_requirements": ["特殊要求"],
  "confidence": 0.0到1.0
}}
```

注意：
1. 如果描述简单，合理推断补充
2. 保持与用户意图一致
3. confidence：描述详细则接近1.0，需要大量推断则较低
4. 只输出 JSON
'''

    REFINE_PROMPT_TEMPLATE = '''当前配置：
{current_config}

用户调整意见：
{user_feedback}

请根据用户反馈调整配置，保持其他部分不变，输出完整 JSON。
'''
    
    def __init__(
        self,
        llm_client,
        config: Dict[str, Any] = None
    ):
        """
        初始化增强器
        
        Args:
            llm_client: LLM 客户端
            config: 配置选项
        """
        self.llm_client = llm_client
        self.config = config or {}
        
        # 使用 DeepSeek（性价比最高）
        self.enhancer_llm = self.config.get("llm", "deepseek")
        
        # 自动确认阈值
        self.auto_confirm_threshold = self.config.get(
            "auto_confirm_threshold", 0.8
        )
    
    async def enhance(
        self,
        user_input: str,
        mode: str = "novel"
    ) -> EnhancedPrompt:
        """
        将用户简单描述扩展为完整配置
        
        Args:
            user_input: 用户的简单描述（如"写一个玄幻小说，100万字"）
            mode: 写作模式 (novel/script/larp)
            
        Returns:
            EnhancedPrompt: 扩展后的完整配置
        
        示例:
            enhanced = await enhancer.enhance(
                "写个都市修仙，主角重生回高中，有系统金手指"
            )
            print(f"风格: {enhanced.style}")  # 都市修仙
            print(f"置信度: {enhanced.confidence}")  # 0.85
        """
        logger.info(f"🔮 Enhancing user input: {user_input[:50]}...")
        
        # 构建增强提示词
        prompt = self.ENHANCE_PROMPT_TEMPLATE.format(
            user_input=user_input,
            mode=mode
        )
        
        # 调用 LLM 扩展
        response = await self.llm_client.generate(
            prompt=prompt,
            task_type="prompt_enhance",
            llm=self.enhancer_llm,
            temperature=0.7  # 适度创造性
        )
        
        # 解析响应
        enhanced = self._parse_response(response.content, user_input)
        
        logger.info(
            f"✅ Enhancement complete: "
            f"style={enhanced.style}, "
            f"words={enhanced.target_words:,}, "
            f"confidence={enhanced.confidence:.0%}"
        )
        
        return enhanced
    
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
        
        示例:
            enhanced = await enhancer.refine(
                enhanced,
                "主角改成女的，增加感情线"
            )
        """
        logger.info(f"🔄 Refining with feedback: {user_feedback[:50]}...")
        
        prompt = self.REFINE_PROMPT_TEMPLATE.format(
            current_config=json.dumps(asdict(enhanced), ensure_ascii=False, indent=2),
            user_feedback=user_feedback
        )
        
        response = await self.llm_client.generate(
            prompt=prompt,
            task_type="prompt_refine",
            llm=self.enhancer_llm,
            temperature=0.5  # 较低创造性，保持一致
        )
        
        return self._parse_response(response.content, enhanced.raw_input)
    
    def _parse_response(self, response: str, raw_input: str) -> EnhancedPrompt:
        """解析 LLM 的 JSON 响应"""
        try:
            # 尝试直接解析
            data = json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # 尝试提取任何 JSON 对象
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
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
    
    def should_auto_confirm(self, enhanced: EnhancedPrompt) -> bool:
        """判断是否可以自动确认（无需用户交互）"""
        return enhanced.confidence >= self.auto_confirm_threshold


# 便捷函数
async def smart_enhance(
    user_input: str,
    llm_client,
    auto_confirm: bool = True
) -> Dict[str, Any]:
    """
    智能增强并返回配置
    
    Args:
        user_input: 用户描述
        llm_client: LLM 客户端
        auto_confirm: 高置信度时自动确认
        
    Returns:
        可直接用于 LoopEngine 的配置
    """
    enhancer = PromptEnhancer(llm_client)
    enhanced = await enhancer.enhance(user_input)
    
    if auto_confirm and enhancer.should_auto_confirm(enhanced):
        logger.info("✅ High confidence, auto-confirming configuration")
        return enhanced.to_config()
    
    return enhanced
```

**使用流程**：

```
用户: "写一个玄幻小说，主角废材逆袭，100万字"
          │
          ▼
    ┌─────────────┐
    │PromptEnhancer│  ← 使用 DeepSeek，成本约 ¥0.001
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────┐
    │ EnhancedPrompt:                     │
    │   style: "玄幻修仙"                  │
    │   theme: "废材逆袭成仙帝"            │
    │   target_words: 1,000,000           │
    │   protagonist: {...}                │
    │   world_setting: {...}              │
    │   confidence: 0.85                  │
    └──────┬──────────────────────────────┘
           │
           ▼
    ┌─────────────┐
    │ 用户确认/调整│  ← 如果 confidence >= 0.8 可跳过
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ LoopEngine  │  ← 开始正式创作
    └─────────────┘
```

---

### 2.3 MultiLLMClient (多模型客户端)

**文件**: `src/creative_autogpt/utils/llm_client.py`

```python
"""
多 LLM 客户端
统一管理 Qwen、DeepSeek、Doubao 等模型的调用
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger
import asyncio
import os

from openai import AsyncOpenAI
import dashscope


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    tokens_used: Dict[str, int]
    llm_used: str
    cost: float
    latency: float


class MultiLLMClient:
    """多 LLM 客户端"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 初始化各个 LLM 客户端
        self.clients = {}
        
        # Qwen (通过 DashScope)
        if self.config.get("qwen", {}).get("enabled", True):
            dashscope.api_key = os.getenv("ALIYUN_API_KEY")
            self.clients["qwen"] = "dashscope"  # 标记使用 DashScope
        
        # DeepSeek (OpenAI 兼容)
        if self.config.get("deepseek", {}).get("enabled", True):
            self.clients["deepseek"] = AsyncOpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            )
        
        # Doubao (OpenAI 兼容)
        if self.config.get("doubao", {}).get("enabled", True):
            self.clients["doubao"] = AsyncOpenAI(
                api_key=os.getenv("ARK_API_KEY"),
                base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
            )
    
    async def generate(
        self,
        prompt: str,
        task_type: str,
        llm: str,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成内容
        
        Args:
            prompt: 提示词
            task_type: 任务类型
            llm: 使用的 LLM 名称
            temperature: 温度参数
            max_tokens: 最大 tokens
            
        Returns:
            LLM 响应
        """
        import time
        start_time = time.time()
        
        logger.info(f"Calling {llm} for task {task_type}")
        
        try:
            if llm == "qwen":
                response = await self._call_qwen(prompt, temperature, max_tokens, **kwargs)
            elif llm == "deepseek":
                response = await self._call_deepseek(prompt, temperature, max_tokens, **kwargs)
            elif llm == "doubao":
                response = await self._call_doubao(prompt, temperature, max_tokens, **kwargs)
            else:
                raise ValueError(f"Unknown LLM: {llm}")
            
            latency = time.time() - start_time
            logger.info(f"{llm} responded in {latency:.2f}s")
            
            return LLMResponse(
                content=response["content"],
                tokens_used=response["tokens"],
                llm_used=llm,
                cost=self._calculate_cost(llm, response["tokens"]),
                latency=latency
            )
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise
    
    async def _call_qwen(
        self,
        prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """调用 Qwen"""
        from dashscope import Generation
        
        model = self.config.get("qwen", {}).get("model", "qwen-max")
        temperature = temperature or self.config.get("qwen", {}).get("temperature", 0.7)
        max_tokens = max_tokens or self.config.get("qwen", {}).get("max_tokens", 4000)
        
        response = await asyncio.to_thread(
            Generation.call,
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        if response.status_code == 200:
            return {
                "content": response.output.text,
                "tokens": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        else:
            raise Exception(f"Qwen API error: {response.message}")
    
    async def _call_deepseek(
        self,
        prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """调用 DeepSeek"""
        client = self.clients["deepseek"]
        model = self.config.get("deepseek", {}).get("model", "deepseek-chat")
        temperature = temperature or self.config.get("deepseek", {}).get("temperature", 0.5)
        max_tokens = max_tokens or self.config.get("deepseek", {}).get("max_tokens", 2000)
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return {
            "content": response.choices[0].message.content,
            "tokens": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    async def _call_doubao(
        self,
        prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """调用 Doubao"""
        client = self.clients["doubao"]
        model = self.config.get("doubao", {}).get("model", "doubao-pro-32k")
        temperature = temperature or self.config.get("doubao", {}).get("temperature", 0.8)
        max_tokens = max_tokens or self.config.get("doubao", {}).get("max_tokens", 4000)
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return {
            "content": response.choices[0].message.content,
            "tokens": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    def _calculate_cost(self, llm: str, tokens: Dict[str, int]) -> float:
        """计算成本（人民币）"""
        # 价格表（元/1K tokens）
        pricing = {
            "qwen": {"input": 0.04, "output": 0.12},
            "deepseek": {"input": 0.001, "output": 0.002},
            "doubao": {"input": 0.008, "output": 0.008}
        }
        
        if llm not in pricing:
            return 0.0
        
        input_cost = tokens["prompt_tokens"] / 1000 * pricing[llm]["input"]
        output_cost = tokens["completion_tokens"] / 1000 * pricing[llm]["output"]
        
        return input_cost + output_cost
```

---

## 3. API 实现

### 3.1 FastAPI 主文件

**文件**: `src/creative_autogpt/api/main.py`

```python
"""
FastAPI 主应用
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from creative_autogpt.api.routes import sessions, tasks, websocket
from creative_autogpt.api.dependencies import get_settings


# 创建应用
app = FastAPI(
    title="Creative AutoGPT API",
    description="AI-powered creative writing system",
    version="1.0.0"
)

# CORS 配置
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("Starting Creative AutoGPT API")
    # TODO: 初始化数据库连接、向量存储等


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("Shutting down Creative AutoGPT API")
    # TODO: 关闭数据库连接等


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Creative AutoGPT API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
```

---

### 3.2 会话路由

**文件**: `src/creative_autogpt/api/routes/sessions.py`

```python
"""
会话管理路由
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from creative_autogpt.api.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionList
)
from creative_autogpt.storage.session import SessionStorage


router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    session_data: SessionCreate,
    storage: SessionStorage = Depends()
):
    """创建新会话"""
    try:
        session = await storage.create_session(session_data.dict())
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=SessionList)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    storage: SessionStorage = Depends()
):
    """获取会话列表"""
    try:
        sessions = await storage.list_sessions(
            page=page,
            page_size=page_size,
            status=status
        )
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    storage: SessionStorage = Depends()
):
    """获取会话详情"""
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    storage: SessionStorage = Depends()
):
    """删除会话"""
    success = await storage.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}
```

---

## 4. 数据模型

### 4.1 会话模型

**文件**: `src/creative_autogpt/api/schemas/session.py`

```python
"""
会话数据模型
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """会话状态"""
    CREATED = "created"
    CONFIGURED = "configured"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class SessionMode(str, Enum):
    """写作模式"""
    NOVEL = "novel"
    SCRIPT = "script"
    LARP = "larp"


class SessionConfig(BaseModel):
    """会话配置"""
    style: str = Field(..., description="风格类型")
    theme: str = Field(..., description="主题")
    target_words: int = Field(..., gt=0, description="目标字数")
    chapter_count: int = Field(..., gt=0, description="章节数量")
    words_per_chapter: Optional[int] = Field(None, description="每章字数")
    
    llm_config: Dict[str, Any] = Field(default_factory=dict, description="LLM配置")
    

class SessionMetadata(BaseModel):
    """会话元数据"""
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SessionCreate(BaseModel):
    """创建会话请求"""
    mode: SessionMode
    config: SessionConfig
    metadata: SessionMetadata


class SessionProgress(BaseModel):
    """会话进度"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    percentage: float


class SessionStats(BaseModel):
    """会话统计"""
    total_words: int = 0
    chapters_completed: int = 0
    llm_calls: Dict[str, int] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """会话响应"""
    session_id: str
    mode: SessionMode
    status: SessionStatus
    config: SessionConfig
    metadata: SessionMetadata
    progress: Optional[SessionProgress] = None
    stats: Optional[SessionStats] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class SessionList(BaseModel):
    """会话列表响应"""
    total: int
    page: int
    page_size: int
    sessions: List[SessionResponse]
```

---

## 5. 数据库设计

### 5.1 SQLAlchemy 模型

**文件**: `src/creative_autogpt/storage/models.py`

```python
"""
数据库模型
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum


Base = declarative_base()


class SessionStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Session(Base):
    """会话表"""
    __tablename__ = "sessions"
    
    session_id = Column(String(50), primary_key=True)
    mode = Column(String(20), nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.CREATED)
    
    config = Column(JSON, nullable=False)
    metadata = Column(JSON, nullable=False)
    
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    tasks = relationship("Task", back_populates="session", cascade="all, delete-orphan")
    checkpoints = relationship("Checkpoint", back_populates="session")


class Task(Base):
    """任务表"""
    __tablename__ = "tasks"
    
    task_id = Column(String(50), primary_key=True)
    session_id = Column(String(50), ForeignKey("sessions.session_id"), nullable=False)
    
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    
    prompt = Column(Text)
    result_content = Column(Text)
    
    llm_used = Column(String(20))
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    evaluation_score = Column(Float)
    evaluation_passed = Column(Boolean)
    
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 关系
    session = relationship("Session", back_populates="tasks")


class Checkpoint(Base):
    """检查点表"""
    __tablename__ = "checkpoints"
    
    checkpoint_id = Column(String(50), primary_key=True)
    session_id = Column(String(50), ForeignKey("sessions.session_id"), nullable=False)
    
    description = Column(String(200))
    completed_tasks = Column(Integer)
    state_snapshot = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    session = relationship("Session", back_populates="checkpoints")
```

---

**由于文档非常长，继续创建其他技术细节...**

---

*版本: 1.0*  
*最后更新: 2026-01-23*
