"""
Session API routes
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from loguru import logger

from creative_autogpt.api.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
    SessionProgress,
    SessionExportRequest,
    SessionStatus,
)
from creative_autogpt.api.schemas.response import SuccessResponse, ErrorResponse
from creative_autogpt.storage.session import SessionStorage, SessionStatus as DBSessionStatus
from creative_autogpt.storage.file_store import FileStore, ExportFormat
from creative_autogpt.api.dependencies import get_session_storage
from creative_autogpt.utils.config import get_settings

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Create a new writing session

    - **title**: Session title (required)
    - **mode**: Writing mode (default: novel)
    - **goal**: Creation goal configuration
    - **config**: Session configuration
    """
    try:
        session_id = await storage.create_session(
            title=data.title,
            mode=data.mode,
            goal=data.goal,
            config=data.config,
        )

        session = await storage.get_session(session_id)
        return session

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    List all sessions

    - **status**: Optional status filter
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    try:
        offset = (page - 1) * page_size

        sessions = await storage.list_sessions(
            status=status_filter,
            limit=page_size,
            offset=offset,
        )

        # Get total count (simplified - in production use proper count query)
        total = len(sessions)

        return SessionListResponse(
            sessions=sessions,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Get a session by ID
    """
    session = await storage.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Update a session

    - **title**: New title
    - **status**: New status
    - **goal**: Updated goal
    - **config**: Updated configuration
    """
    # Verify session exists
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # Update status if provided
        if data.status:
            await storage.update_session_status(session_id, DBSessionStatus(data.status.value))

        # Note: Updating other fields would require additional methods in SessionStorage
        # For now, return the updated session
        updated_session = await storage.get_session(session_id)
        return updated_session

    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Delete a session and all its data
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        await storage.delete_session(session_id)

        # Also delete files
        file_store = FileStore()
        await file_store.delete_session_files(session_id)

        return SuccessResponse(
            success=True,
            message=f"Session {session_id} deleted successfully"
        )

    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{session_id}/progress", response_model=SessionProgress)
async def get_session_progress(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Get session execution progress
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    total = session["total_tasks"]
    completed = session["completed_tasks"]
    percentage = (completed / total * 100) if total > 0 else 0

    return SessionProgress(
        session_id=session_id,
        status=SessionStatus(session["status"]),
        total_tasks=total,
        completed_tasks=completed,
        failed_tasks=session["failed_tasks"],
        percentage=percentage,
    )


@router.get("/{session_id}/tasks", response_model=List[dict])
async def get_session_tasks(
    session_id: str,
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    chapter_index: Optional[int] = Query(None, description="Filter by chapter index"),
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Get all task results for a session
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    tasks = await storage.get_task_results(
        session_id,
        task_type=task_type,
        chapter_index=chapter_index,
    )

    return tasks


@router.post("/{session_id}/export")
async def export_session(
    session_id: str,
    data: SessionExportRequest,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Export session to file

    - **format**: Export format (txt, json, md, full)
      - txt: 仅导出章节内容
      - json: 导出完整JSON数据
      - md: 导出章节内容为Markdown
      - full: 导出完整创作过程（推荐，包含所有任务输出）
    - **include_metadata**: Include metadata in export
    - **chapter_range**: Optional chapter range to export
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        file_store = FileStore()

        # Get all task results
        tasks = await storage.get_task_results(session_id)

        # Filter by chapter range if specified
        if data.chapter_range:
            start, end = data.chapter_range
            tasks = [
                t for t in tasks
                if t.get("chapter_index") is not None
                and start <= t["chapter_index"] <= end
            ]

        # 完整导出模式（推荐）
        if data.format == "full":
            file_path = await file_store.export_full_creative_process(
                session_id=session_id,
                title=session["title"],
                tasks=tasks,
                metadata=session["goal"] if data.include_metadata else None,
            )
            return FileResponse(
                path=file_path,
                filename=file_path.name,
                media_type="text/markdown",
            )

        # Group chapters
        chapters = []
        current_chapter = None

        for task in tasks:
            if task["task_type"] in ("章节内容", "章节润色"):
                chapter_index = task.get("chapter_index")
                if chapter_index is not None:
                    if current_chapter != chapter_index:
                        chapters.append({
                            "chapter_index": chapter_index,
                            "title": task.get("metadata", {}).get("title", f"第{chapter_index}章"),
                            "content": task["result"] or "",
                        })
                        current_chapter = chapter_index
                elif task["result"]:
                    # Append to current chapter
                    if chapters:
                        chapters[-1]["content"] += "\n\n" + task["result"]

        # Export based on format
        if data.format == "json":
            file_path = await file_store.export_to_json(
                session_id=session_id,
                title=session["title"],
                data={
                    "session": session,
                    "tasks": tasks,
                }
            )
        elif data.format == "md":
            file_path = await file_store.export_to_markdown(
                session_id=session_id,
                title=session["title"],
                chapters=chapters,
                metadata=session["goal"] if data.include_metadata else None,
            )
        else:  # txt
            file_path = await file_store.save_full_novel(
                session_id=session_id,
                title=session["title"],
                chapters=chapters,
                metadata=session["goal"] if data.include_metadata else None,
            )

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="text/plain",
        )

    except Exception as e:
        logger.error(f"Failed to export session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{session_id}/start", response_model=SuccessResponse)
async def start_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Start a session execution (HTTP alternative to WebSocket start)
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # Use engine registry to manage the running engine
        from creative_autogpt.core.engine_registry import get_registry
        from creative_autogpt.utils.llm_client import MultiLLMClient
        from creative_autogpt.core.vector_memory import VectorMemoryManager
        from creative_autogpt.core.evaluator import EvaluationEngine
        from creative_autogpt.core.loop_engine import LoopEngine, ExecutionStatus
        from creative_autogpt.storage.vector_store import VectorStore
        from creative_autogpt.api.routes.websocket import manager

        registry = await get_registry()

        # Check if already running
        if registry.get(session_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session {session_id} is already running"
            )

        # Initialize components
        llm_client = MultiLLMClient()
        vector_store = VectorStore()
        memory = VectorMemoryManager(vector_store=vector_store)
        evaluator = EvaluationEngine(llm_client=llm_client)

        engine = LoopEngine(
            session_id=session_id,
            llm_client=llm_client,
            memory=memory,
            evaluator=evaluator,
            config=session.get("config", {}),
        )

        # Real-time updates via WebSocket broadcast
        def on_task_start(task):
            import asyncio
            asyncio.create_task(
                manager.broadcast_to_session(
                    {
                        "event": "task_start",
                        "session_id": session_id,
                        "task": {
                            "task_id": task.task_id,
                            "task_type": task.task_type.value,
                            "description": task.description,
                        },
                    },
                    session_id,
                )
            )

        def on_task_complete(task, result, evaluation):
            import asyncio
            asyncio.create_task(
                manager.broadcast_to_session(
                    {
                        "event": "task_complete",
                        "session_id": session_id,
                        "task": {
                            "task_id": task.task_id,
                            "task_type": task.task_type.value,
                            "result": result[:500] if result else None,
                            "evaluation": evaluation.to_dict() if evaluation else None,
                        },
                    },
                    session_id,
                )
            )

        def on_progress(progress):
            import asyncio
            asyncio.create_task(
                manager.broadcast_to_session(
                    {
                        "event": "progress",
                        "session_id": session_id,
                        "progress": progress,
                    },
                    session_id,
                )
            )

        engine.set_callbacks(
            on_task_start=on_task_start,
            on_task_complete=on_task_complete,
            on_progress=on_progress,
        )

        # Register and mark running
        await registry.register(session_id, engine)
        await storage.update_session_status(session_id, DBSessionStatus.RUNNING)

        # Run in background
        import asyncio

        async def run_engine():
            try:
                result = await engine.run(
                    goal=session.get("goal", {}),
                    chapter_count=session.get("config", {}).get("chapter_count"),
                )

                event_type = "completed" if result.status == ExecutionStatus.COMPLETED else "failed"
                payload = {
                    "event": event_type,
                    "session_id": session_id,
                    "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "stats": result.stats.to_dict() if hasattr(result.stats, 'to_dict') else {},
                }
                await manager.broadcast_to_session(payload, session_id)

                final_status = DBSessionStatus.COMPLETED if result.status == ExecutionStatus.COMPLETED else DBSessionStatus.FAILED
                await storage.update_session_status(session_id, final_status)

            except Exception as e:
                await manager.broadcast_to_session(
                    {
                        "event": "failed",
                        "session_id": session_id,
                        "error": str(e),
                    },
                    session_id,
                )
                await storage.update_session_status(session_id, DBSessionStatus.FAILED)
            finally:
                await registry.unregister(session_id)

        asyncio.create_task(run_engine())

        return SuccessResponse(success=True, message=f"Session {session_id} started")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{session_id}/pause", response_model=SuccessResponse)
async def pause_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Pause a running session
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # Use engine registry to pause the actual running engine
        from creative_autogpt.core.engine_registry import get_registry

        registry = await get_registry()
        engine_paused = await registry.pause(session_id)

        if not engine_paused:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not pause session {session_id}. It may not be running."
            )

        # Update session status in storage
        await storage.update_session_status(session_id, DBSessionStatus.PAUSED)

        return SuccessResponse(
            success=True,
            message=f"Session {session_id} paused"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{session_id}/resume", response_model=SuccessResponse)
async def resume_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Resume a paused session
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # Use engine registry to resume the paused engine
        from creative_autogpt.core.engine_registry import get_registry

        registry = await get_registry()
        engine_resumed = await registry.resume(session_id)

        if not engine_resumed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not resume session {session_id}. It may not be paused or the engine has been cleaned up."
            )

        # Update session status in storage
        await storage.update_session_status(session_id, DBSessionStatus.RUNNING)

        return SuccessResponse(
            success=True,
            message=f"Session {session_id} resumed"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{session_id}/stop", response_model=SuccessResponse)
async def stop_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Stop a running session
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # Use engine registry to stop the running engine
        from creative_autogpt.core.engine_registry import get_registry

        registry = await get_registry()
        engine_stopped = await registry.stop(session_id)

        if not engine_stopped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not stop session {session_id}. It may not be running."
            )

        # Update session status in storage
        await storage.update_session_status(session_id, DBSessionStatus.CANCELLED)

        # Unregister the engine from registry
        await registry.unregister(session_id)

        return SuccessResponse(
            success=True,
            message=f"Session {session_id} stopped"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
