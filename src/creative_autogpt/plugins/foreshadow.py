"""
Foreshadow Plugin - Manages foreshadowing plant and payoff tracking

This plugin handles:
- Foreshadowing element planning
- Plant tracking (when and where foreshadowing is placed)
- Payoff tracking (when foreshadowing is resolved)
- Foreshadowing consistency validation
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


class ForeshadowPlugin(NovelElementPlugin):
    """
    Plugin for managing foreshadowing elements

    Tracks planted foreshadowing and ensures proper payoff.
    """

    name = "foreshadow"
    version = "1.0.0"
    description = "Manages foreshadowing plant and payoff tracking"
    author = "Creative AutoGPT"

    # Foreshadowing state storage
    _elements: List[Dict[str, Any]] = []
    _plants: Dict[str, List[Dict[str, Any]]] = {}  # element_id -> plant locations
    _payoffs: Dict[str, List[Dict[str, Any]]] = {}  # element_id -> payoff locations

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._elements = []
        self._plants = {}
        self._payoffs = {}

    async def on_init(self, context: WritingContext) -> None:
        """Initialize foreshadow plugin with session context"""
        logger.info(f"ForeshadowPlugin initialized for session {context.session_id}")

        # Try to load from database first
        state = await self.load_state(context)
        if state:
            self._elements = state.get("elements", [])
            self._plants = state.get("plants", {})
            self._payoffs = state.get("payoffs", {})
            logger.info(f"Loaded {len(self._elements)} foreshadow elements from database")
        else:
            # Fallback to metadata
            if "foreshadow_elements" in context.metadata:
                self._elements = context.metadata.get("foreshadow_elements", [])
            if "foreshadow_plants" in context.metadata:
                self._plants = context.metadata.get("foreshadow_plants", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for foreshadow data"""
        return {
            "type": "object",
            "title": "Foreshadow Schema",
            "description": "Schema for foreshadowing elements",
            "properties": {
                "element_id": {
                    "type": "string",
                    "description": "Unique foreshadow element identifier"
                },
                "name": {
                    "type": "string",
                    "description": "Foreshadow element name"
                },
                "type": {
                    "type": "string",
                    "enum": ["plot", "character", "object", "dialogue", "symbolic", "atmospheric"],
                    "description": "Type of foreshadowing"
                },
                "description": {
                    "type": "string",
                    "description": "What is being foreshadowed"
                },
                "importance": {
                    "type": "string",
                    "enum": ["critical", "major", "minor"],
                    "description": "Importance level"
                },
                "plant_chapter": {
                    "type": "integer",
                    "description": "Chapter where foreshadow is planted"
                },
                "payoff_chapter": {
                    "type": "integer",
                    "description": "Chapter where foreshadow is resolved"
                },
                "subtlety": {
                    "type": "string",
                    "enum": ["obvious", "moderate", "subtle", "very_subtle"],
                    "description": "How obvious the foreshadow should be"
                },
                "related_events": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Related event IDs"
                }
            },
            "required": ["element_id", "name", "type", "description"]
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for foreshadow-related tasks"""
        return {
            "foreshadow_planning": """## 任务: 规划伏笔系统

### 故事大纲
{outline}

### 事件链
{events}

### 伏笔规划要求

请为小说规划完整的伏笔系统:

**主线伏笔 (5-10个):**
每个伏笔包含:
1. **伏笔编号**: 唯一标识
2. **伏笔名称**: 简洁的名称
3. **伏笔类型**: 情节/角色/物品/对话/象征/氛围
4. **伏笔描述**: 要暗示什么内容 (50-100字)
5. **重要性等级**: 关键/重要/次要
6. **埋设位置**: 第几章埋设
7. **埋设方式**:
   - 对话暗示
   - 物品描写
   - 场景细节
   - 行为异常
   - 其他方式
8. **回收位置**: 第几章回收
9. **回收方式**: 如何揭示/解决
10. **影响范围**: 对故事的影响程度
11. **隐蔽程度**: 明显/适度/微妙/极微妙

**支线伏笔 (3-5个):**
同样的结构，但针对支线情节

**细节伏笔:**
- 可以埋藏伏笔的细节类型列表
- 隐藏技巧建议

**伏笔分布表:**
请制作表格显示:
- 章节
- 埋设的伏笔
- 回收的伏笔
- 确保分布均匀

请以 JSON 格式输出伏笔规划。
""",

            "foreshadow_validation": """## 任务: 检查伏笔一致性

### 伏笔规划
{foreshadow_plan}

### 检查内容
{content_to_check}

### 检查维度

1. **埋设检查**: 伏笔是否正确埋设
2. **回收检查**: 伏笔是否得到回收
3. **时机检查**: 埋设和回收的时机是否合理
4. **一致性检查**: 回收是否与埋设一致
5. **遗漏检查**: 是否有未回收的伏笔

### 输出要求

