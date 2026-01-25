"""
Scene Plugin - Manages scene descriptions and atmosphere

This plugin handles:
- Scene environment descriptions
- Atmosphere and mood tracking
- Sensory details management
- Scene-to-scene transitions
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


class ScenePlugin(NovelElementPlugin):
    """
    Plugin for managing scene descriptions

    Tracks locations, atmospheres, and sensory details.
    """

    name = "scene"
    version = "1.0.0"
    description = "Manages scene descriptions and atmosphere"
    author = "Creative AutoGPT"

    # Scene state storage
    _scenes: Dict[str, Dict[str, Any]] = {}
    _atmospheres: Dict[str, List[str]] = {}
    _sensory_templates: Dict[str, Dict[str, List[str]]] = {}

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._scenes = {}
        self._atmospheres = {}
        self._sensory_templates = {}

    async def on_init(self, context: WritingContext) -> None:
        """Initialize scene plugin with session context"""
        logger.info(f"ScenePlugin initialized for session {context.session_id}")
        if "scenes" in context.metadata:
            self._scenes = context.metadata.get("scenes", {})
        if "atmospheres" in context.metadata:
            self._atmospheres = context.metadata.get("atmospheres", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for scene data"""
        return {
            "type": "object",
            "title": "Scene Schema",
            "description": "Schema for scene descriptions",
            "properties": {
                "scene_id": {
                    "type": "string",
                    "description": "Unique scene identifier"
                },
                "name": {
                    "type": "string",
                    "description": "Scene name"
                },
                "location_id": {
                    "type": "string",
                    "description": "Reference to location ID"
                },
                "time_of_day": {
                    "type": "string",
                    "enum": ["dawn", "morning", "noon", "afternoon", "evening", "dusk", "night", "midnight"],
                    "description": "Time of day"
                },
                "weather": {
                    "type": "string",
                    "description": "Weather conditions"
                },
                "atmosphere": {
                    "type": "object",
                    "properties": {
                        "mood": {"type": "string"},
                        "tension": {"type": "integer", "minimum": 0, "maximum": 10},
                        "emotional_tone": {"type": "string"}
                    }
                },
                "visuals": {
                    "type": "object",
                    "properties": {
                        "lighting": {"type": "string"},
                        "colors": {"type": "array", "items": {"type": "string"}},
                        "key_objects": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "sounds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Auditory details"
                },
                "smells": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Olfactory details"
                },
                "textures": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tactile details"
                },
                "transitions": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "type": {"type": "string", "enum": ["cut", "fade", "dissolve", "match_cut"]}
                    }
                }
            },
            "required": ["scene_id", "name"]
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for scene-related tasks"""
        return {
            "scene_generation": """## 任务: 生成场景内容

### 场景设定
- 时间: {time_of_day}
- 天气: {weather}
- 地点: {location}
- 氛围: {atmosphere}

### 上下文
{context}

### 场景生成要求

请生成详细的场景内容，包含:

1. **环境描述** (100-150字):
   - 空间布局
   - 视觉元素
   - 光线与色彩

2. **感官细节**:
   - 声音: 3-5种声音
   - 气味: 2-3种气味
   - 触觉: 如适用
   - 温度感

3. **氛围营造**:
   - 情绪基调
   - 张力水平
   - 预示感

4. **人物活动**:
   - 人物位置
   - 动作描述
   - 互动细节

5. **节奏把控**:
   - 快/慢节奏选择
   - 细节与动作的平衡

请直接输出场景内容，1500-2500字。
""",

            "atmosphere_check": """## 任务: 检查场景氛围

### 场景内容
{scene_content}

### 期望氛围
{expected_atmosphere}

### 检查维度

1. **氛围一致性**: 是否符合期望氛围
2. **感官丰富度**: 五感描写是否充分
3. **细节质量**: 细节是否生动具体
4. **沉浸感**: 是否能让读者身临其境

### 输出要求

请输出 JSON 格式的检查结果。
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for scene-related operations"""
        return [
            {
                "task_id": "scene_generation",
                "task_type": "场景生成",
                "description": "Generate detailed scene content",
                "depends_on": ["章节大纲"],
                "metadata": {
                    "plugin": "scene",
                    "operation": "generate"
                }
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate scene data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Scene data must be a dictionary"]
            )

        if "scene_id" not in data:
            errors.append("Missing scene_id")
        if "name" not in data:
            errors.append("Missing scene name")

        # Check for sensory details
        atmosphere = data.get("atmosphere", {})
        if not atmosphere.get("mood"):
            suggestions.append("Add mood description for better atmosphere")

        # Check sensory elements
        has_visuals = bool(data.get("visuals"))
        has_sounds = bool(data.get("sounds"))
        has_smells = bool(data.get("smells"))

        if not (has_visuals or has_sounds or has_smells):
            suggestions.append("Add sensory details for immersive scenes")

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
        """Process scene-related task results"""
        task_type = task.get("task_type", "")

        if task_type == "场景生成":
            chapter_index = task.get("metadata", {}).get("chapter_index")
            scene_index = task.get("metadata", {}).get("scene_index")

            if chapter_index is not None and scene_index is not None:
                scene_id = f"ch{chapter_index}_scene{scene_index}"
                self._scenes[scene_id] = {
                    "scene_id": scene_id,
                    "content": result,
                    "chapter": chapter_index,
                    "scene_index": scene_index,
                    "created_at": datetime.utcnow().isoformat()
                }

        return result

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with scene information"""
        task_type = task.get("task_type", "")

        if "场景" in task_type or "章节" in task_type:
            # Add atmosphere templates
            if self._atmospheres:
                context["atmosphere_templates"] = self._atmospheres

            # Add sensory templates
            if self._sensory_templates:
                context["sensory_templates"] = self._sensory_templates

        return context

    def add_scene(self, scene_id: str, scene_data: Dict[str, Any]) -> None:
        """Add a scene"""
        self._scenes[scene_id] = scene_data

    def get_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get a scene by ID"""
        return self._scenes.get(scene_id)

    def get_scenes_for_chapter(self, chapter_index: int) -> List[Dict[str, Any]]:
        """Get all scenes for a chapter"""
        return [
            scene for scene in self._scenes.values()
            if scene.get("chapter") == chapter_index
        ]

    def set_atmosphere(self, atmosphere_type: str, elements: List[str]) -> None:
        """Set atmosphere elements for a type"""
        self._atmospheres[atmosphere_type] = elements

    def set_sensory_template(self, sense: str, templates: Dict[str, List[str]]) -> None:
        """Set sensory templates"""
        self._sensory_templates[sense] = templates

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize scene plugin and persist data"""
        logger.info("ScenePlugin finalized")
        context.metadata["scenes"] = self._scenes
        context.metadata["atmospheres"] = self._atmospheres
        context.metadata["sensory_templates"] = self._sensory_templates
