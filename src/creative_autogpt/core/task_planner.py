"""
Task Planner - Plans and schedules creative writing tasks

Defines task types, dependencies, and execution order for novel creation.
Implements the DAG-based task scheduling from the architecture.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class NovelTaskType(str, Enum):
    """Task types for novel creation"""

    # Phase 0: Creative Brainstorm (创意脑暴阶段)
    CREATIVE_BRAINSTORM = "创意脑暴"  # 产生多个故事点子

    # Phase 1: Enhanced Outline (加强版大纲 - 包含所有细节)
    OUTLINE = "大纲"  # 完整大纲，包含事件、伏笔、章节规划

    # Phase 2: Elements (元素设计 - 基于大纲)
    CHARACTER_DESIGN = "人物设计"
    WORLDVIEW_RULES = "世界观规则"

    # Phase 3: Sequential Chapter Generation (逐章生成 - 确保连贯性)
    CHAPTER_CONTENT = "章节内容"  # 逐章生成，每章依赖前一章，确保连贯性（直接生成高质量内容，无需润色）
    # BATCH_CHAPTER_GENERATION = "批量章节生成"  # ⚠️ 已禁用：批量生成无法保证章节间连贯性
    # CHAPTER_POLISH = "章节润色"  # ⚠️ 已移除：使用 Qwen Long 直接生成高质量内容，无需单独润色步骤

    # Evaluation phase
    EVALUATION = "评估"

    # Revision phase
    REVISION = "修订"


@dataclass
class TaskDefinition:
    """Definition of a task in the novel creation pipeline"""

    task_type: NovelTaskType
    description: str
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    optional: bool = False
    can_parallel: bool = False
    is_foundation: bool = False  # 🔥 新增：是否是基础任务（章节创作必须参考）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type.value,
            "description": self.description,
            "depends_on": self.depends_on,
            "metadata": self.metadata,
            "optional": self.optional,
            "can_parallel": self.can_parallel,
            "is_foundation": self.is_foundation,
        }


@dataclass
class Task:
    """An instance of a task ready for execution"""

    task_id: str
    task_type: NovelTaskType
    description: str
    status: str = "pending"  # pending, ready, running, completed, failed, skipped
    depends_on: List[str] = field(default_factory=list)
    dependencies_met: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    optional: bool = False
    can_parallel: bool = False
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # 🔥 新增：任务统计字段
    started_at: Optional[str] = None  # ISO 格式时间字符串
    completed_at: Optional[str] = None  # ISO 格式时间字符串
    execution_time_seconds: float = 0.0  # 执行时间（秒）
    total_tokens: int = 0  # 总 token 数
    prompt_tokens: int = 0  # 提示词 token 数
    completion_tokens: int = 0  # 生成的 token 数
    cost_usd: float = 0.0  # 费用（美元）
    failed_attempts: int = 0  # 🔥 失败尝试次数
    is_foundation: bool = False  # 🔥 是否是基础任务（章节创作必须参考）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "description": self.description,
            "status": self.status,
            "depends_on": self.depends_on,
            "dependencies_met": self.dependencies_met,
            "metadata": self.metadata,
            "optional": self.optional,
            "can_parallel": self.can_parallel,
            "is_foundation": self.is_foundation,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            # 🔥 新增统计字段
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time_seconds": self.execution_time_seconds,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
            "failed_attempts": self.failed_attempts,
        }


class TaskPlanner:
    """
    Plans and schedules tasks for novel creation

    🎯 顶级作家创作流程（布兰登·桑德森式 - 微调版）：

    ════════════════════════════════════════════════════════════════
    📋 任务分类说明
    ════════════════════════════════════════════════════════════════

    【基础任务】- is_foundation=True - 章节创作必须参考，存入向量库
    ├── 创意脑暴：产生多个故事点子
    ├── 大纲：故事骨架，章节规划
    ├── 世界观规则：世界运作的限制
    └── 人物设计：角色设定

    【风格任务】- 影响写作方式
    ├── 主题确认（可选）
    ├── 风格元素
    └── 市场定位

    【细节任务】- 丰富故事，也存入向量库
    ├── 事件：具体发生什么
    ├── 场景物品冲突：在哪里发生，用什么
    └── 伏笔列表：埋线和回收

    ════════════════════════════════════════════════════════════════
    📈 执行流程
    ════════════════════════════════════════════════════════════════

    Phase 0: 创意脑暴 🟡细节
    Phase 1: 大纲（骨架版）🔴基础
    Phase 2: 世界观规则 🔴基础
    Phase 3: 人物设计 🔴基础
    Phase 4: 主题确认 → 风格元素 → 市场定位
    Phase 5: 事件 → 场景物品冲突 → 伏笔列表 🟡细节
    Phase 6: 章节创作（使用 Qwen Long 直接生成高质量内容，无需润色步骤）

    章节创作时会从向量库检索：大纲、世界观、人物、事件、伏笔
    确保不会跑偏！
    """

    # Default task definitions for novel creation
    DEFAULT_TASK_DEFINITIONS: List[TaskDefinition] = [
        # ============ Phase 0: 创意脑暴 ============
        TaskDefinition(
            task_type=NovelTaskType.CREATIVE_BRAINSTORM,
            description="像顶级作家一样进行创意脑暴，产生3-5个有吸引力的故事点子，每个点子包含：核心冲突、独特卖点、情感钩子",
            depends_on=[],
            is_foundation=False,
        ),

        # ============ Phase 1: 完整大纲（包含所有细节）============
        TaskDefinition(
            task_type=NovelTaskType.OUTLINE,
            description="""基于创意脑暴的结果，选择最佳点子并设计完整的小说大纲，包含：
