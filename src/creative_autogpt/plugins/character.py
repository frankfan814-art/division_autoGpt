"""
Character Plugin - Manages character profiles, relationships, and development arcs

This plugin handles:
- Character profile creation and validation
- Relationship mapping between characters
- Character arc tracking throughout the story
- Voice consistency checking
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


class CharacterPlugin(NovelElementPlugin):
    """
    Plugin for managing novel characters

    Tracks character profiles, relationships, and development arcs.
    Validates character consistency and provides character context.
    """

    name = "character"
    version = "1.0.0"
    description = "Manages character profiles, relationships, and development"
    author = "Creative AutoGPT"

    # Character state storage
    _characters: Dict[str, Dict[str, Any]] = {}
    _relationships: Dict[str, List[Dict[str, Any]]] = {}
    _arcs: Dict[str, List[Dict[str, Any]]] = {}

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._characters = {}
        self._relationships = {}
        self._arcs = {}

    async def on_init(self, context: WritingContext) -> None:
        """Initialize character plugin with session context"""
        logger.info(f"CharacterPlugin initialized for session {context.session_id}")
        # Load any existing character data from context
        if "characters" in context.metadata:
            self._characters = context.metadata.get("characters", {})
        if "relationships" in context.metadata:
            self._relationships = context.metadata.get("relationships", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for character data"""
        return {
            "type": "object",
            "title": "Character Schema",
            "description": "Schema for novel character profiles",
            "properties": {
                "character_id": {
                    "type": "string",
                    "description": "Unique character identifier"
                },
                "name": {
                    "type": "string",
                    "description": "Character name"
                },
                "age": {
                    "type": "integer",
                    "description": "Character age"
                },
                "gender": {
                    "type": "string",
                    "enum": ["male", "female", "other", "unspecified"],
                    "description": "Character gender"
                },
                "appearance": {
                    "type": "string",
                    "description": "Physical appearance description"
                },
                "personality": {
                    "type": "object",
                    "properties": {
                        "traits": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Personality traits"
                        },
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Character strengths"
                        },
                        "weaknesses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Character weaknesses"
                        }
                    }
                },
                "background": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string"},
                        "family": {"type": "string"},
                        "education": {"type": "string"},
                        "occupation": {"type": "string"},
                        "history": {"type": "string"}
                    }
                },
                "motivation": {
                    "type": "object",
                    "properties": {
                        "primary_goal": {"type": "string"},
                        "secondary_goals": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "fears": {"type": "array", "items": {"type": "string"}},
                        "desires": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "abilities": {
                    "type": "object",
                    "properties": {
                        "skills": {"type": "array", "items": {"type": "string"}},
                        "powers": {"type": "array", "items": {"type": "string"}},
                        "limitations": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "role": {
                    "type": "string",
                    "enum": ["protagonist", "antagonist", "supporting", "minor"],
                    "description": "Character's role in the story"
                },
                "voice_profile": {
                    "type": "object",
                    "properties": {
                        "speech_patterns": {"type": "array", "items": {"type": "string"}},
                        "vocabulary_level": {"type": "string"},
                        "catchphrases": {"type": "array", "items": {"type": "string"}},
                        "tone": {"type": "string"}
                    }
                }
            },
            "required": ["character_id", "name", "role"]
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for character-related tasks"""
        return {
            "character_design": """## 任务: 设计人物角色

请为小说设计详细的人物角色档案。

### 设计要求

**主角档案:**
- 姓名: 具有角色特色的姓名
- 年龄: 符合角色定位
- 性别:
- 外貌: 详细的体貌特征描述 (100-200字)
- 性格特点:
  - 核心性格特质 (3-5个)
  - 优点 (2-3个)
  - 缺点 (2-3个，角色成长的突破口)
- 背景设定:
  - 出身/来历
  - 家庭状况
  - 成长经历
  - 职业/身份
- 核心动机:
  - 主要目标: 主角最想达成的目标
  - 次要目标: 支撑性目标
  - 恐惧: 主角最害怕的事物
  - 渴望: 主角内心深处的渴望
- 能力设定:
  - 技能: 擅长的技能
  - 特殊能力: 如适用
  - 限制: 能力的局限性
- 成长弧线:
  - 初始状态: 故事开始时的状态
  - 成长节点: 关键的成长转折点
  - 最终状态: 预期的成长结果
- 声音特征:
  - 说话习惯: 特殊的说话方式
  - 用词特点: 词汇风格
  - 口头禅: 标志性的话语
  - 语气基调: 整体语气

**配角设计:**
请设计 3-5 个重要配角，每个包含:
- 姓名和定位
- 与主角的关系
- 在故事中的作用
- 核心特征

**人物关系图:**
- 主要人物之间的关系网络
- 关系的动态变化

请以结构化的 JSON 格式输出。
""",

            "relationship_mapping": """## 任务: 构建人物关系图谱

### 已有角色
{characters}

### 关系映射要求

请分析并定义角色之间的关系:

1. **关系类型**: 家人/恋人/朋友/师徒/仇敌/竞争/其他
2. **关系强度**: 密切/一般/疏远
3. **关系性质**: 正面/负面/复杂
4. **关系动态**: 关系在故事中的变化方向
5. **关键场景**: 展现关系的重要场景

请以 JSON 格式输出关系图谱。
""",

            "character_consistency_check": """## 任务: 检查角色一致性

### 角色档案
{character_profiles}

### 检查内容
{content_to_check}

### 检查维度

1. **性格一致性**: 角色行为是否符合已设定性格
2. **声音一致性**: 对话是否符合角色说话风格
3. **能力一致性**: 角色表现的能力是否与设定匹配
4. **动机一致性**: 角色行为是否与其动机一致
5. **关系一致性**: 角色互动是否符合关系设定

### 输出要求

请输出 JSON 格式的检查结果:
```json
{{
  "is_consistent": true/false,
  "issues": ["具体的不一致问题"],
  "suggestions": ["修改建议"],
  "character_usage": {{
    "character_name": {{
      "appearances": 出现次数,
      "consistency_score": 一致性评分,
      "notes": "备注"
    }}
  }}
}}
```
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for character-related operations"""
        return [
            {
                "task_id": "character_design",
                "task_type": "人物设计",
                "description": "Design main and supporting characters with detailed profiles",
                "depends_on": ["大纲"],
                "metadata": {
                    "plugin": "character",
                    "operation": "design"
                }
            },
            {
                "task_id": "relationship_mapping",
                "task_type": "人物关系",
                "description": "Map relationships between characters",
                "depends_on": ["人物设计"],
                "metadata": {
                    "plugin": "character",
                    "operation": "relationships"
                }
            },
            {
                "task_id": "character_voice_check",
                "task_type": "对话检查",
                "description": "Check character voice consistency in dialogue",
                "depends_on": ["章节内容"],
                "metadata": {
                    "plugin": "character",
                    "operation": "voice_check"
                }
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate character data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Character data must be a dictionary"]
            )

        # Check required fields
        required_fields = ["character_id", "name", "role"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate role
        valid_roles = ["protagonist", "antagonist", "supporting", "minor"]
        if "role" in data and data["role"] not in valid_roles:
            errors.append(f"Invalid role: {data['role']}. Must be one of {valid_roles}")

        # Check for character completeness
        if "personality" not in data:
            warnings.append("Character missing personality traits")
        elif "traits" in data["personality"] and len(data["personality"]["traits"]) < 3:
            suggestions.append("Add more personality traits for depth")

        if "motivation" not in data:
            warnings.append("Character missing motivation/goals")
            suggestions.append("Define character motivation for better character development")

        # Check voice profile
        if "voice_profile" not in data:
            suggestions.append("Add voice profile for consistent dialogue")

        # Check relationships exist if this is not the first character
        character_count = len(self._characters)
        if character_count > 0 and "relationships" not in data:
            suggestions.append("Define relationships with existing characters")

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
        """Extract and store character data from task results"""
        task_type = task.get("task_type", "")

        if task_type == "人物设计":
            await self._extract_characters(result, context)
        elif task_type == "人物关系":
            await self._extract_relationships(result, context)
        elif task_type == "对话检查":
            await self._process_voice_check(result, context)

        return result

    async def _extract_characters(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract character profiles from design result"""
        try:
            # Try to parse as JSON
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                # Store characters
                if isinstance(data, dict):
                    if "characters" in data:
                        characters = data["characters"]
                    elif "主角" in data or "protagonist" in data:
                        characters = {"protagonist": data, "supporting": data.get("配角", [])}
                    else:
                        characters = data

                    for char_id, char_data in characters.items():
                        if isinstance(char_data, dict):
                            if "character_id" not in char_data:
                                char_data["character_id"] = char_id
                            self._characters[char_id] = char_data

                logger.info(f"Extracted {len(self._characters)} character profiles")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse character data as JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting characters: {e}")

    async def _extract_relationships(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract relationship data from result"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                # Store relationships
                if isinstance(data, dict) and "relationships" in data:
                    self._relationships = data["relationships"]
                    logger.info(f"Extracted relationship data for {len(self._relationships)} characters")

        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")

    async def _process_voice_check(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Process voice consistency check results"""
        # Store check results in context for future reference
        if "voice_check_results" not in context.metadata:
            context.metadata["voice_check_results"] = []
        context.metadata["voice_check_results"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        })

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with character information"""
        task_type = task.get("task_type", "")

        # Add character summaries to context
        if self._characters:
            context["characters"] = self._get_character_summaries()

        # Add relationships to context
        if self._relationships:
            context["character_relationships"] = self._relationships

        # For dialogue-related tasks, add voice profiles
        if "对话" in task_type or "章节" in task_type:
            voice_profiles = self._get_voice_profiles()
            if voice_profiles:
                context["character_voices"] = voice_profiles

        return context

    def _get_character_summaries(self) -> List[Dict[str, Any]]:
        """Get brief summaries of all characters"""
        summaries = []
        for char_id, char_data in self._characters.items():
            summary = {
                "id": char_id,
                "name": char_data.get("name", char_id),
                "role": char_data.get("role", "unknown"),
                "traits": char_data.get("personality", {}).get("traits", [])[:3]
            }
            summaries.append(summary)
        return summaries

    def _get_voice_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get voice profiles for all characters"""
        profiles = {}
        for char_id, char_data in self._characters.items():
            voice = char_data.get("voice_profile")
            if voice:
                profiles[char_id] = {
                    "name": char_data.get("name", char_id),
                    "voice": voice
                }
        return profiles

    def get_characters(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored character data"""
        return self._characters.copy()

    def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific character by ID"""
        return self._characters.get(character_id)

    def get_relationships(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all relationship data"""
        return self._relationships.copy()

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize character plugin and persist data"""
        logger.info("CharacterPlugin finalized")
        # Store final state in context for persistence
        context.metadata["characters"] = self._characters
        context.metadata["relationships"] = self._relationships
        context.metadata["character_arcs"] = self._arcs
