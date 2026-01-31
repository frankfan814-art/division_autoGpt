"""
Growth Plugin - Manages character cultivation progression and breakthroughs

This plugin handles:
- Cultivation realm progression
- Breakthrough conditions and events
- Technique upgrade paths
- Key awakening moments
- Power level tracking
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
    ValidationResult,
    WritingContext,
)


class GrowthPlugin(NovelElementPlugin):
    """
    Plugin for managing character cultivation growth and progression

    Tracks realm progression, breakthroughs, and power development.
    """

    name = "growth"
    version = "1.0.0"
    description = "Manages character cultivation progression and breakthroughs"
    author = "Creative AutoGPT"

    _growth_paths: Dict[str, Dict[str, Any]] = {}
    _breakthroughs: Dict[str, List[Dict[str, Any]]] = {}
    _technique_levels: Dict[str, Dict[str, Any]] = {}
    _awakening_moments: List[Dict[str, Any]] = []
    _power_levels: Dict[str, float] = {}

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._growth_paths = {}
        self._breakthroughs = {}
        self._technique_levels = {}
        self._awakening_moments = []
        self._power_levels = {}

    async def on_init(self, context: WritingContext) -> None:
        """Initialize growth plugin with session context"""
        logger.info(f"GrowthPlugin initialized for session {context.session_id}")

        state = await self.load_state(context)
        if state:
            self._growth_paths = state.get("growth_paths", {})
            self._breakthroughs = state.get("breakthroughs", {})
            self._technique_levels = state.get("technique_levels", {})
            self._awakening_moments = state.get("awakening_moments", [])
            self._power_levels = state.get("power_levels", {})
            logger.info(f"Loaded growth data from database")
        else:
            if "growth_paths" in context.metadata:
                self._growth_paths = context.metadata.get("growth_paths", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for growth data"""
        return {
            "type": "object",
            "title": "Growth Schema",
            "description": "Schema for character growth paths",
            "properties": {
                "character_id": {"type": "string"},
                "current_realm": {"type": "string", "description": "Current cultivation realm"},
                "target_realm": {"type": "string", "description": "Next target realm"},
                "realms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "level": {"type": "integer"},
                            "description": {"type": "string"},
                            "breakthrough_condition": {"type": "string"},
                            "breakthrough_chapter": {"type": "integer"}
                        }
                    }
                },
                "technique_upgrades": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "technique_name": {"type": "string"},
                            "current_level": {"type": "integer"},
                            "upgrade_requirements": {"type": "string"},
                            "upgrade_chapter": {"type": "integer"}
                        }
                    }
                },
                "awakening_moments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "moment_name": {"type": "string"},
                            "chapter": {"type": "integer"},
                            "description": {"type": "string"},
                            "power_boost": {"type": "number"}
                        }
                    }
                }
            }
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for growth-related tasks"""
        return {
            "growth_path_design": """## 任务: 规划主角成长路径

### 世界观力量体系
{power_system}

### 主角设定
{character}

### 成长路径设计要求

请为主角设计完整的成长路径，融入哲学思想指导修炼:

**1. 境界划分** (炼气→筑基→金丹→元婴→化神→渡劫→大乘):
   - 每个境界的名称和等级
   - 每个境界的能力描述 (不仅是力量，更重心境)
   - **突破条件** (重点):
     * **心境修为**: 需要领悟什么道理才能突破？
     * **哲学领悟**: 如"炼气期"重"积累"，"筑基期"重"根基"，"金丹期"重"凝练"
     * **德位相配**: 修为提升需与心性修养同步 (避免"德不配位")
   - 突破章节规划
   - **境界哲学内涵**: 每个境界对应什么哲学思想？
     * 例如：炼气期 - "千里之行，始于足下"(积累)
     * 例如：元婴期 - "返璞归真"(回归本源)

**2. 功法升级路径**:
   - 主角核心功法的等级提升
   - 每个等级的能力变化
   - **功法哲学原理** (重点):
     * 功法基于什么哲学思想？ (阴阳五行、天人合一、无为而治)
     * 功法名称体现什么哲学概念？
   - 升级需要的条件
   - 章节规划