1. 故事核心：一句话概括（主角是谁+想要什么+面临什么阻碍+为什么读者会在意）
2. 故事结构：开端→发展→高潮→结局
3. 事件链：所有关键事件的时间线
4. 伏笔系统：埋设位置、暗示内容、回收时机
5. 章节规划：每章的核心内容和目标字数
6. 人物关系：主要人物的关系网络
7. 世界观要点：影响故事的关键设定""",
            depends_on=["创意脑暴"],
            is_foundation=True,  # 🔴 基础任务！所有创作的蓝图
        ),

        # ============ Phase 2: 元素设计（基于大纲）============
        TaskDefinition(
            task_type=NovelTaskType.WORLDVIEW_RULES,
            description="根据大纲需要，构建让故事能够发生的世界。定义世界运作的核心规则、限制和可能性",
            depends_on=["大纲"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.CHARACTER_DESIGN,
            description="根据大纲和世界观规则，设计能够推动故事发展的人物。主角的目标、缺陷、成长弧线都要服务于大纲",
            depends_on=["大纲", "世界观规则"],
            is_foundation=True,
        ),

        # ============ Phase 3: 章节内容生成（逐章生成，确保连贯性）============
        # ⚠️ 不再使用批量生成，改用逐章生成模式
        # 章节内容任务将在 _create_chapter_tasks 中动态创建，每章依赖前一章

        # ============ Phase 4: 分章节润色 ============
        # 章节润色任务将在 _create_chapter_tasks 中动态创建
    ]

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        plugin_manager: Optional[Any] = None,
    ):
        """
        Initialize task planner

        Args:
            config: Optional configuration
            plugin_manager: Optional plugin manager for loading plugin tasks
        """
        self.config = config or {}
        self.task_definitions: Dict[str, TaskDefinition] = {}
        self.tasks: Dict[str, Task] = {}
        self.plugin_manager = plugin_manager

        # Register default task definitions
        for definition in self.DEFAULT_TASK_DEFINITIONS:
            self.register_task_definition(definition)

        logger.info(f"TaskPlanner initialized with {len(self.task_definitions)} definitions")

    def register_task_definition(self, definition: TaskDefinition) -> None:
        """
        Register a task definition

        Args:
            definition: The task definition to register
        """
        self.task_definitions[definition.task_type.value] = definition
        logger.debug(f"Registered task definition: {definition.task_type.value}")

    def _load_plugin_tasks(self) -> List[TaskDefinition]:
        """
        Load task definitions from plugins

        Returns:
            List of task definitions from plugins
        """
        if not self.plugin_manager:
            return []

        plugin_tasks = []
        try:
            # Get all task definitions from plugins
            all_plugin_tasks = self.plugin_manager.get_tasks()

            for task_dict in all_plugin_tasks:
                task_type_str = task_dict.get("task_type")
                if not task_type_str:
                    continue

                # Try to match with existing NovelTaskType enum
                task_type = None
                for enum_value in NovelTaskType:
                    if enum_value.value == task_type_str:
                        task_type = enum_value
                        break

                # If not found in enum, skip this task (we only support defined task types)
                if task_type is None:
                    logger.debug(f"Skipping plugin task '{task_type_str}' - not in NovelTaskType enum")
                    continue

                # Mark as plugin task in metadata
                metadata = task_dict.get("metadata", {})
                metadata["plugin"] = task_dict.get("plugin", "unknown")
                metadata["plugin_source"] = True

                definition = TaskDefinition(
                    task_type=task_type,
                    description=task_dict.get("description", ""),
                    depends_on=task_dict.get("depends_on", []),
                    metadata=metadata,
                    optional=task_dict.get("optional", False),
                    can_parallel=task_dict.get("can_parallel", False),
                    is_foundation=task_dict.get("is_foundation", False),
                )
                plugin_tasks.append(definition)
                logger.debug(f"Loaded plugin task: {task_type_str} from {metadata['plugin']}")

            logger.info(f"Loaded {len(plugin_tasks)} task definitions from plugins")

        except Exception as e:
            logger.error(f"Failed to load plugin tasks: {e}")

        return plugin_tasks

    async def plan(
        self,
        goal: Dict[str, Any],
        chapter_count: Optional[int] = None,
    ) -> List[Task]:
        """
        Generate a task plan based on the creation goal

        Args:
            goal: Creation goal with style, theme, length, etc.
            chapter_count: Number of chapters to create (启用逐章生成模式)

        Returns:
            List of tasks ready for execution
        """
        logger.info(f"Planning tasks for goal: {goal.get('title', 'Untitled')}")

        # Clear previous tasks
        self.tasks = {}

        # 创建基础任务（创意脑暴 → 故事核心 → 大纲 → 世界观规则 → 人物设计）
        for definition in self.DEFAULT_TASK_DEFINITIONS:
            task = self._create_task_from_definition(definition, goal)
            self.tasks[task.task_id] = task

        # 🔥 加载插件任务（插件任务覆盖同类型的硬编码任务）
        plugin_tasks = self._load_plugin_tasks()
        for plugin_def in plugin_tasks:
            # 插件任务覆盖策略：相同 task_type 时，插件版本优先
            task_type_str = plugin_def.task_type.value
            if task_type_str in self.task_definitions:
                logger.info(f"🔥 插件任务覆盖硬编码: {task_type_str} from {plugin_def.metadata.get('plugin')}")

            # 注册插件任务定义（覆盖硬编码版本）
            self.register_task_definition(plugin_def)

            # 创建任务实例
            task = self._create_task_from_definition(plugin_def, goal)
            self.tasks[task.task_id] = task
            logger.debug(f"Created plugin task: {task_type_str}")

        # Create chapter tasks if chapter count specified (逐章生成模式)
        if chapter_count:
            logger.info(f"🔥 逐章生成模式已启用：{chapter_count}章，每章依赖前一章确保连贯性")
            await self._create_chapter_tasks(chapter_count, goal)
        else:
            logger.warning("⚠️ 未指定章节数量，将跳过章节生成！请确保在 goal 中提供 chapter_count 参数")

        # Resolve dependencies
        self._resolve_dependencies()

        # Mark ready tasks
        self._update_ready_tasks()

        logger.info(f"Generated {len(self.tasks)} tasks")
        return list(self.tasks.values())

    def _create_task_from_definition(
        self,
        definition: TaskDefinition,
        goal: Dict[str, Any],
    ) -> Task:
        """Create a Task instance from a TaskDefinition"""
        task_id = str(uuid.uuid4())

        # Copy metadata from definition and add goal info
        metadata = definition.metadata.copy()
        metadata["goal_style"] = goal.get("style")
        metadata["goal_theme"] = goal.get("theme")
        metadata["goal_length"] = goal.get("length")

        return Task(
            task_id=task_id,
            task_type=definition.task_type,
            description=definition.description,
            depends_on=definition.depends_on.copy(),
            metadata=metadata,
            optional=definition.optional,
            can_parallel=definition.can_parallel,
            is_foundation=definition.is_foundation,  # 🔴 复制基础任务标志
        )

    async def _create_chapter_tasks(
        self,
        chapter_count: int,
        goal: Dict[str, Any],
    ) -> None:
        """
        创建章节任务（逐章生成方案）

        逐章生成流程：
        1. 每个章节单独生成（章节内容，使用 Qwen Long 直接生成高质量内容）
        2. 每个章节依赖于前面章节（保证连贯性）
        3. 无需单独润色步骤（已整合到章节生成提示词中）
        """
        logger.info(f"Creating tasks for {chapter_count} chapters (逐章生成方案，使用 Qwen Long 直接生成高质量内容)")

        # Phase 3: 逐章生成任务
        # 每个章节依赖于：大纲、世界观、人物设计，以及上一章节
        previous_chapter_task_id = None

        for chapter_index in range(1, chapter_count + 1):
            # 构建依赖列表
            depends_on = ["大纲", "世界观规则", "人物设计"]
            if previous_chapter_task_id:
                depends_on.append(previous_chapter_task_id)

            # 创建章节内容任务（直接生成高质量，无需润色）
            chapter_task = Task(
                task_id=str(uuid.uuid4()),
                task_type=NovelTaskType.CHAPTER_CONTENT,
                description=f"生成第{chapter_index}章内容（使用 Qwen Long 直接生成高质量内容）",
                depends_on=depends_on,
                metadata={
                    "chapter_index": chapter_index,
                    "chapter_count": chapter_count,
                    "goal_style": goal.get("style"),
                    "goal_length": goal.get("length"),
                    "is_first_chapter": chapter_index == 1,
                    "direct_quality": True,  # 标记：直接生成高质量，无需润色
                },
            )
            self.tasks[chapter_task.task_id] = chapter_task
            previous_chapter_task_id = chapter_task.task_id

        logger.info(f"✅ 创建了 {chapter_count} 个章节内容任务（使用 Qwen Long 直接生成高质量内容，无需润色步骤）")

    def _resolve_dependencies(self) -> None:
        """Resolve task dependencies by task_id"""
        # Build a map of task_type to task_ids
        type_to_ids: Dict[str, List[str]] = {}
        for task_id, task in self.tasks.items():
            task_type = task.task_type.value
            if task_type not in type_to_ids:
                type_to_ids[task_type] = []
            type_to_ids[task_type].append(task_id)

        # Resolve each task's depends_on list
        for task in self.tasks.values():
            resolved_deps = []
            for dep in task.depends_on:
                if dep in type_to_ids:
                    # Use the first task of this type
                    resolved_deps.append(type_to_ids[dep][0])
                elif dep in self.tasks:
                    # Direct task ID reference
                    resolved_deps.append(dep)
            task.depends_on = resolved_deps

        logger.debug("Resolved all task dependencies")

    def _update_ready_tasks(self) -> None:
        """Update tasks whose dependencies are met"""
        for task in self.tasks.values():
            if task.status == "pending":
                task.dependencies_met = self._check_dependencies_met(task)
                if task.dependencies_met:
                    task.status = "ready"

        ready_count = sum(1 for t in self.tasks.values() if t.status == "ready")
        logger.debug(f"Updated ready tasks: {ready_count} ready")

    def _check_dependencies_met(self, task: Task) -> bool:
        """Check if all dependencies of a task are completed"""
        for dep_id in task.depends_on:
            if dep_id not in self.tasks:
                logger.warning(f"Task {task.task_id} depends on unknown task {dep_id}")
                return False

            dep_task = self.tasks[dep_id]
            if dep_task.status != "completed":
                return False

        return True

    def get_next_task(self) -> Optional[Task]:
        """
        Get the next task ready for execution

        Returns:
            The next ready task, or None if no tasks are ready
        """
        # Prefer non-parallel tasks first (to maintain order)
        for task in self.tasks.values():
            if task.status == "ready" and not task.can_parallel:
                return task

        # Then parallel tasks
        for task in self.tasks.values():
            if task.status == "ready":
                return task

        return None

    def get_ready_tasks(self, max_count: Optional[int] = None) -> List[Task]:
        """
        Get all tasks ready for execution

        Args:
            max_count: Maximum number of tasks to return

        Returns:
            List of ready tasks
        """
        ready_tasks = [t for t in self.tasks.values() if t.status == "ready"]
        ready_tasks.sort(key=lambda t: not t.can_parallel)

        if max_count:
            return ready_tasks[:max_count]
        return ready_tasks

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update the status of a task

        Args:
            task_id: The task ID
            status: New status
            result: Task result (if completed)
            error: Error message (if failed)
        """
        if task_id not in self.tasks:
            logger.warning(f"Unknown task ID: {task_id}")
            return

        task = self.tasks[task_id]
        task.status = status

        if result is not None:
            task.result = result

        if error is not None:
            task.error = error

        # Update dependent tasks
        if status == "completed":
            self._update_ready_tasks()

        logger.debug(f"Updated task {task_id} status to {status}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: str) -> List[Task]:
        """Get all tasks with a specific status"""
        return [t for t in self.tasks.values() if t.status == status]

    def get_tasks_by_type(self, task_type: NovelTaskType) -> List[Task]:
        """Get all tasks of a specific type"""
        return [t for t in self.tasks.values() if t.task_type == task_type]

    def get_progress(self) -> Dict[str, Any]:
        """
        Get overall progress information

        Returns:
            Dictionary with progress stats
        """
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        failed = sum(1 for t in self.tasks.values() if t.status == "failed")
        running = sum(1 for t in self.tasks.values() if t.status == "running")
        ready = sum(1 for t in self.tasks.values() if t.status == "ready")
        
        # Get current running task
        current_task = None
        current_task_retry_count = 0
        current_task_started_at = None
        running_tasks = [t for t in self.tasks.values() if t.status == "running"]
        if running_tasks:
            current_task = running_tasks[0].task_type.value
            # 获取重试次数
            current_task_retry_count = running_tasks[0].metadata.get("retry_count", 0)
            # 获取任务开始时间
            current_task_started_at = running_tasks[0].metadata.get("started_at")
        
        # 检查是否全部完成
        is_completed = self.is_complete() and failed == 0

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
            "ready_tasks": ready,
            "pending_tasks": total - completed - failed - running - ready,
            "percentage": (completed / total * 100) if total > 0 else 0,
            "current_task": current_task,
            "retry_count": current_task_retry_count,
            "task_started_at": current_task_started_at,
            "is_completed": is_completed,
        }

    def is_complete(self) -> bool:
        """Check if all tasks are complete"""
        return all(
            t.status in ("completed", "failed", "skipped")
            for t in self.tasks.values()
        )

    def get_failed_tasks(self) -> List[Task]:
        """Get all failed tasks"""
        return self.get_tasks_by_status("failed")

    def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task

        Args:
            task_id: The task to retry

        Returns:
            True if task can be retried
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status != "failed":
            return False

        if task.retry_count >= task.max_retries:
            logger.warning(f"Task {task_id} has reached max retries")
            return False

        task.retry_count += 1
        task.status = "ready"
        task.error = None

        logger.info(f"Retrying task {task_id} (attempt {task.retry_count})")
        return True

    def reset(self) -> None:
        """Reset all tasks to pending state"""
        for task in self.tasks.values():
            task.status = "pending"
            task.result = None
            task.error = None
            task.retry_count = 0
            task.dependencies_met = False

        self._update_ready_tasks()
        logger.info("Reset all tasks to pending state")