请输出 JSON 格式的检查结果:
```json
{{
  "is_consistent": true/false,
  "planted": ["已埋设的伏笔"],
  "resolved": ["已回收的伏笔"],
  "unresolved": ["未回收的伏笔"],
  "issues": ["具体问题"],
  "suggestions": ["修改建议"]
}}
```
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for foreshadow-related operations"""
        return [
            {
                "task_id": "foreshadow_list",
                "task_type": "伏笔列表",
                "description": "Plan foreshadowing elements for the story",
                "depends_on": ["事件"],
                "metadata": {
                    "plugin": "foreshadow",
                    "operation": "plan"
                }
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate foreshadow data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Foreshadow data must be a dictionary"]
            )

        # Check required fields
        required_fields = ["element_id", "name", "type", "description"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate foreshadow type
        valid_types = ["plot", "character", "object", "dialogue", "symbolic", "atmospheric"]
        if "type" in data and data["type"] not in valid_types:
            errors.append(f"Invalid foreshadow type: {data['type']}")

        # Check payoff chapter is after plant chapter
        plant_chapter = data.get("plant_chapter")
        payoff_chapter = data.get("payoff_chapter")
        if plant_chapter and payoff_chapter and payoff_chapter <= plant_chapter:
            errors.append(f"Payoff chapter ({payoff_chapter}) must be after plant chapter ({plant_chapter})")

        # Check for proper spacing
        if plant_chapter and payoff_chapter:
            spacing = payoff_chapter - plant_chapter
            if spacing < 3:
                warnings.append(f"Foreshadow spacing is short ({spacing} chapters), consider extending for better effect")

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
        """Extract and store foreshadow data from task results"""
        task_type = task.get("task_type", "")

        if task_type == "伏笔列表":
            await self._extract_foreshadows(result, context)

        return result

    async def _extract_foreshadows(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract foreshadow data from result"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                if isinstance(data, dict) and "foreshadows" in data:
                    self._elements = data["foreshadows"]
                    # Initialize plant and payoff tracking
                    for element in self._elements:
                        element_id = element.get("element_id")
                        if element_id:
                            self._plants[element_id] = []
                            self._payoffs[element_id] = []

                logger.info(f"Extracted {len(self._elements)} foreshadow elements")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse foreshadow data as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting foreshadows: {e}")

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with foreshadow information"""
        task_type = task.get("task_type", "")
        chapter_index = task.get("metadata", {}).get("chapter_index")

        # Add foreshadow info for chapter generation
        if chapter_index is not None and ("章节" in task_type or "场景" in task_type):
            # Get foreshadows to plant in this chapter
            to_plant = self._get_foreshadows_to_plant(chapter_index)
            if to_plant:
                context["foreshadows_to_plant"] = to_plant

            # Get foreshadows to payoff in this chapter
            to_payoff = self._get_foreshadows_to_payoff(chapter_index)
            if to_payoff:
                context["foreshadows_to_payoff"] = to_payoff

        return context

    def _get_foreshadows_to_plant(self, chapter_index: int) -> List[Dict[str, Any]]:
        """Get foreshadows that should be planted in this chapter"""
        return [
            element for element in self._elements
            if element.get("plant_chapter") == chapter_index
        ]

    def _get_foreshadows_to_payoff(self, chapter_index: int) -> List[Dict[str, Any]]:
        """Get foreshadows that should be paid off in this chapter"""
        return [
            element for element in self._elements
            if element.get("payoff_chapter") == chapter_index
        ]

    def record_plant(self, element_id: str, chapter_index: int, details: Dict[str, Any]) -> None:
        """Record that a foreshadow was planted"""
        if element_id not in self._plants:
            self._plants[element_id] = []
        self._plants[element_id].append({
            "chapter": chapter_index,
            "timestamp": datetime.utcnow().isoformat(),
            **details
        })

    def record_payoff(self, element_id: str, chapter_index: int, details: Dict[str, Any]) -> None:
        """Record that a foreshadow was paid off"""
        if element_id not in self._payoffs:
            self._payoffs[element_id] = []
        self._payoffs[element_id].append({
            "chapter": chapter_index,
            "timestamp": datetime.utcnow().isoformat(),
            **details
        })

    def get_unresolved_foreshadows(self) -> List[Dict[str, Any]]:
        """Get foreshadows that haven't been paid off yet"""
        unresolved = []
        for element in self._elements:
            element_id = element.get("element_id")
            if element_id and not self._payoffs.get(element_id):
                unresolved.append(element)
        return unresolved

    def get_elements(self) -> List[Dict[str, Any]]:
        """Get all foreshadow elements"""
        return self._elements.copy()

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize foreshadow plugin and persist data"""
        logger.info(f"ForeshadowPlugin finalized - persisting {len(self._elements)} elements")

        # Persist to database
        await self.persist_all(context, {
            "elements": self._elements,
            "plants": self._plants,
            "payoffs": self._payoffs,
        })

        # Also store in metadata for compatibility
        context.metadata["foreshadow_elements"] = self._elements
        context.metadata["foreshadow_plants"] = self._plants
        context.metadata["foreshadow_payoffs"] = self._payoffs
