"""
Event Plugin - Manages plot events, causality, and conflicts

This plugin handles:
- Plot event tracking and organization
- Event causality and dependencies
- Conflict design and resolution
- Story pacing through events
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
    ValidationResult,
    WritingContext,
)


class EventPlugin(NovelElementPlugin):
    """
    Plugin for managing plot events and story structure

    Tracks events, their relationships, conflicts, and story progression.
    """

    name = "event"
    version = "1.0.0"
    description = "Manages plot events, causality, and conflicts"
    author = "Creative AutoGPT"

    # Event state storage
    _events: List[Dict[str, Any]] = []
    _conflicts: List[Dict[str, Any]] = []
    _event_graph: Dict[str, List[str]] = {}  # event_id -> dependent event_ids

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._events = []
        self._conflicts = []
        self._event_graph = {}

    async def on_init(self, context: WritingContext) -> None:
        """Initialize event plugin with session context"""
        logger.info(f"EventPlugin initialized for session {context.session_id}")

        # Try to load from database first
        state = await self.load_state(context)
        if state:
            self._events = state.get("events", [])
            self._conflicts = state.get("conflicts", [])
            self._event_graph = state.get("event_graph", {})
            logger.info(f"Loaded {len(self._events)} events from database")
        else:
            # Fallback to metadata
            if "events" in context.metadata:
                self._events = context.metadata.get("events", [])
            if "conflicts" in context.metadata:
                self._conflicts = context.metadata.get("conflicts", [])

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for event data"""
        return {
            "type": "object",
            "title": "Event Schema",
            "description": "Schema for plot events",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Unique event identifier"
                },
                "name": {
                    "type": "string",
                    "description": "Event name/title"
                },
                "type": {
                    "type": "string",
                    "enum": ["setup", "inciting_incident", "rising_action", "climax", "falling_action", "resolution"],
                    "description": "Story structure type"
                },
                "plot_line": {
                    "type": "string",
                    "enum": ["main", "subplot_1", "subplot_2", "subplot_3"],
                    "description": "Which plot line this belongs to"
                },
                "chapter": {
                    "type": "integer",
                    "description": "Chapter where event occurs"
                },
                "description": {
                    "type": "string",
                    "description": "Event description"
                },
                "trigger": {
                    "type": "string",
                    "description": "What triggers this event"
                },
                "outcome": {
                    "type": "string",
                    "description": "Result of this event"
                },
                "characters_involved": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Character IDs involved"
                },
                "locations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Location IDs where event occurs"
                },
                "foreshadowing": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Foreshadowing element IDs"
                },
                "conflicts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Conflict IDs involved"
                },
                "emotional_tone": {
                    "type": "string",
                    "description": "Emotional tone of the event"
                },
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Event IDs that must happen before this"
                }
            },
            "required": ["event_id", "name", "type", "plot_line"]
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for event-related tasks"""
        return {
            "event_design": """## 任务: 设计情节事件链

### 故事大纲
{outline}

### 事件设计要求

请为小说设计完整的情节事件链:

**主线事件 (10-20个):**
按时间顺序列出主线事件，每个事件包含:
1. **事件名称**: 简洁的事件标题
2. **事件类型**: 开端/激励事件/上升动作/高潮/下降动作/结局
3. **章节位置**: 大约在第几章发生
4. **触发条件**: 什么导致这个事件发生
5. **主要内容**: 事件的具体描述 (100-200字)
6. **结果影响**: 这个事件导致的后果
7. **涉及角色**: 出场的主要角色
8. **涉及场景**: 发生的地点
9. **关联伏笔**: 相关的伏笔元素
10. **情感基调**: 事件的整体情感色彩
11. **冲突内容**: 包含的冲突

**支线事件 (3-5条支线):**
每条支线包含:
- 支线主题
- 起承转合事件
- 与主线的交汇点
- 支线结局

**冲突设计:**
1. **主要冲突**:
   - 冲突类型: (人物对抗/社会对抗/自然对抗/自我对抗/命运对抗)
   - 冲突双方
   - 冲突核心
   - 冲突发展路径
   - 冲突解决方式

2. **次要冲突**: 2-3个次要冲突

3. **冲突升级机制**:
   - 冲突如何逐步升级
   - 转折点设置

请以 JSON 格式输出事件设计。
""",

            "conflict_design": """## 任务: 设计故事冲突

### 事件链
{events}

### 冲突设计要求

请设计故事的核心冲突体系:

**1. 核心冲突 (主线冲突):**
- **冲突类型**: 人物/社会/自然/自我/命运
- **冲突双方**: 明确的对抗双方
- **冲突根源**: 为什么产生冲突
- **冲突表现**: 冲突的具体表现形式
- **冲突升级**: 冲突如何随时间升级
- **高潮时刻**: 冲突的最高点
- **解决方式**: 最终如何解决
- **象征意义**: 冲突的深层含义

