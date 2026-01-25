"""
Timeline Plugin - Manages story timeline and chronology

This plugin handles:
- Story timeline tracking
- Event chronology validation
- Time-based consistency checking
- Flashback and flashforward tracking
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


class TimelinePlugin(NovelElementPlugin):
    """
    Plugin for managing story timeline

    Tracks chronology and validates time-based consistency.
    """

    name = "timeline"
    version = "1.0.0"
    description = "Manages story timeline and chronology"
    author = "Creative AutoGPT"

    # Timeline state storage
    _timeline: List[Dict[str, Any]] = []
    _current_chapter_time: Optional[str] = None
    _flashbacks: List[Dict[str, Any]] = []
    _flashforwards: List[Dict[str, Any]] = []

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._timeline = []
        self._current_chapter_time = None
        self._flashbacks = []
        self._flashforwards = []

    async def on_init(self, context: WritingContext) -> None:
        """Initialize timeline plugin with session context"""
        logger.info(f"TimelinePlugin initialized for session {context.session_id}")
        if "timeline" in context.metadata:
            self._timeline = context.metadata.get("timeline", [])

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for timeline data"""
        return {
            "type": "object",
            "title": "Timeline Schema",
            "description": "Schema for timeline events",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Unique event identifier"
                },
                "story_time": {
                    "type": "string",
                    "description": "Time in story world (e.g., 'Day 1', 'Year 3045')"
                },
                "chapter": {
                    "type": "integer",
                    "description": "Chapter where this occurs"
                },
                "duration": {
                    "type": "string",
                    "description": "How long the event lasts"
                },
                "description": {
                    "type": "string",
                    "description": "Event description"
                },
                "location": {
                    "type": "string",
                    "description": "Where this occurs"
                },
                "characters_present": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Characters present"
                },
                "time_jump": {
                    "type": "boolean",
                    "description": "Whether there's a time jump after this"
                },
                "jump_duration": {
                    "type": "string",
                    "description": "Duration of time jump if applicable"
                }
            },
            "required": ["event_id", "story_time", "chapter"]
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for timeline-related tasks"""
        return {
            "timeline_check": """## 任务: 检查时间线一致性

### 当前时间线
{current_timeline}

### 检查内容
{content_to_check}

### 检查维度

1. **时间连贯性**: 时间顺序是否合理
2. **持续时间**: 事件持续时间是否合理
3. **时间跳跃**: 时间跳跃是否明确标注
4. **同时事件**: 同时发生的事件是否合理
5. **回忆/预知**: 闪回和闪前是否清晰标注

### 输出要求

请输出 JSON 格式的检查结果:
```json
{{
  "is_consistent": true/false,
  "timeline_events": ["识别到的时间事件"],
  "issues": ["时间问题"],
  "suggestions": ["修改建议"],
  "current_time_established": "当前确立的时间"
}}
```
""",

            "timeline_creation": """## 任务: 创建故事时间线

### 故事大纲
{outline}

### 事件列表
{events}

### 时间线创建要求

请为小说创建详细的时间线:

**时间系统:**
- 时间计量单位: (天/月/年/纪元/其他)
- 历法系统: 如适用
- 时间参照点

**主线时间线:**
按顺序列出每个章节的时间点:
1. 章节编号
2. 故事时间
3. 持续时间
4. 时间跳跃 (如有)
5. 关键事件

**特殊时间处理:**
- 闪回时刻: 时间点、持续内容
- 闪前时刻: 时间点、展示内容
- 平行时间线: 如适用

**时间一致性检查:**
确保角色位置合理、事件顺序逻辑

请以 JSON 格式输出时间线。
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for timeline-related operations"""
        return [
            {
                "task_id": "timeline_check",
                "task_type": "时间线检查",
                "description": "Check timeline consistency in the story",
                "depends_on": ["章节内容"],
                "metadata": {
                    "plugin": "timeline",
                    "operation": "check"
                }
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate timeline data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Timeline data must be a dictionary"]
            )

        # Check required fields
        if "event_id" not in data:
            errors.append("Missing event_id")
        if "story_time" not in data:
            errors.append("Missing story_time")
        if "chapter" not in data:
            errors.append("Missing chapter")

        # Check chapter ordering
        if "chapter" in data and self._timeline:
            last_chapter = max(t.get("chapter", 0) for t in self._timeline)
            if data["chapter"] < last_chapter:
                warnings.append(f"Chapter {data['chapter']} is before last chapter {last_chapter}")

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
        """Process timeline-related task results"""
        task_type = task.get("task_type", "")

        if task_type == "时间线检查":
            await self._process_timeline_check(result, context)

        return result

    async def _process_timeline_check(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Process timeline check results"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                # Extract timeline events
                if "timeline_events" in data:
                    for event in data["timeline_events"]:
                        if isinstance(event, dict):
                            self._timeline.append(event)

                # Update current time
                if "current_time_established" in data:
                    self._current_chapter_time = data["current_time_established"]

        except Exception as e:
            logger.error(f"Error processing timeline check: {e}")

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with timeline information"""
        task_type = task.get("task_type", "")
        chapter_index = task.get("metadata", {}).get("chapter_index")

        # Add current timeline position for chapter generation
        if chapter_index is not None and "章节" in task_type:
            if self._current_chapter_time:
                context["current_time"] = self._current_chapter_time

            # Add recent timeline events
            recent_events = [
                t for t in self._timeline
                if t.get("chapter", 0) < chapter_index
            ]
            if recent_events:
                context["recent_timeline"] = recent_events[-5:]  # Last 5 events

        return context

    def add_timeline_event(self, event: Dict[str, Any]) -> None:
        """Add a timeline event"""
        self._timeline.append(event)
        # Sort by chapter
        self._timeline.sort(key=lambda x: x.get("chapter", 0))

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get the full timeline"""
        return self._timeline.copy()

    def get_current_time(self) -> Optional[str]:
        """Get the current established story time"""
        return self._current_chapter_time

    def set_current_time(self, time: str) -> None:
        """Set the current story time"""
        self._current_chapter_time = time

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize timeline plugin and persist data"""
        logger.info("TimelinePlugin finalized")
        context.metadata["timeline"] = self._timeline
        context.metadata["flashbacks"] = self._flashbacks
        context.metadata["flashforwards"] = self._flashforwards
