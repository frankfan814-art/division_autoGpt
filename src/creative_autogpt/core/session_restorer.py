"""
Session Restorer - 会话恢复服务

负责从数据库恢复会话状态并重新创建 LoopEngine。
"""

import uuid
from typing import Any, Dict, Optional

from loguru import logger

from creative_autogpt.core.loop_engine import LoopEngine, ExecutionStatus
from creative_autogpt.core.task_planner import TaskPlanner
from creative_autogpt.core.vector_memory import VectorMemoryManager, MemoryType
from creative_autogpt.core.evaluator import EvaluationEngine
from creative_autogpt.storage.session import SessionStorage, SessionStatus


class SessionRestorer:
    """
    会话恢复服务

    提供从数据库恢复会话状态的能力，包括：
    - 恢复任务规划器状态
    - 恢复向量记忆上下文
    - 重新创建 LoopEngine 实例
    """

    def __init__(
        self,
        storage: SessionStorage,
        llm_client: Any,
        memory_factory: Any,
        evaluator_factory: Any,
    ):
        """
        初始化会话恢复服务

        Args:
            storage: 会话存储
            llm_client: LLM 客户端
            memory_factory: 记忆管理器工厂函数
            evaluator_factory: 评估器工厂函数
        """
        self.storage = storage
        self.llm_client = llm_client
        self.memory_factory = memory_factory
        self.evaluator_factory = evaluator_factory

    async def can_restore(self, session_id: str) -> bool:
        """
        检查会话是否可以恢复

        Args:
            session_id: 会话ID

        Returns:
            是否可以恢复
        """
        session_data = await self.storage.get_session(session_id)

        if not session_data:
            return False

        # 检查会话状态
        if session_data["status"] not in [
            SessionStatus.RUNNING.value,
            SessionStatus.PAUSED.value,
        ]:
            return False

        # 检查是否有引擎状态
        engine_state = session_data.get("engine_state")
        if not engine_state:
            return False

        return True

    async def restore_session(
        self,
        session_id: str,
    ) -> Optional[LoopEngine]:
        """
        恢复会话

        Args:
            session_id: 会话ID

        Returns:
            恢复的 LoopEngine 实例或 None
        """
        logger.info(f"Attempting to restore session {session_id}")

        # 检查是否可以恢复
        if not await self.can_restore(session_id):
            logger.warning(f"Session {session_id} cannot be restored")
            return None

        # 获取会话数据
        session_data = await self.storage.get_session(session_id)
        if not session_data:
            return None

        try:
            # 获取任务结果以重建状态
            task_results = await self.storage.get_task_results(session_id)

            # 创建记忆管理器
            memory = self.memory_factory(session_id)

            # 恢复向量记忆（从已完成任务的结果中）
            await self._restore_memory(memory, task_results)

            # 创建评估器
            evaluator = self.evaluator_factory()

            # 创建 LoopEngine
            config = session_data.get("config", {})
            engine = LoopEngine(
                session_id=session_id,
                llm_client=self.llm_client,
                memory=memory,
                evaluator=evaluator,
                config=config,
            )

            # 恢复引擎状态
            engine_state = session_data.get("engine_state", {})
            await self._restore_engine_state(engine, engine_state, task_results)

            # 更新会话状态为可恢复
            await self.storage.update_engine_state(
                session_id=session_id,
                is_resumable=True,
            )

            logger.info(f"Successfully restored session {session_id}")
            return engine

        except Exception as e:
            logger.error(f"Failed to restore session {session_id}: {e}")
            return None

    async def _restore_memory(
        self,
        memory: VectorMemoryManager,
        task_results: list,
    ) -> None:
        """
        从任务结果中恢复记忆

        Args:
            memory: 记忆管理器
            task_results: 任务结果列表
        """
        # 基础任务类型（这些任务的结果会被存储到向量库）
        foundation_tasks = {
            "CREATIVE_BRAINSTORM": MemoryType.GENERAL,
            "STORY_CORE": MemoryType.GENERAL,
            "OUTLINE": MemoryType.OUTLINE,
            "WORLDVIEW_RULES": MemoryType.WORLDVIEW,
            "CHARACTER_DESIGN": MemoryType.CHARACTER,
            "STYLE_ELEMENTS": MemoryType.GENERAL,
            "EVENTS": MemoryType.PLOT,
            "SCENES_ITEMS_CONFLICTS": MemoryType.SCENE,
            "FORESHADOW_LIST": MemoryType.FORESHADOW,
        }

        for task in task_results:
            task_type = task.get("task_type")
            result = task.get("result")

            if not result:
                continue

            # 确定记忆类型
            memory_type = foundation_tasks.get(task_type, MemoryType.GENERAL)

            # 添加到记忆
            try:
                await memory.add(
                    content=result,
                    memory_type=memory_type,
                    metadata={
                        "task_id": task.get("task_id"),
                        "task_type": task_type,
                        "chapter_index": task.get("chapter_index"),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to restore memory for task {task_type}: {e}")

        logger.info(f"Restored {len(task_results)} tasks to memory")

    async def _restore_engine_state(
        self,
        engine: LoopEngine,
        engine_state: Dict[str, Any],
        task_results: list,
    ) -> None:
        """
        恢复引擎内部状态

        Args:
            engine: LoopEngine 实例
            engine_state: 保存的引擎状态
            task_results: 任务结果列表
        """
        # 设置引擎状态
        status_value = engine_state.get("status", ExecutionStatus.PAUSED.value)
        engine.status = ExecutionStatus(status_value)

        # 设置统计信息
        stats = engine_state.get("stats", {})
        if stats:
            engine.stats.total_tasks = stats.get("total_tasks", 0)
            engine.stats.completed_tasks = stats.get("completed_tasks", 0)
            engine.stats.failed_tasks = stats.get("failed_tasks", 0)
            engine.stats.total_tokens = stats.get("total_tokens", 0)
            engine.stats.total_cost = stats.get("total_cost", 0.0)

        # 设置暂停状态（恢复后默认为暂停，等待用户手动继续）
        engine.is_paused = True
        engine.is_running = True

        logger.info(
            f"Restored engine state: status={engine.status}, "
            f"completed={engine.stats.completed_tasks}/{engine.stats.total_tasks}"
        )

    async def get_restore_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话恢复信息

        Args:
            session_id: 会话ID

        Returns:
            恢复信息字典或 None
        """
        session_data = await self.storage.get_session(session_id)
        if not session_data:
            return None

        task_results = await self.storage.get_task_results(session_id)

        return {
            "session_id": session_data["id"],
            "title": session_data["title"],
            "status": session_data["status"],
            "created_at": session_data["created_at"],
            "updated_at": session_data["updated_at"],
            "total_tasks": session_data.get("total_tasks", 0),
            "completed_tasks": session_data.get("completed_tasks", 0),
            "failed_tasks": session_data.get("failed_tasks", 0),
            "can_restore": await self.can_restore(session_id),
            "task_count": len(task_results),
        }
