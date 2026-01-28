"""
Dialogue Plugin - Manages dialogue style and character voice consistency

This plugin handles:
- Character voice profiles
- Dialogue consistency checking
- Dialogue style validation
- Natural dialogue improvement suggestions
"""

import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
    ValidationResult,
    WritingContext,
)


class DialoguePlugin(NovelElementPlugin):
    """
    Plugin for managing dialogue quality and consistency

    Tracks character voices and validates dialogue consistency.
    """

    name = "dialogue"
    version = "1.0.0"
    description = "Manages dialogue style and character voice consistency"
    author = "Creative AutoGPT"

    # Dialogue state storage
    _voice_profiles: Dict[str, Dict[str, Any]] = {}
    _dialogue_samples: Dict[str, List[str]] = {}  # character_id -> sample dialogues
    _dialogue_issues: List[Dict[str, Any]] = []

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._voice_profiles = {}
        self._dialogue_samples = {}
        self._dialogue_issues = []

    async def on_init(self, context: WritingContext) -> None:
        """Initialize dialogue plugin with session context"""
        logger.info(f"DialoguePlugin initialized for session {context.session_id}")

        # Try to load from database first
        state = await self.load_state(context)
        if state:
            self._voice_profiles = state.get("voice_profiles", {})
            self._dialogue_samples = state.get("dialogue_samples", {})
            self._dialogue_issues = state.get("dialogue_issues", [])
            logger.info(f"Loaded {len(self._voice_profiles)} voice profiles from database")
        else:
            # Fallback to metadata
            if "voice_profiles" in context.metadata:
                self._voice_profiles = context.metadata.get("voice_profiles", {})

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for dialogue/voice profile data"""
        return {
            "type": "object",
            "title": "Voice Profile Schema",
            "description": "Schema for character voice profiles",
            "properties": {
                "character_id": {
                    "type": "string",
                    "description": "Character identifier"
                },
                "speech_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Common speech patterns"
                },
                "vocabulary_level": {
                    "type": "string",
                    "enum": ["formal", "casual", "slang", "archaic", "technical", "childish"],
                    "description": "Vocabulary style"
                },
                "sentence_structure": {
                    "type": "string",
                    "description": "Typical sentence structure pattern"
                },
                "catchphrases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Characteristic phrases"
                },
                "tone": {
                    "type": "string",
                    "enum": ["aggressive", "gentle", "sarcastic", "formal", "friendly", "cold", "enthusiastic"],
                    "description": "Default speaking tone"
                },
                "quirks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Speech quirks and habits"
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Frequently discussed topics"
                }
            },
            "required": ["character_id"]
        }

    def get_prompts(self) -> Dict[str, str]:
        """Get prompt templates for dialogue-related tasks"""
        return {
            "dialogue_check": """## 任务: 检查对话一致性

### 角色声音档案
{voice_profiles}

### 检查内容
{content_to_check}

### 检查维度

1. **声音一致性**: 每个角色的对话是否符合其声音设定
2. **说话习惯**: 是否使用了角色特有的说话方式
3. **用词风格**: 词汇水平是否一致
4. **口头禅**: 标志性话语是否得到体现
5. **语气基调**: 整体语气是否符合设定
6. **对话自然度**: 对话是否自然流畅
7. **对话推动**: 对话是否有效推动情节或展现角色

### 输出要求

请输出 JSON 格式的检查结果:
```json
{{
  "overall_score": 85,
  "is_consistent": true,
  "character_scores": {{
    "character_name": {{
      "consistency": 90,
      "naturalness": 85,
      "voice_match": 88,
      "issues": ["具体问题"],
      "suggestions": ["改进建议"]
    }}
  }},
  "overall_issues": ["整体问题"],
  "improvement_suggestions": ["改进建议"]
}}
```
""",

            "dialogue_improvement": """## 任务: 改进对话质量

### 原始对话
{original_dialogue}

### 角色设定
{character_profiles}

### 发现的问题
{issues}

### 改进要求

请根据角色设定改进对话:
1. 保持情节内容不变
2. 使对话更符合角色声音
3. 提升对话自然度
4. 增强对话的表现力

请直接输出改进后的对话片段。
""",

            "voice_profile_creation": """## 任务: 创建角色声音档案

### 角色信息
{character_info}

### 声音档案要求

为每个角色创建详细的声音档案:

**1. 说话模式:**
- 句式特点: (短句/长句/复杂句/简单句)
- 语言风格: (正式/随意/俚语/古风/技术/幼稚)
- 语速感: (快/中/慢)
- 停顿习惯

**2. 用词特征:**
- 常用词汇类型
- 避免使用的词汇
- 专业术语/方言

**3. 口头禅:**
- 3-5个标志性话语
- 使用场景

