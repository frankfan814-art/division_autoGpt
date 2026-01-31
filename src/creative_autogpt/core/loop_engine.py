"""
Loop Engine - Core execution engine for creative writing

Implements the AutoGPT-inspired agent loop:
Think → Plan → Execute → Evaluate → Memory

Coordinates all components for automated novel creation.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Callable, List

from loguru import logger

from creative_autogpt.core.task_planner import (
    TaskPlanner,
    NovelTaskType,
    Task,
)
from creative_autogpt.core.evaluator import (
    EvaluationEngine,
    EvaluationResult,
)
from creative_autogpt.core.vector_memory import (
    VectorMemoryManager,
    MemoryContext,
    MemoryType,
)
from creative_autogpt.core.self_evaluator import SelfEvaluator
from creative_autogpt.core.prompt_evolver import PromptEvolver  # 🔥 改为直接导入类，实现按项目隔离
from creative_autogpt.core.chapter_continuity import ChapterContinuityManager
from creative_autogpt.utils.llm_client import (
    MultiLLMClient,
)


class ExecutionStatus(str, Enum):
    """Status of loop engine execution"""

    IDLE = "idle"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"  # Waiting for user to approve task result
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ExecutionStats:
    """Statistics about execution"""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    retried_tasks: int = 0
    total_time: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "retried_tasks": self.retried_tasks,
            "total_time": self.total_time,
            "llm_calls": self.llm_calls,
            "tokens_used": self.tokens_used,
        }


@dataclass
class ExecutionResult:
    """Result of loop engine execution"""

    status: ExecutionStatus
    stats: ExecutionStats
    outputs: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "stats": self.stats.to_dict(),
            "outputs": self.outputs,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class LoopEngine:
    """
    Core execution engine for creative writing

    🔥 优化：类级别定义公共提示词模板，避免重复构建
    """

    # ═══════════════════════════════════════════════════════════════════════════════
    # 📋 公共提示词模板（只定义一次，所有任务共享）
    # ═══════════════════════════════════════════════════════════════════════════════

    # 通用的白话文写作风格要求（所有任务都适用）
    COLLOQUIAL_STYLE_GUIDE = """
🚨 **核心写作要求：白话文、接地气、通俗易懂**

你是一位擅长讲故事的作家，不是在写学术论文！
请像和朋友聊天一样写作，让高中生也能轻松看懂。

✅ **正确示范（白话文）**：
- ❌ "该角色具有内向型人格特质，在社交场合中呈现回避性行为模式"
- ✅ "他不太爱说话，人多的时候总喜欢躲在角落"

- ❌ "此设定构建了一个以科技发展为核心驱动力的叙事框架"
- ✅ "这个世界因为科技发达，发生了很多有意思的变化"

- ❌ "主角的内在驱动力源于童年创伤所形成的心理补偿机制"
- ✅ "他小时候受过伤，所以长大后特别想证明自己"

🚫 **绝对禁止（这些词看到就改！）**：
- 禁止用词："驱动力"、"机制"、"框架"、"模式"、"特质"、"维度"、"层面"、"范畴"
- 禁止用词："呈现"、"构建"、"探讨"、"阐述"、"论述"、"概述"、"综述"
- 禁止用词："基于"、"鉴于"、"关于"、"就...而言"、"从...角度"
- 禁止用词："具有...特征"、"表现出...倾向"、"体现了...精神"
- 禁止格式：一、二、三的正式大纲格式（可以用但不要过度）
- 禁止格式："首先...其次...最后..."的论文式写法

✅ **推荐写法**：
- 说人话：用"因为...所以..."而不是"鉴于...因此..."
- 用比喻：复杂概念用生活中的例子解释
- 讲故事：用叙事的方式而不是说明文的方式
- 接地气：想象你在给朋友讲一个好玩的故事
"""

    # 简化的风格指南引用（用于后续任务）
    STYLE_GUIDE_REFERENCE = """
💡 **写作风格**：
- 请遵循白话文、接地气的写作风格
- 用讲故事的方式，像和朋友聊天一样
- 避免学术化、论文式的表达
"""

    # 🔥 任务类型分类（类级别常量，所有方法共享）
    ALL_TASKS_TYPES = {
        "strategy": ["创意脑暴"],  # 策略规划任务
        "planning": ["大纲"],  # 规划任务
        "element": ["世界观规则", "势力设计", "场景设计", "人物设计", "功法法宝", "主角成长", "反派设计", "事件", "时间线", "伏笔列表"],  # 元素设计
        "quality": ["一致性检查", "对话检查"],  # 质量检查（每章后自动运行）
        "content": ["章节内容"],  # 内容创作
    }

    # 策略任务的特殊说明
    STRATEGY_TASK_NOTE = """
⚠️ **这是战略阶段，不是写作阶段！**
- 你的任务是确定方向、规划结构、设计框架
- **不要直接写小说内容**
- **不要写章节、场景、对话等具体内容**
- 要用规划性、分析性的语言

🎯 **核心原则**：
1. 规划先于创作 - 先有蓝图，后有内容
2. 结构优先 - 搭建好框架再填充细节
3. 保持抽象 - 在这个阶段保持概念性，不要进入具体写作
"""

    # 规划任务的特殊说明
    PLANNING_TASK_NOTE = """
你正在为一部小说做**前期规划和分析**工作。
这个阶段的任务是帮助明确小说的方向，而不是直接写小说内容。
"""

    # 元素设计任务的特殊说明
    ELEMENT_TASK_NOTE = """
你正在为一部小说**设计创作元素**。
这些元素将用于后续的章节创作，需要既有结构性又有文学性。
"""

    # 🔥 不同类型小说的写作指南
    GENRE_WRITING_GUIDES = {
        "科幻": """
📚 科幻小说写作标准（参考《三体》《流浪地球》等）：
✅ 必须做到：
- 故事性优先：科学设定服务于故事情节
- **通俗易懂**：用白话文写作，让普通人也能看懂
- 科学融入：通过对话、情节自然呈现，不堆砌术语
- 沉浸感：让读者身临其境，不是在读技术文档
- **接地气**：用日常生活比喻解释复杂概念

❌ 严格禁止：
- 学术论文格式、公式推导、科研报告式叙述
- 大量术语堆砌而不解释
- 面向专业研究者的写作风格

💡 要点：
- 科学设定用故事讲出来（像刘慈欣的写法）
- 技术细节融入对话、情节、场景中
- 你的读者是科幻爱好者，不是物理学家
""",
        "都市修仙": """
📚 都市修仙小说写作标准（参考《凡人修仙传》《仙王的日常生活》等）：
✅ 必须做到：
- **轻松愉快**：用幽默诙谐的语言，让读者会心一笑
- **接地气**：修仙元素融入现代都市生活（外卖、地铁、扫码支付）
- 节奏明快：对话生动，情节紧凑，不拖泥带水
- 爽点清晰：打脸、升级、装逼要自然不尴尬
- 人物立体：主角有血有肉，不是工具人

❌ 严格禁止：
- 过度严肃沉重（这不是传统修仙文！）
- 抄袭经典作品的设定和桥段
- 逻辑混乱、前后矛盾
- 无意义的灌水

💡 要点：
- 修仙要"日常化"：用外卖APP接单来接修仙任务
- 战斗要"生活化"：用电瓶车代替飞剑，用保温箱装丹药
- 语言要"网文化"：适当使用网络梗和流行语
""",
        "玄幻": """
📚 玄幻小说写作标准（参考《斗破苍穹》《完美世界》等）：
✅ 必须做到：
- 热血爽快：战斗场面要燃，升级要爽
- 世界宏大：势力等级森严，地图层层递进
- 天才如云：反派不能太弱，主角才能越级挑战
- 功法酷炫：技能招式要有画面感
- 情感真挚：兄弟情、儿女情要动人

❌ 严格禁止：
- 逻辑硬伤和战力崩坏
- 主角光环过重失去合理性
- 重复套路和抄袭桥段
""",
        "武侠": """
📚 武侠小说写作标准（参考金庸、古龙作品）：
✅ 必须做到：
- 侠义精神：路见不平拔刀相助
- 江湖情怀：门派恩怨、正邪对立
- 武功精彩：招式描写要有画面感
- 语言典雅：半文半白，有古典韵味
""",
    }

    # 通用的小说写作标准（默认）
    DEFAULT_CONTENT_TASK_NOTE = """
⚠️ 核心要求：你正在创作一部**小说**，请使用小说的叙事语言和文学手法。

✅ 必须做到：
- 故事性优先：一切设定服务于故事情节
- **通俗易懂**：面向大众读者，用白话文写作
- 文学性强：使用生动的叙事语言和文学手法
- 沉浸感：让读者身临其境
- **接地气**：用日常生活的语言

