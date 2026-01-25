"""Writing modes for Creative AutoGPT"""

from creative_autogpt.modes.base import Mode, ModeRegistry
from creative_autogpt.modes.novel import NovelMode

__all__ = [
    "Mode",
    "ModeRegistry",
    "NovelMode",
]
