"""
Plugin base classes and interfaces

Provides the foundation for the novel element plugin system.
"""

import asyncio
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
    storage: Optional[Any] = None  # SessionStorage reference for plugin persistence

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

    async def save_state(
        self,
        context: WritingContext,
        data_key: str,
        data_value: Any,
    ) -> bool:
        """
        Save plugin state to database

        Args:
            context: Writing context
            data_key: Key for the data
            data_value: Data to store (must be JSON-serializable)

        Returns:
            True if successful
        """
        if context.storage:
            try:
                return await context.storage.save_plugin_data(
                    session_id=context.session_id,
                    plugin_name=self.name,
                    data_key=data_key,
                    data_value=data_value,
                )
            except Exception as e:
                logger.error(f"Failed to save plugin state for {self.name}.{data_key}: {e}")
        return False

    async def load_state(
        self,
        context: WritingContext,
    ) -> Dict[str, Any]:
        """
        Load plugin state from database

        Args:
            context: Writing context

        Returns:
            Dict of data_key -> data_value
        """
        if context.storage:
            try:
                return await context.storage.load_plugin_data(
                    session_id=context.session_id,
                    plugin_name=self.name,
                )
            except Exception as e:
                logger.error(f"Failed to load plugin state for {self.name}: {e}")
        return {}

    async def delete_state(
        self,
        context: WritingContext,
    ) -> bool:
        """
        Delete plugin state from database

        Args:
            context: Writing context

        Returns:
            True if successful
        """
        if context.storage:
            try:
                return await context.storage.delete_plugin_data(
                    session_id=context.session_id,
                    plugin_name=self.name,
                )
            except Exception as e:
                logger.error(f"Failed to delete plugin state for {self.name}: {e}")
        return False

    async def persist_all(
        self,
        context: WritingContext,
        state_dict: Dict[str, Any],
    ) -> bool:
        """
        Persist all plugin state data at once

        Args:
            context: Writing context
            state_dict: Dict of data_key -> data_value to persist

        Returns:
            True if all saves succeeded
        """
        if not context.storage:
            return False

        success = True
        for key, value in state_dict.items():
            if not await self.save_state(context, key, value):
                success = False
        return success

    # ========== Error Handling and Recovery Methods ==========

    async def safe_execute(
        self,
        func,
        *args,
        error_message: str = "Operation failed",
        default_return=None,
        **kwargs,
    ) -> Any:
        """
        Safely execute a function with error handling

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            error_message: Error message to log
            default_return: Default return value on error
            **kwargs: Keyword arguments for the function

        Returns:
            Function result or default_return on error
        """
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{error_message} in plugin '{self.name}': {e}", exc_info=True)
            return default_return

    def handle_json_parse_error(
        self,
        result: str,
        default_value: Any = None,
    ) -> Any:
        """
        Safely parse JSON with error handling

        Args:
            result: String to parse as JSON
            default_value: Default value if parsing fails

        Returns:
            Parsed JSON or default_value
        """
        import json

        try:
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]
                return json.loads(json_str)
            elif "[" in result and "]" in result:
                json_start = result.find("[")
                json_end = result.rfind("]") + 1
                json_str = result[json_start:json_end]
                return json.loads(json_str)
            else:
                return default_value if default_value is not None else {}
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in plugin '{self.name}': {e}")
            return default_value if default_value is not None else {}

    async def backup_state(self, context: WritingContext) -> bool:
        """
        Create a backup of current plugin state

        Args:
            context: Writing context

        Returns:
            True if backup succeeded
        """
        try:
            # Collect state from plugin instance
            state = {}
            for attr_name in dir(self):
                if attr_name.startswith("_") and not attr_name.startswith("__"):
                    attr = getattr(self, attr_name)
                    if isinstance(attr, (dict, list)) and not callable(attr):
                        state[attr_name] = attr

            # Save with backup timestamp
            backup_key = f"backup_{int(datetime.utcnow().timestamp())}"
            return await self.save_state(context, backup_key, state)
        except Exception as e:
            logger.error(f"Failed to create backup for plugin '{self.name}': {e}")
            return False

    async def restore_from_backup(
        self,
        context: WritingContext,
        backup_timestamp: Optional[int] = None,
    ) -> bool:
        """
        Restore plugin state from backup

        Args:
            context: Writing context
            backup_timestamp: Optional specific backup timestamp (uses latest if None)

        Returns:
            True if restore succeeded
        """
        try:
            state = await self.load_state(context)
            if not state:
                logger.warning(f"No backup found for plugin '{self.name}'")
                return False

            # Find the backup
            backup_key = None
            if backup_timestamp:
                backup_key = f"backup_{backup_timestamp}"
            else:
                # Find the latest backup
                backup_keys = [k for k in state.keys() if k.startswith("backup_")]
                if backup_keys:
                    backup_key = max(backup_keys)

            if not backup_key or backup_key not in state:
                logger.warning(f"Backup not found for plugin '{self.name}'")
                return False

            # Restore state
            backup_state = state[backup_key]
            for attr_name, attr_value in backup_state.items():
                if hasattr(self, attr_name):
                    setattr(self, attr_name, attr_value)

            logger.info(f"Restored plugin '{self.name}' from backup")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup for plugin '{self.name}': {e}")
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get plugin health status

        Returns:
            Dict with health status information
        """
        return {
            "plugin_name": self.name,
            "is_enabled": self.is_enabled(),
            "has_errors": False,  # Can be overridden by plugins
            "last_error": None,
            "state_size": sum(
                len(str(getattr(self, attr)))
                for attr in dir(self)
                if attr.startswith("_") and not attr.startswith("__")
                and not callable(getattr(self, attr))
            ),
        }

    async def validate_and_repair(
        self,
        context: WritingContext,
    ) -> ValidationResult:
        """
        Validate plugin state and attempt repairs

        Args:
            context: Writing context

        Returns:
            Validation result with repair actions taken
        """
        errors = []
        warnings = []
        suggestions = []
        repairs_made = []

        # Check for corrupted state
        for attr_name in dir(self):
            if attr_name.startswith("_") and not attr_name.startswith("__"):
                attr = getattr(self, attr_name)
                if isinstance(attr, dict):
                    # Check for corrupted dict values
                    try:
                        _ = len(attr)
                        _ = attr.keys()
                    except Exception:
                        errors.append(f"Corrupted dictionary: {attr_name}")
                        # Attempt repair
                        try:
                            setattr(self, attr_name, {})
                            repairs_made.append(f"Repaired corrupted dictionary: {attr_name}")
                        except Exception:
                            pass
                elif isinstance(attr, list):
                    # Check for corrupted list values
                    try:
                        _ = len(attr)
                        _ = attr[0] if attr else None
                    except Exception:
                        errors.append(f"Corrupted list: {attr_name}")
                        # Attempt repair
                        try:
                            setattr(self, attr_name, [])
                            repairs_made.append(f"Repaired corrupted list: {attr_name}")
                        except Exception:
                            pass

        if repairs_made:
            suggestions.append(f"Repairs made: {repairs_made}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )
