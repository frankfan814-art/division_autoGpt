"""Plugin system for Creative AutoGPT"""

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    PluginConfig,
    PluginPhase,
    ValidationResult,
)
from creative_autogpt.plugins.manager import PluginManager

# Import concrete plugins
from creative_autogpt.plugins.character import CharacterPlugin
from creative_autogpt.plugins.worldview import WorldViewPlugin
from creative_autogpt.plugins.event import EventPlugin
from creative_autogpt.plugins.foreshadow import ForeshadowPlugin
from creative_autogpt.plugins.timeline import TimelinePlugin
from creative_autogpt.plugins.scene import ScenePlugin
from creative_autogpt.plugins.dialogue import DialoguePlugin
from creative_autogpt.plugins.example_extractor import ExampleExtractorPlugin
from creative_autogpt.plugins.power import PowerPlugin
from creative_autogpt.plugins.growth import GrowthPlugin
from creative_autogpt.plugins.villain import VillainPlugin

__all__ = [
    "NovelElementPlugin",
    "PluginConfig",
    "PluginPhase",
    "ValidationResult",
    "PluginManager",
    # Concrete plugins
    "CharacterPlugin",
    "WorldViewPlugin",
    "EventPlugin",
    "ForeshadowPlugin",
    "TimelinePlugin",
    "ScenePlugin",
    "DialoguePlugin",
    "ExampleExtractorPlugin",
    "PowerPlugin",
    "GrowthPlugin",
    "VillainPlugin",
]
