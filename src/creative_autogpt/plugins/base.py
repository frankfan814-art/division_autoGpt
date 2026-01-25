"""
Plugin base classes and interfaces

Provides the foundation for the novel element plugin system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class PluginPhase(str, Enum):
    """Phases when a plugin can intervene"""

    PLANNING = "planning"  # During task planning
    GENERATION = "generation"  # During content generation
    EVALUATION = "evaluation"  # During quality evaluation
    POST_PROCESS = "post_process"  # After content generation


@dataclass
class PluginConfig:
    """Configuration for a plugin"""

    enabled: bool = True
    priority: int = 50  # Execution priority (0-100, higher first)
    phases: List[PluginPhase] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "priority": self.priority,
            "phases": [p.value for p in self.phases],
            "settings": self.settings,
        }


@dataclass
class ValidationResult:
    """Result of validation"""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


@dataclass
class WritingContext:
    """Context shared across plugins during writing"""

    session_id: str
    goal: Dict[str, Any] = field(default_factory=dict)
    current_task: Optional[Dict[str, Any]] = None
    current_chapter: Optional[int] = None
    results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_result(self, task_id: str) -> Optional[Any]:
        """Get a task result"""
        return self.results.get(task_id)

    def set_result(self, task_id: str, result: Any) -> None:
        """Set a task result"""
        self.results[task_id] = result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "goal": self.goal,
            "current_task": self.current_task,
            "current_chapter": self.current_chapter,
            "results": self.results,
            "metadata": self.metadata,
        }


class NovelElementPlugin(ABC):
    """
    Base class for novel element plugins

    Each plugin manages a specific element type:
    - Characters, Worldview, Events, etc.
    - Provides schema, prompts, validation
    - Can inject/modify content during generation
    """

    # Plugin metadata
    name: str = ""  # Unique plugin name
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)  # Required plugins

    # Plugin configuration
    config: PluginConfig = field(default_factory=PluginConfig)

    def __init__(self, config: Optional[PluginConfig] = None):
        """
        Initialize plugin

        Args:
            config: Plugin configuration
        """
        if config:
            self.config = config
        logger.debug(f"Initialized plugin: {self.name}")

    @abstractmethod
    async def on_init(self, context: WritingContext) -> None:
        """
        Called when plugin is initialized

        Args:
            context: Writing context
        """
        pass

    async def on_before_task(
        self,
        task: Dict[str, Any],
        context: WritingContext,
    ) -> Dict[str, Any]:
        """
        Called before a task is executed

        Can modify the task configuration.

        Args:
            task: Task configuration
            context: Writing context

        Returns:
            Modified task configuration
        """
        return task

    async def on_after_task(
        self,
        task: Dict[str, Any],
        result: str,
        context: WritingContext,
    ) -> str:
        """
        Called after a task is executed

        Can modify the generated result.

        Args:
            task: Task configuration
            result: Generated content
            context: Writing context

        Returns:
            Modified content
        """
        return result

    async def on_finalize(self, context: WritingContext) -> None:
        """
        Called when writing session is complete

        Args:
            context: Writing context
        """
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the data schema for this element type

        Returns:
            Schema definition (JSON Schema compatible)
        """
        pass

    @abstractmethod
    def get_prompts(self) -> Dict[str, str]:
        """
        Get prompt templates for this element type

        Returns:
            Dict of prompt_name -> prompt_template
        """
        pass

    @abstractmethod
    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Get task definitions for this element type

        Returns:
            List of task definitions
        """
        pass

    @abstractmethod
    async def validate(
        self,
        data: Any,
        context: WritingContext,
    ) -> ValidationResult:
        """
        Validate data for this element type

        Args:
            data: Data to validate
            context: Writing context

        Returns:
            Validation result
        """
        pass

    async def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enrich context with element-specific information

        Args:
            task: Task configuration
            context: Current context

        Returns:
            Enriched context
        """
        return context

    async def generate_content(
        self,
        task_type: str,
        context: WritingContext,
    ) -> Optional[str]:
        """
        Optional: Generate content for this element type

        Args:
            task_type: Type of task
            context: Writing context

        Returns:
            Generated content, or None if not applicable
        """
        return None

    def get_dependencies(self) -> List[str]:
        """Get list of plugin dependencies"""
        return self.dependencies.copy()

    def is_enabled(self) -> bool:
        """Check if plugin is enabled"""
        return self.config.enabled

    def get_priority(self) -> int:
        """Get plugin execution priority"""
        return self.config.priority

    def get_phases(self) -> List[PluginPhase]:
        """Get phases when plugin should be invoked"""
        return self.config.phases.copy()
