"""
WorldView Plugin - Manages world-building settings, rules, and lore

This plugin handles:
- World setting definitions (geography, history, society)
- Power/magic systems with consistent rules
- Faction and organization definitions
- Location and place descriptions
- World lore and background information
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
    ValidationResult,
    WritingContext,
)


class WorldViewPlugin(NovelElementPlugin):
    """
    Plugin for managing novel worldview and settings

    Tracks world-building elements including magic systems, geography,
    social structures, factions, and lore.
    """

    name = "worldview"
    version = "1.0.0"
    description = "Manages world-building settings and lore"
    author = "Creative AutoGPT"

    # World state storage
    _world_settings: Dict[str, Any] = {}
    _power_systems: Dict[str, Dict[str, Any]] = {}
    _factions: Dict[str, Dict[str, Any]] = {}
    _locations: Dict[str, Dict[str, Any]] = {}
    _lore: List[Dict[str, Any]] = []

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._world_settings = {}
        self._power_systems = {}
        self._factions = {}
        self._locations = {}
        self._lore = []

    async def on_init(self, context: WritingContext) -> None:
        """Initialize worldview plugin with session context"""
        logger.info(f"WorldViewPlugin initialized for session {context.session_id}")

        # Try to load from database first
        state = await self.load_state(context)
        if state:
            self._world_settings = state.get("world_settings", {})
            self._power_systems = state.get("power_systems", {})
            self._factions = state.get("factions", {})
            self._locations = state.get("locations", {})
            self._lore = state.get("lore", [])
            logger.info(f"Loaded worldview data from database")
        else:
            # Fallback to metadata
            if "world_settings" in context.metadata:
                self._world_settings = context.metadata.get("world_settings", {})
            if "power_systems" in context.metadata:
                self._power_systems = context.metadata.get("power_systems", {})
            if "factions" in context.metadata:
                self._factions = context.metadata.get("factions", {})
            if "locations" in context.metadata:
                self._locations = context.metadata.get("locations", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for worldview data"""
        return {
            "type": "object",
            "title": "WorldView Schema",
            "description": "Schema for novel world-building settings",
            "properties": {
                "world_type": {
                    "type": "string",
                    "enum": ["realistic", "fantasy", "scifi", "urban_fantasy", "historical", "post_apocalyptic"],
                    "description": "Type of world setting"
                },
                "time_period": {
                    "type": "string",
                    "description": "Time period of the story"
                },
                "geography": {
                    "type": "object",
                    "properties": {
                        "continents": {"type": "array", "items": {"type": "string"}},
                        "climate": {"type": "string"},
                        "major_features": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Mountains, rivers, forests, etc."
                        }
                    }
                },
                "cosmology": {
                    "type": "object",
                    "properties": {
                        "universe_structure": {"type": "string"},
                        "planes": {"type": "array", "items": {"type": "string"}},
                        "celestial_bodies": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "history": {
                    "type": "object",
                    "properties": {
                        "ancient_events": {"type": "array", "items": {"type": "string"}},
                        "recent_history": {"type": "string"},
                        "calendar_system": {"type": "string"}
                    }
                },
                "society": {
                    "type": "object",
                    "properties": {
                        "political_system": {"type": "string"},
                        "economic_system": {"type": "string"},
                        "social_hierarchy": {"type": "array", "items": {"type": "string"}},
                        "laws": {"type": "array", "items": {"type": "string"}},
                        "customs": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "technology_level": {
                    "type": "string",
                    "enum": ["primitive", "pre_industrial", "industrial", "modern", "advanced", "futuristic"]
                },
                "power_system": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "source": {"type": "string"},
                        "ranks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "level": {"type": "string"},
                                    "description": {"type": "string"},
                                    "capabilities": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        },
                        "limitations": {"type": "array", "items": {"type": "string"}},
                        "costs": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for worldview-related tasks"""
        return {
            "worldview_creation": """## 任务: 构建世界观设定

### 小说类型
{genre}

### 故事大纲
{outline}

### 世界观构建要求

请为小说创建完整的世界观设定:

**1. 基础设定:**
- 世界类型: (现实/架空/奇幻/科幻/都市奇幻/历史/后末日)
- 时代背景: (具体的历史时期或虚构时代)
- 地理环境:
  - 大陆/国家分布
  - 气候特征
  - 重要地理特征 (山脉、河流、森林、海洋等)
  - 特殊地貌 (如适用)

**2. 宇宙观/位面设定** (如适用):
- 世界结构
- 位面/界域划分
- 天体系统
- 特殊空间 (异空间、秘境等)

**3. 历史背景:**
- 远古重大事件
- 近代历史脉络
- 重要历史转折点
- 纪元/历法系统
- 传说与神话

**4. 社会结构:**
- 政治体系: (君主制/民主制/贵族制/联邦制/无政府等)
- 经济体系: (封建/资本主义/计划经济/物物交换等)
- 社会阶层: 阶级划分和晋升机制
- 法律制度: 主要法律和禁忌
- 文化习俗: 风俗、礼仪、节日等
- 宗教信仰: 主要宗教或信仰体系

**5. 科技水平:**
- 科技等级: (原始/前工业/工业/现代/先进/未来)
- 重要技术/发明
- 科技的社会影响

**6. 力量体系** (如适用):
- 能量来源
- 等级划分:
  - 每个等级的名称
  - 每个等级的能力描述
  - 突破条件
- 修炼/成长方法
- 力量限制和代价
- 特殊能力分类
- 宝物/法器设定

**7. 特殊设定:**
- 独特的世界规则
- 异种/种族设定 (如适用)
- 势力分布
- 重要地点详情

请以结构化的 JSON 格式输出，确保世界观设定逻辑自洽、细节丰富。
""",

            "faction_design": """## 任务: 设计势力组织

### 世界观背景
{worldview}

### 势力设计要求

请为小说设计主要势力/组织:

**每个势力包含:**
1. **基本信息:**
   - 势力名称
   - 势力类型 (门派/家族/国家/组织/公司/其他)
   - 势力规模

2. **核心理念:**
   - 宗旨/目标
   - 价值观
   - 信条

3. **组织架构:**
   - 领导层
   - 分支结构
   - 人员构成

4. **实力设定:**
   - 核心能力
   - 独特资源
   - 领地范围
   - 经济基础

5. **对外关系:**
   - 盟友势力
   - 敌对势力
   - 中立势力

6. **特色元素:**
   - 独特功法/技术
   - 标志性物品
   - 特殊传统

请设计 3-5 个主要势力，确保势力间有合理的制衡关系。

以 JSON 格式输出。
""",

            "location_detail": """## 任务: 设计详细地点

### 世界观背景
{worldview}

### 地点设计要求

请为故事中的重要地点创建详细设定:

**地点分类:**
1. **城市/聚落:**
   - 地理位置
   - 规模和人口
   - 建筑风格
   - 功能分区
   - 经济特色
   - 文化氛围

2. **自然景观:**
   - 地理特征
   - 气候条件
   - 生态特色
   - 特殊现象

3. **特殊地点:**
   - 秘境/禁地
   - 遗迹/废墟
   - 神圣之地
   - 危险区域

**每个地点包含:**
- 地点名称
- 地理位置
- 环境描述 (200-300字)
- 特色/秘密
- 相关势力
- 剧情作用

请设计 5-10 个重要地点。

以 JSON 格式输出。
""",

            "worldview_consistency_check": """## 任务: 检查世界观一致性

### 世界观设定
{worldview_rules}

### 检查内容
{content_to_check}

### 检查维度

1. **规则一致性**: 是否遵守设定的世界规则
2. **地理一致性**: 地点和距离是否合理
3. **科技/力量一致性**: 能力水平是否符合设定
4. **社会一致性**: 社会结构和行为是否符合设定
5. **时间一致性**: 时间线是否连贯

### 输出要求

请输出 JSON 格式的检查结果:
```json
{{
  "is_consistent": true/false,
  "issues": ["具体的不一致问题"],
  "suggestions": ["修改建议"],
  "world_elements_used": ["使用到的世界观元素"]
}}
```
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for worldview-related operations"""
        return [
            {
                "task_id": "worldview_rules",
                "task_type": "世界观规则",
                "description": "Create complete worldview settings and rules",
                "depends_on": ["大纲"],
                "metadata": {
                    "plugin": "worldview",
                    "operation": "create"
                }
            },
            {
                "task_id": "faction_design",
                "task_type": "势力设计",
                "description": "Design major factions and organizations (cults, clans, families). Each faction includes: beliefs, goals, power systems, personnel structure, territory, relationships",
                "depends_on": ["大纲", "世界观规则"],
                "metadata": {
                    "plugin": "worldview",
                    "operation": "factions"
                }
            },
            {
                "task_id": "location_design",
                "task_type": "场景设计",
                "description": "Design detailed locations and places (secret realms, forbidden areas, ruins, caves, cities). Each location includes: geographic position, environment description, unique features/secrets, related factions, plot role",
                "depends_on": ["大纲", "世界观规则", "势力设计"],
                "metadata": {
                    "plugin": "worldview",
                    "operation": "locations"
                }
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate worldview data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Worldview data must be a dictionary"]
            )

        # Check for world type
        if "world_type" not in data:
            warnings.append("World type not specified")
            suggestions.append("Define the type of world setting")

        # Check for internal consistency
        if data.get("world_type") == "fantasy":
            if "power_system" not in data:
                warnings.append("Fantasy world missing power/magic system")
                suggestions.append("Define magic/power system for fantasy setting")

        if data.get("world_type") == "scifi":
            if "technology_level" not in data:
                warnings.append("Sci-fi world missing technology level specification")

        # Check geography if locations exist
        if "locations" in data and "geography" not in data:
            suggestions.append("Add geography details for location context")

        # Check social structure consistency
        if "society" in data:
            society = data["society"]
            if "political_system" not in society:
                suggestions.append("Define political system for clearer social structure")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    async def on_after_task(
        self,
        task: Dict[str, Any],
        result: str,
        context: WritingContext,
    ) -> str:
        """Extract and store worldview data from task results"""
        task_type = task.get("task_type", "")

        if task_type == "世界观规则":
            await self._extract_worldview(result, context)
        elif task_type == "势力设计":
            await self._extract_factions(result, context)
        elif task_type == "场景设计":
            await self._extract_locations(result, context)

        return result

    async def _extract_worldview(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract worldview settings from result"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                self._world_settings = data

                # Extract power system if present
                if "power_system" in data:
                    self._power_systems["main"] = data["power_system"]

                logger.info("Extracted worldview settings")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse worldview data as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting worldview: {e}")

    async def _extract_factions(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract faction data from result"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                if isinstance(data, dict) and "factions" in data:
                    for faction_id, faction_data in data["factions"].items():
                        if isinstance(faction_data, dict):
                            self._factions[faction_id] = faction_data

                logger.info(f"Extracted {len(self._factions)} faction definitions")

        except Exception as e:
            logger.error(f"Error extracting factions: {e}")

    async def _extract_locations(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract location data from result"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                if isinstance(data, dict) and "locations" in data:
                    for loc_id, loc_data in data["locations"].items():
                        if isinstance(loc_data, dict):
                            self._locations[loc_id] = loc_data

                logger.info(f"Extracted {len(self._locations)} location definitions")

        except Exception as e:
            logger.error(f"Error extracting locations: {e}")

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with worldview information"""
        task_type = task.get("task_type", "")

        # Add world settings summary
        if self._world_settings:
            context["worldview"] = {
                "type": self._world_settings.get("world_type"),
                "time_period": self._world_settings.get("time_period"),
                "technology_level": self._world_settings.get("technology_level"),
            }

            # Add power system info if available
            if "power_system" in self._world_settings:
                context["power_system"] = self._world_settings["power_system"]

        # Add factions for relevant tasks
        if "章节" in task_type or "情节" in task_type:
            if self._factions:
                context["factions"] = list(self._factions.keys())

        # Add locations for scene generation
        if "场景" in task_type or "章节" in task_type:
            if self._locations:
                context["available_locations"] = [
                    {"id": k, "name": v.get("name", k)}
                    for k, v in self._locations.items()
                ]

        return context

    def get_world_settings(self) -> Dict[str, Any]:
        """Get all world settings"""
        return self._world_settings.copy()

    def get_power_systems(self) -> Dict[str, Dict[str, Any]]:
        """Get all power systems"""
        return self._power_systems.copy()

    def get_factions(self) -> Dict[str, Dict[str, Any]]:
        """Get all factions"""
        return self._factions.copy()

    def get_locations(self) -> Dict[str, Dict[str, Any]]:
        """Get all locations"""
        return self._locations.copy()

    def get_location(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific location by ID"""
        return self._locations.get(location_id)

    def add_lore(self, lore_entry: Dict[str, Any]) -> None:
        """Add a lore entry"""
        lore_entry["added_at"] = datetime.utcnow().isoformat()
        self._lore.append(lore_entry)

    def get_lore(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get lore entries, optionally filtered by category"""
        if category:
            return [entry for entry in self._lore if entry.get("category") == category]
        return self._lore.copy()

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize worldview plugin and persist data"""
        logger.info(f"WorldViewPlugin finalized - persisting {len(self._factions)} factions")

        # Persist to database
        await self.persist_all(context, {
            "world_settings": self._world_settings,
            "power_systems": self._power_systems,
            "factions": self._factions,
            "locations": self._locations,
            "lore": self._lore,
        })

        # Also store in metadata for compatibility
        context.metadata["world_settings"] = self._world_settings
        context.metadata["power_systems"] = self._power_systems
        context.metadata["factions"] = self._factions
        context.metadata["locations"] = self._locations
        context.metadata["world_lore"] = self._lore
