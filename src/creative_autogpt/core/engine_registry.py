"""
Engine Registry - Manages running LoopEngine instances

This module provides a central registry for managing active LoopEngine instances,
enabling pause/resume/stop functionality across API requests.
"""

import asyncio
from typing import Dict, Optional, Set

from loguru import logger

from creative_autogpt.core.loop_engine import LoopEngine, ExecutionStatus


class EngineRegistry:
    """
    Global registry for managing running LoopEngine instances

    Enables:
    - Tracking active engines by session_id
    - Pausing, resuming, and stopping engines
    - Querying engine status
    - Cleanup of completed engines
    """

    _instance: Optional["EngineRegistry"] = None
    _engines: Dict[str, LoopEngine] = {}
    _cleanup_task: Optional[asyncio.Task] = None
    _lock = asyncio.Lock()

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
        self._initialized = True
        logger.info("EngineRegistry initialized")

    async def register(
        self,
        session_id: str,
        engine: LoopEngine,
    ) -> None:
        """
        Register a LoopEngine instance

        Args:
            session_id: Session identifier
            engine: LoopEngine instance
        """
        async with self._lock:
            self._engines[session_id] = engine
            logger.info(f"Registered engine for session {session_id}")

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


# Global singleton instance
registry = EngineRegistry()


async def get_registry() -> EngineRegistry:
    """
    Get the global EngineRegistry instance

    Returns:
        The singleton EngineRegistry instance
    """
    return registry