**2. 次要冲突 (2-4个):**
每个包含:
- 与主线冲突的关系
- 独立的发展路径
- 对主线的推动作用

**3. 内部冲突:**
- 主角内心的矛盾和挣扎
- 成长面临的内在障碍
- 自我超越的契机

**4. 冲突节奏:**
- 冲突的引入时机
- 冲突的缓解和爆发
- 多冲突的交织

请以 JSON 格式输出。
""",

            "event_pacing": """## 任务: 分析事件节奏

### 事件列表
{events}

### 节奏分析要求

请分析事件链的节奏安排:

1. **节奏变化**:
   - 快节奏段落: 高强度、多事件
   - 慢节奏段落: 心理、铺垫
   - 节奏转换点

2. **张力曲线**:
   - 张力上升阶段
   - 张力释放时刻
   - 张力低谷

3. **情感波动**:
   - 情感高潮
   - 情感低谷
   - 情感转换

4. **改进建议**:
   - 节奏问题
   - 调整建议

请输出结构化的节奏分析报告。
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for event-related operations"""
        return [
            {
                "task_id": "events_design",
                "task_type": "事件",
                "description": "Design plot event chain with causality",
                "depends_on": ["大纲", "人物设计"],
                "metadata": {
                    "plugin": "event",
                    "operation": "design"
                }
            },
            {
                "task_id": "conflict_design",
                "task_type": "冲突设计",
                "description": "Design story conflicts and resolution paths",
                "depends_on": ["事件"],
                "metadata": {
                    "plugin": "event",
                    "operation": "conflicts"
                }
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate event data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Event data must be a dictionary"]
            )

        # Check required fields
        required_fields = ["event_id", "name", "type", "plot_line"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate event type
        valid_types = ["setup", "inciting_incident", "rising_action", "climax", "falling_action", "resolution"]
        if "type" in data and data["type"] not in valid_types:
            errors.append(f"Invalid event type: {data['type']}")

        # Check for causality
        if "depends_on" in data and data["depends_on"]:
            for dep_id in data["depends_on"]:
                if not any(e.get("event_id") == dep_id for e in self._events):
                    warnings.append(f"Dependency {dep_id} not found in existing events")

        # Check for emotional content
        if "emotional_tone" not in data:
            suggestions.append("Add emotional tone for better scene writing")

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
        """Extract and store event data from task results"""
        task_type = task.get("task_type", "")

        if task_type == "事件":
            await self._extract_events(result, context)
        elif task_type == "冲突设计":
            await self._extract_conflicts(result, context)

        return result

    async def _extract_events(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract event data from result"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                if isinstance(data, dict) and "events" in data:
                    self._events = data["events"]
                    # Build event dependency graph
                    self._build_event_graph()

                logger.info(f"Extracted {len(self._events)} events")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse event data as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting events: {e}")

    async def _extract_conflicts(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract conflict data from result"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                if isinstance(data, dict) and "conflicts" in data:
                    self._conflicts = data["conflicts"]

                logger.info(f"Extracted {len(self._conflicts)} conflicts")

        except Exception as e:
            logger.error(f"Error extracting conflicts: {e}")

    def _build_event_graph(self) -> None:
        """Build event dependency graph"""
        self._event_graph = {}
        for event in self._events:
            event_id = event.get("event_id")
            if event_id:
                self._event_graph[event_id] = event.get("depends_on", [])

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with event information"""
        task_type = task.get("task_type", "")

        # Add event summary for chapter generation
        if "章节" in task_type:
            chapter_index = task.get("metadata", {}).get("chapter_index")
            if chapter_index is not None:
                chapter_events = self._get_events_for_chapter(chapter_index)
                if chapter_events:
                    context["chapter_events"] = chapter_events

        # Add conflicts for relevant tasks
        if self._conflicts and "章节" in task_type:
            context["conflicts"] = self._conflicts

        return context

    def _get_events_for_chapter(self, chapter_index: int) -> List[Dict[str, Any]]:
        """Get events that occur in a specific chapter"""
        return [
            event for event in self._events
            if event.get("chapter") == chapter_index
        ]

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all events"""
        return self._events.copy()

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific event by ID"""
        for event in self._events:
            if event.get("event_id") == event_id:
                return event
        return None

    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Get all conflicts"""
        return self._conflicts.copy()

    def get_event_chain(self, plot_line: str = "main") -> List[Dict[str, Any]]:
        """Get events for a specific plot line in order"""
        return [
            event for event in self._events
            if event.get("plot_line") == plot_line
        ]

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize event plugin and persist data"""
        logger.info(f"EventPlugin finalized - persisting {len(self._events)} events")

        # Persist to database
        await self.persist_all(context, {
            "events": self._events,
            "conflicts": self._conflicts,
            "event_graph": self._event_graph,
        })

        # Also store in metadata for compatibility
        context.metadata["events"] = self._events
        context.metadata["conflicts"] = self._conflicts
        context.metadata["event_graph"] = self._event_graph
