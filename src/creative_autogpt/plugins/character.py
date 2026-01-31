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

        # Try to load from database first
        state = await self.load_state(context)
        if state:
            self._characters = state.get("characters", {})
            self._relationships = state.get("relationships", {})
            self._arcs = state.get("arcs", {})
            logger.info(f"Loaded {len(self._characters)} characters from database")
        else:
            # Fallback to metadata
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

为小说设计主角和重要配角的角色档案，融入哲学思想塑造人物灵魂。

### 人物哲学定位

每个人物应体现特定的哲学流派或价值观，形成思想碰撞:

**主角哲学特质 (核心):**
- **核心价值观**: 信奉什么哲学思想？(如儒家"仁义"、道家"自然"、墨家"兼爱")
- **道德准则**: 做事的原则和底线 (如"有所为有所不为")
- **人生追求**: 终极理想 (如"内圣外王""逍遥自在""兼济天下")
- **处世智慧**: 处理事情的方式 (如"以柔克刚""中庸之道")

**主角档案结构**

- **基本信息**: 姓名、年龄、性别、外貌特征(100-200字)
- **性格特点**: 核心特质(3-5个)、优点、缺点(成长的突破口)
  - 性格应符合其哲学定位 (如信奉儒家者重仁义，信奉道家者重自然)
- **背景设定**: 出身来历、家庭状况、成长经历、职业身份
- **核心动机**: 主要目标、次要目标、恐惧、渴望
  - 动机应源于其哲学信仰 (如"保护弱小"源于"仁者爱人")
- **能力设定**: 技能、特殊能力(如有)、限制条件
- **成长弧线**: 初始状态、成长节点、最终状态
  - 成长应包含心性修养 (不仅是力量提升，更是境界突破)
- **声音特征**: 说话习惯、用词特点、口头禅、语气基调
  - 可引用哲学经典作为口头禅 (如"天行健，君子以自强不息")
- **哲学修养**: 
  - 座右铭 (如"知行合一")
  - 引用经典的习惯 (在关键时刻引用《道德经》《论语》等)
  - 思辨能力 (对世事有独特哲学见解)

### 配角设计

设计 3-5 个重要配角，每个配角应有明确的哲学定位:

**配角哲学类型示例:**
1. **儒家君子型**: 重仁义礼智信，有社会责任
2. **道家隐士型**: 追求逍遥自在，淡泊名利
3. **法家实干型**: 重规则效率，冷酷理性
4. **墨家侠义型**: 兼爱非攻，行侠仗义
5. **极端功利型**: 唯利是图，成王败寇 (反派或对立面)

每个配角包含: 姓名、定位、与主角关系、故事作用、核心特征、**哲学流派**。

### 人物关系

定义主要人物之间的关系网络及动态变化，体现:
- **志同道合**: 哲学理念相近者成为盟友
- **道不同不相为谋**: 价值观冲突者成为对手
- **思想碰撞**: 不同哲学流派人物的对话和冲突

请以 JSON 格式输出结构化数据。
""",

            "relationship_mapping": """## 任务: 构建人物关系图谱

### 已有角色
{characters}

### 关系定义要求

对每对角色关系，定义:
- 关系类型: 家人/恋人/朋友/师徒/仇敌/竞争/其他
- 关系强度: 密切/一般/疏远
- 关系性质: 正面/负面/复杂
- 关系动态: 故事中的变化方向
- 关键场景: 展现关系的重要场景

请以 JSON 格式输出关系图谱。
""",

            "character_consistency_check": """## 任务: 检查角色一致性

### 角色档案
{character_profiles}

### 检查内容
{content_to_check}

### 检查维度

1. 性格一致性: 角色行为是否符合已设定性格
2. 声音一致性: 对话是否符合角色说话风格
3. 能力一致性: 角色表现的能力是否与设定匹配
4. 动机一致性: 角色行为是否与其动机一致
5. 关系一致性: 角色互动是否符合关系设定

