"""
Engine Registry - Manages running LoopEngine instances

This module provides a central registry for managing active LoopEngine instances,
enabling pause/resume/stop functionality across API requests.
"""

import asyncio
from typing import Dict, Optional, Set, TYPE_CHECKING, Any

from loguru import logger

from creative_autogpt.core.loop_engine import LoopEngine, ExecutionStatus, ExecutionStats

if TYPE_CHECKING:
    from creative_autogpt.storage.session import SessionStorage


class EngineRegistry:
    """
    Global registry for managing running LoopEngine instances

    Enables:
    - Tracking active engines by session_id
    - Pausing, resuming, and stopping engines
    - Querying engine status
    - Cleanup of completed engines
    - Persisting and restoring engine state
    """

    _instance: Optional["EngineRegistry"] = None
    _engines: Dict[str, LoopEngine] = {}
    _cleanup_task: Optional[asyncio.Task] = None
    _lock = asyncio.Lock()
    _storage: Optional["SessionStorage"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._engines = {}
        self._cleanup_task = None
        self._storage = None
        self._initialized = True
        logger.info("EngineRegistry initialized")

    def set_storage(self, storage: "SessionStorage") -> None:
        """Set the session storage for persistence"""
        self._storage = storage
        logger.info("EngineRegistry: Session storage set")

    async def register(
        self,
        session_id: str,
        engine: LoopEngine,
        save_state: bool = True,
    ) -> None:
        """
        Register a LoopEngine instance

        Args:
            session_id: Session identifier
            engine: LoopEngine instance
            save_state: Whether to save engine state to database
        """
        async with self._lock:
            self._engines[session_id] = engine
            logger.info(f"Registered engine for session {session_id}")

            # Save engine state to database for recovery
            if save_state and self._storage:
                await self._save_engine_state(session_id, engine)

            # Start cleanup task if not running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def unregister(self, session_id: str) -> None:
        """
        Unregister a LoopEngine instance

        Args:
            session_id: Session identifier
        """
        async with self._lock:
            if session_id in self._engines:
                del self._engines[session_id]
                logger.info(f"Unregistered engine for session {session_id}")

    def get(self, session_id: str) -> Optional[LoopEngine]:
        """
        Get a registered engine by session_id

        Args:
            session_id: Session identifier

        Returns:
            LoopEngine instance or None
        """
        return self._engines.get(session_id)

    async def pause(self, session_id: str) -> bool:
        """
        Pause a running engine

        Args:
            session_id: Session identifier

        Returns:
            True if successfully paused
        """
        engine = self.get(session_id)
        if engine is None:
            logger.warning(f"No engine found for session {session_id}")
            return False

        if engine.get_status() not in (ExecutionStatus.RUNNING, ExecutionStatus.PLANNING):
            logger.warning(
                f"Cannot pause session {session_id} with status {engine.get_status()}"
            )
            return False

        engine.pause()
        logger.info(f"Paused engine for session {session_id}")
        return True

    async def resume(self, session_id: str) -> bool:
        """
        Resume a paused engine

        Args:
            session_id: Session identifier

        Returns:
            True if successfully resumed
        """
        engine = self.get(session_id)
        if engine is None:
            logger.warning(f"No engine found for session {session_id}")
            return False

        if engine.get_status() != ExecutionStatus.PAUSED:
            logger.warning(
                f"Cannot resume session {session_id} with status {engine.get_status()}"
            )
            return False

        engine.resume()
        logger.info(f"Resumed engine for session {session_id}")
        return True

    async def stop(self, session_id: str) -> bool:
        """
        Stop a running engine

        Args:
            session_id: Session identifier

        Returns:
            True if successfully stopped
        """
        engine = self.get(session_id)
        if engine is None:
            logger.warning(f"No engine found for session {session_id}")
            return False

        if engine.get_status() in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.STOPPED,
        ):
            logger.warning(
                f"Cannot stop session {session_id} with status {engine.get_status()}"
            )
            return False

        engine.stop()
        logger.info(f"Stopped engine for session {session_id}")
        return True

    def get_status(self, session_id: str) -> Optional[ExecutionStatus]:
        """
        Get the status of an engine

        Args:
            session_id: Session identifier

        Returns:
            ExecutionStatus or None if not found
        """
        engine = self.get(session_id)
        if engine:
            return engine.get_status()
        return None

    def get_progress(self, session_id: str) -> Optional[Dict]:
        """
        Get the progress of an engine

        Args:
            session_id: Session identifier

        Returns:
            Progress dict or None if not found
        """
        engine = self.get(session_id)
        if engine:
            return engine.get_progress()
        return None

    def get_stats(self, session_id: str) -> Optional[Dict]:
        """
        Get the statistics of an engine

        Args:
            session_id: Session identifier

        Returns:
            Stats dict or None if not found
        """
        engine = self.get(session_id)
        if engine:
            return engine.get_stats()
        return None

    def list_sessions(self) -> Set[str]:
        """
        List all registered session IDs

        Returns:
            Set of session IDs
        """
        return set(self._engines.keys())

    async def _cleanup_loop(self) -> None:
        """Background task to clean up completed engines"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                async with self._lock:
                    to_remove = []
                    for session_id, engine in self._engines.items():
                        status = engine.get_status()
                        # Clean up engines that are completed/failed/stopped
                        # and have been finished for more than 5 minutes
                        if status in (
                            ExecutionStatus.COMPLETED,
                            ExecutionStatus.FAILED,
                            ExecutionStatus.STOPPED,
                        ):
                            # Check if engine has been in this state for a while
                            # In production, track completion time
                            to_remove.append(session_id)

                    for session_id in to_remove:
                        await self.unregister(session_id)
                        logger.debug(f"Cleaned up engine for session {session_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def shutdown(self) -> None:
        """
        Shutdown the registry and clean up all engines

        Stops all running engines and cancels the cleanup task.
        """
        logger.info("Shutting down EngineRegistry")

        # Stop all running engines
        for session_id, engine in list(self._engines.items()):
            if engine.get_status() in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED):
                logger.info(f"Stopping engine for session {session_id}")
                engine.stop()

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clear registry
        async with self._lock:
            self._engines.clear()

        logger.info("EngineRegistry shutdown complete")

    async def _save_engine_state(self, session_id: str, engine: LoopEngine) -> None:
        """
        保存引擎状态到数据库

        Args:
            session_id: 会话ID
            engine: LoopEngine 实例
        """
        if not self._storage:
            return

        try:
            # 获取引擎状态
            state = {
                "status": engine.get_status().value,
                "stats": {
                    "total_tasks": engine.stats.total_tasks,
                    "completed_tasks": engine.stats.completed_tasks,
                    "failed_tasks": engine.stats.failed_tasks,
                    "total_tokens": engine.stats.total_tokens,
                    "total_cost": engine.stats.total_cost,
                },
            }

            # 获取当前任务信息
            current_task_index = None
            if hasattr(engine, 'planner') and engine.planner:
                # 尝试获取当前任务索引
                if hasattr(engine.planner, '_task_index'):
                    current_task_index = engine.planner._task_index

            await self._storage.update_engine_state(
                session_id=session_id,
                engine_state=state,
                current_task_index=current_task_index,
                is_resumable=True,
            )

            logger.debug(f"Saved engine state for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save engine state for {session_id}: {e}")

    async def get_or_restore_engine(
        self,
        session_id: str,
        llm_client: Any,
        memory: Any,
        evaluator: Any,
    ) -> Optional[LoopEngine]:
        """
        获取已注册的引擎，或从数据库恢复引擎状态

        Args:
            session_id: 会话ID
            llm_client: LLM客户端（用于创建新引擎）
            memory: 记忆管理器（用于创建新引擎）
            evaluator: 评估器（用于创建新引擎）

        Returns:
            LoopEngine 实例或 None
        """
        # 首先检查内存中是否有引擎
        engine = self.get(session_id)
        if engine:
            logger.info(f"Found engine in memory for session {session_id}")
            return engine

        # 尝试从数据库恢复
        if self._storage:
            session_data = await self._storage.get_session(session_id)
            if session_data and session_data.get("is_resumable", False):
                logger.info(f"Restoring engine state from database for session {session_id}")
                # 这里可以返回恢复信息，让调用者决定如何处理
                # 实际的引擎恢复需要在 API 层处理，因为需要重新创建 LoopEngine

        return None

    async def restore_session_on_startup(self) -> int:
        """
        启动时恢复所有可恢复的会话

        Returns:
            恢复的会话数量
        """
        if not self._storage:
            logger.warning("No storage set, cannot restore sessions")
            return 0

        try:
            resumable_sessions = await self._storage.get_resumable_sessions()
            count = len(resumable_sessions)

            if count > 0:
                logger.info(f"Found {count} resumable sessions in database")
                for session in resumable_sessions:
                    logger.info(
                        f"  - Session {session['id']}: {session['title']} "
                        f"(status: {session['status']})"
                    )
                    # 标记为不可恢复，直到用户主动恢复
                    await self._storage.update_engine_state(
                        session_id=session['id'],
                        is_resumable=False,
                    )
            else:
                logger.info("No resumable sessions found")

            return count
        except Exception as e:
            logger.error(f"Error restoring sessions on startup: {e}")
            return 0


# Global singleton instance
registry = EngineRegistry()


async def get_registry() -> EngineRegistry:
    """
    Get the global EngineRegistry instance

    Returns:
        The singleton EngineRegistry instance
    """
    return registry