❌ 严格禁止：
- 学术论文格式
- 信息堆砌和说明文式写作
- 枯燥乏味的叙述
"""

    # AutoGPT-style agent loop specialized for novel creation:
    # 1. Plan - Generate task DAG from goals
    # 2. Execute - Run tasks in dependency order
    # 3. Evaluate - Assess quality of results
    # 4. Rewrite - Retry if quality insufficient
    # 5. Memory - Store results for context

    def __init__(
        self,
        session_id: str,
        llm_client: MultiLLMClient,
        memory: VectorMemoryManager,
        evaluator: EvaluationEngine,
        config: Optional[Dict[str, Any]] = None,
        session_storage = None,  # 🔥 添加 session_storage 参数（可选）
        plugin_manager = None,  # 🔥 添加插件管理器（可选）
    ):
        """
        Initialize loop engine

        Args:
            session_id: Unique session identifier
            llm_client: Multi-LLM client for generation
            memory: Vector memory manager
            evaluator: Quality evaluation engine
            config: Optional configuration
            session_storage: Optional session storage for updating rewrite state
            plugin_manager: Optional plugin manager for element plugins
        """
        self.session_id = session_id
        self.llm_client = llm_client
        self.memory = memory
        self.evaluator = evaluator
        self.config = config or {}
        self.session_storage = session_storage  # 🔥 保存 session_storage
        self.plugin_manager = plugin_manager  # 🔥 保存插件管理器

        # Create task planner (pass plugin_manager for loading plugin tasks)
        self.planner = TaskPlanner(config=config, plugin_manager=plugin_manager)

        # 自我评估和提示词进化系统
        self.self_evaluator = SelfEvaluator(llm_client=llm_client)
        # 🔥 按项目隔离：创建独立的 PromptEvolver 实例，避免跨项目污染
        self.prompt_evolver = PromptEvolver(
            llm_client=llm_client,
            data_dir=f"data/prompt_evolution/{session_id}"  # 使用 session_id 隔离数据目录
        )

        # 章节连贯性管理器
        self.chapter_continuity_manager = ChapterContinuityManager(llm_client)

        # 是否启用自我进化（默认启用）
        self.enable_self_evolution = config.get('enable_self_evolution', True)

        # Execution state
        self.status = ExecutionStatus.IDLE
        self.is_running = False
        self.is_paused = False
        self.current_task: Optional[Task] = None

        # 🔥 已完成的任务ID集合（用于恢复执行时跳过）
        self.completed_task_ids: set = set()

        # Approval mode settings (enabled by default to allow user review)
        self.approval_mode = config.get('approval_mode', True)  # Default to require approval
        self.is_waiting_approval = False
        self.approval_result: Optional[Dict[str, Any]] = None
        self._approval_event = asyncio.Event()

        # Statistics
        self.stats = ExecutionStats()
        
        # 🎯 高分内容示例存储（用于后续任务的参考）
        # 结构: {task_type: {genre: {"score": float, "content": str, "reason": str}}}
        self.best_examples: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # 最低高分阈值（只有超过这个分数的内容才会被记录为示例）
        self.high_score_threshold = config.get('high_score_threshold', 85)

        # Event callbacks
        self._on_task_start: Optional[Callable] = None
        self._on_task_complete: Optional[Callable] = None
        self._on_task_fail: Optional[Callable] = None
        self._on_progress: Optional[Callable] = None
        self._on_task_approval_needed: Optional[Callable] = None
        self._on_step_progress: Optional[Callable] = None  # 🔥 新增：步骤级进度回调

        logger.info(f"LoopEngine initialized for session {session_id}")

    def set_callbacks(
        self,
        on_task_start: Optional[Callable] = None,
        on_task_complete: Optional[Callable] = None,
        on_task_fail: Optional[Callable] = None,
        on_progress: Optional[Callable] = None,
        on_task_approval_needed: Optional[Callable] = None,
        on_step_progress: Optional[Callable] = None,  # 🔥 新增
    ) -> None:
        """Set event callbacks for execution monitoring"""
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_task_fail = on_task_fail
        self._on_progress = on_progress
        self._on_task_approval_needed = on_task_approval_needed
        self._on_step_progress = on_step_progress  # 🔥 新增

    async def run(
        self,
        goal: Dict[str, Any],
        chapter_count: Optional[int] = None,
        completed_task_ids: Optional[List[str]] = None,
        completed_task_records: Optional[List[Dict[str, Any]]] = None,
    ) -> ExecutionResult:
        """
        Main execution loop

        Args:
            goal: Creation goal with style, theme, length, etc.
            chapter_count: Number of chapters to create
            completed_task_ids: [DEPRECATED] List of already completed task IDs to skip
            completed_task_records: List of completed task records for intelligent matching by task_type + chapter_index

        Returns:
            ExecutionResult with outputs and statistics
        """
        start_time = time.time()
        started_at = datetime.utcnow()

        self.status = ExecutionStatus.RUNNING
        self.is_running = True
        self.stats = ExecutionStats()

        # 🔥 记录已完成的任务ID（优先使用 completed_task_records，因为 task_id 会重新生成）
        # 注意：由于 TaskPlanner 会重新生成 task_id，completed_task_ids 参数实际上不起作用
        # 真正的匹配是通过 completed_task_records 在 TaskPlanner.plan 中进行的
        if completed_task_records:
            logger.info(f"📋 Received {len(completed_task_records)} completed task records for intelligent matching")
        self.completed_task_ids = set(completed_task_ids or [])
        if self.completed_task_ids:
            logger.info(f"⏭️ Also received {len(self.completed_task_ids)} completed task IDs (legacy mode)")

        logger.info(f"Starting execution for session {self.session_id}")
        logger.info(f"Goal: {goal.get('title', 'Untitled')}")

        # 🔥 初始化插件系统
        if self.plugin_manager:
            from creative_autogpt.plugins.base import WritingContext
            plugin_context = WritingContext(
                session_id=self.session_id,
                goal=goal,
                current_task=None,
                current_chapter=None,
                results={},
                metadata=self.config,
                storage=self.session_storage,  # 🔥 传递 storage 用于插件数据持久化
            )
            try:
                await self.plugin_manager.initialize_all(plugin_context)
                logger.info(f"✅ Plugin system initialized with {len(self.plugin_manager.list_enabled())} enabled plugins")
            except Exception as e:
                logger.error(f"❌ Failed to initialize plugins: {e}")

        try:
            # Phase 1: Planning
            self.status = ExecutionStatus.PLANNING
            logger.info("Planning phase: generating task DAG")

            tasks = await self.planner.plan(
                goal=goal,
                chapter_count=chapter_count,
                completed_task_records=completed_task_records,  # 🔥 传递已完成的任务记录
            )

            # 🔥 注册插件任务到 LLM 路由映射
            if self.plugin_manager:
                plugin_tasks = self.plugin_manager.get_tasks()
                if plugin_tasks:
                    registered = self.llm_client.register_plugin_tasks(plugin_tasks)
                    logger.info(f"✅ Registered {registered} plugin tasks to LLM routing")

            # 🔥 过滤掉已完成的任务
            if self.completed_task_ids:
                tasks = [t for t in tasks if t.task_id not in self.completed_task_ids]
                logger.info(f"🔍 Filtered to {len(tasks)} remaining tasks (after skipping completed)")

            self.stats.total_tasks = len(tasks) + len(self.completed_task_ids)
            logger.info(f"Generated {len(tasks)} tasks to execute")

            # Phase 2: Execute tasks
            self.status = ExecutionStatus.RUNNING

            # 🔥 初始化 completed_tasks 计数（包括之前已完成的任务）
            self.stats.completed_tasks = len(self.completed_task_ids)
            if self.completed_task_ids:
                logger.info(f"📊 Initial progress: {self.stats.completed_tasks}/{self.stats.total_tasks} tasks already completed")
                # 通知前端初始进度
                if self._on_progress:
                    self._on_progress(self.stats.to_dict())

            while self.is_running:
                # Check for pause
                while self.is_paused:
                    await asyncio.sleep(0.1)
                    if not self.is_running:
                        break

                # Get next task
                task = self.planner.get_next_task()
                if task is None:
                    # Check if all tasks are complete
                    if self.planner.is_complete():
                        logger.info("All tasks completed")
                        break
                    # No ready tasks, wait a bit
                    await asyncio.sleep(0.5)
                    continue

                # Execute task
                await self._execute_task(task, goal)

                # Update progress
                if self._on_progress:
                    progress = self.planner.get_progress()
                    await self._safe_callback(
                        self._on_progress,
                        progress,
                    )

            # Phase 3: Complete
            self.status = ExecutionStatus.COMPLETED
            self.stats.total_time = time.time() - start_time

            result = ExecutionResult(
                status=self.status,
                stats=self.stats,
                outputs=self._collect_outputs(),
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Execution completed: {self.stats.completed_tasks}/{self.stats.total_tasks} tasks, "
                f"{self.stats.total_time:.1f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            self.status = ExecutionStatus.FAILED
            self.stats.total_time = time.time() - start_time

            return ExecutionResult(
                status=self.status,
                stats=self.stats,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

        finally:
            self.is_running = False

            # 🔥 清理插件系统
            if self.plugin_manager:
                from creative_autogpt.plugins.base import WritingContext
                plugin_context = WritingContext(
                    session_id=self.session_id,
                    goal=goal,
                    current_task=None,
                    current_chapter=None,
                    results={},
                    metadata=self.config,
                )
                try:
                    await self.plugin_manager.finalize_all(plugin_context)
                    logger.info("✅ Plugin system finalized")
                except Exception as e:
                    logger.error(f"❌ Failed to finalize plugins: {e}")

    async def _execute_task(
        self,
        task: Task,
        goal: Dict[str, Any],
    ) -> None:
        """
        Execute a single task

        Args:
            task: The task to execute
            goal: Original creation goals
        """
        self.current_task = task
        task.status = "running"
        
        # 🔥 记录任务开始时间（用于统计）
        start_time = datetime.utcnow()
        task.started_at = start_time.isoformat()
        task.metadata["started_at"] = task.started_at

        # 🔥 初始化 token 和费用统计
        task_total_tokens = 0
        task_prompt_tokens = 0
        task_completion_tokens = 0
        task_cost = 0.0

        logger.info(f"Executing task {task.task_id}: {task.task_type.value}")

        # Determine which provider will be used (for UI display)
        selected_provider = self.llm_client._select_provider(task.task_type.value)
        task.metadata["llm_provider"] = selected_provider.value

        if self._on_task_start:
            await self._safe_callback(self._on_task_start, task)

        try:
            # 1. Get context from memory
            await self._send_step_progress(
                step="context_retrieval",
                message=f"🔍 正在检索相关上下文...",
                task_id=task.task_id,
                task_type=task.task_type.value
            )
            # 🔥 针对章节内容任务，增加 recent_count 确保能获取前几章内容
            task_type = task.task_type.value
            recent_count = 10 if task_type == "章节内容" else 3  # 章节内容需要更多历史上下文

            context = await self.memory.get_context(
                task_id=task.task_id,
                task_type=task_type,
                chapter_index=task.metadata.get("chapter_index"),
                recent_count=recent_count,
            )

            # 🔥 发送上下文检索完成事件
            # 使用 relevant_memories（按任务类型映射检索的）而不是 recent_results（按时间顺序的）
            context_types = list(set(r.get("task_type", "unknown") for r in context.relevant_memories[:5]))
            await self._send_step_progress(
                step="context_retrieval_complete",
                message=f"✅ 上下文检索完成 (检索到 {len(context.relevant_memories)} 条相关内容)",
                task_id=task.task_id,
                task_type=task.task_type.value,
                context_count=len(context.relevant_memories),
                context_types=context_types
            )

            # 2. Build prompt for the task
            await self._send_step_progress(
                step="building_prompt",
                message=f"📝 正在构建提示词...",
                task_id=task.task_id,
                task_type=task.task_type.value
            )

            # 🔥 调用插件的 before_task 钩子（让插件可以修改任务配置）
            if self.plugin_manager:
                from creative_autogpt.plugins.base import WritingContext
                plugin_context = WritingContext(
                    session_id=self.session_id,
                    goal=goal,
                    current_task=task.to_dict(),
                    current_chapter=task.metadata.get("chapter_index"),
                    results=context.recent_results,
                    metadata=self.config,
                    storage=self.session_storage,  # 🔥 传递 storage 用于插件数据持久化
                )
                try:
                    modified_task_dict = await self.plugin_manager.before_task(task.to_dict(), plugin_context)
                    # 如果插件修改了任务，更新任务对象（注意：这里简化处理，实际可能需要更复杂的逻辑）
                    if modified_task_dict != task.to_dict():
                        logger.debug(f"Plugin modified task {task.task_id}")
                except Exception as e:
                    logger.error(f"Plugin before_task hook failed: {e}")

            # 🔥 上下文增强：让插件为当前任务提供相关上下文
            if self.plugin_manager:
                try:
                    from creative_autogpt.plugins.base import WritingContext
                    enrich_context = WritingContext(
                        session_id=self.session_id,
                        goal=goal,
                        current_task=task.to_dict(),
                        current_chapter=task.metadata.get("chapter_index"),
                        results=context.recent_results,
                        metadata=self.config,
                        storage=self.session_storage,
                    )
                    enriched = await self.plugin_manager.enrich_context(task.to_dict(), enrich_context.to_dict())
                    if enriched:
                        logger.debug(f"Context enriched by plugins for task {task.task_id}")
                    else:
                        enriched = {}
                except Exception as e:
                    logger.error(f"Plugin enrich_context failed: {e}")
                    enriched = {}

            # 🔥 构建提示词（传递插件增强的上下文）
            prompt = await self._build_prompt(task, context, goal, enriched_context=enriched)

            # 🔥 存储提示词到任务元数据（供前端显示）
            task.metadata["prompt"] = prompt
            task.metadata["prompt_length"] = len(prompt)
            logger.debug(f"Stored prompt for task {task.task_id}, length: {len(prompt)}")

            # 🔥 发送提示词构建完成事件（包含提示词内容）
            await self._send_step_progress(
                step="prompt_built",
                message=f"✅ 提示词构建完成 (长度: {len(prompt)} 字符)",
                task_id=task.task_id,
                task_type=task.task_type.value,
                prompt=prompt,  # 🔥 添加提示词内容
                prompt_length=len(prompt)
            )

            # 3. Call LLM to generate content
            provider_name = {
                "qwen": "阿里云 Qwen",
                "deepseek": "DeepSeek",
                "ark": "字节跳动 Doubao"
            }.get(selected_provider.value, selected_provider.value)

            await self._send_step_progress(
                step="llm_call_start",
                message=f"🤖 正在调用 {provider_name} 生成内容...",
                task_id=task.task_id,
                task_type=task.task_type.value,
                llm_provider=selected_provider.value,
                llm_model="未知"
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                task_type=task.task_type.value,
                temperature=self._get_temperature_for_task(task.task_type),
                max_tokens=self._get_max_tokens_for_task(task.task_type),
            )

            # Update actual provider and model used (may differ due to fallback)
            task.metadata["llm_provider"] = response.provider.value
            task.metadata["llm_model"] = response.model

            self.stats.llm_calls += 1
            self.stats.tokens_used += response.usage.total_tokens

            # 🔥 累计 token 和费用
            task_total_tokens += response.usage.total_tokens
            task_prompt_tokens += response.usage.prompt_tokens
            task_completion_tokens += response.usage.completion_tokens
            task_cost += self._calculate_cost(response.provider.value, response.model, response.usage)

            # 🔥 发送 LLM 调用完成事件
            await self._send_step_progress(
                step="llm_call_complete",
                message=f"✅ 内容生成完成 (使用 {response.usage.total_tokens} tokens)",
                task_id=task.task_id,
                task_type=task.task_type.value,
                llm_provider=response.provider.value,
                llm_model=response.model,
                tokens_used=response.usage.total_tokens,
                content_length=len(response.content)
            )

            # 🔥 调用插件的 after_task 钩子（让插件可以修改生成的内容）
            if self.plugin_manager:
                from creative_autogpt.plugins.base import WritingContext
                plugin_context = WritingContext(
                    session_id=self.session_id,
                    goal=goal,
                    current_task=task.to_dict(),
                    current_chapter=task.metadata.get("chapter_index"),
                    results=context.recent_results,
                    metadata=self.config,
                    storage=self.session_storage,  # 🔥 传递 storage 用于插件数据持久化
                )
                try:
                    modified_content = await self.plugin_manager.after_task(task.to_dict(), response.content, plugin_context)
                    if modified_content != response.content:
                        logger.info(f"Plugin modified content for task {task.task_id}")
                        response.content = modified_content
                except Exception as e:
                    logger.error(f"Plugin after_task hook failed: {e}")

            # 🔥 数据验证：对结构化任务验证解析后的数据
            if self.plugin_manager:
                try:
                    # 定义哪些任务类型需要结构化验证，以及对应的插件
                    structured_tasks = {
                        "人物设计": "character",
                        "人物关系": "character",
                        "世界观规则": "worldview",
                        "势力设定": "worldview",
                        "事件": "event",
                        "伏笔列表": "foreshadow",
                        "时间线": "timeline",
                        "场景物品": "scene",
                        "对话检查": "dialogue",
                    }

                    if task_type in structured_tasks:
                        plugin_name = structured_tasks[task_type]
                        plugin = self.plugin_manager.get(plugin_name)

                        if plugin:
                            # 解析 JSON 数据
                            parsed_data = plugin.handle_json_parse_error(response.content, default_value=None)

                            if parsed_data is not None:
                                from creative_autogpt.plugins.base import WritingContext
                                validation_context = WritingContext(
                                    session_id=self.session_id,
                                    goal=goal,
                                    current_task=task.to_dict(),
                                    current_chapter=task.metadata.get("chapter_index"),
                                    results=context.recent_results,
                                    metadata=self.config,
                                    storage=self.session_storage,
                                )

                                result = await plugin.validate(parsed_data, validation_context)

                                # 记录验证结果
                                task.metadata["validation_result"] = {
                                    "plugin": plugin_name,
                                    "valid": result.valid,
                                    "errors": result.errors,
                                    "warnings": result.warnings,
                                    "suggestions": result.suggestions,
                                }

                                if not result.valid:
                                    logger.warning(f"Plugin '{plugin_name}' validation failed for task {task.task_id}: {result.errors}")
                                elif result.warnings:
                                    logger.info(f"Plugin '{plugin_name}' validation warnings for task {task.task_id}: {result.warnings}")
                                else:
                                    logger.debug(f"Plugin '{plugin_name}' validation passed for task {task.task_id}")
                            else:
                                logger.debug(f"Could not parse structured data for task type {task_type}, skipping validation")
                    else:
                        logger.debug(f"Task type '{task_type}' does not require structured validation")
                except Exception as e:
                    logger.error(f"Plugin validation failed: {e}")

            # 🔥 跨插件一致性检查：对于章节任务，检查插件间数据的一致性
            if self.plugin_manager and task_type in ["章节内容", "章节润色"]:
                try:
                    from creative_autogpt.plugins.base import WritingContext
                    consistency_context = WritingContext(
                        session_id=self.session_id,
                        goal=goal,
                        current_task=task.to_dict(),
                        current_chapter=task.metadata.get("chapter_index"),
                        results=context.recent_results,
                        metadata=self.config,
                        storage=self.session_storage,
                    )
                    consistency_result = self.plugin_manager.validate_cross_plugin_consistency(consistency_context)
                    if consistency_result and not consistency_result.get("consistent", True):
                        issues = consistency_result.get("issues", [])
                        if issues:
                            task.metadata["cross_plugin_issues"] = issues
                            logger.warning(f"Cross-plugin consistency issues found for task {task.task_id}: {issues}")
                except Exception as e:
                    logger.error(f"Cross-plugin consistency check failed: {e}")

            # 4. Evaluate quality
            # 🔥 所有任务都需要评估，包括创意脑暴
            # 创意脑暴检查与用户输入的一致性，其他任务检查前置任务一致性
            await self._send_step_progress(
                step="evaluation_start",
                message=f"📊 正在评估内容质量...",
                task_id=task.task_id,
                task_type=task.task_type.value
            )

            # 🔥 获取前置任务内容和章节上下文（用于跨任务一致性检查）
            task_type = task.task_type.value
            chapter_index = task.metadata.get("chapter_index", None)

            predecessor_contents = None
            chapter_context_str = None

            # 🔥 创意脑暴：基于用户输入进行一致性检查
            if task_type == "创意脑暴":
                # 将用户输入转换为前置内容格式，用于检查是否违背用户原始要求
                user_input_section = "### 用户创建项目时的原始输入\n\n"
                if goal.get('title'):
                    user_input_section += f"**项目标题**：{goal['title']}\n"
                if goal.get('genre'):
                    user_input_section += f"**类型/流派**：{goal['genre']}\n"
                if goal.get('style'):
                    user_input_section += f"**写作风格**：{goal['style']}\n"
                if goal.get('requirement'):
                    user_input_section += f"**创作要求**：{goal['requirement']}\n"
                if goal.get('word_count'):
                    wc = goal['word_count']
                    user_input_section += f"**目标字数**：{wc // 10000}万字\n" if wc >= 10000 else f"**目标字数**：{wc}字\n"
                if goal.get('chapter_count'):
                    user_input_section += f"**章节数量**：{goal['chapter_count']}章\n"

                predecessor_contents = {"用户输入": user_input_section}

            # 🔥 其他任务：检查前置任务
            else:
                predecessor_contents = self._get_predecessor_contents(task_type, context)

                # 对于章节相关任务，额外获取章节上下文
                if task_type in ["章节内容", "章节润色"] and chapter_index and isinstance(chapter_index, int):
                    previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=3)
                    outline_content = predecessor_contents.get("大纲", "") if predecessor_contents else ""
                    chapter_context_str = self._build_consistency_check_context(
                        chapter_index,
                        previous_chapters,
                        outline_content,
                        task_type,
                    )

            evaluation = await self.evaluator.evaluate(
                task_type=task.task_type.value,
                content=response.content,
                context=context.to_dict(),
                goal=goal,
                predecessor_contents=predecessor_contents,
                chapter_context=chapter_context_str,
            )

            # 🔥 获取质量评分和一致性评分
            quality_score = getattr(evaluation, "quality_score", evaluation.score)
            consistency_score = getattr(evaluation, "consistency_score", evaluation.score)

            # 🔥 发送评估完成事件
            await self._send_step_progress(
                step="evaluation_complete",
                message=f"📊 评估完成: 质量评分 {quality_score*10:.1f}/10, 一致性评分 {consistency_score*10:.1f}/10",
                task_id=task.task_id,
                task_type=task.task_type.value,
                quality_score=quality_score,
                consistency_score=consistency_score,
                passed=evaluation.passed
            )

            # 4.5 总览检查：确保任务输出与前面任务保持一致
            # 🔥 已合并到质量评估中，不再需要单独的一致性检查
            # 跨任务一致性和章节连贯性检查已在 evaluator.evaluate() 中完成
            skip_consistency_check = True  # 始终跳过单独的一致性检查

            if skip_consistency_check:
                consistency_check = {"passed": True, "issues": [], "suggestions": []}
                # 不再发送跳过事件，因为一致性检查已合并到质量评估中

            # 5. Handle evaluation result
            final_content = response.content
            if not evaluation.passed:
                logger.warning(
                    f"Task {task.task_id} failed evaluation (score: {evaluation.score:.3f})"
                )

                # 🔥 发送开始重写事件
                quality_score = getattr(evaluation, "quality_score", evaluation.score)
                consistency_score = getattr(evaluation, "consistency_score", evaluation.score)
                failed_reasons = []
                if quality_score < 0.7:
                    failed_reasons.append(f"质量评分 {quality_score*10:.1f}/10 (需要 >= 7.0)")
                if consistency_score < 0.7:
                    failed_reasons.append(f"一致性评分 {consistency_score*10:.1f}/10 (需要 >= 7.0)")

                await self._send_step_progress(
                    step="rewrite_start",
                    message=f"🔄 开始重写 (原因: {', '.join(failed_reasons)})",
                    task_id=task.task_id,
                    task_type=task.task_type.value,
                    rewrite_attempt=1,
                    quality_score=quality_score,
                    consistency_score=consistency_score
                )

                # 🔥 更新 session 状态（标记为正在重写）
                if self.session_storage:
                    await self.session_storage.update_session_rewrite_state(
                        session_id=self.session_id,
                        is_rewriting=True,
                        rewrite_attempt=1,
                        rewrite_task_id=task.task_id,
                        rewrite_task_type=task.task_type.value,
                    )

                # 🔥 传递当前的 token 统计用于累计
                rewrite_token_stats = {
                    "total_tokens": task_total_tokens,
                    "prompt_tokens": task_prompt_tokens,
                    "completion_tokens": task_completion_tokens,
                    "cost": task_cost,
                }

                # 🔥 添加 try-catch 处理重写失败
                try:
                    # 🔥 解包 4 个返回值：(final_content, token_stats_dict, evaluation, passed)
                    final_content, rewrite_token_stats, evaluation, passed = await self._attempt_rewrite(
                        task=task,
                        content=response.content,
                        evaluation=evaluation,
                        context=context,
                        goal=goal,
                        token_stats=rewrite_token_stats,
                    )
                    # 🔥 更新统计（重写成功）
                    task_total_tokens = rewrite_token_stats["total_tokens"]
                    task_prompt_tokens = rewrite_token_stats["prompt_tokens"]
                    task_completion_tokens = rewrite_token_stats["completion_tokens"]
                    task_cost = rewrite_token_stats["cost"]
                except Exception as rewrite_error:
                    # 🔥 重写失败，标记任务为失败并返回
                    logger.error(f"❌ 任务 {task.task_id} 重写失败: {rewrite_error}")

                    # 🔥 更新 session 状态（清除重写状态）
                    if self.session_storage:
                        await self.session_storage.update_session_rewrite_state(
                            session_id=self.session_id,
                            is_rewriting=False,
                            rewrite_attempt=None,
                            rewrite_task_id=None,
                            rewrite_task_type=None,
                        )

                    task.status = "failed"
                    task.error = str(rewrite_error)
                    self.planner.update_task_status(task.task_id, "failed")
                    self.stats.failed_tasks += 1

                    # 🔥 发送任务失败事件
                    await self._send_step_progress(
                        step="task_failed",
                        message=f"❌ {task.task_type.value} 任务失败: {str(rewrite_error)[:100]}",
                        task_id=task.task_id,
                        task_type=task.task_type.value,
                        error=str(rewrite_error)
                    )

                    # 🔥 仍然存储到内存（标记为失败），但返回不继续
                    memory_type = self._get_memory_type_for_task(task.task_type)
                    await self.memory.store(
                        content=response.content,  # 存储原始内容
                        task_id=task.task_id,
                        task_type=task.task_type.value,
                        memory_type=memory_type,
                        metadata=task.metadata,
                        chapter_index=task.metadata.get("chapter_index"),
                        evaluation=evaluation.to_dict(),
                    )

                    # 🔥 返回，不继续执行
                    return

            # 6. Store in memory
            memory_type = self._get_memory_type_for_task(task.task_type)
            await self.memory.store(
                content=final_content,
                task_id=task.task_id,
                task_type=task.task_type.value,
                memory_type=memory_type,
                metadata=task.metadata,
                chapter_index=task.metadata.get("chapter_index"),
                evaluation=evaluation.to_dict(),
            )

            # 🔥 插件状态同步：让插件之间同步数据
            if self.plugin_manager:
                try:
                    from creative_autogpt.plugins.base import WritingContext
                    sync_context = WritingContext(
                        session_id=self.session_id,
                        goal=goal,
                        current_task=task.to_dict(),
                        current_chapter=task.metadata.get("chapter_index"),
                        results=context.recent_results,
                        metadata=self.config,
                        storage=self.session_storage,
                    )
                    await self.plugin_manager.sync_plugin_states(sync_context)
                    logger.debug(f"Plugin states synced after task {task.task_id}")
                except Exception as e:
                    logger.error(f"Plugin state sync failed: {e}")

            # 6.5 🎯 检查是否为高分内容，记录为示例
            await self._check_and_save_high_score_example(
                task_type=task.task_type.value,
                genre=goal.get('genre', '通用'),
                content=final_content,
                score=evaluation.score,
                evaluation=evaluation,
            )

            # 7. Check if approval is needed
            # 🔥 所有任务都需要手动审批（用户要一个一个审核）
            # 创意脑暴任务需要等待用户选择点子
            requires_approval = True  # 强制所有任务都需要审批
            is_brainstorm = task.task_type.value == "创意脑暴"
            
            if requires_approval:
                # 为创意脑暴添加特殊标记，告诉前端需要用户选择点子
                
                logger.info(f"Task {task.task_id} waiting for approval" + 
                           (" (requires idea selection)" if is_brainstorm else ""))
                self.status = ExecutionStatus.WAITING_APPROVAL
                self.is_waiting_approval = True
                
                # 设置任务元数据，标记需要选择
                if is_brainstorm:
                    task.metadata["requires_selection"] = True
                    task.metadata["selection_type"] = "idea"
                    task.metadata["selection_count"] = 4  # 4个点子供选择
                
                # Notify frontend that approval is needed
                if self._on_task_approval_needed:
                    await self._safe_callback(
                        self._on_task_approval_needed,
                        task,
                        final_content,
                        evaluation,
                    )
                
                # Wait for approval
                self._approval_event.clear()
                await self._approval_event.wait()
                
                # Check approval result
                if not self.approval_result or self.approval_result.get('action') != 'approve':
                    if self.approval_result and self.approval_result.get('action') == 'reject':
                        # User rejected, mark as failed and skip
                        task.status = "skipped"
                        task.error = "Rejected by user"
                        self.planner.update_task_status(task.task_id, "skipped")
                        self.stats.skipped_tasks += 1
                        self.is_waiting_approval = False
                        self.status = ExecutionStatus.RUNNING
                        return
                    elif self.approval_result and self.approval_result.get('action') == 'regenerate':
                        # User wants to regenerate, retry the task
                        logger.info(f"Regenerating task {task.task_id}")
                        self.is_waiting_approval = False
                        self.status = ExecutionStatus.RUNNING
                        await self._execute_task(task, goal)
                        return
                
                # 处理创意脑暴的点子选择
                if is_brainstorm and self.approval_result:
                    selected_idea = self.approval_result.get('selected_idea')
                    if selected_idea:
                        logger.info(f"User selected idea {selected_idea} for brainstorm task")
                        # 将选择的点子编号存入任务元数据，供后续大纲任务使用
                        task.metadata["selected_idea"] = selected_idea
                        # 更新内存中的内容，标记选中的点子
                        final_content = f"【用户选择】点子{selected_idea}\n\n{final_content}"
                        # 重新存储更新后的内容
                        await self.memory.store(
                            content=final_content,
                            task_id=task.task_id,
                            task_type=task.task_type.value,
                            memory_type=memory_type,
                            metadata=task.metadata,
                            chapter_index=task.metadata.get("chapter_index"),
                            evaluation=evaluation.to_dict(),
                        )
                
                self.is_waiting_approval = False
                self.status = ExecutionStatus.RUNNING

            # 8. Update task status
            task.status = "completed"
            task.result = final_content
            
            # 🔥 记录任务完成时间和统计信息
            end_time = datetime.utcnow()
            task.completed_at = end_time.isoformat()
            task.execution_time_seconds = (end_time - start_time).total_seconds()
            task.total_tokens = task_total_tokens
            task.prompt_tokens = task_prompt_tokens
            task.completion_tokens = task_completion_tokens
            task.cost_usd = task_cost
            
            # 也更新到 metadata 中（方便前端访问）
            task.metadata["completed_at"] = task.completed_at
            task.metadata["execution_time_seconds"] = task.execution_time_seconds
            task.metadata["total_tokens"] = task.total_tokens
            task.metadata["prompt_tokens"] = task.prompt_tokens
            task.metadata["completion_tokens"] = task.completion_tokens
            task.metadata["cost_usd"] = round(task.cost_usd, 6)
            task.metadata["failed_attempts"] = task.failed_attempts
            # 🔥 添加完整提示词到 metadata（方便用户查看）
            task.metadata["prompt"] = prompt
            
            self.planner.update_task_status(
                task.task_id,
                "completed",
                result=final_content,
            )

            self.stats.completed_tasks += 1

            logger.info(
                f"Task {task.task_id} completed: {len(final_content)} chars, "
                f"tokens: {task_total_tokens}, time: {task.execution_time_seconds:.1f}s, cost: ${task.cost_usd:.4f}"
            )

            # 9. 自我评估和提示词进化（异步执行，不阻塞主流程）
            if self.enable_self_evolution:
                asyncio.create_task(
                    self._self_evolution_pipeline(
                        task=task,
                        content=final_content,
                        prompt=prompt,
                        evaluation_score=evaluation.score,
                        context=context,
                        goal=goal,
                    )
                )

            if self._on_task_complete:
                await self._safe_callback(
                    self._on_task_complete,
                    task,
                    final_content,
                    evaluation,
                )

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)

            task.status = "failed"
            task.error = str(e)
            self.planner.update_task_status(
                task.task_id,
                "failed",
                error=str(e),
            )

            self.stats.failed_tasks += 1

            # 🔥 尝试获取 evaluation 信息（如果有的话）
            eval_info = None
            if 'evaluation' in locals() and evaluation is not None:
                # 存储 evaluation 信息到 task.metadata，这样前端可以访问
                task.metadata["evaluation"] = evaluation.to_dict()
                eval_info = evaluation.to_dict()

            if self._on_task_fail:
                # 🔥 传递 task 对象，这样前端可以访问 metadata 中的 evaluation
                await self._safe_callback(
                    self._on_task_fail,
                    task,
                    str(e),
                )

            # Check if we should continue on error
            if not self.config.get("continue_on_error", False):
                raise

    async def _self_evolution_pipeline(
        self,
        task: Task,
        content: str,
        prompt: str,
        evaluation_score: float,
        context: MemoryContext,
        goal: Dict[str, Any],
    ) -> None:
        """
        自我进化管道：评估内容质量并优化提示词
        
        这是一个后台任务，不会阻塞主流程。
        
        Pipeline 步骤：
        1. 使用 SelfEvaluator 对生成内容进行深度评估
        2. 将评估结果记录到 PromptEvolver
        3. 如果满足条件，触发提示词优化
        
        Args:
            task: 当前任务
            content: 生成的内容
            prompt: 使用的提示词
            evaluation_score: 初步评估分数
            context: 任务上下文
            goal: 创作目标
        """
        task_type = task.task_type.value
        
        try:
            # 1. 深度自我评估
            logger.info(f"🔍 开始自我评估任务: {task_type}")

            # 🔥 获取前置任务内容和章节上下文（用于自我评估）
            chapter_index = task.metadata.get("chapter_index", None)

            predecessor_contents = None
            chapter_context_str = None

            if task_type != "创意脑暴":
                predecessor_contents = self._get_predecessor_contents(task_type, context)

                if task_type in ["章节内容", "章节润色"] and chapter_index and isinstance(chapter_index, int):
                    previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=3)
                    outline_content = predecessor_contents.get("大纲", "") if predecessor_contents else ""
                    chapter_context_str = self._build_consistency_check_context(
                        chapter_index,
                        previous_chapters,
                        outline_content,
                        task_type,
                    )

            self_eval_result = await self.self_evaluator.evaluate(
                task_type=task_type,
                content=content,
                context=context.to_dict() if hasattr(context, 'to_dict') else {},
                goal=goal,
                predecessor_contents=predecessor_contents,
                chapter_context=chapter_context_str,
            )
            
            # 2. 记录提示词性能
            # 合并初步评估分数和深度评估分数
            combined_score = (evaluation_score * 0.4 + self_eval_result.overall_score / 100 * 0.6)
            
            # 构建反馈信息
            feedback = self._build_evolution_feedback(self_eval_result)
            
            self.prompt_evolver.record_performance(
                task_type=task_type,
                prompt=prompt,
                score=combined_score * 100,  # 转为百分制
                feedback=feedback,
            )
            
            logger.info(
                f"📊 评估完成: {task_type}, 综合分数: {combined_score * 100:.1f}, "
                f"优点: {len(self_eval_result.strengths)}, 不足: {len(self_eval_result.weaknesses)}"
            )
            
            # 3. 检查是否需要触发提示词优化
            # 只在分数较低时考虑优化
            if combined_score < 0.75:
                logger.info(f"⚠️ {task_type} 任务分数较低 ({combined_score * 100:.1f})，考虑优化提示词")
                
                # 获取改进见解
                insights = self.self_evaluator.get_improvement_insights(task_type)
                
                if insights.get("optimization_recommended"):
                    logger.info(f"🚀 触发提示词优化: {task_type}")
                    await self.prompt_evolver.evolve_prompt(
                        task_type=task_type,
                        current_prompt=prompt,
                    )
            
            # 4. 将评估历史保存（用于后续分析）
            # 评估结果在 evaluate() 方法中已自动保存
            self.prompt_evolver.save_all_data()
            
        except Exception as e:
            # 自我进化失败不应该影响主流程
            logger.warning(f"⚠️ 自我进化管道异常: {e}", exc_info=True)

    def _build_evolution_feedback(self, eval_result) -> str:
        """
        根据评估结果构建进化反馈
        
        Args:
            eval_result: SelfEvaluator 的评估结果
            
        Returns:
            结构化的反馈文本，用于提示词优化
        """
        feedback_parts = []
        
        # 添加维度分数
        if eval_result.dimensions:
            score_summary = "维度分数: " + ", ".join(
                f"{k}={v:.0f}" for k, v in eval_result.dimensions.items()
            )
            feedback_parts.append(score_summary)
        
        # 添加优点（简化）
        if eval_result.strengths:
            feedback_parts.append(f"优点: {'; '.join(eval_result.strengths[:3])}")
        
        # 添加不足（更详细，因为这是需要改进的）
        if eval_result.weaknesses:
            feedback_parts.append(f"不足: {'; '.join(eval_result.weaknesses)}")
        
        # 添加改进建议
        if eval_result.suggestions:
            feedback_parts.append(f"建议: {'; '.join(eval_result.suggestions[:3])}")
        
        return "\n".join(feedback_parts)

    async def _check_task_consistency(
        self,
        task: Task,
        content: str,
        context: MemoryContext,
        goal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        检查任务输出与前面任务的一致性
        使用Qwen的长上下文能力进行全面检查，确保没有偏离已有设定
        
        关键增强：
        1. 利用Qwen 128K上下文能力，带入更多参考内容
        2. 对于章节内容，带入章节大纲和前面章节内容进行对比
        3. 返回详细的问题描述和修改建议
        
        Returns:
            dict with keys: passed (bool), issues (list of str), suggestions (list of str)
        """
        task_type = task.task_type.value
        chapter_index = task.metadata.get("chapter_index", None)
        
        # 不需要一致性检查的任务
        # - 创意脑暴：第一个任务，没有前置内容可参照
        if task_type == "创意脑暴":
            return {"passed": True, "issues": [], "suggestions": []}
        
        # 获取前置任务内容
        predecessor_contents = self._get_predecessor_contents(task_type, context)
        
        if not predecessor_contents:
            return {"passed": True, "issues": [], "suggestions": []}
        
        # 🔥 对于章节相关任务，额外获取章节大纲和前面章节内容
        chapter_context = ""
        if task_type in ["章节内容", "章节润色"] and chapter_index and isinstance(chapter_index, int):
            # 获取前面的章节
            previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=3)
            outline_content = predecessor_contents.get("大纲", "")
            
            # 构建章节上下文（用于一致性检查）
            chapter_context = self._build_consistency_check_context(
                chapter_index,
                previous_chapters,
                outline_content,
                task_type,
            )
        
        # 构建一致性检查提示词
        check_prompt = f"""## 任务一致性检查 🔍

你是一位**顶级畅销小说**的资深编辑，负责确保创作内容的严格一致性。

⚠️ **这是一个关键检查点**：任何与前面任务不一致的内容都会破坏整个故事的完整性！

### 当前任务
- 任务类型：{task_type}
{f"- 章节：第{chapter_index}章" if chapter_index else ""}

### 当前任务的输出内容
```
{content[:8000]}{"..." if len(content) > 8000 else ""}
```

{chapter_context}

### 前面任务的核心成果（必须严格保持一致）
"""
        # 按重要性添加前置内容
        priority_list = ["大纲", "人物设计", "世界观规则", "事件", "伏笔列表"]
        for pred_type in priority_list:
            if pred_type in predecessor_contents:
                pred_content = predecessor_contents[pred_type]
                # 对于关键内容给予更多空间
                max_len = 4000 if pred_type in ["人物设计", "大纲"] else 2000
                check_prompt += f"\n#### {pred_type}\n```\n{pred_content[:max_len]}{'...' if len(pred_content) > max_len else ''}\n```\n"

        check_prompt += f"""

### 检查要求（请严格执行！）

请检查当前任务的输出是否与前面的任务**严格保持一致**，重点检查：

1. **大纲一致性**（最重要！）
   - 是否紧扣【大纲】中定义的主角目标和核心冲突？
   - 是否服务于大纲的核心情感钩子？

2. **人物一致性**
   - 如果涉及人物，是否使用了【人物设计】中已有的角色？
   - 人物的性格、背景、目标是否与设计一致？
   - 有没有凭空出现的新角色（应该避免）？

3. **世界观一致性**
   - 是否符合【世界观规则】中的设定？
   - 有没有违反已设定的规则？
   - 新增的设定是否与已有设定冲突？

4. **逻辑一致性**
   - 与前面的内容是否存在逻辑矛盾？
   - 时间线是否合理？

{f'''5. **章节连贯性**（针对第{chapter_index}章）
   - 本章开头是否自然衔接上一章结尾？
   - 人物状态、位置、情绪是否延续？
   - 时间线是否连贯？
   - 有没有像独立短篇，与前面脱节？
''' if chapter_index and chapter_index > 1 else ''}

### ⚠️ 评判标准（请严格执行）
- 只要发现**任何一个**上述问题，就必须将 `passed` 设为 `false`
- 评分标准：0.9+（完全一致）、0.7-0.9（小问题）、0.7以下（严重问题）
- 章节连贯性问题必须严格判定！脱节的章节必须判为不通过！

### 输出格式
请严格按照以下JSON格式输出：
```json
{{
  "passed": true/false,
  "score": 0.0-1.0,
  "issues": ["具体问题描述1", "具体问题描述2"],
  "suggestions": ["如何修改的具体建议1", "如何修改的具体建议2"],
  "continuity_issues": ["章节连贯性问题1", "章节连贯性问题2"]
}}
```

如果没有发现问题，passed为true，issues为空数组。
如果发现问题，passed为false，列出**具体的**问题和**可操作的**修改建议。

请直接输出JSON，不要有其他内容。
"""
        
        try:
            # 🔥 使用 Qwen-long 进行评估（利用其128K上下文能力）
            # 通过指定 model_type 为 LONG_CONTEXT 来确保使用 Qwen
            response = await self.llm_client.generate(
                prompt=check_prompt,
                task_type="一致性检查",  # 会路由到支持长上下文的模型
                temperature=0.2,  # 降低温度，让检查更严格
                max_tokens=2000,  # 增加token，确保能输出完整的问题描述
            )
            
            # 解析响应
            import json
            import re
            
            # 尝试从响应中提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "passed": result.get("passed", True),
                    "score": result.get("score", 1.0),
                    "issues": result.get("issues", []),
                    "suggestions": result.get("suggestions", []),
                    "continuity_issues": result.get("continuity_issues", []),
                }
            else:
                logger.warning(f"Could not parse consistency check response: {response.content[:200]}")
                return {"passed": True, "issues": [], "suggestions": []}
                
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            # 如果检查失败，默认通过（不阻塞流程）
            return {"passed": True, "issues": [], "suggestions": []}

    def _get_predecessor_contents(
        self,
        task_type: str,
        context: MemoryContext,
    ) -> Dict[str, str]:
        """
        获取当前任务所需的前置任务内容
        
        Args:
            task_type: 当前任务类型
            context: 任务上下文，包含前面任务的结果
            
        Returns:
            前置任务内容的字典，key 是任务类型，value 是任务输出内容
        """
        # 定义每个任务需要的前置任务
        # 完整流程：
        # 创意脑暴 → 大纲 → 世界观规则 → 势力设计 → 场景设计 → 人物设计 → 功法法宝 → 主角成长 → 反派设计 → 事件 → 时间线 → 伏笔列表 → 章节内容
        # 质量检查（一致性检查、对话检查）在每章生成后自动运行
        task_dependencies = {
            # Phase 0: 创意脑暴阶段
            "创意脑暴": [],  # 第一个任务，无依赖

            # Phase 1: 大纲设计（结构优先！）
            "大纲": ["创意脑暴"],  # 🔥 大纲直接基于脑暴结果，包含故事核心

            # Phase 2: 元素设计（基于大纲）
            "世界观规则": ["大纲"],  # 世界观服务于大纲
            "势力设计": ["大纲", "世界观规则"],  # 势力基于世界观规则
            "场景设计": ["大纲", "世界观规则", "势力设计"],  # 场景基于世界观和势力
            "人物设计": ["大纲", "世界观规则", "势力设计"],  # 人物在势力中完成大纲
            "功法法宝": ["大纲", "世界观规则", "势力设计"],  # 功法基于世界观和势力
            "主角成长": ["大纲", "世界观规则", "功法法宝", "人物设计"],  # 成长路径基于功法和人物
            "反派设计": ["大纲", "人物设计", "主角成长", "势力设计"],  # 反派基于主角和势力

            # Phase 3: 详细规划
            "事件": ["大纲", "世界观规则", "势力设计", "场景设计", "人物设计", "反派设计"],  # 事件综合所有元素
            "时间线": ["大纲", "人物设计", "事件", "主角成长"],  # 时间线基于事件和成长
            "伏笔列表": ["大纲", "势力设计", "人物设计", "事件", "时间线"],  # 伏笔基于事件和时间线

            # Phase 4: 章节创作 - 🔴 必须包含所有基础设定！
            # 基础设定 = 大纲 + 世界观规则 + 势力设计 + 场景设计 + 人物设计 + 功法法宝 + 主角成长 + 反派设计 + 事件 + 时间线 + 伏笔列表
            # 上一章内容通过 _get_previous_chapters() 单独获取
            "章节内容": ["大纲", "世界观规则", "势力设计", "场景设计", "人物设计", "功法法宝", "主角成长", "反派设计", "事件", "时间线", "伏笔列表"],

            # Phase 5: 质量检查（每章后自动运行）
            "一致性检查": ["章节内容"],  # 检查刚生成的章节
            "对话检查": ["章节内容"],  # 检查刚生成的章节对话
        }
        
        needed_tasks = task_dependencies.get(task_type, [])
        predecessor_contents = {}
        
        # 从 recent_results 中提取前置任务内容
        if context.recent_results:
            for result in context.recent_results:
                result_type = result.get("task_type", "")
                if result_type in needed_tasks:
                    predecessor_contents[result_type] = result.get("content", "")
        
        # 从 relevant_memories 中补充
        if context.relevant_memories:
            for mem in context.relevant_memories:
                # 尝试从 content 中识别任务类型
                mem_type = mem.get("memory_type", "")
                content = mem.get("content", "")
                # 检查是否是需要的任务类型（通过 memory_type 或内容匹配）
                for needed in needed_tasks:
                    if needed not in predecessor_contents and needed.lower() in mem_type.lower():
                        predecessor_contents[needed] = content
        
        return predecessor_contents

    async def _analyze_context_needs(
        self,
        task: Task,
        goal: Dict[str, Any],
        predecessor_contents: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        使用LLM动态分析当前任务需要哪些上下文信息
        
        让LLM自己决定需要参考哪些内容，而不是使用固定规则。
        这样可以更智能地选择相关上下文，避免信息过载。
        
        Args:
            task: 当前任务
            goal: 创作目标
            predecessor_contents: 所有可用的前置任务内容
            
        Returns:
            包含选择的上下文和理由的字典：
            {
                "selected_contexts": ["大纲", "人物设计", ...],
                "context_focus": {"大纲": "需要关注主角动机", ...},
                "reasoning": "选择理由"
            }
        """
        task_type = task.task_type.value
        chapter_index = task.metadata.get("chapter_index", None)
        
        # 构建可用上下文列表
        available_contexts = list(predecessor_contents.keys())
        if not available_contexts:
            return {
                "selected_contexts": [],
                "context_focus": {},
                "reasoning": "没有可用的前置任务内容"
            }
        
        # 构建分析提示词
        analysis_prompt = f"""
你是一位经验丰富的小说创作顾问。你正在帮助一位作家完成创作任务。

## 当前任务信息
- **任务类型**: {task_type}
- **章节**: {f"第{chapter_index}章" if chapter_index else "非章节任务"}
- **创作目标**: {goal.get('theme', '未指定主题')}

## 可用的参考资料

以下是你可以参考的前置任务成果（按重要性排序）：

{chr(10).join([f"- **{name}**: {len(content)}字" for name, content in predecessor_contents.items()])}

## 你的任务

请分析当前任务（{task_type}）最需要参考哪些内容，以及需要重点关注什么。

**注意**：
1. 不要选择所有内容！只选择**真正必要**的
2. 对于章节创作，前面章节的内容和大纲是必需的
3. 说明每个选择需要关注的**具体方面**

请用JSON格式输出：
```json
{{
    "selected_contexts": ["需要的内容1", "需要的内容2"],
    "context_focus": {{
        "需要的内容1": "需要关注的具体方面",
        "需要的内容2": "需要关注的具体方面"
    }},
    "reasoning": "为什么选择这些内容的简短理由"
}}
```
"""
        
        try:
            # 使用LLM进行分析
            response = await self.llm_client.generate(
                prompt=analysis_prompt,
                task_type="上下文分析",
                temperature=0.3,  # 低温度，更确定性
                max_tokens=1000,
            )
            
            # 解析JSON响应
            import re
            import json
            
            response_text = response.content  # 从 LLMResponse 对象获取内容
            
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # 尝试直接解析整个响应
                result = json.loads(response_text)
            
            # 验证选择的上下文是否有效
            valid_contexts = [ctx for ctx in result.get("selected_contexts", []) if ctx in predecessor_contents]
            result["selected_contexts"] = valid_contexts
            
            logger.info(f"🧠 动态上下文分析完成: 选择了 {len(valid_contexts)} 个上下文 - {valid_contexts}")
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 动态上下文分析失败，使用默认规则: {e}")
            # 失败时返回所有内容（降级策略）
            return {
                "selected_contexts": list(predecessor_contents.keys()),
                "context_focus": {},
                "reasoning": f"分析失败，使用全部内容: {str(e)}"
            }

    def _build_focused_context_section(
        self,
        predecessor_contents: Dict[str, str],
        context_analysis: Dict[str, Any],
    ) -> str:
        """
        根据动态分析结果构建聚焦的上下文部分
        
        Args:
            predecessor_contents: 所有前置任务内容
            context_analysis: 动态分析结果
            
        Returns:
            聚焦的上下文提示词
        """
        selected = context_analysis.get("selected_contexts", [])
        focus = context_analysis.get("context_focus", {})
        reasoning = context_analysis.get("reasoning", "")
        
        if not selected:
            return ""
        
        sections = []
        
        sections.append(f"""
╔══════════════════════════════════════════════════════════════════╗
║  🎯 聚焦参考资料 - 经过智能分析后的必要信息                     ║
╚══════════════════════════════════════════════════════════════════╝

📝 **选择理由**: {reasoning}

---

""")
        
        # 按选择顺序展示内容
        for ctx_name in selected:
            if ctx_name not in predecessor_contents:
                continue
                
            content = predecessor_contents[ctx_name]
            focus_point = focus.get(ctx_name, "")
            
            # 根据是否有焦点来决定展示多少内容
            if focus_point:
                # 有明确焦点，截取更短
                max_len = 1500
                sections.append(f"\n### 📌 {ctx_name}\n")
                sections.append(f"**关注重点**: {focus_point}\n\n")
            else:
                # 没有明确焦点，展示更多
                max_len = 2500
                sections.append(f"\n### {ctx_name}\n")
            
            # 截取内容
            if len(content) > max_len:
                content = content[:max_len] + "\n...\n（内容已截断，请聚焦上述要点）"
            
            sections.append(f"```\n{content}\n```\n")
        
        sections.append("""
---

💡 **使用指南**：
- 以上是经过分析后认为对当前任务最重要的参考资料
- 请特别关注标注的"关注重点"
- 确保你的创作与这些内容保持一致

""")
        
        return "".join(sections)

    async def _get_previous_chapters(
        self,
        current_chapter: int,
        context: MemoryContext,
        max_chapters: int = 3,
    ) -> Dict[int, Dict[str, str]]:
        """
        获取前面章节的内容，用于保持故事连贯性
        
        Args:
            current_chapter: 当前章节号
            context: 记忆上下文
            max_chapters: 最多获取多少章（默认前3章，避免上下文过长）
            
        Returns:
            字典，key是章节号，value是包含outline和content的字典
        """
        previous_chapters = {}
        
        # 从 recent_results 中查找前面章节
        if context.recent_results:
            for result in context.recent_results:
                task_type = result.get("task_type", "")
                chapter_index = result.get("chapter_index")
                
                if chapter_index is not None and chapter_index < current_chapter:
                    if chapter_index not in previous_chapters:
                        previous_chapters[chapter_index] = {}
                    
                    if task_type == "章节大纲":
                        previous_chapters[chapter_index]["outline"] = result.get("content", "")
                    elif task_type in ("章节内容", "章节润色"):
                        # 优先使用润色后的内容
                        if task_type == "章节润色" or "content" not in previous_chapters[chapter_index]:
                            previous_chapters[chapter_index]["content"] = result.get("content", "")
        
        # 从 relevant_memories 中补充
        if context.relevant_memories:
            for mem in context.relevant_memories:
                chapter_index = mem.get("chapter_index")
                mem_type = mem.get("memory_type", "").lower()
                
                if chapter_index is not None and chapter_index < current_chapter:
                    if chapter_index not in previous_chapters:
                        previous_chapters[chapter_index] = {}
                    
                    content = mem.get("content", "")
                    if "章节大纲" in mem_type and "outline" not in previous_chapters[chapter_index]:
                        previous_chapters[chapter_index]["outline"] = content
                    elif ("章节内容" in mem_type or "章节润色" in mem_type) and "content" not in previous_chapters[chapter_index]:
                        previous_chapters[chapter_index]["content"] = content
        
        # 只保留最近的 max_chapters 章
        if len(previous_chapters) > max_chapters:
            sorted_chapters = sorted(previous_chapters.keys(), reverse=True)[:max_chapters]
            previous_chapters = {k: previous_chapters[k] for k in sorted_chapters}
        
        return previous_chapters

    def _build_chapter_continuity_context(
        self,
        current_chapter: int,
        previous_chapters: Dict[int, Dict[str, str]],
        outline_content: str,
    ) -> str:
        """
        构建章节连贯性上下文
        
        Args:
            current_chapter: 当前章节号
            previous_chapters: 前面章节的内容
            outline_content: 总大纲内容
            
        Returns:
            连贯性上下文字符串
        """
        if not previous_chapters and not outline_content:
            return ""
        
        sections = []
        
        sections.append("""
╔══════════════════════════════════════════════════════════════════╗
║  🔗 故事连贯性约束 - 必须与前面章节紧密衔接！                  ║
╚══════════════════════════════════════════════════════════════════╝

⚠️ **核心要求**：
- 当前章节必须**承接前面的情节**，不能像独立的小故事
- 人物状态、情感、位置必须**延续**前一章结尾
- 悬念、伏笔必须**有回应**或**继续铺垫**
- 时间线必须**连贯**，不能出现跳跃或矛盾

""")
        
        # 添加总大纲摘要（帮助理解整体走向）
        if outline_content:
            sections.append(f"""
### 📋 故事总大纲（参考整体走向）

```
{outline_content[:2000]}{"..." if len(outline_content) > 2000 else ""}
```

""")
        
        # 添加前面章节的内容
        if previous_chapters:
            sorted_chapters = sorted(previous_chapters.keys())
            
            for chapter_num in sorted_chapters:
                chapter_data = previous_chapters[chapter_num]
                
                sections.append(f"""
### 📖 第{chapter_num}章 回顾

""")
                
                if chapter_data.get("outline"):
                    sections.append(f"""
**章节大纲**：
```
{chapter_data["outline"][:800]}{"..." if len(chapter_data.get("outline", "")) > 800 else ""}
```

""")
                
                if chapter_data.get("content"):
                    content = chapter_data["content"]
                    # 提取结尾部分（最后500字左右），这对衔接最重要
                    ending = content[-800:] if len(content) > 800 else content
                    sections.append(f"""
**章节结尾**（必须从这里衔接！）：
```
{ending}
```

""")
        
        # 添加连贯性检查清单
        sections.append(f"""
### ✅ 连贯性检查清单（写作时必须确认）

- [ ] **人物状态**：第{current_chapter}章开头的人物状态是否与前一章结尾一致？
- [ ] **时间连续**：时间是否连贯？如有跳跃是否交代清楚？
- [ ] **空间连续**：人物位置是否合理过渡？
- [ ] **情节承接**：是否回应了前面的悬念/冲突？
- [ ] **情感延续**：人物情绪是否有合理的延续或转变？
- [ ] **伏笔处理**：是否有伏笔需要揭示或继续铺垫？

""")
        
        return "\n".join(sections)

    def _build_consistency_check_context(
        self,
        current_chapter: int,
        previous_chapters: Dict[int, Dict[str, str]],
        outline_content: str,
        task_type: str,
    ) -> str:
        """
        构建一致性检查专用的上下文
        
        与 _build_chapter_continuity_context 类似，但专门用于一致性检查，
        会包含更详细的内容以便检查连贯性问题。
        
        Args:
            current_chapter: 当前章节号
            previous_chapters: 前面章节的内容
            outline_content: 总大纲内容
            task_type: 当前任务类型
            
        Returns:
            一致性检查上下文字符串
        """
        if not previous_chapters and not outline_content:
            return ""
        
        sections = []
        
        sections.append(f"""
### 🔗 章节连贯性检查参考（针对第{current_chapter}章）

""")
        
        # 添加总大纲（完整版，利用 Qwen 的长上下文）
        if outline_content:
            sections.append(f"""
#### 📋 故事总大纲
```
{outline_content[:6000]}{"..." if len(outline_content) > 6000 else ""}
```

""")
        
        # 添加前面章节的内容（尽量完整）
        if previous_chapters:
            sorted_chapters = sorted(previous_chapters.keys())
            
            for chapter_num in sorted_chapters:
                chapter_data = previous_chapters[chapter_num]
                
                sections.append(f"""
#### 📖 第{chapter_num}章

""")
                
                if chapter_data.get("outline"):
                    outline = chapter_data["outline"]
                    sections.append(f"""
**大纲**：
```
{outline[:1500]}{"..." if len(outline) > 1500 else ""}
```

""")
                
                if chapter_data.get("content"):
                    content = chapter_data["content"]
                    # 对于一致性检查，给更多内容（特别是前一章的结尾部分）
                    if chapter_num == current_chapter - 1:
                        # 前一章，给更多结尾内容
                        ending = content[-2000:] if len(content) > 2000 else content
                        sections.append(f"""
**结尾部分**（必须衔接）：
```
{ending}
```

""")
                    else:
                        # 更早的章节，给简短摘要
                        ending = content[-800:] if len(content) > 800 else content
                        sections.append(f"""
**结尾摘要**：
```
{ending}
```

""")
        
        sections.append(f"""
#### ⚠️ 一致性检查重点

请特别检查第{current_chapter}章：
1. **开头衔接**：是否自然承接第{current_chapter - 1}章的结尾？
2. **人物状态**：人物的位置、情绪、状态是否延续？
3. **时间线**：时间是否连贯，有无跳跃或矛盾？
4. **情节连贯**：是否像一个完整故事的一部分，而非独立短篇？

""")
        
        return "\n".join(sections)

    def _build_foundation_reference(
        self,
        predecessor_contents: Dict[str, str],
        task_type: str,
    ) -> str:
        """
        构建基础设定参考部分 - 章节创作必看！

        基础设定（is_foundation=True的任务）是整个故事的锚点：
        - 大纲：故事骨架和核心，必须按此推进
        - 世界观规则：世界运作的限制，不能违反
        - 人物设计：角色设定，行为必须符合性格

        Args:
            predecessor_contents: 前置任务内容
            task_type: 当前任务类型

        Returns:
            基础设定参考字符串
        """
        if not predecessor_contents:
            return ""

        # 定义基础设定任务（与 task_planner.py 中 is_foundation=True 的任务对应）
        foundation_tasks = ["大纲", "世界观规则", "势力设计", "场景设计", "人物设计", "功法法宝", "主角成长", "反派设计", "事件", "时间线", "伏笔列表"]

        # 提取存在的基础设定内容
        foundation_contents = {
            k: v for k, v in predecessor_contents.items()
            if k in foundation_tasks
        }
        
        if not foundation_contents:
            return ""
        
        sections = []
        
        sections.append("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔴 【基础设定参考 - 绝对不能违反！】                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  以下内容是整个故事的"宪法"，章节创作必须严格遵守！                         ║
║  任何偏离都会导致故事不连贯、人物崩坏、世界观矛盾！                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

⚠️ 警告：写作前请仔细阅读以下基础设定，写作中请反复对照确认！

""")
        
        # 按重要程度排序展示基础设定
        priority_order = [
            ("大纲", "📋 故事大纲（核心和章节规划）", "所有创作必须围绕大纲展开，本章内容必须符合大纲中的规划"),
            ("世界观规则", "🌍 世界观规则（运作限制）", "所有行为和事件必须符合世界规则"),
            ("人物设计", "👤 人物设计（角色设定）", "人物言行必须符合性格，不能崩人设"),
            ("事件", "⚡ 事件（具体发生什么）", "本章应包含相应的事件"),
            ("伏笔列表", "🔮 伏笔列表（埋设和回收）", "本章应埋设或回收相应伏笔"),
        ]
        
        for task_name, title, tip in priority_order:
            if task_name in foundation_contents:
                content = foundation_contents[task_name]
                # 基础设定内容要尽量完整，利用长上下文
                max_len = 3500 if task_name in ["大纲", "人物设计", "世界观规则"] else 2000
                if len(content) > max_len:
                    content = content[:max_len] + "\n...\n（内容已截断，核心要点如上）"
                
                sections.append(f"""
### {title}

💡 **使用提示**：{tip}

```
{content}
```

""")
        
        sections.append(f"""
═══════════════════════════════════════════════════════════════════════════════

📌 **创作检查清单**（写完后请逐一确认）：

✅ 本章内容是否紧扣【大纲】？
✅ 本章是否按照【大纲】规划推进？
✅ 人物言行是否符合【人物设计】的性格？
✅ 世界运作是否符合【世界观规则】？
✅ 本章是否正确处理了【事件】？
✅ 本章是否正确处理了【伏笔】（埋设或回收）？

❌ **绝对禁止**：
- 禁止偏离大纲，写成另一个故事
- 禁止让人物做出不符合性格的行为
- 禁止违反世界观规则
- 禁止遗忘已埋设的伏笔
- 禁止与前面章节脱节

═══════════════════════════════════════════════════════════════════════════════

""")
        
        return "".join(sections)

    def _build_dynamic_context_section(
        self,
        task_type: str,
        predecessor_contents: Dict[str, str],
        goal: Dict[str, Any],
    ) -> str:
        """
        根据前置任务内容动态构建上下文部分
        
        Args:
            task_type: 当前任务类型
            predecessor_contents: 前置任务内容
            goal: 创作目标
            
        Returns:
            动态生成的上下文提示词
        """
        if not predecessor_contents:
            return ""
        
        sections = []
        
        # 强调关联性的开头
        sections.append("""
╔══════════════════════════════════════════════════════════════════╗
║  📚 前置任务成果 - 你必须基于这些内容创作，保持紧密关联！      ║
╚══════════════════════════════════════════════════════════════════╝

⚠️ **重要提醒**：
- 当前任务必须与以下内容**紧密关联**
- 不要"另起炉灶"，要在前面的基础上**延伸和深化**
- 评估时会检查你与前置任务的**关联程度**

""")

        # 🔥 按重要程度排序展示前置内容
        # 注意：实际显示哪些内容由 predecessor_contents 决定（基于依赖关系）
        # priority_order 只决定显示顺序和标记
        priority_order = [
            "大纲",  # 🔴 蓝图
            "人物设计", "世界观规则", "事件", "伏笔列表",  # 核心元素
        ]
        
        for task_name in priority_order:
            if task_name in predecessor_contents:
                content = predecessor_contents[task_name]
                # 截取合理长度（避免超长）
                max_len = 2500 if task_name in ["大纲", "人物设计", "世界观规则"] else 1200
                if len(content) > max_len:
                    content = content[:max_len] + "...\n（内容已截断，请参考要点）"
                
                # 为重要任务添加特殊标记
                if task_name in ["大纲", "人物设计"]:
                    sections.append(f"\n### 🎯 {task_name}（核心参考）\n")
                else:
                    sections.append(f"\n### {task_name}\n")
                sections.append(f"{content}\n")
        
        sections.append("""
---

📌 **你的任务**：在以上基础上继续创作，确保：
1. 与【大纲】保持一致
2. 人物行为符合【人物设计】
3. 世界运作符合【世界观规则】
4. 风格符合【风格元素】（如已确定）

""")
        
        return "".join(sections)

    def _build_brainstorm_prompt_simple(self, goal: Dict[str, Any]) -> str:
        """
        为创意脑暴任务构建简洁的提示词

        只包含项目创建时的上下文，移除不必要的约束和写作指导
        """
        # 提取项目基础信息
        title = goal.get("title", "")
        genre = goal.get("genre", "")
        style = goal.get("style", "")
        requirement = goal.get("requirement", "")
        word_count = goal.get("word_count", 0)
        chapter_count = goal.get("chapter_count", 0)

        # 格式化字数显示
        if word_count >= 10000:
            word_display = f"{word_count // 10000}万字"
        else:
            word_display = f"{word_count}字"

        # 构建项目上下文部分
        context_info = "### 📋 项目基础信息\n\n"
        if title:
            context_info += f"**标题**：{title}\n"
        if genre:
            context_info += f"**类型**：{genre}\n"
        if style:
            context_info += f"**风格**：{style}\n"
        if requirement:
            context_info += f"**创作要求**：{requirement}\n"
        if word_count:
            context_info += f"**目标字数**：{word_display}\n"
        if chapter_count:
            context_info += f"**章节数量**：{chapter_count}章\n"

        # 构建简洁的提示词
        prompt = f"""## 任务：创意脑暴 🎯

{context_info}

---

### 🎯 你的任务

基于以上项目信息，产生 **4 个独特的故事点子**。

### 每个点子包含：

**故事概念**（2-3句话）- 用"如果...会怎样"的方式描述

### 输出格式：

---
## 💡 点子一：[标题]

**故事概念**：...

---
## 💡 点子二：[标题]

**故事概念**：...

---
## 💡 点子三：[标题]

**故事概念**：...

---
## 💡 点子四：[标题]

**故事概念**：...

---

## 🏆 推荐点子

**推荐**：点子[X]

**理由**：（简短说明）

⚠️ **要求**：
- 每个点子 100-200 字
- 点子之间要有差异
- 考虑是否能支撑 {chapter_count} 章、{word_display} 的完整小说
"""

        return prompt

    def _build_plugin_context_section(self, enriched_context: Dict[str, Any]) -> str:
        """
        Build plugin context section for prompt

        Args:
            enriched_context: Context data from plugins

        Returns:
            Formatted context section
        """
        if not enriched_context:
            return ""

        sections = []

        sections.append("""
╔══════════════════════════════════════════════════════════════════╗
║  🔌 插件增强上下文 - 智能元素管理系统提供的额外信息            ║
╚══════════════════════════════════════════════════════════════════╝

""")

        # Process different plugin data types
        for plugin_name, plugin_data in enriched_context.items():
            if not plugin_data:
                continue

            # Format plugin data based on type
            if plugin_name == "character":
                sections.append(self._format_character_context(plugin_data))
            elif plugin_name == "worldview":
                sections.append(self._format_worldview_context(plugin_data))
            elif plugin_name == "event":
                sections.append(self._format_event_context(plugin_data))
            elif plugin_name == "foreshadow":
                sections.append(self._format_foreshadow_context(plugin_data))
            else:
                # Generic formatting for unknown plugin types
                sections.append(f"\n### 🔌 {plugin_name.title()} 插件数据\n")
                if isinstance(plugin_data, dict):
                    for key, value in plugin_data.items():
                        if value:
                            sections.append(f"**{key}**: {value}\n")
                elif isinstance(plugin_data, str):
                    sections.append(f"{plugin_data}\n")
                else:
                    sections.append(f"{str(plugin_data)[:500]}\n")

        return "".join(sections)

    def _format_character_context(self, character_data: Dict[str, Any]) -> str:
        """Format character plugin data"""
        sections = []

        sections.append("\n### 👥 角色信息（来自角色管理插件）\n")

        # Current scene characters
        if "current_scene_characters" in character_data:
            chars = character_data["current_scene_characters"]
            if chars:
                sections.append("**当前场景角色**：\n")
                for char in chars:
                    name = char.get("name", "未知")
                    role = char.get("role", "")
                    location = char.get("location", "")
                    mood = char.get("mood", "")
                    sections.append(f"- {name} ({role})")
                    if location:
                        sections.append(f" - 位置: {location}")
                    if mood:
                        sections.append(f" - 状态: {mood}")
                    sections.append("\n")

        # Character relationships
        if "relationships" in character_data:
            rels = character_data["relationships"]
            if rels:
                sections.append("**角色关系**：\n")
                for rel in rels[:5]:  # Limit to 5 relationships
                    char1 = rel.get("character1", "")
                    char2 = rel.get("character2", "")
                    rel_type = rel.get("type", "")
                    sections.append(f"- {char1} ↔ {char2}: {rel_type}\n")

        return "".join(sections)

    def _format_worldview_context(self, worldview_data: Dict[str, Any]) -> str:
        """Format worldview plugin data"""
        sections = []

        sections.append("\n### 🌍 世界观信息（来自世界观插件）\n")

        # Current location
        if "current_location" in worldview_data:
            loc = worldview_data["current_location"]
            if loc:
                sections.append(f"**当前场景**：{loc}\n")

        # World rules
        if "relevant_rules" in worldview_data:
            rules = worldview_data["relevant_rules"]
            if rules:
                sections.append("**相关世界规则**：\n")
                for rule in rules[:3]:  # Limit to 3 rules
                    sections.append(f"- {rule}\n")

        return "".join(sections)

    def _format_event_context(self, event_data: Dict[str, Any]) -> str:
        """Format event plugin data"""
        sections = []

        sections.append("\n### ⚡ 事件信息（来自事件插件）\n")

        # Current events
        if "current_events" in event_data:
            events = event_data["current_events"]
            if events:
                sections.append("**当前相关事件**：\n")
                for event in events[:3]:
                    name = event.get("name", "")
                    status = event.get("status", "")
                    sections.append(f"- {name} ({status})\n")

        return "".join(sections)

    def _format_foreshadow_context(self, foreshadow_data: Dict[str, Any]) -> str:
        """Format foreshadow plugin data"""
        sections = []

        sections.append("\n### 🔮 伏笔信息（来自伏笔插件）\n")

        # Foreshadows to plant
        if "to_plant" in foreshadow_data:
            to_plant = foreshadow_data["to_plant"]
            if to_plant:
                sections.append("**需要埋设的伏笔**：\n")
                for item in to_plant[:2]:
                    sections.append(f"- {item}\n")

        # Foreshadows to payoff
        if "to_payoff" in foreshadow_data:
            to_payoff = foreshadow_data["to_payoff"]
            if to_payoff:
                sections.append("**需要回收的伏笔**：\n")
                for item in to_payoff[:2]:
                    sections.append(f"- {item}\n")

        return "".join(sections)

    async def _build_prompt_from_plugin(
        self,
        task: Task,
        context: MemoryContext,
        goal: Dict[str, Any],
    ) -> Optional[str]:
        """
        Build prompt from plugin system

        Args:
            task: The task to build prompt for
            context: Memory context
            goal: Creation goal

        Returns:
            Prompt string from plugin, or None if not available
        """
        if not self.plugin_manager:
            return None

        # Get plugin name from task metadata
        plugin_name = task.metadata.get("plugin")
        if not plugin_name:
            return None

        try:
            # Get all prompts from plugins
            all_prompts = self.plugin_manager.get_prompts()

            # Get prompts for this specific plugin
            plugin_prompts = all_prompts.get(plugin_name, {})
            if not plugin_prompts:
                logger.debug(f"No prompts found for plugin: {plugin_name}")
                return None

            # Get prompt for this task type
            task_type = task.task_type.value
            prompt_template = plugin_prompts.get(task_type)

            if not prompt_template:
                logger.debug(f"No prompt template for task type: {task_type} in plugin: {plugin_name}")
                return None

            # For now, return the template as-is
            # TODO: Implement variable substitution with Jinja2
            logger.debug(f"Using plugin prompt for {task_type} from {plugin_name}")
            return prompt_template

        except Exception as e:
            logger.error(f"Failed to build prompt from plugin: {e}")
            return None

    def _get_genre_writing_guide(self, genre: str) -> str:
        """
        根据小说类型获取对应的写作指南

        Args:
            genre: 小说类型（科幻、都市修仙、玄幻等）

        Returns:
            对应类型的写作指南字符串
        """
        # 标准化类型名称（去除空格、统一大小写）
        genre_normalized = genre.strip().replace(" ", "")

        # 尝试精确匹配
        if genre_normalized in self.GENRE_WRITING_GUIDES:
            return self.GENRE_WRITING_GUIDES[genre_normalized]

        # 尝试模糊匹配（处理"都市修仙"和"修仙"等情况）
        for key, guide in self.GENRE_WRITING_GUIDES.items():
            if key in genre_normalized or genre_normalized in key:
                return guide

        # 没有匹配，返回通用指南
        logger.debug(f"未找到类型 '{genre}' 的写作指南，使用通用指南")
        return self.DEFAULT_CONTENT_TASK_NOTE

    async def _build_prompt(
        self,
        task: Task,
        context: MemoryContext,
        goal: Dict[str, Any],
        enriched_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for a task"""

        # Get task type value for matching
        task_type = task.task_type.value

        # 🔥 脑暴任务使用专门的简洁提示词
        if task_type == "创意脑暴":
            return self._build_brainstorm_prompt_simple(goal)

        # 🔥 优先级 1: 尝试从插件系统获取提示词
        if task.metadata.get("plugin_source"):
            plugin_prompt = await self._build_prompt_from_plugin(task, context, goal)
            if plugin_prompt:
                task.metadata["prompt_source"] = "plugin"
                return plugin_prompt
            else:
                logger.debug(f"Plugin prompt not available for {task_type}, falling back to default")

        # Base prompt sections
        sections = []

        # 🔥 首先构建配置约束部分 - 所有任务都需要看到这些硬性约束
        word_count = goal.get("word_count", 50000)
        chapter_count = goal.get("chapter_count", 10)
        words_per_chapter = word_count // max(chapter_count, 1)
        genre = goal.get("genre", "")
        style = goal.get("style", "")
        
        # 根据字数显示不同格式
        if word_count >= 10000:
            word_display = f"{word_count // 10000}万字"
        else:
            word_display = f"{word_count}字"
        
        config_constraints = f"""
════════════════════════════════════════════════════════════════
📋 【核心配置约束 - 必须严格遵守】
════════════════════════════════════════════════════════════════

🎯 总字数限制：{word_display}（这是硬性要求，不能超出！）
📚 章节数量：{chapter_count}章（严格按此规划，不多不少！）
📝 每章字数：约{words_per_chapter}字

⚠️ 重要：所有规划、设计、创作都必须在这个框架内进行！
   不要超出字数限制，不要规划超出指定的章节数！

════════════════════════════════════════════════════════════════

"""
        sections.append(config_constraints)
        
        # 🎯 添加类型特定的创作指南（仙侠、科幻、言情等各不相同）
        genre_guide = self.get_genre_specific_guide(genre)
        sections.append(genre_guide)

        # Determine if this is a planning/analysis task or a content generation task
        # 🔥 优化：使用类级别常量，避免重复定义
        all_tasks_types = self.ALL_TASKS_TYPES

        # 🔥 优化：使用类级别常量，避免重复定义
        # Build goal section based on task type
        if task_type in all_tasks_types["strategy"]:
            # 🔴 策略规划任务 - 明确说明不是写小说内容
            goal_section = f"""## 任务背景

你正在为一部小说做**策略规划**工作。

{self.STRATEGY_TASK_NOTE}

{self.COLLOQUIAL_STYLE_GUIDE}
"""
        elif task_type in all_tasks_types["planning"]:
            # Planning/analysis tasks - structured output
            goal_section = f"""## 任务背景

{self.PLANNING_TASK_NOTE}

{self.COLLOQUIAL_STYLE_GUIDE}
"""
        elif task_type in all_tasks_types["element"]:
            # Element creation tasks - semi-structured output
            goal_section = f"""## 任务背景

{self.ELEMENT_TASK_NOTE}

{self.COLLOQUIAL_STYLE_GUIDE}
"""
        else:
            # Content generation tasks - narrative output
            # 🔥 根据小说类型动态获取写作指南
            genre = goal.get("genre", "")
            writing_guide = self._get_genre_writing_guide(genre)
            goal_section = f"""## 创作目标

{writing_guide}
{self.COLLOQUIAL_STYLE_GUIDE}
"""

        # 🔥 优化：只添加项目基本信息，避免重复字数/章节数（已在config_constraints中）
        if goal.get("title"):
            goal_section += f"小说标题: {goal['title']}\n"
        if goal.get("genre"):
            goal_section += f"小说类型: {goal['genre']}\n"
        if goal.get("theme"):
            goal_section += f"小说主题: {goal['theme']}\n"
        if goal.get("style"):
            goal_section += f"写作风格: {goal['style']}\n"
        if goal.get("requirement"):
            goal_section += f"创作要求: {goal['requirement']}\n"
        # 注意：word_count 和 chapter_count 已在 config_constraints 中显示，此处不再重复
        sections.append(goal_section)

        # 🔥 动态获取前置任务内容并构建上下文
        predecessor_contents = self._get_predecessor_contents(task_type, context)

        # 🧠 对于复杂任务（章节相关），使用动态上下文选择
        # 🔥 优化：使用前面定义的任务类型分类
        chapter_related_tasks = all_tasks_types["content"]
        use_dynamic_context = (
            predecessor_contents 
            and task_type in chapter_related_tasks
            and self.config.get("dynamic_context_selection", True)  # 配置开关，默认开启
        )
        
        # 🔴 对于章节相关任务，首先添加基础设定参考（最重要！）
        if task_type in chapter_related_tasks and predecessor_contents:
            foundation_reference = self._build_foundation_reference(predecessor_contents, task_type)
            if foundation_reference:
                sections.append(foundation_reference)
                logger.info(f"🔴 已添加基础设定参考到 {task_type} 的 prompt 中")
        
        if use_dynamic_context:
            # 动态分析需要哪些上下文
            try:
                context_analysis = await self._analyze_context_needs(task, goal, predecessor_contents)
                dynamic_context = self._build_focused_context_section(predecessor_contents, context_analysis)
                logger.info(f"🧠 使用动态上下文选择: 从{len(predecessor_contents)}个上下文中选择了{len(context_analysis.get('selected_contexts', []))}个")
            except Exception as e:
                logger.warning(f"⚠️ 动态上下文选择失败，使用默认方式: {e}")
                dynamic_context = self._build_dynamic_context_section(task_type, predecessor_contents, goal)
            sections.append(dynamic_context)
        elif predecessor_contents:
            # 对于其他任务，使用原有的固定规则
            dynamic_context = self._build_dynamic_context_section(task_type, predecessor_contents, goal)
            sections.append(dynamic_context)

        # 🔥 添加插件提供的增强上下文（角色、世界观、事件等）
        if enriched_context:
            plugin_context_section = self._build_plugin_context_section(enriched_context)
            if plugin_context_section:
                sections.append(plugin_context_section)
                logger.debug(f"Added plugin context for task {task.task_id}")

        # Task-specific instruction based on task type
        # ============ Phase 0: 创意脑暴阶段 ============
        if task_type == "创意脑暴":
            # 🔥 获取用户提供的基础设定
            title = goal.get('title', '')
            genre = goal.get('genre', '科幻')
            style = goal.get('style', '')
            requirement = goal.get('requirement', '')
            word_count = goal.get('word_count', 0)
            chapter_count = goal.get('chapter_count', 0)

            # 构建基础设定部分
            foundation_info = ""
            if title:
                foundation_info += f"\n**项目标题**：{title}"
            if genre:
                foundation_info += f"\n**类型/流派**：{genre}"
            if style:
                foundation_info += f"\n**写作风格**：{style}"
            if requirement:
                foundation_info += f"\n**创作要求**：{requirement}"
            if word_count:
                if word_count >= 10000:
                    foundation_info += f"\n**目标字数**：{word_count // 10000}万字"
                else:
                    foundation_info += f"\n**目标字数**：{word_count}字"
            if chapter_count:
                foundation_info += f"\n**章节数量**：{chapter_count}章"

            task_section = f"""
## 当前任务：{task_type} 🎯

你现在是一个**顶级畅销小说家**，正在为新书进行创意脑暴。

---

### ⚠️ 重要：基于用户提供的基础设定进行脑暴

以下是本项目的**基础锚点**（所有点子都必须符合这些基础设定）：
{foundation_info}

🔴 **要求**：
- 所有故事点子**必须保留**以上基础设定
- 在这些基础设定上自由发挥，添加创意元素
- 不要偏离标题、类型、风格等核心设定

---

### 📌 脑暴目标

基于上述基础设定，产生 **4 个独特的故事点子**，并从中推荐最佳的一个

### 每个点子必须包含：

1. **故事概念**（2-3句话）
   - 基于「{title}」这个标题展开
   - 用"如果...会怎样"的方式描述
   - 必须体现「{style}」的写作风格
   - 符合「{genre}」类型的设定

2. **核心冲突**
   - 主角面对什么困境/挑战？
   - 什么东西阻止主角得到他想要的？
   - 如何体现「{style}」的紧张感？

3. **情感钩子**
   - 这个故事能触动读者什么情感？
   - 为什么读者会在意这个故事？

4. **独特卖点**
   - 这个故事与市面上其他{genre}小说有什么不同？
   - 一句话能让人记住的特点是什么？

5. **潜力评估**（简短）
   - 这个点子适合发展成{word_count // 10000 if word_count >= 10000 else word_count}字的小说吗？
   - 可能的受众是谁？

### 脑暴原则

✅ **要做到**：
- 🔴 **必须基于用户提供的基础设定**：标题「{title}」、类型「{genre}」、风格「{style}」
- 点子要大胆、新奇，不要老套
- 每个点子之间要有差异性，不要太相似
- 想想读者看到这个设定会不会眼前一亮
- 考虑故事的"可展开性"——能支撑起{chapter_count}章、{word_count}字的完整小说吗？

❌ **要避免**：
- 🚫 **不要偏离基础设定**：标题、类型、风格是锚点，不能改！
- 不要写成长篇大纲，每个点子控制在 200-300 字
- 不要学术化，用讲故事的语气
- 不要太平庸，那种"一看就知道结局"的故事不要

### 输出格式

请用以下格式输出（**必须严格按照此格式**）：

---
## 💡 点子一：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 💡 点子二：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 💡 点子三：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 💡 点子四：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 🏆 AI推荐

**推荐点子**：点子[X]

**推荐理由**：
（从以下维度分析为什么这个点子最有潜力：新颖程度、情感共鸣、市场潜力、可展开性）

---

⚠️ **重要**：用户将从这4个点子中选择一个作为后续创作的基础，请确保每个点子都有足够的质量和差异性！
"""
        elif task_type == "风格元素":
            genre = goal.get('genre', '')
            # 科幻类型特别强调通俗易懂
            sci_fi_note = ""
            if genre == "科幻":
                sci_fi_note = """
🔔 **科幻小说特别提醒**：
- 科幻不等于学术论文！要用故事讲科学，不是写科普文章
- 参考《三体》《流浪地球》的写法：科技元素融入情节，而不是堆砌术语
- 让不懂科学的读者也能看懂、也能感动
- 避免大段的技术说明，用对话、情节来展现科技
"""
            
            task_section = f"""
## 当前任务：{task_type} 🎨

你是一位顶级畅销小说家，正在为新书确定**最合适的文学风格**。

> "风格不是装饰，而是讲故事的方式。选错了风格，再好的故事也会被毁掉。" — 斯蒂芬·金

---

### 📌 任务说明

基于前面确定的**大纲**，定义最能展现这个故事魅力的风格元素。

⚠️ **风格必须服务于故事！** 不同的故事需要不同的讲述方式。

---

### 🏆 顶级作家的风格法则

**法则一：风格要与故事内核匹配**
- 《三体》用冷峻克制的语言讲宇宙的残酷
- 《追风筝的人》用温暖细腻的文字讲救赎
- 《教父》用沉稳老练的笔调讲家族传承

**法则二：风格要考虑目标读者**
- 网文读者喜欢爽快节奏
- 文学读者欣赏精致文字
- 大众读者需要通俗易懂

**法则三：风格要始终如一**
- 一旦确定风格，全书要保持一致
- 风格不一致会让读者出戏
{sci_fi_note}
---

### 📋 请输出以下内容

#### 一、叙事视角选择

1. **选择的视角**：[第几人称？全知/限制/多视角？]
2. **选择理由**：[为什么这个视角最适合讲述这个故事？2-3句话]
3. **参考作品**：[有哪些成功作品用了类似视角？]

#### 二、语言风格定位

1. **风格关键词**：[3个词概括，如"简洁、有力、画面感强"]
2. **具体说明**：
   - 句子长度偏好：长句/短句/混合
   - 用词倾向：口语化/书面化/诗意化
   - 修辞偏好：多用比喻/少用修辞/适度点缀
3. **风格示例**：[写2-3句示例句子，展示这种风格]

⚠️ 必须是**通俗易懂的白话文**！

#### 三、叙事节奏设计

1. **整体节奏**：[快节奏/中速/慢节奏]
2. **节奏变化规律**：
   - 什么时候加速？（紧张场面、动作戏）
   - 什么时候放缓？（情感戏、铺垫）
3. **章节长度倾向**：[长章节/短章节/混合]

#### 四、氛围基调

1. **主导氛围**：[一个词概括，如"紧张""温暖""压抑"]
2. **氛围层次**：
   - 底色氛围：贯穿全书的基调
   - 情绪高点：什么氛围？
   - 情绪低点：什么氛围？

#### 五、文学技巧选择

| 技巧类型 | 使用频率 | 使用场景 |
|---------|---------|---------|
| 对话 | 高/中/低 | 什么时候用？ |
| 内心独白 | 高/中/低 | 什么时候用？ |
| 环境描写 | 高/中/低 | 什么时候用？ |
| 动作场面 | 高/中/低 | 什么时候用？ |
| 闪回/插叙 | 高/中/低 | 什么时候用？ |

---

### ❌ 禁止事项

- 禁止写成小说正文，这是规划阶段
- 禁止堆砌专业术语
- 禁止脱离大纲空谈风格

📝 **输出长度**：500-800字，清晰、实用
"""
        elif task_type == "人物设计":
            # 根据字数估算需要的人物数量
            word_count = goal.get("word_count", 50000)
            chapter_count = goal.get("chapter_count", 10)
            genre = goal.get("genre", "通用")
            
            # 根据字数动态调整人物数量 - 长篇需要更多人物来支撑故事
            if word_count >= 1000000:  # 100万字以上
                main_chars = "2-4"
                support_chars = "12-18"
                minor_chars = "25-40"
                char_note = "超长篇需要丰富的人物群像，多条支线需要各自的人物来承载。"
            elif word_count >= 500000:  # 50万字以上
                main_chars = "2-3"
                support_chars = "8-12"
                minor_chars = "15-25"
                char_note = "长篇小说需要足够的人物来支撑复杂的故事线。"
            elif word_count >= 200000:  # 20万字以上
                main_chars = "1-2"
                support_chars = "5-8"
                minor_chars = "10-15"
                char_note = "中长篇需要适量的配角来丰富故事世界。"
            elif word_count >= 100000:  # 10万字以上
                main_chars = "1-2"
                support_chars = "4-6"
                minor_chars = "6-10"
                char_note = "中篇小说人物要精简，每个人物都要有存在价值。"
            else:  # 10万字以下
                main_chars = "1"
                support_chars = "2-4"
                minor_chars = "3-5"
                char_note = "短篇小说人物要少而精，避免角色过多分散焦点。"
            
            task_section = f"""
## 当前任务：{task_type} 🎭

你是一位顶级畅销小说家，正在为新书设计人物。

> "情节是人物的证明。读者不记得情节，但永远记得人物。" — 斯蒂芬·金

---

### 📌 任务说明

⚠️ **重要**：请参考【大纲】中列出的人物列表，为每个人物进行详细设计！

📊 **本书规模**：目标 **{word_count//10000}万字**，共 **{chapter_count}章**
💡 **人物规模建议**：{char_note}

---

### 🏆 顶级作家的人物法则

**法则一：人物即故事**
- 情节不是发生在人物身上的事，而是人物性格导致的必然
- 《教父》的麦克不是被动卷入，是他的性格让他必然成为教父

**法则二：欲望+缺陷=动力**
- 人物必须极度渴望某样东西（欲望）
- 人物必须有阻碍他得到的内在弱点（缺陷）
- 这两者的碰撞产生故事

**法则三：每个人物都认为自己是主角**
- 反派也有他的逻辑和理由
- 配角有自己的人生，不只是主角的工具

---

### 📋 请输出以下内容

---

## 一、主角设计（{main_chars}人）

主角是故事大纲的**核心体现**。设计时必须回答：**为什么必须是他/她来经历这个故事？**

### 主角：[姓名]

#### 1. 基本信息
| 项目 | 内容 |
|-----|------|
| 姓名 | （含名字的含义或由来）|
| 年龄 | |
| 性别 | |
| 身份/职业 | |
| 外貌特征 | （2-3个让人记住的特点）|

#### 2. 性格内核（最重要！）

**人物三角**：
- **想要什么（Want）**：表面目标，故事层面的追求
- **需要什么（Need）**：深层需求，主题层面的真相
- **致命缺陷（Flaw）**：什么性格弱点会阻碍他？

**人物谎言**：
- 主角相信的一个关于世界/自己的错误信念是什么？
- 这个谎言如何影响他的行为？
- 故事中何时/如何打破这个谎言？

#### 3. 人物小传（重要！500-800字）

⚠️ **用故事的方式讲述这个人物的过去**，不要写档案式的条目！

请用叙事的方式描述：
- 他/她的童年是怎样的？（家庭环境、重要经历）
- 什么事件塑造了他/她现在的性格？（关键创伤或转折）
- 在故事开始前，他/她过着怎样的生活？
- 他/她有什么执念或心结？
- 他/她最珍视什么？最害怕什么？

[请写一段500-800字的人物小传，像在讲一个人的故事]

#### 4. 基于世界观的能力（如有）

⚠️ **参考【世界观规则】设计人物能力**，确保能力符合世界规则！

| 项目 | 内容 |
|-----|------|
| 能力名称 | |
| 能力来源 | [根据世界观设定] |
| 能力效果 | |
| 使用限制/代价 | [每个能力都应该有代价] |
| 在故事中的作用 | [这个能力如何推动剧情？] |

**能力设计原则**：
- 能力必须符合世界观规则
- 能力要有明确的限制和代价
- 能力要为故事服务，不是炫技

#### 5. 人物弧光
| 阶段 | 状态 | 触发事件 |
|-----|------|---------|
| 开始 | [性格状态] | - |
| 考验 | [面对什么挑战] | [什么事件] |
| 转变 | [如何改变] | [什么事件] |
| 结局 | [最终状态] | - |

#### 6. 标志性特征
- 口头禅/说话方式：
- 习惯性动作：
- 独特的小细节：

---

## 二、重要配角（{support_chars}人）

⚠️ **配角存在的唯一理由**：推动或阻碍主角的旅程。

### 配角设计模板（每人填写）

**[姓名]** - [一句话定义：身份+与主角的关系]

| 项目 | 内容 |
|-----|------|
| 与主角关系 | [盟友/对手/导师/恋人/镜像] |
| 故事功能 | [这个人物为什么必须存在？] |
| 性格关键词 | [2-3个词] |
| 个人目标 | [他自己想要什么？] |
| 外貌特征 | [1-2个记忆点] |

**人物小传**（200-300字）：
[用叙事方式描述这个人物的背景故事]

**能力设定**（如有，参考世界观规则）：
- 能力：
- 限制/代价：

**配角类型参考**：
- 🤝 **盟友**：帮助主角，但可能有自己的议程
- ⚔️ **对手/反派**：阻碍主角（注意：反派也认为自己是对的）
- 🎓 **导师**：提供智慧或技能，可能需要被超越
- 🪞 **镜像人物**：与主角形成对比，展示另一条路
- 💕 **情感纽带**：给主角提供情感动力

---

## 三、次要人物（{minor_chars}人）

简要列出，每人一行：

| 姓名 | 身份 | 出场章节 | 作用 | 能力（如有）|
|-----|------|---------|-----|----------|
| | | 约第X章 | [一句话说明] | |

---

## 四、人物关系网

用文字描述人物之间的关系：

**主要关系线**：
- [人物A] ←→ [人物B]：[关系性质 + 关系如何变化]
- ...

**隐藏关系**（如果有）：
- [什么关系是隐藏的？什么时候揭示？]

**冲突关系**：
- [谁和谁有冲突？为什么？]

---

## 五、人物出场规划（重要！）

⚠️ **这是给后续章节创作的重要参考**，请认真规划每个人物的出场节奏。

### 章节出场分布表

📊 本书共 **{chapter_count}章**，请规划每个人物在哪些章节出场：

| 人物 | 出场章节（列出所有章节编号） | 首次出场 | 高光章节 | 退场/结局 |
|-----|--------------------------|---------|---------|---------|
| [主角名] | 1-{chapter_count}（全书贯穿） | 第1章 | 第X、X、X章 | 第{chapter_count}章 |
| [配角1] | 第2、5、8、12、...章 | 第2章 | 第X章 | 第X章 |
| [配角2] | 第3、6、9、15章 | 第3章 | 第X章 | - |
| ... | ... | ... | ... | ... |

### 出场规划原则

1. **主角**：应贯穿全书，每章都有出场
2. **重要配角**：出场率约50-70%的章节，要有节奏感
3. **次要人物**：出场率约20-40%的章节，按需出场
4. **过场人物**：仅在必要章节出场

### 人物密度建议

| 章节阶段 | 建议同时在场人物数 | 说明 |
|---------|------------------|-----|
| 开篇（1-3章）| 2-4人 | 建立核心关系 |
| 发展期 | 4-6人 | 逐步引入配角 |
| 高潮期 | 5-8人 | 人物汇聚 |
| 结局 | 3-5人 | 收束 |

---

### ❌ 禁止事项

- 禁止写成档案表格，人物要**活**
- 禁止人物没有缺点（完美人物不真实）
- 禁止配角只是工具人（每个人都有自己的人生）
- 禁止人物数量超出规模建议太多
- 禁止人物出场规划模糊不清（必须明确到具体章节）

📝 **输出长度**：1500-2500字（根据字数规模调整）
"""
        elif task_type == "功法法宝":
            word_count = goal.get("word_count", 50000)
            genre = goal.get('genre', '通用')

            # 根据字数调整功法数量
            if word_count >= 1000000:
                power_count = "15-25个功法 + 20-30件法宝"
                detail_note = "超长篇需要丰富的功法体系来支撑漫长的修炼过程。"
            elif word_count >= 500000:
                power_count = "10-15个功法 + 15-20件法宝"
                detail_note = "长篇需要完整的功法体系，让读者有期待感。"
            elif word_count >= 200000:
                power_count = "6-10个功法 + 10-15件法宝"
                detail_note = "中长篇需要有层次的功法体系。"
            else:
                power_count = "3-5个功法 + 5-8件法宝"
                detail_note = "中短篇功法要精简，避免过多设定让读者记不住。"

            task_section = f"""
## 当前任务：{task_type} ⚔️

你是一位修仙/玄幻小说的功法体系设计师，正在为小说创建完整的功法法宝系统。

> "功法是修仙小说的血脉，等级森严是基础，成长空间是期待。" — 网文经典

---

### 📌 任务说明

⚠️ **重要**：功法法宝必须与【世界观规则】和【势力设计】保持一致！

📊 **本书规模**：目标 **{word_count//10000}万字**
⚔️ **功法规模建议**：{detail_note}

---

### 🏆 功法设计法则

**法则一：等级森严**
- 每个功法都有明确的等级划分（炼气/筑基/金丹...）
- 高级功法对低级有碾压式优势
- 但低级功法可以修炼到更高层次（需要更多努力）

**法则二：各有特色**
- 不同势力有不同的功法传承
- 功法要体现势力的核心信仰（正道/魔道/旁门）
- 功法之间可以有相生相克

**法则三：成长空间**
- 主角的功法要有升级路线
- 每次升级都有明显的变化
- 给读者明确的期待感

---

### 📋 请输出以下内容

## 一、功法体系设计

### 1. 主角核心功法

**功法名称**：[名称]（如：青玄剑诀、九转金身诀）

**功法等级**：
- 炼气期：[效果]
- 筑基期：[效果]
- 金丹期：[效果]
- 元婴期：[效果]
- 化神期：[效果]

**功法特点**：
- 攻击/防御/辅助/特殊
- 需要什么条件才能修炼
- 有什么限制或代价

**升级路线**：
- 在第几章获得？
- 如何升级？（顿悟/秘籍/传承）
- 每次升级发生在哪章？

### 2. 各势力特色功法

**正道势力（如青玄宗）**：
- 核心功法1：[名称] - [特点]
- 核心功法2：[名称] - [特点]

**魔道势力（如魔门）**：
- 核心功法1：[名称] - [特点]
- 核心功法2：[名称] - [特点]

**其他势力**：[按需要添加]

### 3. 辅助功法

- 炼丹术
- 炼器术
- 阵法
- 神识修炼
- 身法/遁术
- 其他：[根据需要]

---

## 二、法宝体系设计

### 1. 主角法宝

| 法宝名称 | 类型 | 品阶 | 获得章节 | 能力 | 成长空间 |
|---------|------|------|---------|------|---------|
| [示例] | 飞剑 | 下品 | 第5章 | 发出剑气，可升级 | 可吞噬金属进化 |
| | | | | | |

**重点法宝详细设定**：

**[法宝名称]**：
- 外形：[描述]
- 器灵：[是否有器灵？性格如何？]
- 能力：
  - 初始：[能力]
  - 升级后：[新能力]
- 成长路线：[如何升级？有什么变化？]

### 2. 重要配角/反派法宝

列出主要配角的法宝，用于战斗和剧情：

| 角色名称 | 法宝名称 | 能力描述 | 作用 |
|---------|---------|---------|------|
| | | | |

### 3. 特殊物品

- 丹药：[重要的丹药及其作用]
- 符箓：[特殊的符箓]
- 玉简/传承：[重要的传承物品]
- 其他：[根据剧情需要]

---

## 三、功法法宝关系网

**相生关系**：
- 哪些功法可以配合使用？
- 哪些法宝可以组合？

**相克关系**：
- 哪些功法互相克制？
- 哪些法宝可以克制另一些法宝？

**传承关系**：
- 功法从哪里来？（上古传承/自创/师门）
- 法宝的来历？

---

### ⚠️ 质量检查

输出前请检查：
- [ ] 功法等级是否与世界观一致？
- [ ] 每个势力是否有特色功法？
- [ ] 主角的功法是否有明确的升级路线？
- [ ] 法宝是否与剧情节点对应？
- [ ] 是否有足够的成长空间支撑长篇故事？

---

### 🚫 禁止事项

- 禁止功法等级模糊不清
- 禁止所有功法都一样（要有特色）
- 禁止主角一开始就无敌（要有成长过程）
- 禁止法宝数量过多导致读者记不住

📝 **输出长度**：2000-3000字
"""
        elif task_type == "主角成长":
            word_count = goal.get("word_count", 50000)
            chapter_count = goal.get("chapter_count", 10)

            # 根据字数和章节数规划成长节奏
            chapters_per_realm = chapter_count // 6  # 假设6个大境界

            task_section = f"""
## 当前任务：{task_type} 📈

你是一位修仙/玄幻小说的成长规划师，正在设计主角的完整成长路径。

> "成长是长篇小说的核心，读者看的就是主角如何从弱变强。" — 网文核心

---

### 📌 任务说明

⚠️ **重要**：必须参考【大纲】、【功法法宝】和【人物设计】！

📊 **本书规模**：目标 **{word_count//10000}万字**，共 **{chapter_count}章**
📈 **成长节奏**：约每 **{chapters_per_realm}章** 突破一个大境界

---

### 🏆 成长规划法则

**法则一：节奏感**
- 不能太快（读者没代入感）
- 不能太慢（读者会失去耐心）
- 波浪式前进：爆发期 → 平台期 → 突破期 → 爆发期

**法则二：有代价**
- 每次突破都要有付出
- 资源、机缘、生死考验
- 不可能一帆风顺

**法则三：有惊喜**
- 偶尔的越级挑战
- 意外的机缘
- 顿悟时刻

---

### 📋 请输出以下内容

## 一、境界体系规划

### 1. 完整境界划分

| 境界 | 等级 | 突破条件 | 修炼年限 | 预计达成章节 | 战力表现 |
|-----|------|---------|---------|------------|---------|
| 炼气期 | 1-9层 | [条件] | [年限] | 第1-{chapters_per_realm}章 | [描述] |
| 筑基期 | 初/中/后 | [条件] | [年限] | 第{chapters_per_realm}-{chapters_per_realm*2}章 | [描述] |
| 金丹期 | 初/中/后/圆满 | [条件] | [年限] | 第{chapters_per_realm*2}-{chapters_per_realm*3}章 | [描述] |
| 元婴期 | 初/中/后/圆满 | [条件] | [年限] | 第{chapters_per_realm*3}-{chapters_per_realm*4}章 | [描述] |
| 化神期 | 初/中/后/圆满 | [条件] | [年限] | 第{chapters_per_realm*4}-{chapters_per_realm*5}章 | [描述] |
| | | | | | |

**注**：根据实际章节数调整

### 2. 每个境界的修炼重点

**炼气期**（打基础）：
- 主要任务：[感应灵气、修炼基础功法]
- 关键事件：[第X章获得XX机缘]
- 突破契机：[第X章因XX事件突破]

**筑基期**（初入仙途）：
- 主要任务：[筑基成功、掌握核心技能]
- 关键事件：[第X章进入秘境]
- 突破契机：[...]

[继续填写其他境界]

---

## 二、核心功法成长路线

**主角核心功法**：[功法名称]

### 阶段一：入门（第1-{chapters_per_realm}章）
- 获得方式：[第X章从哪里获得]
- 修炼进度：[达到什么程度]
- 关键突破：[第X章有什么变化]

### 阶段二：小成（第{chapters_per_realm}-{chapters_per_realm*2}章）
- 升级契机：[第X章发生了什么]
- 新增能力：[获得了什么新能力]
- 战力提升：[具体表现]

### 阶段三：大成（第{chapters_per_realm*2}-{chapters_per_realm*3}章）
- 升级契机：[...]
- 新增能力：[...]
- 战力提升：[...]

[继续填写后续阶段]

---

## 三、重要顿悟时刻

长篇小说需要多个顿悟时刻来推动成长：

| 顿悟时刻 | 所在章节 | 触发原因 | 获得感悟 | 能力提升 |
|---------|---------|---------|---------|---------|
| 第一次顿悟 | 第X章 | [生死考验/看到特殊景象/长者点拨] | [明白了什么道理] | [功法精进度X%] |
| 第二次顿悟 | 第X章 | [...] | [...] | [...] |
| | | | | |

---

## 四、成长曲线可视化

```
战力
  │
  │                                    ╱──── 化神期
  │                              ╱─────
  │                        ╱────元婴期
  │                  ╱─────
  │            ╱────金丹期
  │      ╱─────
  │╱────筑基期
  └─────────────────────────────────────→ 章节推进
    1  5  10  15  20  25  30  ...
```

**节奏说明**：
- 平台期（修炼积累）：约{chapters_per_realm//2}章
- 爆发期（战斗突破）：约{chapters_per_realm//2}章
- 每个大境界遵循这个节奏

---

## 五、与剧情的结合

### 关键剧情节点的成长状态

**第1-{chapters_per_realm}章（炼气期）**：
- 主角战力：[弱小，需要依靠智慧]
- 能处理的冲突：[小型冲突、同门竞争]
- 关键成长：[第X章首次突破炼气X层]

**第{chapters_per_realm}-{chapters_per_realm*2}章（筑基期）**：
- 主角战力：[初入仙途，有了自保能力]
- 能处理的冲突：[中型冲突、探索秘境]
- 关键成长：[...]

[继续填写其他阶段]

---

### ⚠️ 质量检查

输出前请检查：
- [ ] 成长节奏是否合理？（不能太快或太慢）
- [ ] 每个境界是否有明确的内容支撑？
- [ ] 顿悟时刻是否与剧情结合？
- [ ] 成长是否与功法升级对应？
- [ ] 是否给读者足够的期待感？

---

### 🚫 禁止事项

- 禁止成长节奏混乱（今天炼气明天金丹）
- 禁止突破没有代价
- 禁止所有境界都一样（要有差异化）
- 禁止后期战力崩坏

📝 **输出长度**：1500-2500字
"""
        elif task_type == "反派设计":
            word_count = goal.get("word_count", 50000)

            # 根据字数调整反派数量
            if word_count >= 1000000:
                villain_count = "1个终极反派 + 3-5个中期反派 + 8-12个阶段性对手"
                detail_note = "超长篇需要多层次的反派体系来支撑漫长的故事。"
            elif word_count >= 500000:
                villain_count = "1个终极反派 + 2-3个中期反派 + 5-8个阶段性对手"
                detail_note = "长篇需要有层次的反派体系。"
            elif word_count >= 200000:
                villain_count = "1个终极反派 + 1-2个中期反派 + 3-5个阶段性对手"
                detail_note = "中长篇需要有层次的对手。"
            else:
                villain_count = "1个主要反派 + 2-3个对手"
                detail_note = "中短篇反派要精简。"

            task_section = f"""
## 当前任务：{task_type} 😈

你是一位小说反派设计师，正在为小说创建完整的对手体系。

> "反派的高度决定了主角的上限。最好的反派是让自己认为自己在做正确的事。" — 编剧经典

---

### 📌 任务说明

⚠️ **重要**：必须参考【大纲】、【人物设计】、【主角成长】和【势力设计】！

📊 **本书规模**：目标 **{word_count//10000}万字**
😈 **反派规模建议**：{detail_note}

---

### 🏆 反派设计法则

**法则一：有逻辑**
- 反派不是为坏而坏
- 他们有自己的价值观和目标
- 从他们的角度看，自己是正确的

**法则二：有层次**
- 终极反派：隐藏在幕后，最后才出场
- 中期反派：阶段性主要对手
- 阶段性对手：每个篇章的不同敌人

**法则三：有成长**
- 反派也在变强
- 反派和主角互相促进
- 有些反派可以转化（成为盟友或更复杂的对手）

---

### 📋 请输出以下内容

## 一、终极反派设计

**反派姓名**：[姓名]
**势力**：[所属势力]
**定位**：[幕后黑手/明面霸主/双重身份]

### 1. 基本信息
| 项目 | 内容 |
|-----|------|
| 年龄/修为 | [与主角对比] |
| 外貌特征 | [2-3个让人记住的特点] |
| 性格特点 | [核心性格] |

### 2. 核心动机
- **表面目标**：[他公开想要什么？]
- **深层动机**：[他真正想要什么？为什么？]
- **核心信念**：[他坚信什么？]
- **与主角的冲突**：[为什么一定要和主角对立？]

### 3. 实力设定
- 修为境界：[比主角高多少？]
- 核心能力：[有什么特殊能力？]
- 独门功法：[功法名称和特点]
- 法宝：[有什么强大的法宝？]

### 4. 与主角的关系
- **初次交锋**：在第几章？结果如何？
- **逐渐展露**：如何让读者发现他的存在？
- **最终对决**：预计在哪章？胜负如何？

---

## 二、中期反派设计

| 反派姓名 | 所属势力 | 登场章节 | 活跃周期 | 与主角关系 | 最终结局 |
|---------|---------|---------|---------|-----------|---------|
| [示例] | 魔门长老 | 第20章 | 第20-50章 | 杀徒之仇 | 被主角击杀 |
| | | | | | |

### 详细设定（选2-3个重点反派）

**[反派姓名]**：
- 背景：[为什么与主角为敌？]
- 实力：[修为、能力]
- 性格：[有什么特点？]
- 发展：[如何与主角交锋？结局如何？]

---

## 三、阶段性对手

**按篇章划分**（每个主要篇章1-3个对手）：

### 第1-{chapter_count//3}章（前期）
| 对手姓名 | 类型 | 冲突原因 | 交锋章节 | 结局 |
|---------|------|---------|---------|------|
| [同门竞争者] | 竞争型 | 争夺资源 | 第5-10章 | 成为手下败将，后续转化 |
| | | | | |

### 第{chapter_count//3}-{chapter_count//3*2}章（中期）
| 对手姓名 | 类型 | 冲突原因 | 交锋章节 | 结局 |
|---------|------|---------|---------|------|
| [秘境对手] | 敌对型 | 秘境争夺 | 第X-Y章 | [...] |
| | | | | |

### 第{chapter_count//3*2}-章（后期）
| 对手姓名 | 类型 | 冲突原因 | 交锋章节 | 结局 |
|---------|------|---------|---------|------|
| [终极反派出手] | 生死型 | [原因] | 第X-Y章 | [最终对决] |
| | | | | |

---

## 四、反派关系网

**反派之间的关系**：
- 终极反派如何利用中期反派？
- 中期反派是否知道终极反派的存在？
- 阶段性对手之间是否有冲突？

**反派的下属**：
- 每个主要反派有什么手下？
- 这些手下是否会与主角交锋？

---

## 五、反派与主角的互相促进

**主角从反派那里学到什么**：
- 第X章：从[反派]那里学到[功法/经验]
- 第Y章：被[反派]逼迫，突破[境界]

**反派因主角发生什么变化**：
- 第X章：[反派]因为主角的[行为]改变了计划
- 第Y章：[反派]对主角产生了[敬意/忌惮/复杂情感]

---

## 六、反派的成长和变化

**有些反派不是一成不变的**：

| 反派 | 初始状态 | 转化契机 | 最终状态 | 转化原因 |
|-----|---------|---------|---------|---------|
| [示例] | 敌对 | 第30章被主角救过 | 盟友 | 发现主角才是对的 |
| | | | | |

---

### ⚠️ 质量检查

输出前请检查：
- [ ] 每个反派是否有明确的动机？
- [ ] 反派是否有层次（不是都在同一水平）？
- [ ] 反派是否与主角的成长对应？
- [ ] 是否有足够的对手支撑长篇故事？
- [ ] 反派之间的关系是否清晰？

---

### 🚫 禁止事项

- 禁止反派为坏而坏（要有自己的逻辑）
- 禁止所有反派都一样（要有差异化）
- 禁止反派没有成长（也在变强）
- 禁止反派数量过多导致读者记不住

📝 **输出长度**：1500-2500字
"""
        elif task_type == "世界观规则":
            genre = goal.get('genre', '科幻')
            word_count = goal.get("word_count", 50000)
            
            # 根据字数调整世界观复杂度
            if word_count >= 500000:
                complexity = "高复杂度"
                detail_note = "长篇需要完整的世界观体系，但仍需确保读者能理解。"
            elif word_count >= 200000:
                complexity = "中等复杂度"
                detail_note = "中长篇可以有较完整的设定，但要避免设定过载。"
            else:
                complexity = "简洁"
                detail_note = "短中篇世界观要精简，只保留故事必需的设定。"
            
            # 科幻类型特别提醒
            sci_fi_worldview_note = ""
            if genre == "科幻":
                sci_fi_worldview_note = """
🔔 **科幻世界观特别提醒**：
- 世界观是给你自己参考的，不是给读者看的学术论文
- 设定要**能用故事讲出来**，不是干巴巴的规则罗列
- 科技设定要**通俗易懂**，用生活中的比喻来解释
- 参考《三体》：复杂的科学概念用简单的比喻解释（如"二向箔像一张纸"）
"""
            
            task_section = f"""
## 当前任务：{task_type}

基于大纲，构建完整、独特的世界观设定。

📊 **本书规模**：{word_count//10000}万字 → 复杂度：{complexity}
{sci_fi_worldview_note}

## 一、世界基础设定

### 1. 时空背景
| 项目 | 设定 | 对故事的影响 |
|-----|------|------------|
| 时代 | | |
| 地点 | | |
| 历史背景 | | |
| 与现实的差异 | | |

### 2. 社会结构
| 政治体制 | 社会阶层 | 经济体系 | 文化习俗 |
|---------|---------|---------|---------|
| | | | |

### 3. 主角位置
- 主角社会地位与处境
- 可能成为阻力的社会因素

## 二、独特/特殊设定（关键！）

每个特殊设定包含：名称、运作规则、限制/代价、对故事的影响、展示方式

### 特殊设定1：[名称]
- **设定内容**：是什么
- **运作规则**：如何运作、限制、谁可用
- **故事影响**：推动剧情、主角互动
- **展示方式**：自然展现的章节/场景

### 特殊设定2：[名称]
[同上]

### 特殊设定3：[名称]
[同上]

## 三、核心规则体系

### 1. 与现实的关键差异
| 差异点 | 具体设定 | 呈现方式 |
|-------|---------|---------|
| | | |

### 2. 能力/魔法/科技体系
| 项目 | 内容 |
|-----|------|
| 体系名称 | |
| 能力来源 | |
| 激活条件 | |
| 等级划分 | |
| 使用代价 | |
| 能力限制 | |

**能力分类**：
| 类型 | 效果 | 获得方式 | 限制 |
|-----|-----|---------|-----|
| | | | |

### 3. 核心规则（最多5条）
| 规则 | 内容 | 故事功能 | 可能的破例 |
|-----|------|---------|----------|
| | | | |

## 四、日常生活细节
| 衣 | 食 | 住 | 行 | 娱乐 | 工作 |
|----|----|----|----|------|------|
| | | | | | |

## 五、重要组织/势力
| 势力名称 | 性质 | 核心理念 | 实力规模 | 与主角关系 |
|---------|------|----------|----------|-----------|
| | | | | |

## 六、世界观词典
| 专有名词 | 解释（用比喻/日常语言） | 首现时机 |
|---------|---------------------|---------|
| | | |

## 七、与大纲的关联
1. **核心冲突**：世界观如何制造外部阻碍
2. **主题强化**：设定如何体现故事主题
3. **人物舞台**：人物如何在世界中行动

### 要求
- 用白话文描述，通俗易懂
- 必须有独特/特殊设定
- 设定要有代价和限制
- 输出1500-3000字
"""
        elif task_type in ["事件设定", "事件"]:
            chapter_count = goal.get("chapter_count", 10)
            word_count = goal.get("word_count", 50000)
            
            # 根据章节数调整事件数量
            if chapter_count >= 30:
                event_count = "10-15"
            elif chapter_count >= 15:
                event_count = "7-10"
            else:
                event_count = "5-8"
                
            task_section = f"""
## 当前任务：{task_type} ⚡

你是一位顶级畅销小说家，正在为新书规划**关键转折事件**。

> "故事就是一系列有因果关系的事件，每个事件都让情况变得更好或更糟。" — 罗伯特·麦基

---

### 📌 任务说明

设计推动故事发展的**核心转折事件**。

📊 **本书规模**：{chapter_count}章，约{word_count//10000}万字
💡 **建议事件数**：{event_count}个关键转折点

---

### 🏆 顶级作家的事件法则

**法则一：事件必须改变现状**
- 好的事件让事情变得更好或更糟，不能是无关紧要的
- 每个事件后，人物的处境必须不同于之前

**法则二：事件必须有因果关系**
- 事件A导致事件B，事件B导致事件C
- 不是"然后发生了..."，而是"因为...所以..."

**法则三：事件要考验人物**
- 好的事件迫使人物做出选择
- 选择揭示性格，性格决定命运

---

### 📋 请输出以下内容

---

## 一、核心冲突定义

**主要矛盾**：
1. **冲突本质**：[一句话概括]
2. **冲突双方**：[谁vs谁/什么]
3. **赌注**：[如果失败会失去什么？要够重！]
4. **为何难解**：[为什么不能轻易解决？]

---

## 二、故事结构（三幕式）

### 第一幕：建立 → 进入（约占20%，第1-{max(1, chapter_count//5)}章）

**目标**：建立世界、人物、日常，然后打破日常

| 事件 | 章节 | 功能 | 描述 |
|-----|-----|-----|-----|
| 开场状态 | 第1章 | 展示日常 | |
| 触发事件 | 第X章 | 打破日常 | |
| 跨越门槛 | 第X章 | 进入主线 | |

### 第二幕：对抗 → 升级（约占60%，第{max(2, chapter_count//5+1)}-{max(3, int(chapter_count*0.8))}章）

**目标**：冲突升级，人物成长，困难加剧

| 事件 | 章节 | 功能 | 描述 |
|-----|-----|-----|-----|
| 第一考验 | 第X章 | 初次挫折 | |
| 小胜利 | 第X章 | 虚假希望 | |
| 中点反转 | 约第{chapter_count//2}章 | 重大转折 | |
| 困境加深 | 第X章 | 形势恶化 | |
| 黑暗时刻 | 第X章 | 最低谷 | |

### 第三幕：决战 → 结局（约占20%，第{max(4, int(chapter_count*0.8)+1)}-{chapter_count}章）

| 事件 | 章节 | 功能 | 描述 |
|-----|-----|-----|-----|
| 觉醒/准备 | 第X章 | 重新振作 | |
| 最终对决 | 第X章 | 高潮 | |
| 结局 | 第{chapter_count}章 | 收尾 | |

---

## 三、关键转折事件详解（{event_count}个）

每个事件详细描述：

### 事件1：[事件名称]

| 项目 | 内容 |
|-----|------|
| 发生章节 | 约第X章 |
| 事件类型 | [触发/发展/转折/高潮/结局] |
| 参与人物 | |

**事件描述**（100-150字）：
[具体发生什么]

**因果关系**：
- 因为什么导致这个事件？
- 这个事件导致什么后果？

**人物选择**：
- 主角必须做什么选择？
- 这个选择揭示了什么性格？

**情绪效果**：
- 读者会有什么感受？

---

### 事件2：[事件名称]
[同上格式...]

---

## 四、支线冲突（2-3条）

| 支线 | 涉及人物 | 与主线关系 | 起止章节 |
|-----|---------|----------|---------|
| | | [平行/辅助/对照] | 第X-X章 |

---

## 五、事件时间线总览

| 章节 | 主线事件 | 支线事件 | 情绪曲线 |
|-----|---------|---------|---------|
| 1 | | | ⬛⬛⬛⬜⬜ |
| 2 | | | |
| ... | | | |
| {chapter_count} | | | |

---

### ❌ 禁止事项

- 禁止事件之间没有因果关系
- 禁止事件不改变现状
- 禁止所有事件都是打斗/灾难（要有情感戏）
- 禁止写成小说正文

📝 **输出长度**：1200-2000字
"""
        elif task_type == "伏笔列表":
            chapter_count = goal.get("chapter_count", 10)
            word_count = goal.get("word_count", 50000)
            
            # 根据章节数/字数调整伏笔数量
            if chapter_count >= 30:
                main_foreshadow = "5-8"
                char_foreshadow = "2-3"
            elif chapter_count >= 15:
                main_foreshadow = "4-6"
                char_foreshadow = "1-2"
            else:
                main_foreshadow = "3-4"
                char_foreshadow = "1"
                
            task_section = f"""
## 当前任务：{task_type} 🔮

你是一位顶级畅销小说家，正在为新书设计**伏笔系统**。

> "伏笔是作者与读者之间的秘密游戏——埋下时不动声色，揭晓时恍然大悟。" — 阿加莎·克里斯蒂

---

### 📌 任务说明

设计故事中的**伏笔网络**——那些看似不经意的细节，在后文中会产生重要意义。

📊 **本书规模**：{chapter_count}章，约{word_count//10000}万字
💡 **建议伏笔数**：主线伏笔{main_foreshadow}个，人物伏笔每人{char_foreshadow}个

---

### 🏆 顶级作家的伏笔法则

**法则一：伏笔要"藏在眼皮底下"**
- 最好的伏笔是读者看到了但没当回事
- 可以藏在对话中、环境描写中、角色习惯中
- 例：《哈利波特》中斯内普对莉莉的感情线索

**法则二：揭晓要有"啊哈！"时刻**
- 读者看到揭晓时应该有恍然大悟的感觉
- 回看时能发现所有线索都在那里
- 不能太早揭晓（失去悬念）也不能太晚（读者忘了）

**法则三：伏笔必须回收**
- 埋下的伏笔一定要揭示，否则是欺骗读者
- 每个伏笔的回收要有足够的冲击力
- 多个伏笔可以连锁揭示，制造高潮

---

### 📋 请输出以下内容

---

## 一、主线伏笔（{main_foreshadow}个）

这些伏笔直接关系到故事大纲，揭示时会产生重大剧情转折。

### 伏笔1：[伏笔名称]

| 项目 | 内容 |
|-----|------|
| 伏笔内容 | [什么细节/台词/物品/行为] |
| 真正含义 | [这个细节背后的真相是什么] |

**埋设设计**：
- 埋设位置：第X章，[什么场景]
- 埋设方式：[对话/描写/行动/背景]
- 伪装技巧：[如何让读者看到但不起疑]

**揭示设计**：
- 揭示位置：第X章，[什么事件中]
- 揭示方式：[如何揭晓真相]
- 冲击效果：[读者会有什么反应]

**线索链**：
- 第一次暗示（埋设）：第X章
- 第二次呼应（强化）：第X章
- 最终揭示：第X章

---

### 伏笔2：[伏笔名称]
[同上格式...]

---

## 二、人物伏笔

每个主要人物的隐藏信息：

| 人物 | 隐藏内容 | 伏笔类型 | 埋设章节 | 揭示章节 | 揭示影响 |
|-----|---------|---------|---------|---------|---------|
| | | [身份/动机/秘密/能力/关系] | 第X章 | 第X章 | |

**人物伏笔详解**（选2-3个重要的展开）：

### [人物名]的隐藏

**伏笔内容**：
- 隐藏的是什么：
- 为什么要隐藏：

**埋设线索**：
1. 第X章：[什么细节暗示]
2. 第X章：[什么行为可疑]
3. 第X章：[什么对话有深意]

**揭示时刻**：
- 如何揭晓：
- 对其他人物的影响：
- 对剧情的影响：

---

## 三、世界观伏笔（2-3个）

关于设定的隐藏规则，后面会变得重要：

| 伏笔 | 表面理解 | 真正含义 | 埋设/揭示 |
|-----|---------|---------|----------|
| | [读者一开始以为] | [实际上是] | 第X/X章 |

---

## 四、红鲱鱼（1-2个）

故意误导读者的假线索：

| 误导内容 | 让读者以为 | 实际真相 | 揭穿章节 | 设计目的 |
|---------|----------|---------|---------|---------|
| | | | 第X章 | [转移注意力/制造意外] |

---

## 五、伏笔时间线

| 章节 | 埋设的伏笔 | 呼应/强化 | 揭示的伏笔 |
|-----|----------|----------|----------|
| 第1章 | | | |
| 第2章 | | | |
| ... | | | |
| 第{chapter_count}章 | | | |

---

## 六、伏笔关联图

```
伏笔A ─────┐
          ├──→ 揭示X（第Y章）──→ 连锁揭示
伏笔B ─────┘
         ↑
伏笔C ────┘
```

**关联说明**：
- [伏笔A]和[伏笔B]互相印证
- [伏笔C]的揭示触发[伏笔D]的揭示

---

### ❌ 禁止事项

- 禁止伏笔埋了不揭示
- 禁止揭示时机不当（太早或太晚）
- 禁止伏笔太明显（读者一看就猜到）
- 禁止伏笔和主线无关

📝 **输出长度**：1000-1500字
"""
        elif task_type == "大纲":
            chapter_count = goal.get('chapter_count', 20)
            word_count = goal.get('word_count', 50000)
            words_per_chapter = word_count // max(chapter_count, 1)
            
            # 根据字数显示
            if word_count >= 10000:
                word_display = f"{word_count // 10000}万字"
            else:
                word_display = f"{word_count}字"
            
            task_section = f"""
## 当前任务：{task_type} 📋

请为这部小说创建**精简核心大纲**。

### 📌 核心约束

| 项目 | 要求 |
|-----|------|
| 总字数 | {word_display} |
| 章节数 | **{chapter_count} 章**（必须规划全部，一章不少） |
| 每章字数 | 约 {words_per_chapter} 字 |

### 📋 输出内容

**一、故事核心**（200字左右）
- 一句话概括：主角+想要什么+面临什么阻碍+为什么读者会在意
- 主角内核：核心目标、核心恐惧、核心欲望、性格特点

**二、核心门派**（只写直接相关的，其他由插件扩展）

| 门派 | 内核 | 与主角关系 | 首次出场 |
|-----|------|-----------|---------|
| [名称] | [理念] | [关系] | 第X章 |

**三、主角团**（只写核心成员，配角由插件扩展）

| 角色 | 性格/作用 | 团队定位 |
|-----|----------|---------|
| [姓名] | [特点] | [定位] |

**四、主线伏笔**（只写主线伏笔，细节由插件追踪）

| 伏笔 | 埋设 | 回收 | 重要性 |
|-----|------|------|--------|
| [名称] | 第X章 | 第X章 | 关键/重要 |

**五、章节骨架**（核心部分，每章一句话梗概）

### 三幕结构
- 第一幕：第1-{chapter_count//5}章（建立与进入）
- 第二幕：第{chapter_count//5+1}-{int(chapter_count*0.8)}章（对抗与发展）
- 第三幕：第{int(chapter_count*0.8)+1}-{chapter_count}章（高潮与结局）

### 详细章节规划（必须全部{chapter_count}章，每章一句话）

| 章节 | 梗概 | 功能标记 |
|-----|------|---------|
| 第1章 | | [日常/触发/反转] |
| 第2章 | | |
| ... | ... | ... |
| 第{chapter_count}章 | | [终局] |

⚠️ **关键标记**：中点反转（约第{chapter_count//2}章）、黑暗时刻（约第{int(chapter_count*0.75)}章）、最终对决（第{chapter_count-1}章）

### 输出格式

1. **直接输出大纲内容**，不要输出额外的说明或标题
2. **从"一、故事核心"开始输出**
3. **章节规划必须覆盖全部 {chapter_count} 章**，不要用"..."省略
4. 每章用一句话概括即可，不需要详细场景
5. 使用表格和标题组织内容，格式清晰
"""
        elif task_type == "章节大纲":
            chapter_index = task.metadata.get("chapter_index", "未知")
            chapter_count = goal.get("chapter_count", 10)
            word_count = goal.get("word_count", 50000)
            words_per_chapter = word_count // max(chapter_count, 1)
            
            # 🔥 获取前面章节内容，构建连贯性上下文
            chapter_continuity = ""
            if isinstance(chapter_index, int) and chapter_index > 1:
                previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=2)
                outline_content = predecessor_contents.get("大纲", "")
                chapter_continuity = self._build_chapter_continuity_context(
                    chapter_index, previous_chapters, outline_content
                )
            
            task_section = f"""
{chapter_continuity}

## 当前任务：第{chapter_index}章 - 详细章节大纲 📝

你是一位顶级畅销小说家，正在为第{chapter_index}章创建**详细写作蓝图**。

> "好的章节像一部微型电影——有开场、有发展、有高潮、有余韵。每一章都应该让读者感到值得。" — 布兰登·桑德森

---

### ⚠️ 连贯性要求（第{chapter_index}章必须做到）

{"**这是第一章**，是故事的开端。需要：引入主角、建立世界、制造钩子。" if chapter_index == 1 else f"**必须承接第{chapter_index-1}章的结尾**！开场要从上一章结束的地方自然过渡，不能像另一个故事。"}

---

### 📌 章节信息

| 项目 | 内容 |
|-----|------|
| 章节位置 | 第 **{chapter_index}** / {chapter_count} 章 |
| 目标字数 | 约 **{words_per_chapter}** 字 |
| 建议场景数 | **4-6** 个场景 |

---

### 🏆 顶级作家的章节法则

**法则一：开头要抓人**
- 前100字必须让读者想继续读
- 可以用悬念、冲突、有趣的画面开场

**法则二：每个场景要有"转变"**
- 进入场景时的状态 ≠ 离开时的状态
- 信息变了、关系变了、或情绪变了

**法则三：结尾要有钩子**
- 章节结尾要让读者舍不得放下书
- 可以用悬念、转折、或情感冲击

---

### 📋 请输出以下内容

---

## 一、章节概览

**章节标题**：[吸引人的标题]

| 项目 | 内容 |
|-----|------|
| 叙事阶段 | [开端/发展/高潮/收尾] |
| 主要POV | [谁的视角] |
| 情绪基调 | [紧张/温馨/压抑/...] |

**本章目标**（必须完成）：
1. 📖 情节目标：[推进什么剧情]
2. 👤 人物目标：[展现/发展谁]
3. 💡 信息目标：[告诉读者什么]
4. 💗 情感目标：[让读者感到什么]

---

## 二、场景分解（4-6个场景）

### 场景1：[场景名/一句话概括]

| 项目 | 内容 |
|-----|------|
| 地点 | [参考【世界观规则】] |
| 时间 | [具体时间/天气] |
| 氛围 | [一个词概括] |

**出场人物**：
| 人物 | 状态 | 这场景的目标 |
|-----|-----|-------------|
| | [情绪/状态] | [想要什么] |

**场景内容**（200-300字）：

**开场**：
[如何进入这个场景？第一个画面是什么？]

**发展**：
[发生什么？对话/行动的要点]

**冲突/转变**：
[这个场景的张力点是什么？发生了什么变化？]

**结束**：
[如何过渡到下一场景？]

**关键对话要点**：
- [对话1要传达的信息]
- [对话2要传达的信息]

---

### 场景2：[场景名]
[同上格式...]

### 场景3：[场景名]
[同上格式...]

### 场景4：[场景名]
[同上格式...]

（继续到4-6个场景...）

---

## 三、伏笔操作

**本章埋设**：
| 伏笔 | 埋设方式 | 将在哪揭示 |
|-----|---------|----------|
| | [对话/描写/行动] | 第X章 |

**本章揭示**：
| 伏笔 | 揭示方式 | 读者反应 |
|-----|---------|---------|
| | | [恍然大悟/震惊/感动] |

---

## 四、情绪节奏

**本章情绪曲线**：

```
开头 [情绪] ──→ 场景2 [情绪] ──→ 中间 [情绪] ──→ 场景4 [情绪] ──→ 结尾 [情绪]
         ↗︎              ↘︎                ↗︎              ↘︎
```

**节奏控制**：
| 场景 | 节奏 | 原因 |
|-----|-----|-----|
| 场景1 | 快/中/慢 | |
| 场景2 | | |
| ... | | |

---

## 五、章节衔接

**承上**：
- 时间：[紧接上章/过了X时间]
- 情绪：[延续/转换]
- 信息：[承接什么]

**启下**：
- 悬念：[留下什么钩子]
- 铺垫：[为下章埋什么线]

---

## 六、写作备忘

**必须写好**：
- [本章最重要的场景/对话]

**避免问题**：
- [需要注意的一致性]

---

### ❌ 禁止事项

- 禁止场景之间跳跃突兀
- 禁止章节没有情绪起伏
- 禁止开头平淡无味
- 禁止结尾没有钩子

📝 **输出长度**：800-1200字
"""
        elif task_type == "场景生成":
            chapter_index = task.metadata.get("chapter_index", "未知")
            scene_index = task.metadata.get("scene_index", "未知")
            task_section = f"""
## 当前任务：第{chapter_index}章 - 场景{scene_index} 🎬

你是一位顶级畅销小说家，正在创作第{chapter_index}章的场景{scene_index}。

> "好的场景就像电影画面，读者能'看到'发生了什么。" — 詹姆斯·斯科特·贝尔

---

### 📌 场景写作要求

**核心原则**：让读者身临其境

**必须包含**：
1. **环境渲染**：用五感细节（视/听/嗅/触/味）营造氛围
2. **人物动作**：具体的行动而非笼统的描述
3. **自然对话**：符合人物性格，推动剧情
4. **情绪张力**：场景要有起伏和变化

---

### 🏆 顶级作家的场景法则

**法则一：进入场景要快**
- 直接进入动作或对话
- 不要用大段环境描写开场

**法则二：展示而非告诉**
- ❌ "他很紧张"
- ✅ "他的手指不自觉地敲着桌面，目光在门口和窗户之间来回游移"

**法则三：对话要有潜台词**
- 人物说的不一定是想的
- 对话背后要有情感和目的

---

### ❌ 禁止事项

- 禁止标注"场景X"等标记
- 禁止大段心理独白
- 禁止对话无意义的寒暄
- 禁止纯描写无动作
- 禁止违反已设定的人物性格

📝 **输出**：直接输出小说正文，800-1500字
"""
        elif task_type == "章节内容":
            chapter_index = task.metadata.get("chapter_index", "未知")
            # 计算每章目标字数
            word_count = goal.get("word_count", 50000)
            chapter_count = goal.get("chapter_count", 10)
            words_per_chapter = word_count // chapter_count
            # 设置合理的范围
            min_words = max(2000, int(words_per_chapter * 0.8))
            max_words = int(words_per_chapter * 1.2)

            # 🔥 获取前面章节内容，构建连贯性上下文
            chapter_continuity = ""
            continuity_framework = ""
            if isinstance(chapter_index, int) and chapter_index > 1:
                previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=2)
                outline_content = predecessor_contents.get("大纲", "")
                chapter_continuity = self._build_chapter_continuity_context(
                    chapter_index, previous_chapters, outline_content
                )

                # 🎯 生成章节衔接框架（由 ChapterContinuityManager 提供）
                # 提取上一章结尾（最后500字）
                previous_chapter_ending = None
                if (chapter_index - 1) in previous_chapters:
                    prev_content = previous_chapters[chapter_index - 1].get("content", "")
                    if prev_content:
                        previous_chapter_ending = prev_content[-500:] if len(prev_content) > 500 else prev_content

                # 获取当前章节大纲
                current_chapter_outline = ""
                for result in (context.recent_results or []):
                    if result.get("task_type") == "章节大纲" and result.get("chapter_index") == chapter_index:
                        current_chapter_outline = result.get("content", "")
                        break

                # 生成衔接框架
                if previous_chapter_ending or chapter_index == 1:
                    framework_result = await self.chapter_continuity_manager.generate_continuity_framework(
                        chapter_index=chapter_index,
                        previous_chapter_ending=previous_chapter_ending,
                        chapter_outline=current_chapter_outline,
                        context={"goal": goal, "config": self.config}
                    )
                    # 将框架格式化为提示词
                    if framework_result.get("opening_framework") or framework_result.get("opening_instructions"):
                        continuity_framework = f"""

### 🎯 本章衔接框架（请严格参考）

**开头框架指导**：
{framework_result.get("opening_instructions", "").strip()}

{framework_result.get("opening_framework", "").strip()}

**结尾框架指导**：
{framework_result.get("closing_instructions", "").strip()}

{framework_result.get("closing_hook_template", "").strip()}
---
"""

            task_section = f"""
{chapter_continuity}
{continuity_framework}

## 当前任务：第{chapter_index}章 - 章节内容 ✍️

你是一位顶级畅销小说家，正在创作第{chapter_index}章的**完整正文**。

> "写作的秘诀是把每一个句子都写得让读者想读下一句。" — 约翰·格里森

---

### ⚠️ 连贯性要求（最重要！）

{"**这是第一章**，是读者接触故事的第一印象。需要：吸引人的开场、引入主角、建立世界观基调、制造悬念钩子。" if chapter_index == 1 else f'''**必须从第{chapter_index-1}章结尾处衔接！**

本章开头必须：
1. 自然承接上一章的结尾场景/情绪/悬念
2. 人物状态与上一章结尾保持一致
3. 时间线和空间位置要连贯
4. 如果有时间跳跃，必须用过渡语句交代

❌ **绝对禁止**：本章开头像另一个独立的故事，与前面毫无关联'''}

---

### 📌 写作要求

| 项目 | 要求 |
|-----|------|
| 目标字数 | **{min_words}-{max_words}** 字 |
| 叙事视角 | [根据风格元素设定] |
| 语言风格 | [根据风格元素设定] |

---

### 🏆 顶级作家的写作法则

**法则一：展示，不要告诉（Show, Don't Tell）**
- ❌ "他很生气"
- ✅ "他的手指收紧，指节发白，咬着牙一字一顿地说……"

**法则二：对话要推动剧情**
- 每句对话都要有目的：揭示信息/制造冲突/展现性格
- 避免无意义的寒暄和废话

**法则三：场景转换要流畅**
- 场景之间需要过渡，不能生硬跳切
- 可以用时间跳跃、空间移动、或情绪转换

**法则四：五感细节要丰富**
- 不只是"看到"，还有听到、闻到、触到、尝到
- 细节要服务于氛围和情绪

**法则五：保持故事线索连贯**
- 每一章都是整体故事的一部分，不是独立短篇
- 前面埋的伏笔要有回应或继续铺垫
- 人物弧线要有连续性发展

---

### 📋 写作指南

**基于章节大纲，创作完整的章节正文**

**内容要求**：
1. {"从引人入胜的场景开始" if chapter_index == 1 else "从上一章结尾自然衔接开始"}
2. 按场景顺序自然展开
3. 场景之间有流畅过渡
4. 人物性格保持一致
5. 世界观设定保持一致
6. 节奏有张有弛
7. **与前面章节保持情节连贯**

**格式要求**：
- 直接输出小说正文
- 以章节标题开头（如："第{chapter_index}章 [标题]"）
- 不要输出"场景1"、"场景2"之类的标记
- 段落分明，对话独立成行

**质量标准**：
- {"开头100字要抓住读者，建立第一印象" if chapter_index == 1 else "开头要自然衔接上一章"}
- 对话要自然有节奏
- 描写要有画面感
- 结尾要有钩子，让读者想读下一章

---

### ❌ 禁止事项

- 禁止大段心理独白（要化为行动和对话）
- 禁止信息堆砌式描写
- 禁止对话冗长无重点
- 禁止场景转换生硬
- 禁止输出写作说明或注释
- **禁止与前面章节脱节，像独立短篇**

📝 **输出**：完整的章节正文，{min_words}-{max_words}字
"""
        elif task_type == "章节润色":
            chapter_index = task.metadata.get("chapter_index", "未知")
            
            # 🔥 获取前面章节内容，确保润色时保持连贯性
            chapter_continuity = ""
            if isinstance(chapter_index, int) and chapter_index > 1:
                previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=2)
                outline_content = predecessor_contents.get("大纲", "")
                chapter_continuity = self._build_chapter_continuity_context(
                    chapter_index, previous_chapters, outline_content
                )
            
            task_section = f"""
{chapter_continuity}

## 当前任务：第{chapter_index}章 - 章节润色 ✨

你是一位顶级文学编辑，正在为第{chapter_index}章进行**精细润色**。

> "好的写作是改出来的。第一稿是把沙子倒出来，修改是从沙子里淘金。" — 欧内斯特·海明威

---

### 📌 润色目标

把一份"好"的稿子变成"优秀"的稿子。

---

### 🏆 顶级编辑的润色法则

**法则一：删掉所有不必要的词**
- 每个形容词、每个副词都要质问：真的需要吗？
- "非常美丽的花" → "绚烂的花"

**法则二：加强动词的力度**
- 弱动词换强动词："他走过去" → "他冲过去/踱过去/溜过去"
- 动词承载情绪

**法则三：对话要能"听出"性格**
- 不同人物说话方式应该不同
- 读对话时能分辨是谁在说

**法则四：节奏感要体现在句子长度**
- 紧张时用短句
- 抒情时可以用长句
- 避免句式单调

---

### 📋 润色方向

**1. 文字层面**
- [ ] 删除冗余词汇
- [ ] 替换弱动词为强动词
- [ ] 优化形容词使用
- [ ] 调整句子节奏

**2. 描写层面**
- [ ] 补充必要的感官细节
- [ ] 强化有画面感的描写
- [ ] 删除无意义的环境描写

**3. 对话层面**
- [ ] 让对话更符合人物性格
- [ ] 删除无意义的对话
- [ ] 对话标签多样化（不只是"说"）

**4. 结构层面**
- [ ] 检查场景过渡是否流畅
- [ ] 检查节奏起伏是否合适
- [ ] 检查开头是否抓人
- [ ] 检查结尾是否有钩子

**5. 一致性检查**
- [ ] 人物性格是否一致
- [ ] 设定是否一致
- [ ] 与前后章节是否衔接

---

### ❌ 禁止事项

- 禁止改变情节走向
- 禁止改变人物关系
- 禁止添加新的剧情元素
- 禁止输出修改说明（只输出润色后的正文）

---

### 📝 输出要求

直接输出**润色后的完整章节内容**
- 不要输出对比说明
- 不要标注修改位置
- 不要写"修改前/修改后"
- 只输出最终版本
"""
        elif task_type == "一致性检查":
            task_section = f"""
## 当前任务：{task_type} 🔍

🚨🚨🚨 **极其重要的警告** 🚨🚨🚨

你是一位**质量检查员**，正在做**检查报告**，而不是写小说！！！

❌ **绝对禁止**：输出任何小说内容、故事情节、人物对话
✅ **你的任务**：只输出问题清单和评估报告

如果你输出了小说内容，说明你完全理解错了任务！这是**检查任务**，不是**创作任务**！

---

> "读者会原谅作者的写作瑕疵，但不会原谅逻辑漏洞。" — 布兰登·桑德森

---

### 📌 检查维度

**1. 人物一致性**
| 检查项 | 要点 |
|-------|------|
| 性格一致 | 人物行为是否前后矛盾 |
| 外貌一致 | 外貌描写有无冲突 |
| 背景一致 | 人物背景有无自相矛盾 |
| 关系一致 | 人物关系有无错乱 |

**2. 世界观一致性**
| 检查项 | 要点 |
|-------|------|
| 规则一致 | 设定的规则是否被违反 |
| 时间线 | 时间顺序有无矛盾 |
| 空间 | 地理/距离有无冲突 |
| 科技/魔法 | 能力体系是否自洽 |

**3. 情节一致性**
| 检查项 | 要点 |
|-------|------|
| 伏笔回收 | 埋下的伏笔是否揭示 |
| 因果关系 | 事件之间因果是否成立 |
| 情节漏洞 | 有无逻辑问题 |

---

### 📋 输出格式

**问题清单**（按严重程度排序）：

| 严重度 | 位置 | 问题描述 | 修改建议 |
|-------|-----|---------|---------|
| 🔴严重 | 第X章 | | |
| 🟡中等 | 第X章 | | |
| 🟢轻微 | 第X章 | | |

**总体评估**：
- 一致性评分：X/10
- 主要问题：
- 整体评价：

🚨🚨🚨 **再次强调** 🚨🚨🚨
- 这是**检查报告**任务
- 只输出上面格式的**问题清单**和**总体评估**
- **绝对不要**输出任何小说内容、故事情节、人物描写
- 如果检查发现没有问题，就写"未发现明显问题"
"""
        elif task_type == "评估":
            task_section = f"""
## 当前任务：{task_type} 📊

你是一位资深的文学评论家和编辑，正在对创作内容进行**综合质量评估**（同时评估文学质量和逻辑一致性）。

> "好的编辑不只关注文字优美，更要确保逻辑自洽。" — 罗伯特·戈特利布

---

### 📌 评估维度

**第一部分：文学质量评分**

| 维度 | 评分 | 说明 |
|-----|-----|------|
| **故事性** | X/10 | 情节是否吸引人？有无让人想继续读的欲望？ |
| **人物** | X/10 | 人物是否立体？有无让人记住的角色？ |
| **文学性** | X/10 | 文字是否有美感？语言是否得当？ |
| **可读性** | X/10 | 是否通俗易懂？节奏是否合适？ |
| **完整性** | X/10 | 结构是否完整？有无遗漏？ |
| **创意性** | X/10 | 有无新意？是否有独特之处？ |

**第二部分：逻辑一致性检查**

| 维度 | 评分 | 说明 |
|-----|-----|------|
| **人物一致性** | X/10 | 性格、外貌、背景、关系是否前后矛盾？ |
| **世界观一致性** | X/10 | 规则、时间线、空间、能力体系是否自洽？ |
| **情节一致性** | X/10 | 伏笔、因果关系、逻辑是否有问题？ |

---

### 📋 请按以下格式输出

**一、文学质量评分**

| 维度 | 评分 | 优点 | 不足 |
|-----|-----|-----|-----|
| 故事性 | /10 | | |
| 人物 | /10 | | |
| 文学性 | /10 | | |
| 可读性 | /10 | | |
| 完整性 | /10 | | |
| 创意性 | /10 | | |

**二、逻辑一致性检查**

🔴 **严重问题**（必须修复）：
- 问题1：[位置] - [具体问题] - [修改建议]
- ...

🟡 **中等问题**（建议修复）：
- 问题1：[位置] - [具体问题] - [修改建议]
- ...

🟢 **轻微问题**（可选修复）：
- 问题1：[位置] - [具体问题] - [修改建议]
- ...

✅ 如果未发现明显问题，请写"未发现明显逻辑问题"

**三、问题清单汇总**（按优先级排序）

| 优先级 | 类型 | 位置 | 问题描述 | 建议 |
|-------|------|-----|---------|-----|
| 🔴P0 | [质量/一致性] | 第X章/全局 | | |
| 🟡P1 | [质量/一致性] | 第X章/全局 | | |
| 🟢P2 | [质量/一致性] | 第X章/全局 | | |

**四、亮点总结**（3-5条）
-

**五、总体评价**
- 综合质量评分：X/10
- 一致性评分：X/10
- 一句话评价：

⚠️ **重要提醒**：
- 这是**评估报告**，请客观专业
- 质量问题和逻辑问题都要关注
- 不要输出小说内容或情节，只输出评估报告
- 如果内容很完美，也要如实给出高分评价
"""
        elif task_type == "修订":
            task_section = f"""
## 当前任务：{task_type} ✏️

你是创作这部小说的顶级畅销小说家，现在需要根据反馈**修订内容**。

> "写作是改出来的。第一稿是把沙子倒出来，修改是从沙子里淘金。" — 海明威

---

### 📌 修订原则

**优先级**：
1. 🔴 **先修逻辑**：情节漏洞、设定矛盾
2. 🟡 **再改结构**：节奏问题、结构松散
3. 🟢 **最后润色**：文字质量、细节描写

**守则**：
- 保持原有风格和基调
- 不过度改写，保留原作特点
- 确保与整体设定一致
- 改善但不改变故事大纲

---

### ❌ 禁止事项

- 禁止改变已确定的情节走向
- 禁止改变人物基本性格
- 禁止添加未经规划的新元素
- 禁止输出修订说明（只输出最终内容）

---

### 📝 输出要求

直接输出**修订后的完整内容**
- 不要输出"修改前/修改后"
- 不要标注修改位置
- 不要写修改说明
- 只输出最终版本
"""
        else:
            # Default for other tasks
            task_section = f"\n## 当前任务\n{task.description}\n\n"
            task_section += f"任务类型: {task.task_type.value}\n"

            if task.metadata.get("chapter_index"):
                task_section += f"章节: 第{task.metadata['chapter_index']}章\n"
            if task.metadata.get("scene_index"):
                task_section += f"场景: {task.metadata['scene_index']}\n"

        sections.append(task_section)
        
        # 🎯 添加高分示例参考（如果有的话）
        best_example = self._get_best_example_for_task(task_type, genre)
        if best_example:
            sections.append(best_example)
            logger.info(f"📌 为任务 {task_type} 添加了高分示例参考")

        # Output format instruction based on task type
        # 🔥 优化：使用类级别常量
        if task_type in self.ALL_TASKS_TYPES["strategy"]:
            sections.append("""
## 输出要求
⚠️ **这是策略规划阶段，不是小说创作！**

- 用简洁、概括性的语言
- 明确核心要素，不要展开细节
- 输出格式：结构化的要点列表
- **不要写小说正文、对话、场景描写**
- 保持抽象和战略层面的思考

""")
        elif task_type in self.ALL_TASKS_TYPES["planning"]:
            sections.append("""
## 输出要求
- 使用结构化的格式输出（标题+内容）
- 语言简洁明了，每项1-3句话
- 这是规划文档，不是小说正文
- 不要写成学术论文，用通俗的语言
""")
        elif task_type in self.ALL_TASKS_TYPES["element"]:
            sections.append("""
## 输出要求
- 结构清晰，便于后续参考
- 描述要有文学性，但也要实用
- 这是创作素材，不是小说正文
- 适度使用描述性语言，让素材生动
""")
        elif task_type == "大纲":
            sections.append("""
## 输出要求

⚠️ **最关键的输出要求**：

1. **必须规划全部 {chapter_count} 章**，从第1章到第{chapter_count}章，一章都不能少！

2. **每一幕都要有完整的章节列表**：
   - 第一幕：第1章到第X章
   - 第二幕：第X+1章到第Y章
   - 第三幕：第Y+1章到第{chapter_count}章

3. **详细章节规划必须覆盖每一章**，不要用"..."省略

4. **输出格式要清晰**，使用表格和标题来组织内容

5. **不要输出标题或额外说明**，直接从"一、故事完整概览"开始输出

⚠️ 如果内容太长被截断，请优先确保：
- ✅ 三幕结构完整（每一幕的所有章节都列出）
- ✅ 详细章节规划至少覆盖前10章
- ✅ 人物列表完整
""")
        else:
            # Content generation tasks
            # 🔥 根据小说类型动态获取写作指南
            genre = goal.get("genre", "")
            writing_guide = self._get_genre_writing_guide(genre)

            sections.append(f"""
## 输出要求
请直接输出小说内容，使用文学化的语言：
- 必须是故事性的、叙事性的内容
- 使用生动、形象的文学语言
- 内容应该适合普通读者阅读
- 不需要额外的说明、标题或标注

{writing_guide}
""")

        prompt = "".join(sections)
        
        # 🧬 检查是否有进化后的更优提示词片段
        if self.enable_self_evolution:
            evolved_prompt = self.prompt_evolver.get_best_prompt(task_type)
            if evolved_prompt:
                # 将进化后的优化建议添加到提示词末尾
                prompt += f"""

════════════════════════════════════════════════════════════════
🧬 【提示词进化优化 - 基于历史反馈】
════════════════════════════════════════════════════════════════

根据以往的评估反馈，请特别注意以下优化建议：

{evolved_prompt}

════════════════════════════════════════════════════════════════
"""
                logger.info(f"📈 已加载进化提示词: {task_type}")

        # 🔥 标记提示词来源
        if not task.metadata.get("prompt_source"):
            task.metadata["prompt_source"] = "hardcoded"

        return prompt

    async def _attempt_rewrite(
        self,
        task: Task,
        content: str,
        evaluation: EvaluationResult,
        context: MemoryContext,
        goal: Dict[str, Any],
        max_retries: int = 3,  # 🔥 改为最多重写3次
        token_stats: Dict[str, int] = None,  # 🔥 用于累计 token 统计
    ) -> tuple:
        """
        Attempt to rewrite content based on evaluation feedback

        🔥 新机制：
        - 最多重写3次（避免无限循环）
        - 保留最佳版本（即使不通过）
        - 标记质量未通过的章节
        - 🔥 保存所有版本到数据库（版本历史管理）

        Args:
            max_retries: 最大重试次数（默认3次）

        Returns:
            tuple: (final_content, token_stats_dict, evaluation, passed)
            final_content: 最佳版本内容
            token_stats_dict 包含: total_tokens, prompt_tokens, completion_tokens, cost
            evaluation: 最终评估结果
            passed: 是否通过评估
        """

        logger.info(f"🔄 开始重写任务 {task.task_id}，最多 {max_retries} 次重写")

        # 初始化统计
        if token_stats is None:
            token_stats = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}

        attempt = 0
        best_content = content
        best_evaluation = evaluation
        best_score = evaluation.score
        passed = evaluation.passed

        # 🔥 初始化当前内容和评估（用于重写循环）
        current_content = content
        current_evaluation = evaluation

        # 🔥 获取一致性检查结果（如果有的话）
        consistency_result = task.metadata.get("consistency_check_result", None)

        # 🔥 保存初始版本（v1）- 仅对章节内容任务
        chapter_index = task.metadata.get("chapter_index", None)
        if chapter_index is not None and self.session_storage and task.task_type.value in ["章节内容", "章节润色"]:
            try:
                initial_token_stats = {
                    "total_tokens": token_stats.get("total_tokens", 0),
                    "prompt_tokens": token_stats.get("prompt_tokens", 0),
                    "completion_tokens": token_stats.get("completion_tokens", 0),
                    "cost": token_stats.get("cost", 0.0),
                }
                await self.session_storage.create_chapter_version(
                    session_id=self.session_id,
                    task_id=task.task_id,
                    chapter_index=chapter_index,
                    content=content,
                    version_number=1,
                    is_current=not evaluation.passed,  # 如果未通过则设为当前，否则后面会更新
                    evaluation=evaluation.to_dict(),
                    created_by="auto",
                    rewrite_reason=None,
                    token_stats=initial_token_stats,
                )
                logger.info(f"💾 已保存初始版本 v1 (分数: {evaluation.score:.2f})")
            except Exception as e:
                logger.warning(f"⚠️ 保存初始版本失败: {e}")

        while attempt < max_retries:  # 🔥 最多重写3次
            # 如果已经通过，直接返回
            if passed:
                logger.info(f"✅ 评估已通过，无需重写")
                return best_content, token_stats, best_evaluation, passed

            attempt += 1
            logger.info(f"🔄 重写尝试 #{attempt} - 任务: {task.task_type.value} (当前最佳分数: {best_score:.2f})")

            # 通知前端重试状态
            if self._on_task_start:
                task.metadata["retry_count"] = attempt
                task.metadata["retry_reason"] = f"评估未通过 (得分: {current_evaluation.score:.2f})"
                await self._safe_callback(self._on_task_start, task)

            # 🔥 发送重写进度
            quality_score = getattr(current_evaluation, "quality_score", current_evaluation.score)
            consistency_score = getattr(current_evaluation, "consistency_score", current_evaluation.score)
            await self._send_step_progress(
                step="rewrite_attempt",
                message=f"🔄 正在进行第 {attempt} 次重写...",
                task_id=task.task_id,
                task_type=task.task_type.value,
                rewrite_attempt=attempt,
                quality_score=quality_score,
                consistency_score=consistency_score
            )

            # Build improved prompt with feedback
            # 🔥 传递一致性检查结果
            feedback_prompt = self._build_rewrite_prompt(
                task=task,
                original_content=current_content,
                evaluation=current_evaluation,
                context=context,
                goal=goal,
                attempt=attempt,
                consistency_result=consistency_result,  # 传递一致性检查结果
            )

            try:
                # 🔥 发送 LLM 重写调用事件
                await self._send_step_progress(
                    step="rewrite_llm_call",
                    message=f"🤖 正在调用 LLM 进行第 {attempt} 次重写...",
                    task_id=task.task_id,
                    task_type=task.task_type.value,
                    rewrite_attempt=attempt
                )

                response = await self.llm_client.generate(
                    prompt=feedback_prompt,
                    task_type=task.task_type.value,
                    temperature=min(0.7 + attempt * 0.05, 1.0),  # 逐渐提高温度增加变化
                    max_tokens=self._get_max_tokens_for_task(task.task_type),
                )

                # 🔥 累计重写过程中的 token 消耗
                token_stats["total_tokens"] += response.usage.total_tokens
                token_stats["prompt_tokens"] += response.usage.prompt_tokens
                token_stats["completion_tokens"] += response.usage.completion_tokens
                token_stats["cost"] += self._calculate_cost(
                    response.provider.value, response.model, response.usage
                )

                # Re-evaluate
                await self._send_step_progress(
                    step="rewrite_evaluation",
                    message=f"📊 正在评估第 {attempt} 次重写结果...",
                    task_id=task.task_id,
                    task_type=task.task_type.value,
                    rewrite_attempt=attempt
                )

                # 🔥 获取前置任务内容和章节上下文（用于重写评估）
                task_type = task.task_type.value
                chapter_index = task.metadata.get("chapter_index", None)

                predecessor_contents = None
                chapter_context_str = None

                if task_type != "创意脑暴":
                    predecessor_contents = self._get_predecessor_contents(task_type, context)

                    if task_type in ["章节内容", "章节润色"] and chapter_index and isinstance(chapter_index, int):
                        previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=3)
                        outline_content = predecessor_contents.get("大纲", "") if predecessor_contents else ""
                        chapter_context_str = self._build_consistency_check_context(
                            chapter_index,
                            previous_chapters,
                            outline_content,
                            task_type,
                        )

                new_evaluation = await self.evaluator.evaluate(
                    task_type=task.task_type.value,
                    content=response.content,
                    context=context.to_dict(),
                    goal=goal,
                    predecessor_contents=predecessor_contents,
                    chapter_context=chapter_context_str,
                )

                # 🔥 获取新的评分
                new_quality_score = getattr(new_evaluation, "quality_score", new_evaluation.score)
                new_consistency_score = getattr(new_evaluation, "consistency_score", new_evaluation.score)

                if new_evaluation.passed:
                    logger.info(f"✅ 重写成功！尝试 #{attempt}，得分: {new_evaluation.score:.2f}")
                    self.stats.retried_tasks += 1
                    task.metadata["final_retry_count"] = attempt

                    # 🔥 发送重写成功事件
                    await self._send_step_progress(
                        step="rewrite_success",
                        message=f"✅ 重写成功！第 {attempt} 次重写通过评估",
                        task_id=task.task_id,
                        task_type=task.task_type.value,
                        rewrite_attempt=attempt,
                        quality_score=new_quality_score,
                        consistency_score=new_consistency_score
                    )

                    # 🔥 保存重写版本 - 仅对章节内容任务
                    if chapter_index is not None and self.session_storage and task.task_type.value in ["章节内容", "章节润色"]:
                        try:
                            rewrite_token_stats = {
                                "total_tokens": token_stats.get("total_tokens", 0),
                                "prompt_tokens": token_stats.get("prompt_tokens", 0),
                                "completion_tokens": token_stats.get("completion_tokens", 0),
                                "cost": token_stats.get("cost", 0.0),
                            }
                            await self.session_storage.create_chapter_version(
                                session_id=self.session_id,
                                task_id=task.task_id,
                                chapter_index=chapter_index,
                                content=response.content,
                                version_number=attempt + 1,
                                is_current=True,  # 通过评估，设为当前版本
                                evaluation=new_evaluation.to_dict(),
                                created_by="rewrite",
                                rewrite_reason=f"v{attempt} 得分 {evaluation.score:.2f}，重写后得分 {new_evaluation.score:.2f}",
                                token_stats=rewrite_token_stats,
                            )
                            # 更新版本计数
                            await self.session_storage.update_task_version_count(
                                task_id=task.task_id,
                                version_count=attempt + 1,
                            )
                            logger.info(f"💾 已保存重写版本 v{attempt + 1} (分数: {new_evaluation.score:.2f})")
                        except Exception as e:
                            logger.warning(f"⚠️ 保存重写版本失败: {e}")

                    # 🔥 更新 session 状态（重写完成）
                    if self.session_storage:
                        await self.session_storage.update_session_rewrite_state(
                            session_id=self.session_id,
                            is_rewriting=False,
                            rewrite_attempt=None,
                            rewrite_task_id=None,
                            rewrite_task_type=None,
                        )

                    return response.content, token_stats, new_evaluation, True

                # 🔥 保留最佳版本（即使不通过）
                if new_evaluation.score > best_score:
                    best_content = response.content
                    best_evaluation = new_evaluation
                    best_score = new_evaluation.score
                    logger.info(f"📈 更新最佳版本：得分 {best_score:.2f} (尝试 #{attempt})")

                # 🔥 保存每次重写版本 - 仅对章节内容任务
                if chapter_index is not None and self.session_storage and task.task_type.value in ["章节内容", "章节润色"]:
                    try:
                        rewrite_token_stats = {
                            "total_tokens": token_stats.get("total_tokens", 0),
                            "prompt_tokens": token_stats.get("prompt_tokens", 0),
                            "completion_tokens": token_stats.get("completion_tokens", 0),
                            "cost": token_stats.get("cost", 0.0),
                        }
                        version_id = await self.session_storage.create_chapter_version(
                            session_id=self.session_id,
                            task_id=task.task_id,
                            chapter_index=chapter_index,
                            content=response.content,
                            version_number=attempt + 1,
                            is_current=False,  # 先不标记为当前
                            evaluation=new_evaluation.to_dict(),
                            created_by="rewrite",
                            rewrite_reason=f"v{attempt} 得分 {evaluation.score:.2f}，重写后得分 {new_evaluation.score:.2f}",
                            token_stats=rewrite_token_stats,
                        )
                        # 如果这是更好的版本，标记为当前
                        if new_evaluation.score > best_score or (new_evaluation.score == best_score and attempt == 1):
                            await self.session_storage.restore_chapter_version(
                                session_id=self.session_id,
                                task_id=task.task_id,
                                version_id=version_id,
                            )
                        # 更新版本计数
                        await self.session_storage.update_task_version_count(
                            task_id=task.task_id,
                            version_count=attempt + 1,
                        )
                        logger.info(f"💾 已保存重写版本 v{attempt + 1} (分数: {new_evaluation.score:.2f})")
                    except Exception as e:
                        logger.warning(f"⚠️ 保存重写版本失败: {e}")

                # Update for next retry
                current_content = response.content
                current_evaluation = new_evaluation

                # 🔥 记录失败尝试次数
                task.failed_attempts += 1

                # 🔥 发送重写未通过事件
                await self._send_step_progress(
                    step="rewrite_failed",
                    message=f"⚠️ 第 {attempt} 次重写未通过 (质量: {new_quality_score*10:.1f}/10, 一致性: {new_consistency_score*10:.1f}/10)，继续重试...",
                    task_id=task.task_id,
                    task_type=task.task_type.value,
                    rewrite_attempt=attempt,
                    quality_score=new_quality_score,
                    consistency_score=new_consistency_score,
                    quality_issues=getattr(new_evaluation, "quality_issues", [])[:2],
                    consistency_issues=getattr(new_evaluation, "consistency_issues", [])[:2]
                )

                logger.warning(
                    f"⚠️ 尝试 #{attempt} 未通过评估，得分: {new_evaluation.score:.2f}，继续重试..."
                )

            except Exception as e:
                logger.error(f"❌ 重写尝试 #{attempt} 失败: {e}")
                task.failed_attempts += 1

                # 🔥 发送重写错误事件
                await self._send_step_progress(
                    step="rewrite_error",
                    message=f"❌ 第 {attempt} 次重写出错: {str(e)[:50]}，正在重试...",
                    task_id=task.task_id,
                    task_type=task.task_type.value,
                    rewrite_attempt=attempt,
                    error=str(e)
                )

                # 出错后等待一下再重试
                await asyncio.sleep(1)

        # 🔥 达到最大重试次数，返回最佳版本（不抛出异常）
        quality_score = getattr(best_evaluation, "quality_score", best_evaluation.score)
        consistency_score = getattr(best_evaluation, "consistency_score", best_evaluation.score)

        logger.warning(
            f"⚠️ 任务 {task.task_id} ({task.task_type.value}) "
            f"在 {max_retries} 次重写后仍未通过评估\n"
            f"保留最佳版本: 质量 {quality_score*10:.1f}/10, 一致性 {consistency_score*10:.1f}/10"
        )
        logger.warning(f"主要原因: {best_evaluation.reasons[:3] if best_evaluation.reasons else '未知'}")

        # 🔥 标记质量未通过
        task.metadata["quality_failed"] = True
        task.metadata["quality_score"] = best_evaluation.score
        task.metadata["quality_issues"] = best_evaluation.reasons[:3] if best_evaluation.reasons else []

        # 🔥 发送重写结束事件（保留最佳版本）
        await self._send_step_progress(
            step="rewrite_completed_with_issues",
            message=f"⚠️ {task.task_type.value} 重写 {max_retries} 次后仍未通过，保留最佳版本",
            task_id=task.task_id,
            task_type=task.task_type.value,
            quality_score=quality_score,
            consistency_score=consistency_score,
            best_attempt=attempt,
            issues=best_evaluation.reasons[:3] if best_evaluation.reasons else []
        )

        # 🔥 更新 session 状态（重写完成）
        if self.session_storage:
            await self.session_storage.update_session_rewrite_state(
                session_id=self.session_id,
                is_rewriting=False,
                rewrite_attempt=None,
                rewrite_task_id=None,
                rewrite_task_type=None,
            )

        # 🔥 返回最佳版本，标记为未通过
        return best_content, token_stats, best_evaluation, False

    def _build_rewrite_prompt(
        self,
        task: Task,
        original_content: str,
        evaluation: EvaluationResult,
        context: MemoryContext,
        goal: Dict[str, Any],
        attempt: int = 1,
        consistency_result: Dict[str, Any] = None,  # 🔥 新增参数
    ) -> str:
        """Build prompt for content rewriting with retry information and consistency feedback"""

        task_type = task.task_type.value
        chapter_index = task.metadata.get("chapter_index", None)

        # 🔥 新增：获取分别的质量评分和一致性评分
        quality_score = getattr(evaluation, "quality_score", evaluation.score)
        consistency_score = getattr(evaluation, "consistency_score", evaluation.score)
        quality_issues = getattr(evaluation, "quality_issues", [])
        consistency_issues = getattr(evaluation, "consistency_issues", [])

        # 根据重试次数调整提示强度
        urgency = ""
        if attempt >= 3:
            urgency = f"""
⚠️ **警告**：这是第 {attempt} 次重写尝试！
请认真阅读评估反馈，针对性地修改问题。不要只是小修小补，要从根本上解决问题。
"""
        if attempt >= 5:
            urgency = f"""
🚨 **紧急**：这是第 {attempt} 次重写尝试！
之前的修改显然没有解决核心问题。请：
1. 仔细阅读每一条反馈
2. 思考为什么之前的修改没有效果
3. 尝试完全不同的写作方式
"""

        # 🔥 构建一致性问题部分（如果有一致性检查失败）
        consistency_section = ""
        if consistency_result and not consistency_result.get("passed", True):
            issues = consistency_result.get("issues", [])
            suggestions = consistency_result.get("suggestions", [])
            continuity_issues = consistency_result.get("continuity_issues", [])
            score = consistency_result.get("score", 0)

            consistency_section = f"""
## 🚨 一致性检查失败（必须修复！）

一致性评分：{score:.2f}/1.00

"""
            if issues:
                consistency_section += f"""### ❌ 发现的一致性问题
{chr(10).join(f'- {issue}' for issue in issues)}

"""

            if continuity_issues:
                consistency_section += f"""### ❌ 章节连贯性问题（非常重要！）
{chr(10).join(f'- {issue}' for issue in continuity_issues)}

**重要**：这些连贯性问题说明当前章节像独立短篇，与前面章节脱节！
必须确保：
1. 开头自然衔接上一章结尾
2. 人物状态延续（位置、情绪、正在做的事）
3. 时间线连贯
4. 情节有承接关系

"""

            if suggestions:
                consistency_section += f"""### 💡 修改建议
{chr(10).join(f'- {s}' for s in suggestions)}

"""

        # 🔥 新增：构建质量问题部分
        quality_section = ""
        if quality_issues and quality_score < 0.7:
            quality_section = f"""
## 📝 文学质量问题（必须改进！）

文学质量评分：{quality_score * 10:.1f}/10 (需要 >= 7.0)

### ❌ 发现的质量问题：
{chr(10).join(f'- {issue}' for issue in quality_issues[:5])}

"""

        # 🔥 新增：构建一致性问题部分（从评估结果中）
        eval_consistency_section = ""
        if consistency_issues and consistency_score < 0.7:
            eval_consistency_section = f"""
## 🔍 逻辑一致性问题（必须修复！）

逻辑一致性评分：{consistency_score * 10:.1f}/10 (需要 >= 7.0)

### ❌ 发现的一致性问题：
{chr(10).join(f'- {issue}' for issue in consistency_issues[:5])}

"""

        prompt = f"""## 重写任务（第 {attempt} 次尝试）

任务类型: {task_type}
{f"章节: 第{chapter_index}章" if chapter_index else ""}
描述: {task.description}
{urgency}

{consistency_section}

{quality_section}

{eval_consistency_section}

## 📊 评估结果详情

### 评分情况
- 📈 文学质量评分：{quality_score * 10:.1f}/10 {'✅ 通过' if quality_score >= 0.7 else '❌ 未通过 (需要 >= 7.0)'}
- 🔍 逻辑一致性评分：{consistency_score * 10:.1f}/10 {'✅ 通过' if consistency_score >= 0.7 else '❌ 未通过 (需要 >= 7.0)'}

### 综合评估
{chr(10).join(f'💡 {r}' for r in evaluation.reasons[:3])}

### 改进建议
{chr(10).join(f'- {s}' for s in evaluation.suggestions[:5])}

## 原始内容
```
{original_content[:3000]}
{"..." if len(original_content) > 3000 else ""}
```

## 🎯 重写要求

### 📌 通过标准（必须同时满足）
1. ✅ 文学质量评分 >= 7.0/10
2. ✅ 逻辑一致性评分 >= 7.0/10

### 📝 修改重点
请根据评估反馈改进内容：
- **质量问题**：{'请改进文学质量，包括故事性、人物塑造、文笔、可读性、完整性、创意性等' if quality_score < 0.7 else '文学质量已达标'}
- **一致性问题**：{'请修复逻辑一致性问题，包括人物一致性、世界观一致性、情节一致性等' if consistency_score < 0.7 else '逻辑一致性已达标'}

{"特别注意：确保本章开头与前一章结尾自然衔接，不要像另一个独立故事！" if chapter_index and chapter_index > 1 else ""}

## 输出要求
请直接输出改进后的完整内容，不需要解释或说明。
"""

        return prompt

    def _calculate_cost(self, provider: str, model: str, usage) -> float:
        """
        计算 API 调用的费用（美元）
        
        基于不同提供商和模型的定价计算。
        
        Args:
            provider: LLM 提供商（deepseek, aliyun, ark 等）
            model: 模型名称
            usage: token 使用统计对象
            
        Returns:
            费用（美元）
        """
        # 定价表（每百万 token 的价格，美元）
        # 注意：这些价格可能会变化，需要定期更新
        pricing = {
            # DeepSeek 定价（很便宜）
            "deepseek": {
                "deepseek-chat": {"input": 0.14, "output": 0.28},
                "deepseek-reasoner": {"input": 0.55, "output": 2.19},
                "default": {"input": 0.14, "output": 0.28},
            },
            # 阿里云通义千问定价（人民币转美元，汇率约 7.2）
            "aliyun": {
                "qwen-long": {"input": 0.07, "output": 0.28},  # 0.5/3.5M tokens CNY
                "qwen-max": {"input": 2.78, "output": 8.33},  # 20/60 CNY per M
                "qwen-plus": {"input": 0.56, "output": 1.39},  # 4/10 CNY per M
                "qwen-turbo": {"input": 0.14, "output": 0.28},
                "default": {"input": 0.07, "output": 0.28},
            },
            # 火山引擎 Ark (豆包) 定价
            "ark": {
                "doubao-pro": {"input": 0.11, "output": 0.28},  # 0.8/2 CNY per M
                "doubao-lite": {"input": 0.04, "output": 0.14},
                "default": {"input": 0.11, "output": 0.28},
            },
            # 默认定价（保守估计）
            "default": {"input": 0.50, "output": 1.00},
        }
        
        # 获取提供商定价
        provider_pricing = pricing.get(provider, pricing["default"])
        
        # 获取模型定价
        if isinstance(provider_pricing, dict) and "input" in provider_pricing:
            model_pricing = provider_pricing
        else:
            # 尝试匹配模型名称
            model_pricing = None
            for key in provider_pricing:
                if key != "default" and key in model.lower():
                    model_pricing = provider_pricing[key]
                    break
            if not model_pricing:
                model_pricing = provider_pricing.get("default", pricing["default"])
        
        # 计算费用
        input_cost = (usage.prompt_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (usage.completion_tokens / 1_000_000) * model_pricing["output"]
        
        return input_cost + output_cost

    def _get_temperature_for_task(self, task_type: NovelTaskType) -> float:
        """Get appropriate temperature for a task type"""
        # Creative tasks need higher temperature
        high_temp_tasks = {
            NovelTaskType.CHAPTER_CONTENT,  # 逐章生成
            # NovelTaskType.CHAPTER_POLISH,  # ⚠️ 已移除
            NovelTaskType.REVISION,
        }

        # Structured tasks need lower temperature
        low_temp_tasks = {
            NovelTaskType.OUTLINE,
            NovelTaskType.CHARACTER_DESIGN,
            NovelTaskType.WORLDVIEW_RULES,
        }

        if task_type in high_temp_tasks:
            return 0.8
        elif task_type in low_temp_tasks:
            return 0.5
        else:
            return 0.7

    def _get_max_tokens_for_task(self, task_type: NovelTaskType) -> int:
        """Get appropriate max tokens for a task type"""
        # 逐章生成需要较多 tokens
        if task_type == NovelTaskType.CHAPTER_CONTENT:
            return 8000  # 约 6000 字中文（单章内容）

        # 大纲需要较多 tokens
        elif task_type == NovelTaskType.OUTLINE:
            return 16000  # 约 12000 字中文，确保能输出所有章节

        # 章节润色需要较多 tokens
        # elif task_type == NovelTaskType.CHAPTER_POLISH:  # ⚠️ 已移除
        #     return 8000  # 约 6000 字中文

        # 规划类任务需要足够空间
        elif task_type in {NovelTaskType.CHARACTER_DESIGN, NovelTaskType.WORLDVIEW_RULES,
                           NovelTaskType.CREATIVE_BRAINSTORM}:
            return 8000  # 约 6000 字中文

        # 其他任务
        else:
            return 4000  # 约 3000 字中文
    
    async def _check_and_save_high_score_example(
        self, 
        task_type: str, 
        genre: str, 
        content: str, 
        score: float,
        evaluation: Any
    ) -> bool:
        """
        🎯 检查内容是否为高分，如果是则保存为示例供后续任务参考
        
        Args:
            task_type: 任务类型
            genre: 小说类型（仙侠、科幻、言情等）
            content: 生成的内容
            score: 评分（0-1）
            evaluation: 评估结果对象
            
        Returns:
            bool: 是否保存为高分示例
        """
        score_100 = int(score * 100)
        
        # 只有超过阈值的内容才考虑保存
        if score_100 < self.high_score_threshold:
            return False
        
        # 初始化存储结构
        if task_type not in self.best_examples:
            self.best_examples[task_type] = {}
        
        # 检查该类型+题材是否已有更高分的示例
        current_best = self.best_examples[task_type].get(genre)
        
        if current_best is None or score_100 > current_best.get("score", 0):
            # 截取内容摘要（不超过2000字）
            content_summary = content[:2000] + "..." if len(content) > 2000 else content
            
            # 提取评估中的优点（如果有的话）
            strengths = []
            if hasattr(evaluation, 'dimension_scores') and evaluation.dimension_scores:
                for dim, data in evaluation.dimension_scores.items():
                    if isinstance(data, dict) and data.get('score', 0) >= 80:
                        strengths.append(f"{dim}: {data.get('reason', '表现优秀')}")
            
            # 保存为最佳示例
            self.best_examples[task_type][genre] = {
                "score": score_100,
                "content": content_summary,
                "strengths": strengths,
                "saved_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"🏆 记录高分示例: {task_type}/{genre} 得分 {score_100}/100")
            return True
        
        return False
    
    def _get_best_example_for_task(self, task_type: str, genre: str) -> Optional[str]:
        """
        🎯 获取该任务类型和题材的最佳示例（用于提示词参考）
        
        Returns:
            Optional[str]: 格式化的示例文本，如果没有则返回 None
        """
        if task_type not in self.best_examples:
            return None
        
        # 优先获取同题材的示例
        example = self.best_examples[task_type].get(genre)
        
        # 如果没有同题材的，尝试获取通用的
        if not example and genre != "通用":
            example = self.best_examples[task_type].get("通用")
        
        if not example:
            return None
        
        strengths_text = ""
        if example.get("strengths"):
            strengths_text = "\n**优点**:\n" + "\n".join(f"- {s}" for s in example["strengths"])
        
        return f"""
---
📌 **高分参考示例**（评分: {example['score']}/100）
{strengths_text}

**内容摘要**:
{example['content']}
---
"""

    def _get_memory_type_for_task(self, task_type: NovelTaskType) -> MemoryType:
        """Map task type to memory type for storage

        所有核心任务都需要被正确分类存储到向量数据库，
        方便后续章节创作时能够检索到相关内容。
        """
        mapping = {
            # 核心创意阶段 - 使用 GENERAL（最重要，会被频繁检索）
            NovelTaskType.CREATIVE_BRAINSTORM: MemoryType.GENERAL,

            # 元素创建阶段
            NovelTaskType.CHARACTER_DESIGN: MemoryType.CHARACTER,
            NovelTaskType.WORLDVIEW_RULES: MemoryType.WORLDVIEW,

            # 大纲阶段（包含事件、伏笔）
            NovelTaskType.OUTLINE: MemoryType.OUTLINE,

            # 章节生成阶段
            NovelTaskType.CHAPTER_CONTENT: MemoryType.CHAPTER,
            # NovelTaskType.CHAPTER_POLISH: MemoryType.CHAPTER,  # ⚠️ 已移除
        }

        return mapping.get(task_type, MemoryType.GENERAL)

    def _collect_outputs(self) -> Dict[str, str]:
        """Collect all task outputs"""
        outputs = {}

        # Get completed tasks from planner
        for task in self.planner.get_tasks_by_status("completed"):
            if task.result:
                key = f"{task.task_type.value}"
                if task.metadata.get("chapter_index"):
                    key += f"_ch{task.metadata['chapter_index']}"
                outputs[key] = task.result

        return outputs

    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Safely execute a callback"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    async def _send_step_progress(
        self,
        step: str,
        message: str,
        task_id: str = None,
        task_type: str = None,
        **extra_data
    ) -> None:
        """🔥 发送步骤级进度更新

        Args:
            step: 步骤名称 (context_retrieval, llm_call, evaluation, rewrite, etc.)
            message: 进度消息
            task_id: 当前任务ID
            task_type: 当前任务类型
            **extra_data: 额外数据 (llm_provider, model, score, retry_count, etc.)
        """
        if self._on_step_progress:
            await self._safe_callback(
                self._on_step_progress,
                {
                    "step": step,
                    "message": message,
                    "task_id": task_id,
                    "task_type": task_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    **extra_data
                }
            )

    # Control methods

    async def pause_and_save(self) -> bool:
        """
        Pause execution and save state for resume capability

        Saves:
        - Completed task IDs
        - Current task
        - Execution statistics
        - Memory context state

        Returns:
            True if state saved successfully
        """
        self.is_paused = True
        self.status = ExecutionStatus.PAUSED

        # Save engine state to database
        try:
            # Collect state to save
            engine_state = {
                "completed_task_ids": list(self.completed_task_ids) if self.completed_task_ids else [],
                "current_task": self.current_task.to_dict() if self.current_task else None,
                "stats": self.stats.to_dict() if self.stats else {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Save to database
            success = await self.session_storage.save_engine_state(
                session_id=self.session_id,
                engine_state=engine_state,
                current_task_index=None,  # Will be calculated by planner
            )

            if success:
                # Update session status
                from creative_autogpt.storage.session import SessionStatus
                await self.session_storage.update_session_status(
                    self.session_id,
                    SessionStatus.PAUSED
                )
                logger.info(f"✅ Saved state for session {self.session_id} - {len(self.completed_task_ids)} tasks completed")
            else:
                logger.warning(f"⚠️ Failed to save state for session {self.session_id}")

            return success

        except Exception as e:
            logger.error(f"Error saving state during pause: {e}")
            return False

    def pause(self) -> None:
        """Pause execution (use pause_and_save() for persistence)"""
        self.is_paused = True
        self.status = ExecutionStatus.PAUSED
        logger.info(f"Paused execution for session {self.session_id}")

    def resume(self) -> None:
        """Resume execution (use resume_from_checkpoint() to load saved state)"""
        self.is_paused = False
        self.status = ExecutionStatus.RUNNING
        logger.info(f"Resumed execution for session {self.session_id}")

    async def resume_from_checkpoint(self) -> bool:
        """
        Load saved state and resume execution

        Returns:
            True if state loaded successfully
        """
        try:
            # Load state from database
            state_data = await self.session_storage.load_engine_state(self.session_id)

            if not state_data or not state_data.get("is_resumable"):
                logger.warning(f"⚠️ No saved state found for session {self.session_id}")
                return False

            engine_state = state_data["engine_state"]

            # Restore state
            self.completed_task_ids = set(engine_state.get("completed_task_ids", []))

            # Restore statistics
            if engine_state.get("stats"):
                stats_dict = engine_state["stats"]
                self.stats.total_tasks = stats_dict.get("total_tasks", 0)
                self.stats.completed_tasks = stats_dict.get("completed_tasks", 0)
                self.stats.failed_tasks = stats_dict.get("failed_tasks", 0)
                self.stats.skipped_tasks = stats_dict.get("skipped_tasks", 0)
                self.stats.retried_tasks = stats_dict.get("retried_tasks", 0)
                self.stats.llm_calls = stats_dict.get("llm_calls", 0)
                self.stats.total_tokens = stats_dict.get("total_tokens", 0)
                self.stats.total_cost_usd = stats_dict.get("total_cost_usd", 0.0)

            # Update session status
            from creative_autogpt.storage.session import SessionStatus
            await self.session_storage.update_session_status(
                self.session_id,
                SessionStatus.RUNNING
            )

            self.is_paused = False
            self.status = ExecutionStatus.RUNNING
            self.is_running = True

            logger.info(f"✅ Restored state for session {self.session_id} - {len(self.completed_task_ids)} tasks completed")

            return True

        except Exception as e:
            logger.error(f"Error loading state during resume: {e}")
            return False

    def stop(self) -> None:
        """Stop execution"""
        self.is_running = False
        self.status = ExecutionStatus.STOPPED
        logger.info(f"Stopped execution for session {self.session_id}")

    async def skip_task(self, task_id: str) -> bool:
        """
        Skip a task (mark as skipped and continue to next task)

        This is used when user wants to skip a failed chapter and continue.

        Args:
            task_id: Task ID to skip

        Returns:
            True if successfully skipped
        """
        try:
            # Get the task from planner
            task = self.planner.get_task(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return False

            # Mark as skipped
            task.status = "skipped"
            task.error = "Skipped by user"
            self.planner.update_task_status(task_id, "skipped")
            self.stats.skipped_tasks += 1

            # Add to completed tasks so it won't be executed again
            if task_id not in self.completed_task_ids:
                self.completed_task_ids.add(task_id)

            # Save the updated task status
            await self.planner.save_progress(self.session_id, self.session_storage)

            logger.info(f"✅ Task {task_id} skipped by user")
            return True

        except Exception as e:
            logger.error(f"Failed to skip task {task_id}: {e}")
            return False

    def approve_task(self, action: str = 'approve', feedback: Optional[str] = None, selected_idea: Optional[int] = None) -> None:
        """
        Approve or reject the current task result
        
        Args:
            action: 'approve', 'reject', or 'regenerate'
            feedback: Optional feedback for regeneration
            selected_idea: For brainstorm tasks, the number of the selected idea (1-4)
        """
        if not self.is_waiting_approval:
            logger.warning("No task is waiting for approval")
            return
        
        self.approval_result = {
            'action': action,
            'feedback': feedback,
            'selected_idea': selected_idea
        }
        self._approval_event.set()
        logger.info(f"Task approval: {action}" + (f", selected idea: {selected_idea}" if selected_idea else ""))

    def get_status(self) -> ExecutionStatus:
        """Get current execution status"""
        return self.status

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress"""
        return self.planner.get_progress()

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.stats.to_dict()
    
    @staticmethod
    def get_genre_specific_guide(genre: str) -> str:
        """
        🎯 获取针对特定小说类型的创作指南
        
        不同类型的小说有不同的创作要点和禁忌，
        这个方法返回类型特定的提示词，帮助AI写出符合类型特点的内容。
        
        Args:
            genre: 小说类型
            
        Returns:
            str: 类型特定的创作指南
        """
        genre_guides = {
            "科幻": """
🔬 **科幻小说创作要点**

**类型特色**：
- 以科学或技术设定为核心驱动故事
- 探讨科技对人类/社会的影响
- 创造令人惊叹的未来/平行世界

**必须做到**：
- 科学设定要自洽（不需要完全准确，但要能自圆其说）
- 用故事讲科学，而非科普式解释
- 技术细节融入情节，不要单独讲解
- 人物情感和科技设定同样重要

**经典参考**：《三体》《流浪地球》《银河帝国》《沙丘》

**常见问题**：
- ❌ 大段技术原理解释
- ❌ 过于追求"硬核"而牺牲可读性
- ❌ 人物只是展示科技的工具
- ✅ 用角色的眼睛展示世界
""",
            "仙侠": """
⚔️ **仙侠小说创作要点**

**类型特色**：
- 修仙求道的主线
- 江湖恩怨、门派争斗
- 天道规则、境界突破

**必须做到**：
- 修炼体系设定清晰（炼气→筑基→金丹...）
- 突出快意恩仇的江湖气
- 人物要有"道心"和追求
- 打斗描写要有画面感

**经典参考**：《凡人修仙传》《遮天》《仙逆》《诛仙》

**常见问题**：
- ❌ 境界划分混乱
- ❌ 主角金手指过于离谱
- ❌ 配角智商下线
- ✅ 注重修炼过程的合理性
""",
            "玄幻": """
✨ **玄幻小说创作要点**

**类型特色**：
- 自由度高，设定可以天马行空
- 强调"爽感"和主角成长
- 异世界冒险、升级打怪

**必须做到**：
- 力量体系设定明确
- 主角的"金手指"要有代价或限制
- 升级节奏要有松有紧
- 要有让读者期待的长期目标

**经典参考**：《斗破苍穹》《斗罗大陆》《完美世界》《武动乾坤》

**常见问题**：
- ❌ 主角无脑碾压没有挑战
- ❌ 配角全是衬托主角的工具人
- ❌ 升级太快缺乏积累感
- ✅ 每个强敌都让读者印象深刻
""",
            "言情": """
💕 **言情小说创作要点**

**类型特色**：
- 以感情线为核心
- 男女主的情感发展是主线
- 强调情感的细腻表达

**必须做到**：
- 男女主人设要立体、有魅力
- 感情发展要有层次，不能太突兀
- 注重细节描写和氛围营造
- 误会/阻碍要合理，不能太刻意

**经典参考**：《何以笙箫默》《微微一笑很倾城》《你好，旧时光》

**常见问题**：
- ❌ 为虐而虐，误会太牵强
- ❌ 男/女主人设崩塌
- ❌ 配角刻意制造矛盾
- ✅ 甜与虐的节奏要平衡
""",
            "悬疑": """
🔍 **悬疑小说创作要点**

**类型特色**：
- 以解谜、查案为核心
- 设置悬念吸引读者
- 层层剥茧、逻辑推理

**必须做到**：
- 线索要公平，不能藏着关键信息
- 推理逻辑要严密
- 节奏要紧凑，保持紧张感
- 反转要在情理之中

**经典参考**：《白夜行》《嫌疑人X的献身》《福尔摩斯》《坏小孩》

**常见问题**：
- ❌ 关键线索没给读者就揭晓答案
- ❌ 推理过程有明显漏洞
- ❌ 为反转而反转，不合逻辑
- ✅ 让读者可以一起推理
""",
            "都市": """
🏙️ **都市小说创作要点**

**类型特色**：
- 现代都市为背景
- 贴近现实生活
- 职场、商战、人际关系

**必须做到**：
- 设定要贴合现实（除非是都市异能类）
- 人物职业、生活要真实可信
- 对话要有现代感
- 情节要接地气

**经典参考**：《遥远的救世主》《余罪》《杜拉拉升职记》

**常见问题**：
- ❌ 主角开局就是顶级大佬
- ❌ 对职业/行业描写不专业
- ❌ 人物言行脱离现实
- ✅ 让读者有代入感
""",
            "武侠": """
🗡️ **武侠小说创作要点**

**类型特色**：
- 江湖侠客、快意恩仇
- 武功招式、武林门派
- 侠之大者，为国为民

**必须做到**：
- 武功招式描写要有画面感
- 江湖规矩、门派设定要合理
- 人物要有侠义精神
- 情节要有武侠的氛围感

**经典参考**：金庸系列、古龙系列、《雪中悍刀行》

**常见问题**：
- ❌ 武功越写越离谱
- ❌ 侠义精神空洞
- ❌ 江湖味不够
- ✅ 注重"侠"的内涵
""",
            "历史": """
📜 **历史小说创作要点**

**类型特色**：
- 以历史事件/人物为背景
- 还原历史氛围
- 可以是架空但要有历史感

**必须做到**：
- 重大历史事件要有据可查
- 人物言行要符合时代
- 器物、服饰、习俗要考究
- 即使架空也要有历史质感

**经典参考**：《明朝那些事儿》《大明王朝1566》《庆余年》

**常见问题**：
- ❌ 明显的历史错误
- ❌ 人物思维太现代
- ❌ 细节穿帮
- ✅ 让读者感受到时代氛围
""",
        }
        
        # 获取类型指南，如果没有特定类型则返回通用指南
        guide = genre_guides.get(genre, f"""
📚 **{genre}小说创作要点**

**通用原则**：
- 遵循{genre}类型的惯例和读者期待
- 人物塑造要立体真实
- 情节发展要有逻辑
- 保持类型的核心吸引力

请发挥你对{genre}类型的理解，创作符合类型特色的内容。
""")
        
        return guide