### 输出格式

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
                "description": "Design main and supporting characters with detailed profiles and relationships",
                "depends_on": ["大纲", "世界观规则", "势力设计"],
                "metadata": {
                    "plugin": "character",
                    "operation": "design"
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
            # Relationships are included in character design output
            await self._extract_relationships(result, context)

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

    # ========== Character Arc Tracking Methods ==========

    def create_arc(
        self,
        character_id: str,
        arc_name: str,
        arc_type: str,
        start_state: Dict[str, Any],
        end_state: Dict[str, Any],
        milestone_chapters: Optional[List[int]] = None,
    ) -> str:
        """
        Create a character development arc

        Args:
            character_id: Character ID
            arc_name: Name of the arc
            arc_type: Type of arc (e.g., "growth", "fall", "redemption", "coming_of_age")
            start_state: Character's state at arc start
            end_state: Character's state at arc end
            milestone_chapters: Chapters where key arc events occur

        Returns:
            Arc ID
        """
        import uuid
        arc_id = str(uuid.uuid4())

        if character_id not in self._arcs:
            self._arcs[character_id] = []

        arc = {
            "arc_id": arc_id,
            "name": arc_name,
            "type": arc_type,
            "start_state": start_state,
            "end_state": end_state,
            "current_state": start_state.copy(),
            "milestone_chapters": milestone_chapters or [],
            "milestones_reached": [],
            "completed": False,
            "created_at": datetime.utcnow().isoformat(),
        }

        self._arcs[character_id].append(arc)
        logger.info(f"Created arc '{arc_name}' for character {character_id}")
        return arc_id

    def record_milestone(
        self,
        character_id: str,
        arc_id: str,
        chapter_index: int,
        milestone_description: str,
        state_changes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a milestone in character's arc

        Args:
            character_id: Character ID
            arc_id: Arc ID
            chapter_index: Chapter where milestone occurs
            milestone_description: Description of the milestone
            state_changes: Changes to character's state

        Returns:
            True if successful
        """
        if character_id not in self._arcs:
            logger.warning(f"No arcs found for character {character_id}")
            return False

        arc = next((a for a in self._arcs[character_id] if a["arc_id"] == arc_id), None)
        if not arc:
            logger.warning(f"Arc {arc_id} not found for character {character_id}")
            return False

        milestone = {
            "chapter": chapter_index,
            "description": milestone_description,
            "state_changes": state_changes or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        arc["milestones_reached"].append(milestone)

        # Update current state if state changes provided
        if state_changes:
            arc["current_state"].update(state_changes)

        logger.info(f"Recorded milestone for {character_id} at chapter {chapter_index}")
        return True

    def complete_arc(
        self,
        character_id: str,
        arc_id: str,
        final_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark an arc as completed

        Args:
            character_id: Character ID
            arc_id: Arc ID
            final_state: Final character state (overrides planned end state)

        Returns:
            True if successful
        """
        if character_id not in self._arcs:
            return False

        arc = next((a for a in self._arcs[character_id] if a["arc_id"] == arc_id), None)
        if not arc:
            return False

        arc["completed"] = True
        arc["completed_at"] = datetime.utcnow().isoformat()

        if final_state:
            arc["current_state"] = final_state

        logger.info(f"Completed arc '{arc['name']}' for character {character_id}")
        return True

    def get_character_arcs(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all arcs for a character"""
        return self._arcs.get(character_id, []).copy()

    def get_arc_progress(self, character_id: str, arc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get arc progress information

        Returns:
            Dict with progress info or None if not found
        """
        arcs = self._arcs.get(character_id, [])
        arc = next((a for a in arcs if a["arc_id"] == arc_id), None)

        if not arc:
            return None

        # Calculate progress based on milestones
        total_milestones = len(arc.get("milestone_chapters", []))
        reached_milestones = len(arc.get("milestones_reached", []))

        progress = {
            "arc_id": arc_id,
            "name": arc["name"],
            "type": arc["type"],
            "completed": arc["completed"],
            "milestones_planned": total_milestones,
            "milestones_reached": reached_milestones,
            "progress_percent": (reached_milestones / total_milestones * 100) if total_milestones > 0 else 0,
            "current_state": arc["current_state"],
            "start_state": arc["start_state"],
            "end_state": arc["end_state"],
        }

        return progress

    def check_arc_consistency(
        self,
        character_id: str,
        current_chapter: int,
    ) -> ValidationResult:
        """
        Check if character's arc progression is consistent

        Args:
            character_id: Character ID
            current_chapter: Current chapter index

        Returns:
            Validation result with arc consistency issues
        """
        errors = []
        warnings = []
        suggestions = []

        arcs = self._arcs.get(character_id, [])

        for arc in arcs:
            # Check if milestones are being tracked
            if arc["milestone_chapters"]:
                missed_milestones = [
                    ch for ch in arc["milestone_chapters"]
                    if ch <= current_chapter and
                    not any(m["chapter"] == ch for m in arc["milestones_reached"])
                ]

                if missed_milestones:
                    warnings.append(
                        f"Arc '{arc['name']}': Missed milestones at chapters {missed_milestones}"
                    )

            # Check if arc should be completed
            if arc["milestone_chapters"] and current_chapter > max(arc["milestone_chapters"]):
                if not arc["completed"]:
                    suggestions.append(
                        f"Arc '{arc['name']}' should be completed - all milestone chapters passed"
                    )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize character plugin and persist data"""
        logger.info(f"CharacterPlugin finalized - persisting {len(self._characters)} characters")

        # Persist to database
        await self.persist_all(context, {
            "characters": self._characters,
            "relationships": self._relationships,
            "arcs": self._arcs,
        })

        # Also store in metadata for compatibility
        context.metadata["characters"] = self._characters
        context.metadata["relationships"] = self._relationships
        context.metadata["character_arcs"] = self._arcs
