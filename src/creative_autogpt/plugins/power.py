"""
Power Plugin - Manages cultivation systems, techniques, and treasures

This plugin handles:
- Power/cultivation system definitions
- Technique hierarchies and upgrades
- Magical treasures and artifacts
- Power progression tracking
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


class PowerPlugin(NovelElementPlugin):
    """
    Plugin for managing power systems, techniques, and treasures

    Tracks cultivation realms, technique hierarchies, and magical items.
    """

    name = "power"
    version = "1.0.0"
    description = "Manages cultivation systems, techniques, and treasures"
    author = "Creative AutoGPT"

    _power_systems: Dict[str, Dict[str, Any]] = {}
    _techniques: Dict[str, Dict[str, Any]] = {}
    _treasures: Dict[str, Dict[str, Any]] = {}
    _technique_upgrades: Dict[str, List[Dict[str, Any]]] = {}

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._power_systems = {}
        self._techniques = {}
        self._treasures = {}
        self._technique_upgrades = {}

    async def on_init(self, context: WritingContext) -> None:
        """Initialize power plugin with session context"""
        logger.info(f"PowerPlugin initialized for session {context.session_id}")

        state = await self.load_state(context)
        if state:
            self._power_systems = state.get("power_systems", {})
            self._techniques = state.get("techniques", {})
            self._treasures = state.get("treasures", {})
            self._technique_upgrades = state.get("technique_upgrades", {})
            logger.info(f"Loaded power data from database")
        else:
            if "power_systems" in context.metadata:
                self._power_systems = context.metadata.get("power_systems", {})
            if "techniques" in context.metadata:
                self._techniques = context.metadata.get("techniques", {})
            if "treasures" in context.metadata:
                self._treasures = context.metadata.get("treasures", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for power data"""
        return {
            "type": "object",
            "title": "Power Schema",
            "description": "Schema for power systems",
            "properties": {
                "system_id": {"type": "string"},
                "name": {"type": "string", "description": "System name"},
                "source": {"type": "string", "description": "Power source description"},
                "realms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "level": {"type": "integer"},
                            "description": {"type": "string"},
                            "capabilities": {"type": "array", "items": {"type": "string"}},
                            "limitations": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "technique_categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Categories: attack, defense, healing, etc."
                }
            }
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for power-related tasks"""
        return {
            "power_system_design": """## 任务: 设计力量体系

### 世界观背景
{worldview}

### 力量体系设计要求

请为小说设计完整的力量体系:

**1. 能量来源**:
   - 力量的本质是什么
   - 如何获取和修炼
   - 有什么限制和代价

**2. 境界划分** (至少5-7个境界):
   - 每个境界的名称
   - 每个境界的具体能力描述
   - 突破条件和要求
   - 寿命影响（如适用）

**3. 功法体系**:
   - 功法等级划分（天、地、玄、黄或类似）
   - 每种等级的代表功法
   - 功法的修炼难度和效果

**4. 战斗技能**:
   - 攻击类技能
   - 防御类技能
   - 身法/速度类
   - 特殊/辅助类

**5. 限制设定**:
   - 战斗消耗
   - 使用限制
   - 反噬风险

请以 JSON 格式输出。
""",
            "treasure_design": """## 任务: 设计功法法宝

### 力量体系
{power_system}

### 法宝设计要求

请设计核心功法与法宝:

**功法设计** (核心功法3-5种):
- 功法名称
- 等级 (天/地/玄/黄)
- 修炼条件
- 核心效果
- 修炼风险
- 与主角的关系

**法宝设计** (核心法宝3-5件):
- 法宝名称
- 等级/品阶
- 来历（如何获得）
- 核心能力
- 器灵描述（如有）
- 限制条件

请以 JSON 格式输出。
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for power-related operations"""
        return [
            {
                "task_id": "power_system",
                "task_type": "功法法宝",
                "description": "Design power/cultivation system, techniques, and treasures",
                "depends_on": ["大纲", "世界观规则", "势力设计"],
                "metadata": {"plugin": "power", "operation": "design"}
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate power data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(valid=False, errors=["Power data must be a dictionary"])

        if "name" not in data:
            errors.append("Missing power system name")
        if "realms" not in data:
            warnings.append("No realm definitions found")
        else:
            realms = data["realms"]
            if len(realms) < 3:
                suggestions.append("Consider adding more cultivation realms for depth")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, suggestions=suggestions)

    async def on_after_task(
        self,
        task: Dict[str, Any],
        result: str,
        context: WritingContext,
    ) -> str:
        """Extract and store power data from task results"""
        if task.get("task_type") == "功法法宝":
            await self._extract_power_data(result, context)
        return result

    async def _extract_power_data(self, result: str, context: WritingContext) -> None:
        """Extract power system data from result"""
        import json
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                if "power_system" in data:
                    self._power_systems["main"] = data["power_system"]
                if "techniques" in data:
                    for tech_id, tech_data in data["techniques"].items():
                        self._techniques[tech_id] = tech_data
                if "treasures" in data:
                    for item_id, item_data in data["treasures"].items():
                        self._treasures[item_id] = item_data

                logger.info(f"Extracted power data: {len(self._power_systems)} systems, {len(self._techniques)} techniques")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse power data as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting power data: {e}")

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with power system information"""
        task_type = task.get("task_type", "")

        if "章节" in task_type:
            if self._power_systems:
                context["power_system"] = self._power_systems.get("main", {})
            if self._techniques:
                context["techniques"] = list(self._techniques.values())
            if self._treasures:
                context["treasures"] = list(self._treasures.values())

        return context

    def get_power_system(self, system_id: str = "main") -> Optional[Dict[str, Any]]:
        """Get a power system by ID"""
        return self._power_systems.get(system_id)

    def get_technique(self, technique_id: str) -> Optional[Dict[str, Any]]:
        """Get a technique by ID"""
        return self._techniques.get(technique_id)

    def get_treasure(self, treasure_id: str) -> Optional[Dict[str, Any]]:
        """Get a treasure by ID"""
        return self._treasures.get(treasure_id)

    def get_all_techniques(self) -> Dict[str, Dict[str, Any]]:
        """Get all techniques"""
        return self._techniques.copy()

    def get_all_treasures(self) -> Dict[str, Dict[str, Any]]:
        """Get all treasures"""
        return self._treasures.copy()

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize power plugin and persist data"""
        logger.info(f"PowerPlugin finalized - persisting {len(self._techniques)} techniques")

        await self.persist_all(context, {
            "power_systems": self._power_systems,
            "techniques": self._techniques,
            "treasures": self._treasures,
            "technique_upgrades": self._technique_upgrades,
        })

        context.metadata["power_systems"] = self._power_systems
        context.metadata["techniques"] = self._techniques
        context.metadata["treasures"] = self._treasures
