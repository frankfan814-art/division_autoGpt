"""
Story Unit Plugin - Manages story arc planning for long-form novels

This plugin handles detailed planning for each story unit/module:
- Unit-level plot architecture (three-act structure within unit)
- Local character systems (allies, mentors, unit-specific antagonists)
- Local faction distributions
- Key events within the unit (10-15 detailed events)
- Foreshadowing system (unit-internal and cross-unit)
- Character growth trajectory within the unit
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from loguru import logger

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
    ValidationResult,
    WritingContext,
)


@dataclass
class UnitAntagonist:
    """Antagonist definition within a story unit"""
    name: str
    level: str  # "minor" | "medium" | "major"
    appearance_chapter: int
    defeat_chapter: int
    motivation: str
    power_level: str
    relationship_to_protagonist: str


@dataclass
class UnitEvent:
    """Key event within a story unit"""
    name: str
    chapter: int
    description: str
    involved_characters: List[str]
    outcome: str
    importance: str  # "critical" | "major" | "minor"


@dataclass
class UnitForeshadow:
    """Foreshadowing element within a story unit"""
    name: str
    plant_chapter: int
    payoff_chapter: Optional[int] = None
    payoff_unit: Optional[int] = None  # Which unit pays off (if cross-unit)
    description: str = ""
    importance: str = "normal"  # "critical" | "important" | "normal"


@dataclass
class StoryUnitPlan:
    """Detailed plan for a story unit (100-200 chapters)"""
    unit_number: int
    title: str
    chapter_start: int
    chapter_end: int
    world_level: str
    power_level_start: str
    power_level_end: str
    
    # Three-act structure within unit
    act1_chapters: List[int] = field(default_factory=list)
    act2_chapters: List[int] = field(default_factory=list)
    act3_chapters: List[int] = field(default_factory=list)
    
    # Plot architecture
    act1_plot: Dict[str, Any] = field(default_factory=dict)
    act2_plot: Dict[str, Any] = field(default_factory=dict)
    act3_plot: Dict[str, Any] = field(default_factory=dict)
    
    # Character system
    local_allies: List[Dict[str, Any]] = field(default_factory=list)
    mentors: List[Dict[str, Any]] = field(default_factory=list)
    antagonists: List[UnitAntagonist] = field(default_factory=list)
    
    # Factions
    local_factions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Events
    key_events: List[UnitEvent] = field(default_factory=list)
    
    # Foreshadowing
    unit_foreshadows: List[UnitForeshadow] = field(default_factory=list)
    
    # Growth trajectory
    growth_start: Dict[str, Any] = field(default_factory=dict)
    growth_end: Dict[str, Any] = field(default_factory=dict)
    acquired_items: List[str] = field(default_factory=list)
    relationship_changes: List[str] = field(default_factory=list)
    
    def get_chapter_count(self) -> int:
        return self.chapter_end - self.chapter_start + 1


class StoryUnitPlugin(NovelElementPlugin):
    """
    Plugin for detailed story unit planning
    
    Manages detailed plans for each story module/unit, ensuring:
    - Unit-level plot coherence
    - Complete three-act structure within unit
    - Local character and faction systems
    - Event planning and foreshadowing
    - Character growth tracking per unit
    """
    
    name = "story_unit"
    version = "1.0.0"
    description = "Manages detailed planning for story units/arcs"
    author = "Creative AutoGPT"
    
    _unit_plans: Dict[int, StoryUnitPlan] = {}
    _current_unit: Optional[int] = None
    
    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._unit_plans = {}
        self._current_unit = None
    
    async def on_init(self, context: WritingContext) -> None:
        """Initialize plugin with session context"""
        logger.info(f"StoryUnitPlugin initialized for session {context.session_id}")
        
        state = await self.load_state(context)
        if state:
            # Restore unit plans from state
            for unit_num, plan_data in state.get("unit_plans", {}).items():
                self._unit_plans[int(unit_num)] = self._deserialize_unit_plan(plan_data)
            logger.info(f"Loaded {len(self._unit_plans)} unit plans from database")
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for story unit data"""
        return {
            "type": "object",
            "title": "Story Unit Plan Schema",
            "description": "Schema for detailed story unit planning",
            "properties": {
                "unit_number": {"type": "integer"},
                "title": {"type": "string"},
                "chapter_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer"},
                        "end": {"type": "integer"}
                    }
                },
                "world_level": {"type": "string"},
                "power_progression": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"}
                    }
                },
                "three_act_structure": {
                    "type": "object",
                    "properties": {
                        "act1": {
                            "type": "object",
                            "properties": {
                                "chapters": {"type": "array", "items": {"type": "integer"}},
                                "hook": {"type": "string"},
                                "status_quo": {"type": "string"},
                                "inciting_incident": {"type": "string"}
                            }
                        },
                        "act2": {
                            "type": "object",
                            "properties": {
                                "chapters": {"type": "array", "items": {"type": "integer"}},
                                "rising_action": {"type": "string"},
                                "midpoint": {"type": "string"},
                                "confrontation": {"type": "string"}
                            }
                        },
                        "act3": {
                            "type": "object",
                            "properties": {
                                "chapters": {"type": "array", "items": {"type": "integer"}},
                                "crisis": {"type": "string"},
                                "climax": {"type": "string"},
                                "resolution": {"type": "string"},
                                "transition": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    
    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for story unit planning"""
        return {
            "story_unit_plan": """## 任务: 故事单元详细规划

### 单元基本信息
- 单元编号: {unit_number}
- 单元标题: {title}
- 章节范围: 第{chapter_start}章 - 第{chapter_end}章（共{chapter_count}章）
- 世界层级: {world_level}
- 修为境界: {power_start} → {power_end}

### 小说整体背景
{novel_context}

### 前一单元结果（如适用）
{previous_unit_summary}

### 单元规划要求

请为这个单元创建详细的剧情规划，确保单元内故事完整、逻辑自洽。

**一、单元剧情架构（三幕结构）**

**第一幕：建立与进入（第{act1_start}-{act1_end}章，约20%）**
- 钩子设计：如何吸引读者进入本单元？
- 现状建立：主角进入新世界时的状态
- 规则介绍：本单元的世界规则和势力分布
- 引发事件：什么事件打破现状，迫使主角行动？

**第二幕：对抗与发展（第{act2_start}-{act2_end}章，约60%）**
- 上升动作：主角如何在本单元提升实力？
- 中点转折：第{midpoint_chapter}章左右的重大转折是什么？
- 持续对抗：与单元反派的多次交锋
- 盟友建立：主角在本单元结交哪些盟友？

**第三幕：高潮与解决（第{act3_start}-{act3_end}章，约20%）**
- 危机设计：单元内的最大危机是什么？
- 高潮战斗：与单元最终BOSS的决战
- 胜利条件：主角如何获胜？
- 过渡钩子：如何引出下一单元？

**二、单元人物体系**

**本地盟友（3-5人）**:
- 姓名、身份、性格、与主角的关系发展

**导师/引路人（1-2人）**:
- 谁帮助主角适应新世界？
- 传授什么技能/知识？

**单元反派体系**:
- 小BOSS（第{minor_boss_chapter}章）：姓名、动机、实力
- 中BOSS（第{medium_boss_chapter}章）：姓名、动机、实力
- 大BOSS（第{major_boss_chapter}章）：姓名、动机、实力、与主角的恩怨

**三、单元势力分布**
- 本地主要势力及其立场
- 各势力与主角的关系

**四、单元关键事件（10-15个）**
为每章规划核心事件：
| 章节 | 事件名称 | 事件描述 | 涉及人物 | 事件结果 |
|-----|---------|---------|---------|---------|
| {act1_start} | | | | |
| ... | | | | |
| {midpoint_chapter} | [中点转折] | | | |
| ... | | | | |
| {major_boss_chapter} | [单元高潮] | | | |

**五、单元伏笔系统**
- 本单元埋设的伏笔（5个左右）
- 本单元回收的伏笔（3个左右）
- 留给后续单元的伏笔（2个左右）

**六、单元成长轨迹**
- 进入时状态：主角的实力、装备、人际关系
- 离开时状态：主角的成长、收获、变化
- 获得的关键物品/功法
- 关系变化：与谁结盟、与谁结仇

请以JSON格式输出详细的单元规划。
""",
            "chapter_guidance": """## 第{chapter_index}章创作指导

基于故事单元{unit_number}的规划：

**单元信息**: {unit_title}
**所属三幕**: {act_type}
**单元进度**: {progress_in_unit}%

**本章要求**:
{chapter_requirements}

**必须包含的元素**:
{required_elements}

**与单元规划的关联**:
{unit_connection}
"""
        }
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for story unit planning"""
        return [
            {
                "task_id": "story_unit_plan",
                "task_type": "故事单元规划",
                "description": "Detailed planning for a story unit including plot architecture, characters, events, and foreshadowing",
                "depends_on": ["大纲", "世界观规则", "势力设计", "人物设计"],
                "metadata": {"plugin": "story_unit", "operation": "plan"}
            }
        ]
    
    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate story unit plan"""
        errors = []
        warnings = []
        suggestions = []
        
        if not isinstance(data, dict):
            return ValidationResult(valid=False, errors=["Story unit data must be a dictionary"])
        
        if "unit_number" not in data:
            errors.append("Missing unit number")
        if "title" not in data:
            errors.append("Missing unit title")
        if "chapter_range" not in data:
            errors.append("Missing chapter range")
        
        if "three_act_structure" in data:
            acts = data["three_act_structure"]
            for act_name in ["act1", "act2", "act3"]:
                if act_name not in acts:
                    warnings.append(f"Missing {act_name} structure")
        else:
            warnings.append("Missing three-act structure")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, suggestions=suggestions)
    
    async def on_after_task(
        self,
        task: Dict[str, Any],
        result: str,
        context: WritingContext,
    ) -> str:
        """Extract and store story unit plan from task results"""
        if task.get("task_type") == "故事单元规划":
            await self._extract_unit_plan(result, task, context)
        return result
    
    async def _extract_unit_plan(self, result: str, task: Dict[str, Any], context: WritingContext) -> None:
        """Extract story unit plan from result"""
        import json
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)
                
                unit_number = task.get("metadata", {}).get("unit_number", 1)
                
                # Parse the unit plan
                plan = StoryUnitPlan(
                    unit_number=unit_number,
                    title=data.get("title", f"单元{unit_number}"),
                    chapter_start=data.get("chapter_range", {}).get("start", 1),
                    chapter_end=data.get("chapter_range", {}).get("end", 100),
                    world_level=data.get("world_level", ""),
                    power_level_start=data.get("power_progression", {}).get("start", ""),
                    power_level_end=data.get("power_progression", {}).get("end", ""),
                )
                
                # Parse three-act structure
                three_act = data.get("three_act_structure", {})
                if "act1" in three_act:
                    plan.act1_chapters = three_act["act1"].get("chapters", [])
                    plan.act1_plot = three_act["act1"]
                if "act2" in three_act:
                    plan.act2_chapters = three_act["act2"].get("chapters", [])
                    plan.act2_plot = three_act["act2"]
                if "act3" in three_act:
                    plan.act3_chapters = three_act["act3"].get("chapters", [])
                    plan.act3_plot = three_act["act3"]
                
                # Parse antagonists
                for ant_data in data.get("antagonists", []):
                    plan.antagonists.append(UnitAntagonist(**ant_data))
                
                # Parse events
                for evt_data in data.get("key_events", []):
                    plan.key_events.append(UnitEvent(**evt_data))
                
                # Parse foreshadows
                for fs_data in data.get("foreshadows", []):
                    plan.unit_foreshadows.append(UnitForeshadow(**fs_data))
                
                # Store plan
                self._unit_plans[unit_number] = plan
                logger.info(f"Extracted story unit plan {unit_number}: {plan.title} ({plan.get_chapter_count()} chapters)")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse story unit plan as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting story unit plan: {e}")
    
    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with story unit information for chapter generation"""
        task_type = task.get("task_type", "")
        chapter_index = task.get("metadata", {}).get("chapter_index")
        
        if "章节" in task_type and chapter_index is not None:
            # Find which unit this chapter belongs to
            unit_plan = self._get_unit_for_chapter(chapter_index)
            if unit_plan:
                context["story_unit"] = {
                    "unit_number": unit_plan.unit_number,
                    "title": unit_plan.title,
                    "world_level": unit_plan.world_level,
                    "power_start": unit_plan.power_level_start,
                    "power_end": unit_plan.power_level_end,
                }
                
                # Determine which act
                act = self._get_act_for_chapter(chapter_index, unit_plan)
                if act:
                    context["unit_act"] = act
                    context["act_progress"] = self._get_progress_in_act(chapter_index, unit_plan, act)
                
                # Get upcoming events
                upcoming = self._get_upcoming_events(chapter_index, unit_plan, limit=3)
                if upcoming:
                    context["upcoming_events"] = upcoming
                
                # Get active foreshadows
                active_foreshadows = self._get_active_foreshadows(chapter_index, unit_plan)
                if active_foreshadows:
                    context["unit_foreshadows"] = active_foreshadows
                
                # Get current antagonist
                current_antagonist = self._get_current_antagonist(chapter_index, unit_plan)
                if current_antagonist:
                    context["current_antagonist"] = current_antagonist
        
        return context
    
    def _get_unit_for_chapter(self, chapter_index: int) -> Optional[StoryUnitPlan]:
        """Get the unit plan for a specific chapter"""
        for plan in self._unit_plans.values():
            if plan.chapter_start <= chapter_index <= plan.chapter_end:
                return plan
        return None
    
    def _get_act_for_chapter(self, chapter_index: int, unit_plan: StoryUnitPlan) -> Optional[str]:
        """Determine which act a chapter belongs to"""
        if chapter_index in unit_plan.act1_chapters:
            return "第一幕_建立"
        elif chapter_index in unit_plan.act2_chapters:
            return "第二幕_对抗"
        elif chapter_index in unit_plan.act3_chapters:
            return "第三幕_解决"
        return None
    
    def _get_progress_in_act(self, chapter_index: int, unit_plan: StoryUnitPlan, act: str) -> float:
        """Calculate progress percentage within an act"""
        if act == "第一幕_建立":
            chapters = unit_plan.act1_chapters
        elif act == "第二幕_对抗":
            chapters = unit_plan.act2_chapters
        elif act == "第三幕_解决":
            chapters = unit_plan.act3_chapters
        else:
            return 0.0
        
        if not chapters:
            return 0.0
        
        position = chapters.index(chapter_index) if chapter_index in chapters else 0
        return (position / len(chapters)) * 100
    
    def _get_upcoming_events(self, chapter_index: int, unit_plan: StoryUnitPlan, limit: int = 3) -> List[Dict[str, Any]]:
        """Get upcoming events in the unit"""
        upcoming = []
        for event in unit_plan.key_events:
            if event.chapter > chapter_index and len(upcoming) < limit:
                upcoming.append({
                    "name": event.name,
                    "chapter": event.chapter,
                    "description": event.description,
                    "importance": event.importance
                })
        return upcoming
    
    def _get_active_foreshadows(self, chapter_index: int, unit_plan: StoryUnitPlan) -> List[Dict[str, Any]]:
        """Get foreshadows that should be active at this chapter"""
        active = []
        for fs in unit_plan.unit_foreshadows:
            # Active if planted but not yet paid off, or should be paid off at this chapter
            if fs.plant_chapter <= chapter_index:
                if fs.payoff_chapter is None or fs.payoff_chapter >= chapter_index:
                    active.append({
                        "name": fs.name,
                        "description": fs.description,
                        "should_payoff": fs.payoff_chapter == chapter_index,
                        "importance": fs.importance
                    })
        return active
    
    def _get_current_antagonist(self, chapter_index: int, unit_plan: StoryUnitPlan) -> Optional[Dict[str, Any]]:
        """Get the active antagonist at this chapter"""
        for ant in unit_plan.antagonists:
            if ant.appearance_chapter <= chapter_index <= ant.defeat_chapter:
                return {
                    "name": ant.name,
                    "level": ant.level,
                    "motivation": ant.motivation,
                    "power_level": ant.power_level,
                }
        return None
    
    def get_unit_plan(self, unit_number: int) -> Optional[StoryUnitPlan]:
        """Get a specific unit plan"""
        return self._unit_plans.get(unit_number)
    
    def get_all_unit_plans(self) -> Dict[int, StoryUnitPlan]:
        """Get all unit plans"""
        return self._unit_plans.copy()
    
    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize plugin and persist data"""
        logger.info(f"StoryUnitPlugin finalized - persisting {len(self._unit_plans)} unit plans")
        
        # Serialize plans for storage
        plans_data = {}
        for unit_num, plan in self._unit_plans.items():
            plans_data[unit_num] = self._serialize_unit_plan(plan)
        
        await self.persist_all(context, {
            "unit_plans": plans_data,
        })
        
        context.metadata["story_units"] = plans_data
    
    def _serialize_unit_plan(self, plan: StoryUnitPlan) -> Dict[str, Any]:
        """Serialize unit plan to dictionary"""
        return {
            "unit_number": plan.unit_number,
            "title": plan.title,
            "chapter_start": plan.chapter_start,
            "chapter_end": plan.chapter_end,
            "world_level": plan.world_level,
            "power_level_start": plan.power_level_start,
            "power_level_end": plan.power_level_end,
            "act1_chapters": plan.act1_chapters,
            "act2_chapters": plan.act2_chapters,
            "act3_chapters": plan.act3_chapters,
            "act1_plot": plan.act1_plot,
            "act2_plot": plan.act2_plot,
            "act3_plot": plan.act3_plot,
            "antagonists": [self._serialize_antagonist(a) for a in plan.antagonists],
            "key_events": [self._serialize_event(e) for e in plan.key_events],
            "foreshadows": [self._serialize_foreshadow(f) for f in plan.unit_foreshadows],
        }
    
    def _deserialize_unit_plan(self, data: Dict[str, Any]) -> StoryUnitPlan:
        """Deserialize unit plan from dictionary"""
        plan = StoryUnitPlan(
            unit_number=data.get("unit_number", 1),
            title=data.get("title", ""),
            chapter_start=data.get("chapter_start", 1),
            chapter_end=data.get("chapter_end", 100),
            world_level=data.get("world_level", ""),
            power_level_start=data.get("power_level_start", ""),
            power_level_end=data.get("power_level_end", ""),
            act1_chapters=data.get("act1_chapters", []),
            act2_chapters=data.get("act2_chapters", []),
            act3_chapters=data.get("act3_chapters", []),
            act1_plot=data.get("act1_plot", {}),
            act2_plot=data.get("act2_plot", {}),
            act3_plot=data.get("act3_plot", {}),
        )
        
        for ant_data in data.get("antagonists", []):
            plan.antagonists.append(UnitAntagonist(**ant_data))
        for evt_data in data.get("key_events", []):
            plan.key_events.append(UnitEvent(**evt_data))
        for fs_data in data.get("foreshadows", []):
            plan.unit_foreshadows.append(UnitForeshadow(**fs_data))
        
        return plan
    
    def _serialize_antagonist(self, ant: UnitAntagonist) -> Dict[str, Any]:
        return {
            "name": ant.name,
            "level": ant.level,
            "appearance_chapter": ant.appearance_chapter,
            "defeat_chapter": ant.defeat_chapter,
            "motivation": ant.motivation,
            "power_level": ant.power_level,
            "relationship_to_protagonist": ant.relationship_to_protagonist,
        }
    
    def _serialize_event(self, evt: UnitEvent) -> Dict[str, Any]:
        return {
            "name": evt.name,
            "chapter": evt.chapter,
            "description": evt.description,
            "involved_characters": evt.involved_characters,
            "outcome": evt.outcome,
            "importance": evt.importance,
        }
    
    def _serialize_foreshadow(self, fs: UnitForeshadow) -> Dict[str, Any]:
        return {
            "name": fs.name,
            "plant_chapter": fs.plant_chapter,
            "payoff_chapter": fs.payoff_chapter,
            "payoff_unit": fs.payoff_unit,
            "description": fs.description,
            "importance": fs.importance,
        }
