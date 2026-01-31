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

请为小说设计完整的力量体系，融入中国传统哲学思想:

**1. 能量来源** (体现哲学思想):
   - **力量的本质**:
     * 道家: "气"源于天地自然，顺应"道"而生
     * 儒家: "德"化为力量，厚德载物
     * 阴阳五行: 金木水火土五行相生相克
   - **如何获取和修炼**:
     * "天人合一": 吸收天地灵气
     * "知行合一": 理论领悟与实践结合
     * "日积月累": 遵循"千里之行，始于足下"
   - **有什么限制和代价**:
     * "德不配位": 修为需与心性匹配
     * "物极必反": 过度追求力量导致反噬
     * "因果循环": 滥用力量必遭天谴

**2. 境界划分** (至少5-7个境界，融入哲学内涵):
   - **每个境界的名称**: 可引用经典概念
     * 如"炼气"(积少成多)、"筑基"(根基扎实)
     * 如"金丹"(凝练精华)、"元婴"(返璞归真)
   - **每个境界的具体能力描述**
   - **突破条件和要求** (哲学内涵):
     * 不仅需力量积累，更需"悟道"
     * 体现"厚积薄发""水到渠成"
     * 每个境界对应一种哲学领悟
   - **寿命影响**（如适用）
   - **境界哲学映射**:
     * 炼气期 → "积跬步以至千里"
     * 筑基期 → "千里之行，始于足下"
     * 金丹期 → "凝练精华，去芜存菁"
     * 元婴期 → "返璞归真，回归本源"
     * 化神期 → "天人合一，与道合真"

**3. 功法体系** (基于阴阳五行):
   - **功法等级划分**（天、地、玄、黄或类似）
   - **功法哲学分类**:
     * **道家功法**: 顺应自然，无为而治，以柔克刚
     * **儒家功法**: 以德为本，仁义化形，正气凛然
     * **阴阳功法**: 阴阳相生，刚柔并济，平衡之道
     * **五行功法**: 金木水火土，相生相克，循环不息
   - **每种等级的代表功法**
   - **功法的修炼难度和效果**
   - **功法命名**: 可引用经典 (如"上善若水诀""仁者无敌功")

**4. 战斗技能** (体现哲学思想):
   - **攻击类技能**:
     * "以柔克刚": 柔弱胜刚强
     * "四两拨千斤": 借力打力
   - **防御类技能**:
     * "上善若水": 水善利万物而不争
     * "厚德载物": 包容万物
   - **身法/速度类**:
     * "无为而治": 顺应自然，不刻意追求
     * "风行水上": 自然而然
   - **特殊/辅助类**:
     * "格物致知": 洞察万物本质
     * "知行合一": 理论与实践统一

**5. 限制设定** (体现天道平衡):
   - **战斗消耗**: 体现"损益平衡"
   - **使用限制**: 体现"物极必反"
   - **反噬风险**: 
     * "逆天而行"必遭天谴
     * "德不配位"必受反噬
     * "因果报应"循环不爽

**6. 功法与心境关系** (重点):
   - **功法修炼需匹配心境**:
     * 低级功法: 重"技"，可单纯积累
     * 中级功法: 重"法"，需领悟原理
     * 高级功法: 重"道"，需心境圆满
   - **心境不足强行修炼的后果**:
     * 走火入魔
     * 境界跌落
     * 心性扭曲

请以 JSON 格式输出，确保力量体系体现"道法自然""阴阳五行""天人合一"等哲学思想。
""",
            "treasure_design": """## 任务: 设计功法法宝

### 力量体系
{power_system}

### 法宝设计要求

请设计核心功法与法宝，融入哲学思想和文化内涵:

**功法设计** (核心功法3-5种):

每个功法应体现特定的哲学思想:

1. **道家功法示例**:
   - 功法名称: "上善若水诀" / "无为真经" / "太极玄功"
   - 等级 (天/地/玄/黄)
   - **修炼条件**: 
     * 心境要求: 需领悟"无为""自然"之理
     * 德性要求: 淡泊名利，不争不抢
   - **核心效果**: 
     * 以柔克刚，四两拨千斤
     * 顺应天道，借力打力
   - **修炼风险**: 
     * 急于求成则"走火入魔"
     * 违背"自然"原则则遭反噬
   - **哲学内涵**: 
     * 体现"柔弱胜刚强"
     * 体现"无为而无不为"
   - 与主角的关系

2. **儒家功法示例**:
   - 功法名称: "浩然正气诀" / "仁义神罡" / "君子剑法"
   - 等级 (天/地/玄/黄)
   - **修炼条件**: 
     * 心境要求: 需领悟"仁义""礼智"之理
     * 德性要求: 心怀天下，仁义为本
   - **核心效果**: 
     * 正气凛然，邪魔退散
     * 仁者无敌，以德服人
   - **修炼风险**: 
     * 违背"仁义"则功力倒退
     * 心生邪念则正气反噬
   - **哲学内涵**: 
     * 体现"仁者爱人"
     * 体现"修身齐家治国平天下"
   - 与主角的关系

3. **阴阳五行功法**:
   - 功法名称: "阴阳太极功" / "五行轮转诀" / "乾坤大挪移"
   - 等级 (天/地/玄/黄)
   - **修炼条件**: 
     * 需理解阴阳相生相克之理
     * 需平衡五行属性
   - **核心效果**: 
     * 阴阳调和，刚柔并济
     * 五行相生，生生不息
   - **修炼风险**: 
     * 阴阳失衡则经脉错乱
     * 五行相克则走火入魔
   - **哲学内涵**: 
     * 体现"一阴一阳之谓道"
     * 体现"万物负阴而抱阳"
   - 与主角的关系

**法宝设计** (核心法宝3-5件):

每个法宝应有文化典故或哲学寓意:

1. **法宝命名** (引用经典或文化意象):
   - "太极图": 阴阳调和，包罗万象
   - "乾坤袋": 厚德载物，包容万物
   - "君子剑": 仁者之兵，以德服人
   - "八卦镜": 洞察天机，明察秋毫
   - "五行环": 相生相克，循环不息

2. **法宝详情**:
   - 法宝名称 (含哲学寓意)
   - 等级/品阶
   - **来历**（如何获得）:
     * 可引用历史典故或神话传说
     * 体现"因果""机缘"
   - **核心能力**:
     * 体现某种哲学思想 (如"以柔克刚""厚德载物")
   - **器灵描述**（如有）:
     * 器灵性格应符合法宝属性
     * 可引用经典语句作为器灵台词
   - **限制条件**:
     * 体现"物极必反"
     * 体现"德不配位"
   - **法宝与主人关系**:
     * 认主条件: 需心性相合
     * 使用限制: 需德位相配

**3. 功法法宝与哲学对应表**:
- 列出每个功法/法宝对应的哲学思想
- 说明其体现的核心理念
- 描述其在故事中的象征意义

请以 JSON 格式输出，确保每个功法法宝都有深厚的文化内涵和哲学寓意。
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
