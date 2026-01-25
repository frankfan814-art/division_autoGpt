"""
Creative AutoGPT - AI-powered creative writing system

An AI Agent system specialized for long-form novel writing, inspired by AutoGPT
with multi-LLM collaboration and plugin-based element management.
"""

__version__ = "0.1.0"

from creative_autogpt.core.loop_engine import LoopEngine
from creative_autogpt.core.task_planner import TaskPlanner
from creative_autogpt.core.evaluator import EvaluationEngine
from creative_autogpt.core.vector_memory import VectorMemoryManager
from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.plugins.manager import PluginManager
from creative_autogpt.modes.novel import NovelMode

__all__ = [
    "LoopEngine",
    "TaskPlanner",
    "EvaluationEngine",
    "VectorMemoryManager",
    "MultiLLMClient",
    "PluginManager",
    "NovelMode",
    "__version__",
]
