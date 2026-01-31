"""
Task Planner - Plans and schedules creative writing tasks

Defines task types, dependencies, and execution order for novel creation.
Implements the DAG-based task scheduling from the architecture.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
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
    WORLDVIEW_RULES = "世界观规则"
    FACTION_DESIGN = "势力设计"  # 门派、家族、组织等势力设定
    SCENE_DESIGN = "场景设计"  # 秘境、禁地、遗迹、洞府等地点详细设定
    CHARACTER_DESIGN = "人物设计"
    POWER_SYSTEM = "功法法宝"  # 功法、秘术、法宝设定
    GROWTH_PATH = "主角成长"  # 主角境界划分、突破条件、成长路径
    VILLAIN_DESIGN = "反派设计"  # 主要反派、阶段性对手
    EVENTS = "事件"  # 详细事件列表，包含章节、人物、起因、经过、结果
    TIMELINE = "时间线"  # 事件时间顺序、人物年龄变化
    FORESHADOW_LIST = "伏笔列表"  # 伏笔管理，包含名称、埋设章节、回收章节

    # Phase 2.5: Story Unit Planning (故事单元规划 - 模块化三幕结构)
    STORY_UNIT_PLAN = "故事单元规划"  # 每个模块/单元的详细剧情规划

    # Phase 3: Quality Check (质量检查 - 每章后自动运行)
    CONSISTENCY_CHECK = "一致性检查"  # 检查人物、世界观、时间线一致性
    DIALOGUE_CHECK = "对话检查"  # 检查角色对话风格一致性

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
            task_type=NovelTaskType.FACTION_DESIGN,
            description="基于世界观规则，设计各大势力（门派、家族、组织）。每个势力包含：信仰/目标、能力体系、人员结构、地盘范围、与其他势力的关系",
            depends_on=["大纲", "世界观规则"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.SCENE_DESIGN,
            description="基于世界观和势力设计，详细设计重要地点（秘境、禁地、遗迹、洞府、城市等）。每个地点包含：地理位置、环境描述、特色/秘密、相关势力、剧情作用",
            depends_on=["大纲", "世界观规则", "势力设计"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.CHARACTER_DESIGN,
            description="根据大纲、世界观、势力设计和场景，设计能够推动故事发展的人物。主角的目标、缺陷、成长弧线都要服务于大纲",
            depends_on=["大纲", "世界观规则", "势力设计"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.POWER_SYSTEM,
            description="基于世界观规则，设计功法、秘术、法宝体系。包含：功法名称、等级、效果、修炼条件、限制；法宝来历、能力、器灵",
            depends_on=["大纲", "世界观规则", "势力设计"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.GROWTH_PATH,
            description="基于世界观和功法体系，规划主角成长路径。包含：境界划分（炼气→筑基→金丹→元婴→化神）、每个境界的突破条件、核心功法的获取和升级路径、重要顿悟时刻",
            depends_on=["大纲", "世界观规则", "功法法宝", "人物设计"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.VILLAIN_DESIGN,
            description="基于大纲和主角成长路径，设计反派体系。主要反派：目标、实力、与主角的恩怨；次要反派：阶段性对手；反派的成长和变化",
            depends_on=["大纲", "人物设计", "主角成长", "势力设计"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.EVENTS,
            description="基于大纲，详细规划每个关键事件。包含发生章节、涉及人物、起因、经过、结果、推动的情节",
            depends_on=["大纲", "世界观规则", "势力设计", "场景设计", "人物设计", "反派设计"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.TIMELINE,
            description="基于事件列表，建立精确的时间线。包含：事件时间顺序、人物年龄变化、修为提升的时间跨度、重要时间节点",
            depends_on=["大纲", "人物设计", "事件", "主角成长"],
            is_foundation=True,
        ),
        TaskDefinition(
            task_type=NovelTaskType.FORESHADOW_LIST,
            description="基于大纲、事件和时间线，系统化管理所有伏笔。记录伏笔名称、埋设章节、回收章节、重要性",
            depends_on=["大纲", "势力设计", "人物设计", "事件", "时间线"],
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
        completed_task_ids: Optional[List[str]] = None,
        completed_task_records: Optional[List[Dict[str, Any]]] = None,
        modular_structure: Optional[Any] = None,
    ) -> List[Task]:
        """
        Generate a task plan based on the creation goal

        Args:
            goal: Creation goal with style, theme, length, etc.
            chapter_count: Number of chapters to create (启用逐章生成模式)
            completed_task_ids: [DEPRECATED] List of already completed task IDs (for resume)
            completed_task_records: List of completed task records for intelligent matching by task_type + chapter_index
            modular_structure: Modular three-act structure for story unit planning

        Returns:
            List of tasks ready for execution
        """
        logger.info(f"Planning tasks for goal: {goal.get('title', 'Untitled')}")

        if completed_task_ids:
            logger.info(f"🔄 Resume mode (legacy): {len(completed_task_ids)} task IDs")
        if completed_task_records:
            logger.info(f"🔄 Resume mode (intelligent): {len(completed_task_records)} task records")

        # Clear previous tasks
        self.tasks = {}

        # 🔥 检查是否为二创模式（支持多种配置方式）
        derivative_mode = (
            goal.get('mode') == 'derivative' or  # goal 中的 mode
            goal.get('derivative_mode', False) or  # goal 中的 derivative_mode
            self.config.get('is_derivative', False)  # config 中的 is_derivative（前端传递）
        )
        if derivative_mode:
            logger.info("🔥 二创模式已启用：跳过'创意脑暴'，直接从大纲开始")

        # 创建基础任务（创意脑暴 → 故事核心 → 大纲 → 世界观规则 → 人物设计）
        for definition in self.DEFAULT_TASK_DEFINITIONS:
            task = self._create_task_from_definition(definition, goal)
            self.tasks[task.task_id] = task

        # 🔥 加载插件任务（插件任务覆盖同类型的硬编码任务）
        plugin_tasks = self._load_plugin_tasks()
        for plugin_def in plugin_tasks:
            # 插件任务覆盖策略：相同 task_type 时，插件版本优先
            task_type_str = plugin_def.task_type.value

            # 🔥 如果存在同类型的硬编码任务，先删除它
            if task_type_str in self.task_definitions:
                # 找到并删除硬编码版本的任务实例
                to_delete = []
                for task_id, task in self.tasks.items():
                    if task.task_type.value == task_type_str:
                        # 检查是否是硬编码版本（没有plugin元数据）
                        if not task.metadata.get('plugin'):
                            to_delete.append(task_id)
                            logger.info(f"🔥 删除硬编码任务，将被插件版本替代: {task_type_str} ({task_id})")

                for task_id in to_delete:
                    del self.tasks[task_id]

            # 注册插件任务定义（覆盖硬编码版本）
            self.register_task_definition(plugin_def)

            # 创建任务实例
            task = self._create_task_from_definition(plugin_def, goal)
            self.tasks[task.task_id] = task
            logger.debug(f"Created plugin task: {task_type_str}")

        # 🔥 二创模式：跳过创意脑暴任务，移除大纲对它的依赖
        if derivative_mode:
            brainstorm_task_id = None
            outline_task_id = None

            for task_id, task in self.tasks.items():
                if task.task_type.value == "创意脑暴":
                    brainstorm_task_id = task_id
                elif task.task_type.value == "大纲":
                    outline_task_id = task_id

            # 移除创意脑暴任务
            if brainstorm_task_id:
                del self.tasks[brainstorm_task_id]
                logger.info(f"🔥 二创模式：已跳过'创意脑暴'任务 ({brainstorm_task_id})")

            # 移除大纲对创意脑暴的依赖
            if outline_task_id:
                self.tasks[outline_task_id].depends_on = [
                    dep for dep in self.tasks[outline_task_id].depends_on
                    if dep != "创意脑暴"
                ]
                # 如果大纲依赖现在是空的，说明它已经可以执行了
                if not self.tasks[outline_task_id].depends_on:
                    logger.info(f"🔥 二创模式：大纲任务已移除对创意脑暴的依赖，可直接执行")

        # Create chapter tasks if chapter count specified (逐章生成模式)
        if chapter_count:
            logger.info(f"🔥 逐章生成模式已启用：{chapter_count}章，每章依赖前一章确保连贯性")
            logger.info(f"🔥 模块化结构支持：{len(modular_structure.modules) if modular_structure else '按每100章自动划分'}个故事单元")
            await self._create_chapter_tasks(chapter_count, goal, modular_structure)
        else:
            logger.warning("⚠️ 未指定章节数量，将跳过章节生成！请确保在 goal 中提供 chapter_count 参数")

        # Resolve dependencies
        self._resolve_dependencies()

        # 🔥 恢复模式：标记已完成的任务
        # 🔥 优先使用 completed_task_records 进行智能匹配
        if completed_task_records:
            self._mark_completed_tasks_intelligent(completed_task_records)
        elif completed_task_ids:
            self._mark_completed_tasks(completed_task_ids)

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
        modular_structure: Optional[Any] = None,
    ) -> None:
        """
        创建章节任务（逐章生成方案）

        增强版：支持模块化三幕结构，先创建故事单元规划任务
        逐章生成流程：
        1. 创建故事单元规划任务（每个模块一个）
        2. 每个章节的生成依赖于所属单元规划任务
        3. 每个章节单独生成（章节内容，使用 Qwen Long 直接生成高质量内容）
        4. 每个章节依赖于前面章节（保证连贯性）
        5. 无需单独润色步骤（已整合到章节生成提示词中）
        """
        logger.info(f"Creating tasks for {chapter_count} chapters with modular structure support")

        # 🔥 Phase 3a: 创建故事单元规划任务（每个模块一个）
        unit_plan_tasks = {}  # unit_number -> task_id
        
        if modular_structure:
            # 根据模块化结构创建单元规划任务
            for module in modular_structure.modules:
                unit_number = module.module_number
                
                # 创建故事单元规划任务
                unit_plan_task = Task(
                    task_id=str(uuid.uuid4()),
                    task_type=NovelTaskType.STORY_UNIT_PLAN,
                    description=f"规划故事单元{unit_number}：{module.title}（第{module.start_chapter}-{module.end_chapter}章）",
                    depends_on=[
                        "大纲", "世界观规则", "势力设计", "场景设计",
                        "人物设计", "功法法宝", "主角成长", "反派设计",
                    ],
                    metadata={
                        "unit_number": unit_number,
                        "unit_title": module.title,
                        "chapter_start": module.start_chapter,
                        "chapter_end": module.end_chapter,
                        "world_level": module.world_level,
                        "power_start": module.power_level_start,
                        "power_end": module.power_level_end,
                        "module_size": module.get_chapter_count(),
                        "plugin": "story_unit",
                        "operation": "plan",
                    },
                )
                self.tasks[unit_plan_task.task_id] = unit_plan_task
                unit_plan_tasks[unit_number] = unit_plan_task.task_id
                logger.info(f"  Created story unit plan task for Unit {unit_number}: {module.title}")
        else:
            # 如果没有模块化结构，按每100章创建一个单元规划
            module_size = 100
            num_units = max(1, chapter_count // module_size + (1 if chapter_count % module_size else 0))
            
            for unit_number in range(1, num_units + 1):
                start_chapter = (unit_number - 1) * module_size + 1
                end_chapter = min(unit_number * module_size, chapter_count)
                
                unit_plan_task = Task(
                    task_id=str(uuid.uuid4()),
                    task_type=NovelTaskType.STORY_UNIT_PLAN,
                    description=f"规划故事单元{unit_number}（第{start_chapter}-{end_chapter}章）",
                    depends_on=[
                        "大纲", "世界观规则", "势力设计", "场景设计",
                        "人物设计", "功法法宝", "主角成长", "反派设计",
                    ],
                    metadata={
                        "unit_number": unit_number,
                        "chapter_start": start_chapter,
                        "chapter_end": end_chapter,
                        "module_size": end_chapter - start_chapter + 1,
                        "plugin": "story_unit",
                        "operation": "plan",
                    },
                )
                self.tasks[unit_plan_task.task_id] = unit_plan_task
                unit_plan_tasks[unit_number] = unit_plan_task.task_id
                logger.info(f"  Created story unit plan task for Unit {unit_number} (Chapters {start_chapter}-{end_chapter})")
        
        logger.info(f"✅ Created {len(unit_plan_tasks)} story unit plan tasks")

        # Phase 3b: 逐章生成任务
        # 每个章节依赖于：所有基础设定任务 + 所属单元规划任务 + 上一章节
        previous_chapter_task_id = None

        for chapter_index in range(1, chapter_count + 1):
            # 确定所属单元
            unit_number = (chapter_index - 1) // 100 + 1  # 简单计算，每100章一个单元
            
            # 构建依赖列表
            depends_on = [
                "大纲", "世界观规则", "势力设计", "场景设计",
                "人物设计", "功法法宝", "主角成长", "反派设计",
                "事件", "时间线", "伏笔列表",
            ]
            
            # 添加所属单元规划任务作为依赖
            if unit_number in unit_plan_tasks:
                depends_on.append(unit_plan_tasks[unit_number])
            
            # 添加上一章节作为依赖
            if previous_chapter_task_id:
                depends_on.append(previous_chapter_task_id)

            # 创建章节内容任务
            chapter_task = Task(
                task_id=str(uuid.uuid4()),
                task_type=NovelTaskType.CHAPTER_CONTENT,
                description=f"生成第{chapter_index}章内容（使用 Qwen Long 直接生成高质量内容）",
                depends_on=depends_on,
                metadata={
                    "chapter_index": chapter_index,
                    "chapter_count": chapter_count,
                    "unit_number": unit_number,
                    "goal_style": goal.get("style"),
                    "goal_length": goal.get("length"),
                    "is_first_chapter": chapter_index == 1,
                    "direct_quality": True,
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

    def _mark_completed_tasks(self, completed_task_ids: List[str]) -> None:
        """
        Mark tasks as completed (for resume functionality)

        Args:
            completed_task_ids: List of task IDs that are already completed
        """
        if not completed_task_ids:
            return

        completed_count = 0
        for task_id in completed_task_ids:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                completed_count += 1
                logger.debug(f"Marked task as completed: {task.task_type.value} ({task_id})")
            else:
                logger.warning(f"Completed task ID not found in current plan: {task_id}")

        logger.info(f"✅ Marked {completed_count}/{len(completed_task_ids)} tasks as completed")

    def _mark_completed_tasks_intelligent(self, completed_task_records: List[Dict[str, Any]]) -> None:
        """
        智能标记已完成的任务（通过 task_type + chapter_index 匹配，而不是 task_id）

        因为每次 TaskPlanner.plan() 都会重新生成 task_id，所以不能通过 task_id 匹配。
        相反，我们应该通过 task_type 和 chapter_index 来匹配已完成的任务。

        Args:
            completed_task_records: List of completed task records with task_type and chapter_index
        """
        if not completed_task_records:
            return

        # 构建已完成任务的索引：key = (task_type, chapter_index), value = task_record
        completed_index = {}
        for record in completed_task_records:
            task_type = record.get("task_type", "")
            metadata = record.get("metadata", {}) or {}
            chapter_index = metadata.get("chapter_index")

            # 对于章节任务，使用 (task_type, chapter_index) 作为 key
            # 对于非章节任务，只使用 task_type 作为 key
            if chapter_index is not None:
                key = (task_type, chapter_index)
            else:
                key = task_type

            if key not in completed_index:
                completed_index[key] = record

        logger.info(f"🔍 Built completed task index with {len(completed_index)} entries")

        # 遍历当前任务，匹配已完成的任务
        completed_count = 0
        for task in self.tasks.values():
            task_type = task.task_type.value
            chapter_index = task.metadata.get("chapter_index")

            # 构建与上面相同的 key
            if chapter_index is not None:
                key = (task_type, chapter_index)
            else:
                key = task_type

            if key in completed_index:
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                completed_count += 1
                logger.debug(f"✅ Marked task as completed: {task_type} (chapter: {chapter_index})")

        logger.info(f"✅ Intelligent matching: marked {completed_count}/{len(self.tasks)} tasks as completed")

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