**4. 语气基调:**
- 默认语气
- 情绪变化时的语气
- 特殊情况下的语气

**5. 语言怪癖:**
- 特殊的语言习惯
- 口吃/重复/其他
- 情绪相关的语言特征

**6. 话题偏好:**
- 经常谈论的话题
- 避免的话题
- 表达观点的方式

请以 JSON 格式输出声音档案。
"""
        }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get task definitions for dialogue-related operations"""
        return [
            {
                "task_id": "dialogue_check",
                "task_type": "对话检查",
                "description": "Check dialogue consistency and quality",
                "depends_on": ["章节内容"],
                "metadata": {
                    "plugin": "dialogue",
                    "operation": "check"
                }
            }
        ]

    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """Validate dialogue/voice profile data"""
        errors = []
        warnings = []
        suggestions = []

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Voice profile data must be a dictionary"]
            )

        if "character_id" not in data:
            errors.append("Missing character_id")

        # Check for voice elements
        if not data.get("speech_patterns"):
            suggestions.append("Add speech patterns for better voice definition")

        if not data.get("catchphrases"):
            warnings.append("No catchphrases defined - consider adding some")

        if not data.get("tone"):
            suggestions.append("Define default tone for consistency")

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
        """Process dialogue-related task results"""
        task_type = task.get("task_type", "")

        if task_type == "对话检查":
            await self._process_dialogue_check(result, context)
        elif task_type == "人物设计":
            # Extract voice profiles from character design
            await self._extract_voice_profiles(result, context)

        return result

    async def _process_dialogue_check(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Process dialogue check results"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                # Store issues if any
                if "overall_issues" in data:
                    for issue in data.get("overall_issues", []):
                        self._dialogue_issues.append({
                            "issue": issue,
                            "timestamp": datetime.utcnow().isoformat()
                        })

                # Store character scores
                if "character_scores" in data:
                    for char_name, scores in data["character_scores"].items():
                        if char_name not in self._dialogue_samples:
                            self._dialogue_samples[char_name] = []

        except Exception as e:
            logger.error(f"Error processing dialogue check: {e}")

    async def _extract_voice_profiles(
        self,
        result: str,
        context: WritingContext,
    ) -> None:
        """Extract voice profiles from character design"""
        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                # Look for voice_profile section
                if isinstance(data, dict) and "voice_profile" in data:
                    voice_data = data["voice_profile"]
                    character_id = data.get("character_id") or data.get("name", "unknown")
                    voice_data["character_id"] = character_id
                    self._voice_profiles[character_id] = voice_data

        except Exception as e:
            logger.error(f"Error extracting voice profiles: {e}")

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enrich context with dialogue information"""
        task_type = task.get("task_type", "")

        if "对话" in task_type or "章节" in task_type:
            # Add voice profiles for dialogue generation
            if self._voice_profiles:
                context["voice_profiles"] = self._voice_profiles

        return context

    def set_voice_profile(self, character_id: str, profile: Dict[str, Any]) -> None:
        """Set a character's voice profile"""
        profile["character_id"] = character_id
        self._voice_profiles[character_id] = profile

    def get_voice_profile(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get a character's voice profile"""
        return self._voice_profiles.get(character_id)

    def get_all_voice_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all voice profiles"""
        return self._voice_profiles.copy()

    def add_dialogue_sample(self, character_id: str, dialogue: str) -> None:
        """Add a dialogue sample for a character"""
        if character_id not in self._dialogue_samples:
            self._dialogue_samples[character_id] = []
        self._dialogue_samples[character_id].append(dialogue)

    def get_dialogue_samples(self, character_id: str) -> List[str]:
        """Get dialogue samples for a character"""
        return self._dialogue_samples.get(character_id, []).copy()

    def extract_dialogue_from_content(self, content: str) -> Dict[str, List[str]]:
        """Extract dialogue lines from content"""
        dialogue_pattern = re.compile(r'"([^"]+)"')
        matches = dialogue_pattern.findall(content)

        # This is a simple extraction - in production would need better parsing
        # to associate dialogue with specific characters
        return {"extracted": matches}

    async def on_finalize(self, context: WritingContext) -> None:
        """Finalize dialogue plugin and persist data"""
        logger.info(f"DialoguePlugin finalized - persisting {len(self._voice_profiles)} voice profiles")

        # Persist to database
        await self.persist_all(context, {
            "voice_profiles": self._voice_profiles,
            "dialogue_samples": self._dialogue_samples,
            "dialogue_issues": self._dialogue_issues,
        })

        # Also store in metadata for compatibility
        context.metadata["voice_profiles"] = self._voice_profiles
        context.metadata["dialogue_samples"] = self._dialogue_samples
        context.metadata["dialogue_issues"] = self._dialogue_issues
