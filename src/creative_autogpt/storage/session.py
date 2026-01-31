"""
Session Storage - Manages writing session persistence

Handles session state, task results, and checkpoint management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean, Float, Index, select, delete, update
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

    # 引擎状态持久化字段（用于会话恢复）
    engine_state = Column(JSON, nullable=True)  # 存储引擎状态信息
    current_task_index = Column(Integer, nullable=True)  # 当前任务索引
    is_resumable = Column(Boolean, default=True)  # 是否可以恢复

    # 🔥 重写状态字段（用于前端显示重写进度）
    is_rewriting = Column(Boolean, default=False)  # 是否正在重写
    rewrite_attempt = Column(Integer, nullable=True)  # 当前重写尝试次数
    rewrite_task_id = Column(String, nullable=True)  # 正在重写的任务 ID
    rewrite_task_type = Column(String, nullable=True)  # 正在重写的任务类型


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


class PluginDataModel(Base_Model):
    """SQLAlchemy model for plugin data persistence"""

    __tablename__ = "plugin_data"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    plugin_name = Column(String, nullable=False, index=True)
    data_key = Column(String, nullable=False, index=True)
    data_value = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite index for efficient plugin data retrieval
    __table_args__ = (
        {'sqlite_autoincrement': True}
    )


class ChapterVersionModel(Base_Model):
    """SQLAlchemy model for chapter version history"""

    __tablename__ = "chapter_versions"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=False, index=True)
    chapter_index = Column(Integer, nullable=False, index=True)

    # 版本信息
    version_number = Column(Integer, nullable=False)  # v1=1, v2=2, v3=3
    is_current = Column(Boolean, default=False)  # 是否为当前版本

    # 内容
    content = Column(Text, nullable=False)

    # 评估信息
    score = Column(Float)  # 总分 0-1
    quality_score = Column(Float)  # 质量分
    consistency_score = Column(Float)  # 一致性分
    evaluation = Column(JSON)  # 完整评估结果

    # 元数据
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String)  # "auto" | "manual" | "rewrite"
    rewrite_reason = Column(Text)  # 重写原因（如果是重写版本）

    # Token 统计
    total_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)

    # 复合索引：session_id + chapter_index + version_number
    __table_args__ = (
        Index('ix_chapter_versions_session_chapter_version',
              'session_id', 'chapter_index', 'version_number'),
        {'sqlite_autoincrement': True}
    )


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

    async def update_session_rewrite_state(
        self,
        session_id: str,
        is_rewriting: Optional[bool] = None,
        rewrite_attempt: Optional[int] = None,
        rewrite_task_id: Optional[str] = None,
        rewrite_task_type: Optional[str] = None,
    ) -> bool:
        """
        Update session rewrite state

        Args:
            session_id: The session ID
            is_rewriting: Whether currently rewriting
            rewrite_attempt: Current rewrite attempt number
            rewrite_task_id: Task ID being rewritten
            rewrite_task_type: Task type being rewritten

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result:
                if is_rewriting is not None:
                    result.is_rewriting = is_rewriting
                if rewrite_attempt is not None:
                    result.rewrite_attempt = rewrite_attempt
                if rewrite_task_id is not None:
                    result.rewrite_task_id = rewrite_task_id
                if rewrite_task_type is not None:
                    result.rewrite_task_type = rewrite_task_type

                await session.commit()
                return True

        return False

    async def save_engine_state(
        self,
        session_id: str,
        engine_state: Dict[str, Any],
        current_task_index: Optional[int] = None,
    ) -> bool:
        """
        Save engine execution state for resume capability

        Args:
            session_id: The session ID
            engine_state: Engine state dictionary containing:
                - completed_task_ids: List of completed task IDs
                - current_task: Current task being executed
                - stats: Execution statistics
                - context: Memory context
            current_task_index: Current task index in the queue

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result:
                result.engine_state = engine_state
                if current_task_index is not None:
                    result.current_task_index = current_task_index
                result.is_resumable = True
                result.updated_at = datetime.utcnow()

                await session.commit()
                logger.info(f"Saved engine state for session {session_id}")
                return True

        return False

    async def load_engine_state(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Load engine execution state for resume

        Args:
            session_id: The session ID

        Returns:
            Engine state dictionary or None if not found
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result and result.engine_state:
                logger.info(f"Loaded engine state for session {session_id}")
                return {
                    "engine_state": result.engine_state,
                    "current_task_index": result.current_task_index,
                    "is_resumable": result.is_resumable,
                }

        return None

    async def clear_engine_state(
        self,
        session_id: str,
    ) -> bool:
        """
        Clear engine state (e.g., after completion)

        Args:
            session_id: The session ID

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result:
                result.engine_state = None
                result.current_task_index = None
                result.is_resumable = False
                result.updated_at = datetime.utcnow()

                await session.commit()
                logger.info(f"Cleared engine state for session {session_id}")
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
                        "prompt": metadata.get("prompt"),  # 🔥 添加提示词字段
                        "prompt_length": metadata.get("prompt_length"),  # 🔥 添加提示词长度
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

            # Delete plugin data
            stmt = delete(PluginDataModel).where(
                PluginDataModel.session_id == session_id
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

    async def update_engine_state(
        self,
        session_id: str,
        engine_state: Optional[Dict[str, Any]] = None,
        current_task_index: Optional[int] = None,
        is_resumable: Optional[bool] = None,
    ) -> bool:
        """
        Update engine state for session restoration

        Args:
            session_id: The session ID
            engine_state: Engine state dict (包含执行状态、统计等)
            current_task_index: Current task index
            is_resumable: Whether session can be resumed

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)

            if result:
                if engine_state is not None:
                    result.engine_state = engine_state
                if current_task_index is not None:
                    result.current_task_index = current_task_index
                if is_resumable is not None:
                    result.is_resumable = is_resumable

                await session.commit()
                return True

        return False

    async def get_resumable_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all sessions that can be resumed

        Returns:
            List of resumable sessions
        """
        async with self.session_factory() as session:
            stmt = select(SessionModel).where(
                SessionModel.is_resumable == True,
                SessionModel.status.in_([
                    SessionStatus.RUNNING.value,
                    SessionStatus.PAUSED.value,
                ])
            ).order_by(SessionModel.updated_at.desc())

            result = await session.execute(stmt)
            sessions = result.scalars().all()

            return [
                {
                    "id": s.id,
                    "title": s.title,
                    "mode": s.mode,
                    "status": s.status,
                    "engine_state": s.engine_state,
                    "current_task_index": s.current_task_index,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                    "total_tasks": s.total_tasks,
                    "completed_tasks": s.completed_tasks,
                }
                for s in sessions
            ]

    async def save_plugin_data(
        self,
        session_id: str,
        plugin_name: str,
        data_key: str,
        data_value: Any,
    ) -> bool:
        """
        Save plugin data to database

        Args:
            session_id: The session ID
            plugin_name: Name of the plugin
            data_key: Key for the data
            data_value: Data to store (must be JSON-serializable)

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            # Check if data already exists
            stmt = select(PluginDataModel).filter(
                PluginDataModel.session_id == session_id,
                PluginDataModel.plugin_name == plugin_name,
                PluginDataModel.data_key == data_key,
            )
            existing = await session.execute(stmt)
            existing_data = existing.scalar_one_or_none()

            if existing_data:
                # Update existing
                existing_data.data_value = data_value
            else:
                # Create new
                plugin_data = PluginDataModel(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    plugin_name=plugin_name,
                    data_key=data_key,
                    data_value=data_value,
                )
                session.add(plugin_data)

            await session.commit()
            return True

    async def load_plugin_data(
        self,
        session_id: str,
        plugin_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load plugin data from database

        Args:
            session_id: The session ID
            plugin_name: Optional plugin name filter

        Returns:
            Dict of data_key -> data_value
        """
        async with self.session_factory() as session:
            stmt = select(PluginDataModel).filter(
                PluginDataModel.session_id == session_id
            )

            if plugin_name:
                stmt = stmt.filter(PluginDataModel.plugin_name == plugin_name)

            result = await session.execute(stmt)
            plugin_data_list = result.scalars().all()

            # Return as nested dict: {plugin_name: {data_key: data_value}}
            output = {}
            for data in plugin_data_list:
                if data.plugin_name not in output:
                    output[data.plugin_name] = {}
                output[data.plugin_name][data.data_key] = data.data_value

            return output if not plugin_name else output.get(plugin_name, {})

    async def delete_plugin_data(
        self,
        session_id: str,
        plugin_name: Optional[str] = None,
    ) -> bool:
        """
        Delete plugin data from database

        Args:
            session_id: The session ID
            plugin_name: Optional plugin name filter (if None, deletes all plugin data for session)

        Returns:
            True if successful
        """
        async with self.session_factory() as session:
            stmt = delete(PluginDataModel).where(
                PluginDataModel.session_id == session_id
            )

            if plugin_name:
                stmt = stmt.where(PluginDataModel.plugin_name == plugin_name)

            await session.execute(stmt)
            await session.commit()
            return True

    # ========== 章节版本管理方法 ==========

    async def create_chapter_version(
        self,
        session_id: str,
        task_id: str,
        chapter_index: int,
        content: str,
        version_number: int,
        is_current: bool = False,
        evaluation: Optional[Dict[str, Any]] = None,
        created_by: str = "auto",
        rewrite_reason: Optional[str] = None,
        token_stats: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        创建新章节版本

        Args:
            session_id: 会话ID
            task_id: 任务ID
            chapter_index: 章节索引
            content: 章节内容
            version_number: 版本号 (v1=1, v2=2, ...)
            is_current: 是否为当前版本
            evaluation: 评估结果
            created_by: 创建方式 ("auto" | "manual" | "rewrite")
            rewrite_reason: 重写原因
            token_stats: Token 统计信息

        Returns:
            版本ID
        """
        version_id = str(uuid.uuid4())

        async with self.session_factory() as session:
            # 如果是当前版本，先取消其他版本的当前状态
            if is_current:
                stmt = update(ChapterVersionModel).where(
                    ChapterVersionModel.session_id == session_id,
                    ChapterVersionModel.chapter_index == chapter_index,
                ).values(is_current=False)
                await session.execute(stmt)

            # 创建新版本
            chapter_version = ChapterVersionModel(
                id=version_id,
                session_id=session_id,
                task_id=task_id,
                chapter_index=chapter_index,
                version_number=version_number,
                is_current=is_current,
                content=content,
                score=evaluation.get("score") if evaluation else None,
                quality_score=evaluation.get("quality_score") if evaluation else None,
                consistency_score=evaluation.get("consistency_score") if evaluation else None,
                evaluation=evaluation,
                created_by=created_by,
                rewrite_reason=rewrite_reason,
                total_tokens=token_stats.get("total_tokens", 0) if token_stats else 0,
                prompt_tokens=token_stats.get("prompt_tokens", 0) if token_stats else 0,
                completion_tokens=token_stats.get("completion_tokens", 0) if token_stats else 0,
                cost_usd=token_stats.get("cost", 0.0) if token_stats else 0.0,
            )
            session.add(chapter_version)

            # 更新 task_results 的 current_version_id
            stmt = update(TaskResultModel).where(
                TaskResultModel.task_id == task_id
            ).values(current_version_id=version_id)
            await session.execute(stmt)

            await session.commit()
            logger.info(f"Created chapter version {version_number} for chapter {chapter_index} in session {session_id}")
            return version_id

    async def get_chapter_versions(
        self,
        session_id: str,
        chapter_index: int,
    ) -> List[Dict[str, Any]]:
        """
        获取章节的所有版本

        Args:
            session_id: 会话ID
            chapter_index: 章节索引

        Returns:
            版本列表，按版本号降序排列
        """
        async with self.session_factory() as session:
            stmt = select(ChapterVersionModel).where(
                ChapterVersionModel.session_id == session_id,
                ChapterVersionModel.chapter_index == chapter_index,
            ).order_by(ChapterVersionModel.version_number.desc())

            result = await session.execute(stmt)
            versions = result.scalars().all()

            return [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "is_current": v.is_current,
                    "content": v.content,
                    "score": v.score,
                    "quality_score": v.quality_score,
                    "consistency_score": v.consistency_score,
                    "evaluation": v.evaluation,
                    "created_at": v.created_at.isoformat(),
                    "created_by": v.created_by,
                    "rewrite_reason": v.rewrite_reason,
                    "token_stats": {
                        "total_tokens": v.total_tokens,
                        "prompt_tokens": v.prompt_tokens,
                        "completion_tokens": v.completion_tokens,
                        "cost_usd": v.cost_usd,
                    }
                }
                for v in versions
            ]

    async def restore_chapter_version(
        self,
        session_id: str,
        task_id: str,
        version_id: str,
    ) -> bool:
        """
        恢复到指定版本

        Args:
            session_id: 会话ID
            task_id: 任务ID
            version_id: 版本ID

        Returns:
            是否成功恢复
        """
        async with self.session_factory() as session:
            # 获取要恢复的版本
            version = await session.get(ChapterVersionModel, version_id)
            if not version or version.session_id != session_id:
                logger.warning(f"Version {version_id} not found in session {session_id}")
                return False

            # 取消其他版本的当前状态
            stmt = update(ChapterVersionModel).where(
                ChapterVersionModel.session_id == session_id,
                ChapterVersionModel.chapter_index == version.chapter_index,
            ).values(is_current=False)
            await session.execute(stmt)

            # 设置此版本为当前
            version.is_current = True

            # 更新 task_results
            stmt = update(TaskResultModel).where(
                TaskResultModel.task_id == task_id
            ).values(
                result=version.content,
                current_version_id=version_id,
                evaluation=version.evaluation,
            )
            await session.execute(stmt)

            await session.commit()
            logger.info(f"Restored chapter {version.chapter_index} to version {version.version_number} in session {session_id}")
            return True

    async def update_task_version_count(
        self,
        task_id: str,
        version_count: int,
    ) -> bool:
        """
        更新任务的版本计数

        Args:
            task_id: 任务ID
            version_count: 版本总数

        Returns:
            是否成功
        """
        async with self.session_factory() as session:
            stmt = update(TaskResultModel).where(
                TaskResultModel.task_id == task_id
            ).values(version_count=version_count)
            await session.execute(stmt)
            await session.commit()
            return True

    async def get_current_chapter_version(
        self,
        session_id: str,
        chapter_index: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取章节的当前版本

        Args:
            session_id: 会话ID
            chapter_index: 章节索引

        Returns:
            当前版本信息，如果没有则返回 None
        """
        async with self.session_factory() as session:
            stmt = select(ChapterVersionModel).where(
                ChapterVersionModel.session_id == session_id,
                ChapterVersionModel.chapter_index == chapter_index,
                ChapterVersionModel.is_current == True,
            )
            result = await session.execute(stmt)
            version = result.scalar_one_or_none()

            if version:
                return {
                    "id": version.id,
                    "version_number": version.version_number,
                    "content": version.content,
                    "score": version.score,
                    "evaluation": version.evaluation,
                    "created_at": version.created_at.isoformat(),
                }
            return None

    async def close(self) -> None:
        """Close database connection"""
        await self.engine.dispose()
        logger.info("SessionStorage closed")