**3. 顿悟时刻** (3-5个关键顿悟，重点):
   - **顿悟发生章节**
   - **顿悟触发条件**:
     * 经历什么事情触发顿悟？(如失败后的反思、生死之间的领悟)
     * 符合"穷则思变""物极必反"等哲学规律
   - **顿悟内容** (哲学内涵):
     * 主角领悟了什么道理？
     * 引用什么经典？(如"祸兮福所倚，福兮祸所伏")
     * 体现什么哲学思想？(如"以柔克刚""知行合一")
   - **顿悟效果**:
     * 实力提升: 境界突破或功法升级
     * 心境变化: 心性修养提升 (如从"急功近利"到"淡定从容")
     * 价值观升华: 对人生、世界的新理解
   - **对后续发展的影响**:
     * 改变主角的行为方式
     * 影响后续决策

**4. 实力曲线**:
   - 每个章节/阶段的实力水平
   - **实力提升的节奏**:
     * 体现"厚积薄发"(前期积累，后期爆发)
     * 体现"欲速则不达"(过快提升导致根基不稳)
   - 与反派实力的对比

**5. 心性成长路线** (新增):
   - **初始心态**: 主角最初的价值观和心态
   - **成长节点**: 
     * 遇到挫折后学会"坚韧"
     * 获得力量后学会"谦逊"
     * 面对诱惑时坚守"本心"
   - **最终境界**:
     * "内圣外王": 既有强大实力，又有高尚品德
     * "知行合一": 理论与实践完美统一
     * "天人合一": 与天道和谐共处

请以 JSON 格式输出，重点突出哲学思想在修炼中的作用。
""",
            "breakthrough_scene": """## 任务: 描写突破场景

### 当前境界
- 境界名称: {current_realm}
- 实力积累: {accumulation}

### 突破目标
- 目标境界: {target_realm}
- 突破条件: {condition}

### 突破场景要求

请描写一次重要的境界突破场景，不仅是力量提升，更是**悟道**时刻:

**核心要求：境界突破 = 力量提升 + 心性升华**

1. **突破前兆** (内心/环境的变化):
   - **心境变化**: 主角对当前境界有什么感悟？
   - **哲学领悟**: 主角领悟了什么道理？(如"水满则溢，月满则亏")
   - **环境呼应**: 天地异象呼应主角心境 (体现"天人合一")

2. **突破过程** (危机、困难、应对):
   - **内在危机**: 心魔、执念、欲望的考验
   - **哲学挣扎**: 主角在突破中思考什么人生哲理？
   - **应对智慧**: 主角如何运用哲学智慧化解危机？(如"以柔克刚""放下执念")
   - **引用经典**: 主角在突破时心中默念什么经典语句？

3. **突破瞬间** (实力质变 + 悟道):
   - **力量爆发**: 描写能量涌动、天地变色
   - **悟道瞬间**: 主角顿悟了什么道理？
     * 如"一朝悟道，立地成仙"
     * 如"原来如此，道就在日常生活中"
   - **哲学升华**: 主角对世界、人生的新理解
   - **境界提升**: 不仅是实力，更是心境境界的提升

4. **突破后状态** (实力变化/心境变化):
   - **实力变化**: 新境界的能力
   - **心境变化**: 
     * 从"急躁"到"从容"
     * 从"执念"到"放下"
     * 从"小我"到"大我"
   - **价值观升华**: 主角对人生目标的新认识
   - **引用感悟**: 主角突破后的感悟 (如"天道酬勤""厚德载物")

**写作要点：**
- 不要只写力量升级，要写心性升华
- 融入哲学思想和经典引用
- 体现"内圣外王"的理念 (内在修养与外在实力同步提升)
- 突破场景要有"悟道"的神圣感

