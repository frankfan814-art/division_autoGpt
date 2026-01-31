"""
Villain Plugin - Manages antagonist design and development arcs

This plugin handles:
- Antagonist character profiles
- Villain hierarchy (ultimate, mid-tier, episodic)
- Villain motivations and backstories
- Villain development and redemption arcs
- Antagonist progression tracking
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


class VillainPlugin(NovelElementPlugin):
    """
    Plugin for managing antagonists and villain characters

    Tracks villains, their hierarchies, motivations, and development arcs.
    """

    name = "villain"
    version = "1.0.0"
    description = "Manages antagonist design, hierarchies, and development arcs"
    author = "Creative AutoGPT"

    _villains: Dict[str, Dict[str, Any]] = {}
    _villain_hierarchy: Dict[str, List[str]] = {}
    _antagonist_relationships: Dict[str, List[Dict[str, Any]]] = {}
    _villain_arcs: Dict[str, List[Dict[str, Any]]] = {}

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._villains = {}
        self._villain_hierarchy = {}
        self._antagonist_relationships = {}
        self._villain_arcs = {}

    async def on_init(self, context: WritingContext) -> None:
        """Initialize villain plugin with session context"""
        logger.info(f"VillainPlugin initialized for session {context.session_id}")

        state = await self.load_state(context)
        if state:
            self._villains = state.get("villains", {})
            self._villain_hierarchy = state.get("villain_hierarchy", {})
            self._antagonist_relationships = state.get("antagonist_relationships", {})
            self._villain_arcs = state.get("villain_arcs", {})
            logger.info(f"Loaded {len(self._villains)} villains from database")
        else:
            if "villains" in context.metadata:
                self._villains = context.metadata.get("villains", {})
            if "villain_hierarchy" in context.metadata:
                self._villain_hierarchy = context.metadata.get("villain_hierarchy", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for villain data"""
        return {
            "type": "object",
            "title": "Villain Schema",
            "description": "Schema for antagonist characters",
            "properties": {
                "villain_id": {"type": "string"},
                "name": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["ultimate", "mid_tier", "episodic", "rival"],
                    "description": "Villain type/hierarchy level"
                },
                "role": {
                    "type": "string",
                    "enum": ["final_boss", "arc_villain", "chapter_villain", "rival"],
                    "description": "Story role"
                },
                "appearance_chapter": {"type": "integer"},
                "defeat_chapter": {"type": "integer", "description": "Chapter where defeated"},
                "power_level": {"type": "number", "description": "Relative power compared to protagonist"},
                "motivation": {
                    "type": "object",
                    "properties": {
                        "primary_goal": {"type": "string"},
                        "method": {"type": "string"},
                        "origin_of_evil": {"type": "string"},
                        "tragic_backstory": {"type": "string"}
                    }
                },
                "personality": {
                    "type": "object",
                    "properties": {
                        "traits": {"type": "array", "items": {"type": "string"}},
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "weaknesses": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "relationship_with_hero": {
                    "type": "string",
                    "description": "How villain relates to protagonist"
                },
                "development_arc": {
                    "type": "string",
                    "enum": ["static", "escalation", "redemption", "tragedy", "survival"]
                }
            }
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for villain-related tasks"""
        return {
            "villain_design": """## 任务: 设计反派体系

### 主角设定
{character}

### 主角成长路径
{growth_path}

### 世界观势力
{factions}

### 反派设计要求

请设计完整的反派体系，每个反派应有清晰的**哲学立场**和**价值观**，与主角形成思想碰撞:

**反派哲学定位 (重点):**
反派不应只是"坏人"，而应代表某种**极端化的哲学思想**或**扭曲的价值观**:

1. **极端功利主义反派**:
   - 哲学基础: "成王败寇""弱肉强食"
   - 扭曲理念: 将道家"无为"扭曲为"不作为"，将儒家"仁义"扭曲为"伪善"
   - 行为特征: 为达目的不择手段，信奉"胜者为王"

2. **极端秩序主义反派**:
   - 哲学基础: 法家"以法治国"走向极端
   - 扭曲理念: 绝对控制，抹杀个性，"非黑即白"
   - 行为特征: 冷酷无情，以规则压制人性

3. **虚无主义反派**:
   - 哲学基础: "天地不仁"的极端解读
   - 扭曲理念: 一切毫无意义，毁灭即解脱
   - 行为特征: 愤世嫉俗，想要毁灭世界

4. **个人主义极端反派**:
   - 哲学基础: "人不为己，天诛地灭"
   - 扭曲理念: 绝对自由=无视他人，强者特权
   - 行为特征: 自私自利，践踏弱者

**设计要点:**
- 每个反派都是主角的**"镜子"**，体现"如果主角走错路会怎样"
- 反派与主角的冲突本质上是**价值观冲突**
- 反派也有其**哲学逻辑自洽性** (不是无理由的坏)

**1. 终极大反派 (1个)**:
   - 身份和地位
   - **哲学立场**: 信奉什么极端思想？
   - **核心动机**（为什么与主角作对）:
     * 理念冲突: 与主角的哲学观点根本对立
     * 道路之争: "只有我的路才是正确的"
   - **扭曲的价值观**: 如何误解或极端化某种哲学思想？
   - 实力水平
   - 与主角的恩怨根源
   - 最终命运 (体现"恶有恶报"或"放下屠刀")

**2. 中期反派 (2-3个)**:
   - 每个反派的阶段性目标
   - **哲学定位**: 代表哪种扭曲思想？
   - 与终极反派的关系
   - 与主角的冲突点 (价值观冲突的具体体现)
   - 实力设定
   - 命运走向

**3. 阶段性对手 (3-5个)**:
   - 每章/每段的对手
   - **小反派的哲学**: 即使是小反派也应有其扭曲逻辑
   - 特点和能力
   - 出现和退场安排

**4. 反派等级体系**:
   - 反派实力金字塔
   - **反派思想体系**: 从低级到高级的哲学扭曲程度
   - 势力分布
   - 与主角成长的对应关系 (主角境界提升，反派哲学扭曲加深)

**5. 正邪对比表** (新增):
   - 对比主角与反派的哲学观点
   - 展示"一念之差，正邪两途"
   - 体现"道不同不相为谋"

请以 JSON 格式输出。
""",
            "villain_backstory": """## 任务: 撰写反派背景故事

### 反派设定
{villain_data}

### 背景故事要求

请为这个反派撰写详细的背景故事:

1. **起源**:
   - 出身背景
   - 如何获得力量
   - 价值观如何形成

2. **转折点**:
   - 关键事件导致堕落
   - 心理变化过程

3. **当前状态**:
   - 为何成为反派
   - 核心恐惧和渴望

4. **与主角的镜像关系**:
   - 反派和主角的相似之处
   - 分歧点在哪里

请直接输出背景故事，1500-2500字。
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for villain-related operations"""
        return [
            {
                "task_id": "villain_design",
                "task_type": "反派设计",
                "description": "Design antagonist hierarchy including ultimate villain, mid-tier antagonists, and episodic opponents",
                "depends_on": ["大纲", "人物设计", "主角成长", "势力设计"],
                "metadata": {"plugin": "villain", "operation": "design"}
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate villain data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(valid=False, errors=["Villain data must be a dictionary"])

        if "name" not in data:
            errors.append("Missing villain name")
        if "type" not in data:
            errors.append("Missing villain type/hierarchy level")

        villain_type = data.get("type")
        if villain_type == "ultimate" and data.get("appearance_chapter", 0) > 10:
            suggestions.append("Consider introducing the ultimate villain earlier for tension")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, suggestions=suggestions)

    async def on_after_task(
        self,
        task: Dict[str, Any],
        result: str,
        context: WritingContext,
    ) -> str:
        """Extract and store villain data from task results"""
        if task.get("task_type") == "反派设计":
            await self._extract_villain_data(result, context)
        return result

    async def _extract_villain_data(self, result: str, context: WritingContext) -> None:
        """Extract villain design data from result"""
        import json
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                if "ultimate_villain" in data:
                    villain = data["ultimate_villain"]
                    villain_id = villain.get("villain_id", "ultimate")
                    self._villains[villain_id] = villain
                    self._villain_hierarchy["ultimate"] = [villain_id]

                if "mid_tier_villains" in data:
                    for i, villain in enumerate(data["mid_tier_villains"]):
                        villain_id = villain.get("villain_id", f"mid_tier_{i}")
                        self._villains[villain_id] = villain
                    self._villain_hierarchy["mid_tier"] = [v.get("villain_id") for v in data["mid_tier_villains"]]

                if "episodic_villains" in data:
                    for i, villain in enumerate(data["episodic_villains"]):
                        villain_id = villain.get("villain_id", f"episodic_{i}")
                        self._villains[villain_id] = villain
                    self._villain_hierarchy["episodic"] = [v.get("villain_id") for v in data["episodic_villains"]]

                logger.info(f"Extracted {len(self._villains)} villains")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse villain data as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting villain data: {e}")

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with villain information"""
        task_type = task.get("task_type", "")
        chapter_index = task.get("metadata", {}).get("chapter_index")

        if "章节" in task_type and chapter_index is not None:
            current_villains = self._get_villains_for_chapter(chapter_index)
            if current_villains:
                context["current_villains"] = current_villains

            active_villains = self._get_active_villains(chapter_index)
            if active_villains:
                context["active_villains"] = active_villains

        return context

    def _get_villains_for_chapter(self, chapter_index: int) -> List[Dict[str, Any]]:
        """Get villains that appear in a specific chapter"""
        return [
            v for v in self._villains.values()
            if v.get("appearance_chapter") == chapter_index
        ]

    def _get_active_villains(self, chapter_index: int) -> List[Dict[str, Any]]:
        """Get villains that should be active at this point in the story"""
        active = []
        for villain in self._villains.values():
            appear = villain.get("appearance_chapter", 0)
            defeat = villain.get("defeat_chapter", 9999)
            if appear <= chapter_index < defeat:
                active.append(villain)
        return active

    def get_villain(self, villain_id: str) -> Optional[Dict[str, Any]]:
        """Get a villain by ID"""
        return self._villains.get(villain_id)

    def get_all_villains(self) -> Dict[str, Dict[str, Any]]:
        """Get all villains"""
        return self._villains.copy()

    def get_villain_hierarchy(self) -> Dict[str, List[str]]:
        """Get villain hierarchy"""
        return self._villain_hierarchy.copy()

    def get_ultimate_villain(self) -> Optional[Dict[str, Any]]:
        """Get the ultimate/main antagonist"""
        ultimate_ids = self._villain_hierarchy.get("ultimate", [])
        if ultimate_ids:
            return self._villains.get(ultimate_ids[0])
        return None

    def get_current_antagonist(self, chapter_index: int) -> Optional[Dict[str, Any]]:
        """Get the main antagonist for a specific chapter"""
        active = self._get_active_villains(chapter_index)
        for villain in active:
            if villain.get("type") in ["ultimate", "mid_tier"]:
                return villain
        return active[0] if active else None

    def add_villain_arc(self, villain_id: str, arc: Dict[str, Any]) -> None:
        """Add a development arc for a villain"""
        if villain_id not in self._villain_arcs:
            self._villain_arcs[villain_id] = []
        self._villain_arcs[villain_id].append(arc)

    def get_villain_arcs(self, villain_id: str) -> List[Dict[str, Any]]:
        """Get all arcs for a villain"""
        return self._villain_arcs.get(villain_id, [])

    def get_antagonist_relationships(self, villain_id: str) -> List[Dict[str, Any]]:
        """Get relationships for a villain"""
        return self._antagonist_relationships.get(villain_id, [])

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize villain plugin and persist data"""
        logger.info(f"VillainPlugin finalized - persisting {len(self._villains)} villains")

        await self.persist_all(context, {
            "villains": self._villains,
            "villain_hierarchy": self._villain_hierarchy,
            "antagonist_relationships": self._antagonist_relationships,
            "villain_arcs": self._villain_arcs,
        })

        context.metadata["villains"] = self._villains
        context.metadata["villain_hierarchy"] = self._villain_hierarchy
