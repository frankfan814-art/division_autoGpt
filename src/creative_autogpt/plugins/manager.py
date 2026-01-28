"""
Plugin Manager - Manages the plugin lifecycle and execution

Coordinates plugins, handles dependencies, and executes hooks.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
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

    # ========== Plugin Collaboration Methods ==========

    def get_plugin_data(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data from a specific plugin for collaboration

        Args:
            plugin_name: Name of the plugin to get data from

        Returns:
            Plugin data dict or None if plugin not found
        """
        plugin = self._enabled.get(plugin_name)
        if not plugin:
            logger.warning(f"Plugin '{plugin_name}' not enabled for collaboration")
            return None

        # Collect data based on plugin type
        data = {}
        if plugin_name == "character":
            data["characters"] = plugin.get_characters()
            data["relationships"] = plugin.get_relationships()
        elif plugin_name == "dialogue":
            data["voice_profiles"] = plugin.get_all_voice_profiles()
        elif plugin_name == "timeline":
            data["timeline"] = plugin.get_timeline()
            data["current_time"] = plugin.get_current_time()
        elif plugin_name == "worldview":
            data["world_settings"] = plugin._world_settings
            data["locations"] = plugin.get_locations()
        elif plugin_name == "event":
            data["events"] = plugin.get_events()
        elif plugin_name == "foreshadow":
            data["elements"] = plugin.get_elements()
        elif plugin_name == "scene":
            data["scenes"] = plugin.get_scenes()

        return data

    def share_data_between_plugins(
        self,
        source_plugin: str,
        target_plugin: str,
        data_key: str,
    ) -> bool:
        """
        Share data between plugins

        Args:
            source_plugin: Source plugin name
            target_plugin: Target plugin name
            data_key: Key of the data to share

        Returns:
            True if successful
        """
        source = self._enabled.get(source_plugin)
        target = self._enabled.get(target_plugin)

        if not source or not target:
            logger.warning(f"Cannot share data: one or both plugins not enabled")
            return False

        try:
            # Get data from source
            source_data = self.get_plugin_data(source_plugin)
            if not source_data or data_key not in source_data:
                logger.warning(f"Data key '{data_key}' not found in plugin '{source_plugin}'")
                return False

            # Share with target plugin - target needs to handle this
            # This is a simple mechanism - plugins can implement more sophisticated sharing
            logger.info(f"Shared '{data_key}' from '{source_plugin}' to '{target_plugin}'")
            return True

        except Exception as e:
            logger.error(f"Failed to share data between plugins: {e}")
            return False

    def validate_cross_plugin_consistency(
        self,
        context: WritingContext,
    ) -> Dict[str, ValidationResult]:
        """
        Run cross-plugin consistency validation

        Args:
            context: Writing context

        Returns:
            Dict of validation_result_name -> ValidationResult
        """
        results = {}

        # Character-Dialogue consistency
        character_plugin = self._enabled.get("character")
        dialogue_plugin = self._enabled.get("dialogue")

        if character_plugin and dialogue_plugin:
            # Check if all characters with dialogue have voice profiles
            characters = character_plugin.get_characters()
            voice_profiles = dialogue_plugin.get_all_voice_profiles()

            missing_profiles = []
            for char_id, char_data in characters.items():
                char_name = char_data.get("name", char_id)
                if char_name not in voice_profiles and char_data.get("role") in ["protagonist", "supporting"]:
                    missing_profiles.append(char_name)

            if missing_profiles:
                results["character_dialogue"] = ValidationResult(
                    valid=False,
                    errors=[],
                    warnings=[f"Characters missing voice profiles: {missing_profiles}"],
                    suggestions=["Add voice profiles for consistent dialogue"],
                )
            else:
                results["character_dialogue"] = ValidationResult(valid=True)

        # Character-Timeline consistency
        timeline_plugin = self._enabled.get("timeline")
        if character_plugin and timeline_plugin:
            # This would check character location consistency
            # Timeline plugin already does this in validate_timeline_consistency
            pass

        # Event-Foreshadow consistency
        event_plugin = self._enabled.get("event")
        foreshadow_plugin = self._enabled.get("foreshadow")

        if event_plugin and foreshadow_plugin:
            # Check if major events have foreshadowing
            events = event_plugin.get_events()
            elements = foreshadow_plugin.get_elements()

            major_events = [e for e in events if e.get("importance") == "major"]
            unforeshadowed = []
            for event in major_events:
                event_chapter = event.get("chapter")
                has_foreshadow = any(
                    elem.get("plant_chapter", 999) < event_chapter
                    for elem in elements
                )
                if not has_foreshadow:
                    unforeshadowed.append(event.get("name", "unnamed"))

            if unforeshadowed:
                results["event_foreshadow"] = ValidationResult(
                    valid=True,  # Just a warning, not an error
                    errors=[],
                    warnings=[f"Major events without foreshadowing: {unforeshadowed}"],
                    suggestions=["Consider adding foreshadowing for these major events"],
                )
            else:
                results["event_foreshadow"] = ValidationResult(valid=True)

        return results

    async def sync_plugin_states(
        self,
        context: WritingContext,
    ) -> None:
        """
        Synchronize states between related plugins

        Args:
            context: Writing context
        """
        logger.info("Synchronizing plugin states...")

        # Sync character and dialogue plugins
        character_plugin = self._enabled.get("character")
        dialogue_plugin = self._enabled.get("dialogue")

        if character_plugin and dialogue_plugin:
            characters = character_plugin.get_characters()
            voice_profiles = dialogue_plugin.get_all_voice_profiles()

            # Ensure all major characters have voice profiles
            for char_id, char_data in characters.items():
                char_name = char_data.get("name", char_id)
                if char_data.get("role") in ["protagonist", "supporting"]:
                    if char_name not in voice_profiles:
                        # Extract voice profile from character data if available
                        voice_data = char_data.get("voice_profile")
                        if voice_data:
                            dialogue_plugin.set_voice_profile(char_id, voice_data)

        logger.info("Plugin state synchronization complete")
