"""
Session Storage - Manages writing session persistence

Handles session state, task results, and checkpoint management.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
from loguru import logger
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, JSON, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from creative_autogpt.utils.config import get_settings


Base_Model = declarative_base()


class SessionStatus(str, Enum):
    """Status of a writing session"""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionModel(Base_Model):
    """SQLAlchemy model for sessions"""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    mode = Column(String, nullable=False, default="novel")
    status = Column(String, nullable=False, default=SessionStatus.CREATED.value)
    goal = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    llm_calls = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)


class TaskResultModel(Base_Model):
    """SQLAlchemy model for task results"""

    __tablename__ = "task_results"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=False, index=True)
    task_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    task_metadata = Column(JSON, nullable=True)
    evaluation = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    chapter_index = Column(Integer, nullable=True)


class SessionStorage:
    """
    Storage for writing sessions

    Manages:
    - Session creation and retrieval
    - Session state updates
    - Task result storage
    - Checkpoint management
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize session storage

        Args:
            db_url: Database URL (uses settings if None)
        """
        settings = get_settings()
        self.db_url = db_url or settings.database_url

        # Create async engine
        self.engine = create_async_engine(
            self.db_url,
            echo=settings.is_development,
        )

        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"SessionStorage initialized with DB: {self.db_url}")

    async def initialize(self) -> None:
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base_Model.metadata.create_all)

        logger.info("Database tables initialized")

    async def create_session(
        self,
        title: str,
        mode: str = "novel",
        goal: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new writing session

        Args:
            title: Session title
            mode: Writing mode
            goal: Creation goal
            config: Session configuration

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())

        async with self.session_factory() as session:
            db_session = SessionModel(
                id=session_id,
                title=title,
                mode=mode,
                status=SessionStatus.CREATED.value,
                goal=goal or {},
                config=config or {},
            )

            session.add(db_session)
            await session.commit()

        logger.info(f"Created session {session_id}: {title}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by ID

        Args:
            session_id: The session ID

        Returns:
            Session data or None
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result:
                return {
                    "id": result.id,
                    "title": result.title,
                    "mode": result.mode,
                    "status": result.status,
                    "goal": result.goal,
                    "config": result.config,
                    "created_at": result.created_at.isoformat(),
                    "updated_at": result.updated_at.isoformat(),
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                    "total_tasks": result.total_tasks,
                    "completed_tasks": result.completed_tasks,
                    "failed_tasks": result.failed_tasks,
                    "llm_calls": result.llm_calls,
                    "tokens_used": result.tokens_used,
                }

        return None

    async def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List sessions

        Args:
            status: Filter by status
            limit: Maximum number to return
            offset: Offset for pagination

        Returns:
            List of sessions
        """
        async with self.session_factory() as session:
            stmt = select(SessionModel)

            if status:
                stmt = stmt.where(SessionModel.status == status)

            stmt = stmt.order_by(SessionModel.created_at.desc())
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            sessions = result.scalars().all()

            return [
                {
                    "id": s.id,
                    "title": s.title,
                    "mode": s.mode,
                    "status": s.status,
                    "goal": s.goal or {},
                    "config": s.config or {},
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "total_tasks": s.total_tasks,
                    "completed_tasks": s.completed_tasks,
                    "failed_tasks": s.failed_tasks,
                    "llm_calls": s.llm_calls or 0,
                    "tokens_used": s.tokens_used or 0,
                }
                for s in sessions
            ]

    async def update_session_status(
        self,
        session_id: str,
        status: SessionStatus,
    ) -> bool:
        """
        Update session status

        Args:
            session_id: The session ID
            status: New status

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result:
                result.status = status.value

                if status == SessionStatus.COMPLETED:
                    result.completed_at = datetime.utcnow()

                await session.commit()
                return True

        return False

    async def update_session_progress(
        self,
        session_id: str,
        total_tasks: Optional[int] = None,
        completed_tasks: Optional[int] = None,
        failed_tasks: Optional[int] = None,
        llm_calls: Optional[int] = None,
        tokens_used: Optional[int] = None,
    ) -> bool:
        """
        Update session progress statistics

        Args:
            session_id: The session ID
            total_tasks: Total task count
            completed_tasks: Completed task count
            failed_tasks: Failed task count
            llm_calls: LLM call count
            tokens_used: Token usage

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result:
                if total_tasks is not None:
                    result.total_tasks = total_tasks
                if completed_tasks is not None:
                    result.completed_tasks = completed_tasks
                if failed_tasks is not None:
                    result.failed_tasks = failed_tasks
                if llm_calls is not None:
                    result.llm_calls = llm_calls
                if tokens_used is not None:
                    result.tokens_used = tokens_used

                await session.commit()
                return True

        return False

    async def save_task_result(
        self,
        session_id: str,
        task_id: str,
        task_type: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        evaluation: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save a task result

        Args:
            session_id: The session ID
            task_id: The task ID
            task_type: Type of task
            status: Task status
            result: Task result content
            error: Error message if failed
            metadata: Task metadata
            evaluation: Evaluation result

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            # Check if result already exists
            stmt = select(TaskResultModel).filter(
                TaskResultModel.session_id == session_id,
                TaskResultModel.task_id == task_id,
            )
            existing = await session.execute(stmt)
            existing_result = existing.scalar_one_or_none()

            chapter_index = metadata.get("chapter_index") if metadata else None

            if existing_result:
                # Update existing
                existing_result.status = status
                existing_result.result = result
                existing_result.error = error
                existing_result.task_metadata = metadata
                existing_result.evaluation = evaluation
            else:
                # Create new
                task_result = TaskResultModel(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    task_id=task_id,
                    task_type=task_type,
                    status=status,
                    result=result,
                    error=error,
                    task_metadata=metadata,
                    evaluation=evaluation,
                    chapter_index=chapter_index,
                )
                session.add(task_result)

            await session.commit()
            return True

    async def get_task_results(
        self,
        session_id: str,
        task_type: Optional[str] = None,
        chapter_index: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get task results for a session

        Args:
            session_id: The session ID
            task_type: Filter by task type
            chapter_index: Filter by chapter index

        Returns:
            List of task results
        """
        async with self.session_factory() as session:
            stmt = select(TaskResultModel).filter(
                TaskResultModel.session_id == session_id
            )

            if task_type:
                stmt = stmt.filter(TaskResultModel.task_type == task_type)

            if chapter_index is not None:
                stmt = stmt.filter(TaskResultModel.chapter_index == chapter_index)

            stmt = stmt.order_by(TaskResultModel.created_at)

            result = await session.execute(stmt)
            tasks = result.scalars().all()

            task_list = []
            for t in tasks:
                # Base task data
                task_data = {
                    "id": t.id,
                    "task_id": t.task_id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "result": t.result,
                    "error": t.error,
                    "evaluation": t.evaluation,
                    "created_at": t.created_at.isoformat(),
                    "chapter_index": t.chapter_index,
                }
                
                # Merge metadata fields into task data for frontend compatibility
                if t.task_metadata:
                    metadata = t.task_metadata
                    task_data.update({
                        "description": metadata.get("description"),
                        "started_at": metadata.get("started_at"),
                        "completed_at": metadata.get("completed_at"),
                        "execution_time_seconds": metadata.get("execution_time_seconds"),
                        "total_tokens": metadata.get("total_tokens"),
                        "prompt_tokens": metadata.get("prompt_tokens"),
                        "completion_tokens": metadata.get("completion_tokens"),
                        "cost_usd": metadata.get("cost_usd"),
                        "failed_attempts": metadata.get("failed_attempts"),
                        "retry_count": metadata.get("retry_count"),
                        "llm_provider": metadata.get("llm_provider"),
                        "llm_model": metadata.get("llm_model"),
                        "metadata": metadata,  # Keep full metadata for reference
                    })
                
                task_list.append(task_data)
            
            return task_list

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its data

        Args:
            session_id: The session ID

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            # Delete task results
            stmt = delete(TaskResultModel).where(
                TaskResultModel.session_id == session_id
            )
            await session.execute(stmt)

            # Delete session
            result = await session.get(SessionModel, session_id)
            if result:
                await session.delete(result)

            await session.commit()
            return True

        return False

    async def create_checkpoint(
        self,
        session_id: str,
        name: str,
    ) -> str:
        """
        Create a checkpoint for a session

        Args:
            session_id: The session ID
            name: Checkpoint name

        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"{session_id}_{name}_{int(datetime.utcnow().timestamp())}"

        # For now, checkpoints are implicit - we can restore to any point
        # by loading session state and task results

        logger.info(f"Created checkpoint {checkpoint_id} for session {session_id}")
        return checkpoint_id

    async def close(self) -> None:
        """Close database connection"""
        await self.engine.dispose()
        logger.info("SessionStorage closed")