请直接输出场景内容，1000-2000字。
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for growth-related operations"""
        return [
            {
                "task_id": "growth_path",
                "task_type": "主角成长",
                "description": "Plan character cultivation progression, realm breakthroughs, technique upgrades, and key awakening moments",
                "depends_on": ["大纲", "世界观规则", "功法法宝", "人物设计"],
                "metadata": {"plugin": "growth", "operation": "design"}
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate growth data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(valid=False, errors=["Growth data must be a dictionary"])

        if "realms" not in data:
            errors.append("Missing realm progression data")
        else:
            realms = data["realms"]
            if len(realms) < 3:
                suggestions.append("Consider adding more cultivation realms for depth")

        if "awakening_moments" in data:
            moments = data["awakening_moments"]
            if len(moments) < 2:
                suggestions.append("Consider adding more awakening moments for dramatic effect")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, suggestions=suggestions)

    async def on_after_task(
        self,
        task: Dict[str, Any],
        result: str,
        context: WritingContext,
    ) -> str:
        """Extract and store growth data from task results"""
        if task.get("task_type") == "主角成长":
            await self._extract_growth_data(result, context)
        return result

    async def _extract_growth_data(self, result: str, context: WritingContext) -> None:
        """Extract growth path data from result"""
        import json
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:result.rfind("}") + 1]
                data = json.loads(json_str)

                if "growth_path" in data:
                    self._growth_paths["main"] = data["growth_path"]
                if "breakthroughs" in data:
                    self._breakthroughs["main"] = data["breakthroughs"]
                if "awakening_moments" in data:
                    self._awakening_moments = data["awakening_moments"]

                logger.info(f"Extracted growth data: {len(self._growth_paths)} paths, {len(self._awakening_moments)} awakenings")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse growth data as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting growth data: {e}")

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with growth information"""
        task_type = task.get("task_type", "")
        chapter_index = task.get("metadata", {}).get("chapter_index")

        if "章节" in task_type and chapter_index is not None:
            if self._growth_paths:
                context["growth_path"] = self._growth_paths.get("main", {})

            current_realm = self._get_realm_for_chapter(chapter_index)
            if current_realm:
                context["current_realm"] = current_realm

            techniques_at_level = self._get_techniques_for_chapter(chapter_index)
            if techniques_at_level:
                context["technique_levels"] = techniques_at_level

            awakening = self._get_awakening_for_chapter(chapter_index)
            if awakening:
                context["chapter_awakening"] = awakening

        return context

    def _get_realm_for_chapter(self, chapter_index: int) -> Optional[Dict[str, Any]]:
        """Get the cultivation realm for a specific chapter"""
        if "main" not in self._growth_paths:
            return None

        growth = self._growth_paths["main"]
        realms = growth.get("realms", [])

        for realm in realms:
            breakthrough_chapter = realm.get("breakthrough_chapter")
            if breakthrough_chapter and chapter_index >= breakthrough_chapter:
                return realm
            elif breakthrough_chapter is None:
                return realm

        return realms[0] if realms else None

    def _get_techniques_for_chapter(self, chapter_index: int) -> List[Dict[str, Any]]:
        """Get techniques that should be upgraded by this chapter"""
        if "main" not in self._growth_paths:
            return []

        growth = self._growth_paths["main"]
        upgrades = growth.get("technique_upgrades", [])

        return [
            u for u in upgrades
            if u.get("upgrade_chapter", 999) <= chapter_index
        ]

    def _get_awakening_for_chapter(self, chapter_index: int) -> Optional[Dict[str, Any]]:
        """Get awakening moment for a specific chapter"""
        for moment in self._awakening_moments:
            if moment.get("chapter") == chapter_index:
                return moment
        return None

    def get_growth_path(self, character_id: str = "main") -> Optional[Dict[str, Any]]:
        """Get growth path for a character"""
        return self._growth_paths.get(character_id)

    def get_current_realm(self, character_id: str = "main") -> Optional[str]:
        """Get current cultivation realm for a character"""
        path = self._growth_paths.get(character_id)
        if path:
            return path.get("current_realm")
        return None

    def get_breakthrough_schedule(self, character_id: str = "main") -> List[Dict[str, Any]]:
        """Get all breakthroughs for a character"""
        return self._breakthroughs.get(character_id, [])

    def get_power_level(self, character_id: str = "main") -> float:
        """Get current power level for a character"""
        return self._power_levels.get(character_id, 0.0)

    def set_power_level(self, character_id: str, level: float) -> None:
        """Set power level for a character"""
        self._power_levels[character_id] = level

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize growth plugin and persist data"""
        logger.info(f"GrowthPlugin finalized - persisting growth data")

        await self.persist_all(context, {
            "growth_paths": self._growth_paths,
            "breakthroughs": self._breakthroughs,
            "technique_levels": self._technique_levels,
            "awakening_moments": self._awakening_moments,
            "power_levels": self._power_levels,
        })

        context.metadata["growth_paths"] = self._growth_paths
        context.metadata["awakening_moments"] = self._awakening_moments
