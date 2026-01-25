"""
Plugin Manager - Manages the plugin lifecycle and execution

Coordinates plugins, handles dependencies, and executes hooks.
"""

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Type

from loguru import logger

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
    PluginPhase,
    ValidationResult,
    WritingContext,
)


class PluginDependencyError(Exception):
    """Raised when plugin dependencies are not met"""

    pass


class PluginNotFoundError(Exception):
    """Raised when a required plugin is not found"""

    pass


class PluginManager:
    """
    Manages the plugin system

    Responsibilities:
    - Register/unregister plugins
    - Enable/disable plugins
    - Resolve dependencies
    - Execute plugin hooks in correct order
    """

    def __init__(self):
        """Initialize plugin manager"""
        # Registered plugins (name -> plugin instance)
        self._plugins: Dict[str, NovelElementPlugin] = {}

        # Enabled plugins (name -> plugin instance)
        self._enabled: Dict[str, NovelElementPlugin] = {}

        # Load order (sorted by priority)
        self._load_order: List[str] = []

        logger.info("PluginManager initialized")

    def register(self, plugin: NovelElementPlugin) -> None:
        """
        Register a plugin

        Args:
            plugin: Plugin instance to register

        Raises:
            PluginDependencyError: If dependencies are not met
        """
        # Check for duplicate name
        if plugin.name in self._plugins:
            logger.warning(f"Plugin '{plugin.name}' already registered, replacing")

        # Check dependencies
        for dep in plugin.get_dependencies():
            if dep not in self._plugins:
                raise PluginDependencyError(
                    f"Plugin '{plugin.name}' requires '{dep}' which is not registered"
                )

        # Register the plugin
        self._plugins[plugin.name] = plugin

        # Re-calculate load order
        self._recalculate_load_order()

        # Auto-enable if config says so
        if plugin.is_enabled():
            self.enable(plugin.name)

        logger.info(
            f"Registered plugin: {plugin.name} v{plugin.version} "
            f"(priority: {plugin.get_priority()})"
        )

    def unregister(self, name: str) -> bool:
        """
        Unregister a plugin

        Args:
            name: Plugin name

        Returns:
            True if successful, False if plugin not found
        """
        if name not in self._plugins:
            return False

        # Disable first
        self.disable(name)

        # Remove from registry
        del self._plugins[name]

        # Re-calculate load order
        self._recalculate_load_order()

        logger.info(f"Unregistered plugin: {name}")
        return True

    def enable(self, name: str, config: Optional[PluginConfig] = None) -> None:
        """
        Enable a plugin

        Args:
            name: Plugin name
            config: Optional new configuration

        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' not found")

        plugin = self._plugins[name]

        # Update config if provided
        if config:
            plugin.config = config

        # Check dependencies
        for dep in plugin.get_dependencies():
            if dep not in self._enabled:
                logger.warning(
                    f"Enabling plugin '{name}' but dependency '{dep}' is not enabled"
                )

        # Enable the plugin
        self._enabled[name] = plugin

        logger.info(f"Enabled plugin: {name}")

    def disable(self, name: str) -> None:
        """
        Disable a plugin

        Args:
            name: Plugin name
        """
        if name in self._enabled:
            del self._enabled[name]
            logger.info(f"Disabled plugin: {name}")

    def is_enabled(self, name: str) -> bool:
        """Check if a plugin is enabled"""
        return name in self._enabled

    def get(self, name: str) -> Optional[NovelElementPlugin]:
        """Get a plugin by name"""
        return self._plugins.get(name)

    def list_all(self) -> List[str]:
        """List all registered plugin names"""
        return list(self._plugins.keys())

    def list_enabled(self) -> List[str]:
        """List enabled plugin names"""
        return list(self._enabled.keys())

    def get_load_order(self) -> List[str]:
        """Get the plugin load order"""
        return self._load_order.copy()

    def _recalculate_load_order(self) -> None:
        """Re-calculate plugin load order based on priority"""
        # Sort by priority (higher first), then by name for stability
        sorted_plugins = sorted(
            self._plugins.items(),
            key=lambda x: (-x[1].get_priority(), x[0])
        )

        self._load_order = [name for name, _ in sorted_plugins]

        logger.debug(f"Plugin load order: {self._load_order}")

    async def run_hook(
        self,
        hook_name: str,
        *args,
        **kwargs,
    ) -> List[Any]:
        """
        Run a hook on all enabled plugins

        Args:
            hook_name: Name of the hook method
            *args: Positional arguments for the hook
            **kwargs: Keyword arguments for the hook

        Returns:
            List of results from each plugin
        """
        results = []

        for name in self._load_order:
            if name not in self._enabled:
                continue

            plugin = self._enabled[name]

            # Check if plugin has the hook method
            if not hasattr(plugin, hook_name):
                continue

            hook = getattr(plugin, hook_name)

            # Skip if not callable
            if not callable(hook):
                continue

            try:
                # Execute the hook
                if hook_name in ("on_init", "on_finalize"):
                    # These hooks don't return values
                    await hook(*args, **kwargs)
                else:
                    # These hooks may return modified values
                    result = await hook(*args, **kwargs)
                    results.append(result)

            except Exception as e:
                logger.error(
                    f"Plugin '{name}' hook '{hook_name}' failed: {e}",
                    exc_info=True,
                )

        return results

    async def initialize_all(self, context: WritingContext) -> None:
        """
        Initialize all enabled plugins

        Args:
            context: Writing context
        """
        logger.info(f"Initializing {len(self._enabled)} plugins")

        await self.run_hook("on_init", context)

    async def finalize_all(self, context: WritingContext) -> None:
        """
        Finalize all enabled plugins

        Args:
            context: Writing context
        """
        logger.info("Finalizing all plugins")

        await self.run_hook("on_finalize", context)

    async def before_task(
        self,
        task: Dict[str, Any],
        context: WritingContext,
    ) -> Dict[str, Any]:
        """
        Run before-task hooks

        Args:
            task: Task configuration
            context: Writing context

        Returns:
            Modified task configuration
        """
        results = await self.run_hook("on_before_task", task, context)

        # Apply modifications in order (each plugin sees previous modifications)
        modified_task = task
        for result in results:
            if isinstance(result, dict):
                modified_task = result

        return modified_task

    async def after_task(
        self,
        task: Dict[str, Any],
        result: str,
        context: WritingContext,
    ) -> str:
        """
        Run after-task hooks

        Args:
            task: Task configuration
            result: Generated content
            context: Writing context

        Returns:
            Modified content
        """
        results = await self.run_hook("on_after_task", task, result, context)

        # Apply modifications in order
        modified_result = result
        for plugin_result in results:
            if isinstance(plugin_result, str):
                modified_result = plugin_result

        return modified_result

    async def validate_all(
        self,
        data: Any,
        context: WritingContext,
    ) -> List[ValidationResult]:
        """
        Run validation on all enabled plugins

        Args:
            data: Data to validate
            context: Writing context

        Returns:
            List of validation results
        """
        results = []

        for name in self._load_order:
            if name not in self._enabled:
                continue

            plugin = self._enabled[name]

            try:
                result = await plugin.validate(data, context)
                results.append(result)

                if not result.valid:
                    logger.warning(
                        f"Plugin '{name}' validation failed: {result.errors}"
                    )

            except Exception as e:
                logger.error(f"Plugin '{name}' validation error: {e}")
                results.append(
                    ValidationResult(
                        valid=False,
                        errors=[f"Validation error: {str(e)}"],
                    )
                )

        return results

    def get_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all plugin schemas

        Returns:
            Dict of plugin_name -> schema
        """
        schemas = {}

        for name, plugin in self._plugins.items():
            try:
                schema = plugin.get_schema()
                schemas[name] = schema
            except Exception as e:
                logger.error(f"Failed to get schema for '{name}': {e}")

        return schemas

    def get_prompts(self) -> Dict[str, Dict[str, str]]:
        """
        Get all plugin prompts

        Returns:
            Dict of plugin_name -> prompts
        """
        all_prompts = {}

        for name, plugin in self._plugins.items():
            try:
                prompts = plugin.get_prompts()
                all_prompts[name] = prompts
            except Exception as e:
                logger.error(f"Failed to get prompts for '{name}': {e}")

        return all_prompts

    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all plugin task definitions

        Returns:
            List of task definitions
        """
        all_tasks = []

        for name in self._load_order:
            if name not in self._enabled:
                continue

            plugin = self._enabled[name]

            try:
                tasks = plugin.get_tasks()
                all_tasks.extend(tasks)
            except Exception as e:
                logger.error(f"Failed to get tasks for '{name}': {e}")

        return all_tasks

    def enrich_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enrich context using all enabled plugins

        Args:
            task: Task configuration
            context: Current context

        Returns:
            Enriched context
        """
        for name in self._load_order:
            if name not in self._enabled:
                continue

            plugin = self._enabled[name]

            try:
                context = plugin.enrich_context(task, context)
            except Exception as e:
                logger.error(f"Plugin '{name}' context enrichment failed: {e}")

        return context

    def get_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a plugin

        Args:
            name: Plugin name

        Returns:
            Plugin information dict
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return None

        return {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
            "author": plugin.author,
            "enabled": self.is_enabled(name),
            "priority": plugin.get_priority(),
            "dependencies": plugin.get_dependencies(),
            "config": plugin.config.to_dict(),
        }

    def get_all_info(self) -> List[Dict[str, Any]]:
        """Get information about all plugins"""
        return [
            self.get_info(name)
            for name in self._plugins.keys()
        ]
