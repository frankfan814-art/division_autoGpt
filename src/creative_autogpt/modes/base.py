"""
Base Mode class and mode registry

Provides the foundation for different writing modes (novel, script, etc.)
"""

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from creative_autogpt.core.task_planner import TaskDefinition, NovelTaskType
from creative_autogpt.core.vector_memory import MemoryContext


class WritingMode(str, Enum):
    """Supported writing modes"""

    NOVEL = "novel"
    SCRIPT = "script"
    LARP = "larp"  # 剧本杀


class Mode:
    """
    Base class for writing modes

    Each mode defines:
    - Task types and their execution order
    - Prompt templates for each task type
    - Evaluation criteria
    - Output format requirements
    """

    mode_type: WritingMode = WritingMode.NOVEL
    name: str = "Base Mode"
    description: str = ""

    # Task definitions for this mode
    task_definitions: List[TaskDefinition] = []

    # Prompt templates (task_type -> template)
    prompt_templates: Dict[str, str] = {}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize mode

        Args:
            config: Optional mode configuration
        """
        self.config = config or {}
        logger.debug(f"Initialized mode: {self.name}")

    @abstractmethod
    async def build_prompt(
        self,
        task_type: str,
        context: MemoryContext,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build prompt for a task type

        Args:
            task_type: The type of task
            context: Memory context
            metadata: Additional metadata

        Returns:
            The constructed prompt
        """
        pass

    async def build_improved_prompt(
        self,
        task_type: str,
        previous_result: str,
        feedback: str,
        context: MemoryContext,
    ) -> str:
        """
        Build an improved prompt for rewriting

        Args:
            task_type: The type of task
            previous_result: Previous generation result
            feedback: Feedback/evaluation to address
            context: Memory context

        Returns:
            The improved prompt
        """
        prompt = f"""## 改进任务

任务类型: {task_type}

## 原始结果
```
{previous_result[:3000]}
```

## 反馈意见
{feedback}

## 要求
请根据反馈意见改进内容，保持原有的核心结构和主题，仅改进需要修正的部分。

## 输出
请直接输出改进后的内容，不需要解释或说明。
"""
        return prompt

    def get_task_definitions(self) -> List[TaskDefinition]:
        """Get task definitions for this mode"""
        return self.task_definitions

    def get_prompt_template(self, task_type: str) -> Optional[str]:
        """Get prompt template for a task type"""
        return self.prompt_templates.get(task_type)

    def get_evaluation_criteria(self, task_type: str) -> Dict[str, float]:
        """Get evaluation criteria for a task type"""
        # Default criteria
        return {
            "coherence": 0.2,
            "creativity": 0.2,
            "quality": 0.2,
            "consistency": 0.2,
            "goal_alignment": 0.2,
        }


class ModeRegistry:
    """Registry for writing modes"""

    _modes: Dict[WritingMode, type] = {}

    @classmethod
    def register(cls, mode_class: type) -> None:
        """Register a mode class"""
        if hasattr(mode_class, "mode_type"):
            cls._modes[mode_class.mode_type] = mode_class
            logger.info(f"Registered mode: {mode_class.mode_type.value}")

    @classmethod
    def get(cls, mode_type: WritingMode) -> Optional[type]:
        """Get a mode class by type"""
        return cls._modes.get(mode_type)

    @classmethod
    def create(cls, mode_type: WritingMode, config: Optional[Dict[str, Any]] = None) -> Optional[Mode]:
        """Create a mode instance"""
        mode_class = cls.get(mode_type)
        if mode_class:
            return mode_class(config=config)
        return None

    @classmethod
    def list_modes(cls) -> List[str]:
        """List all registered mode types"""
        return [m.value for m in cls._modes.keys()]

    @classmethod
    def is_registered(cls, mode_type: WritingMode) -> bool:
        """Check if a mode is registered"""
        return mode_type in cls._modes


def register_mode(mode_class: type) -> None:
    """Decorator to register a mode class"""
    ModeRegistry.register(mode_class)
    return mode_class
