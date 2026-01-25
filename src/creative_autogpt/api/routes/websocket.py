"""
WebSocket API routes for real-time communication
"""

import uuid
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger

from creative_autogpt.api.dependencies import (
    get_session_storage,
)
from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.core.vector_memory import VectorMemoryManager
from creative_autogpt.core.evaluator import EvaluationEngine
from creative_autogpt.core.loop_engine import LoopEngine, ExecutionStatus

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_subscribers: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new client"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")

    def disconnect(self, client_id: str):
        """Disconnect a client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # Remove from all session subscriptions
        for session_id, subscribers in self.session_subscribers.items():
            subscribers.discard(client_id)

        logger.info(f"WebSocket client {client_id} disconnected")

    async def send_personal(self, message: dict, client_id: str):
        """Send message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to client {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast_to_session(self, message: dict, session_id: str):
        """Broadcast message to all subscribers of a session"""
        if session_id not in self.session_subscribers:
            return

        for client_id in self.session_subscribers[session_id].copy():
            await self.send_personal(message, client_id)

    def subscribe_to_session(self, client_id: str, session_id: str):
        """Subscribe a client to session updates"""
        if session_id not in self.session_subscribers:
            self.session_subscribers[session_id] = set()

        self.session_subscribers[session_id].add(client_id)
        logger.info(f"Client {client_id} subscribed to session {session_id}")

    def unsubscribe_from_session(self, client_id: str, session_id: str):
        """Unsubscribe a client from session updates"""
        if session_id in self.session_subscribers:
            self.session_subscribers[session_id].discard(client_id)


manager = ConnectionManager()

# Store running engines
running_engines: Dict[str, LoopEngine] = {}


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    Main WebSocket endpoint for real-time communication

    Events:
    - connect: Initial connection
    - subscribe: Subscribe to session updates
    - unsubscribe: Unsubscribe from session
    - start: Start session execution
    - pause: Pause session execution
    - resume: Resume session execution
    - stop: Stop session execution
    - feedback: Submit user feedback
    - preview: Request task preview
    """
    client_id = str(uuid.uuid4())

    await manager.connect(websocket, client_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            event_type = data.get("event")

            logger.debug(f"WebSocket event from {client_id}: {event_type}")

            # Handle different event types
            if event_type == "subscribe":
                await handle_subscribe(client_id, data, storage)

            elif event_type == "unsubscribe":
                await handle_unsubscribe(client_id, data)

            elif event_type == "start":
                await handle_start(client_id, data, storage)

            elif event_type == "pause":
                await handle_pause(client_id, data)

            elif event_type == "resume":
                await handle_resume(client_id, data)

            elif event_type == "stop":
                await handle_stop(client_id, data)

            elif event_type == "approve_task":
                await handle_approve_task(client_id, data)

            elif event_type == "feedback":
                await handle_feedback(client_id, data)

            elif event_type == "preview":
                await handle_preview(client_id, data, storage)

            elif event_type == "ping":
                # Respond to heartbeat ping
                await manager.send_personal(
                    {"event": "pong"},
                    client_id,
                )

            elif event_type == "connect":
                # Acknowledge connection
                await manager.send_personal(
                    {"event": "connected", "client_id": client_id},
                    client_id,
                )

            else:
                await manager.send_personal(
                    {
                        "event": "error",
                        "message": f"Unknown event type: {event_type}",
                    },
                    client_id,
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        await manager.send_personal(
            {
                "event": "error",
                "message": str(e),
            },
            client_id,
        )


async def handle_subscribe(
    client_id: str,
    data: dict,
    storage: SessionStorage,
):
    """Handle subscribe event"""
    session_id = data.get("session_id")
    logger.info(f"🔔 Subscribe request from {client_id[:8]} for session {session_id[:8] if session_id else 'None'}")
    
    if not session_id:
        logger.warning(f"❌ Subscribe failed: no session_id")
        await manager.send_personal(
            {"event": "error", "message": "session_id required"},
            client_id,
        )
        return

    # Verify session exists
    session = await storage.get_session(session_id)
    if not session:
        logger.warning(f"❌ Subscribe failed: session {session_id[:8]} not found")
        await manager.send_personal(
            {"event": "error", "message": f"Session {session_id} not found"},
            client_id,
        )
        return

    logger.info(f"✅ Subscribed to session {session_id[:8]}")
    manager.subscribe_to_session(client_id, session_id)

    # Get current progress if session is running
    progress = None
    if session_id in running_engines:
        engine = running_engines[session_id]
        progress = engine.planner.get_progress()
        # Add session_id and status to progress
        progress["session_id"] = session_id
        progress["status"] = session.get("status", "created")

    # Send current session state
    await manager.send_personal(
        {
            "event": "subscribed",
            "session_id": session_id,
            "session": session,
            "progress": progress,  # Include current progress
        },
        client_id,
    )


async def handle_unsubscribe(client_id: str, data: dict):
    """Handle unsubscribe event"""
    session_id = data.get("session_id")
    if session_id:
        manager.unsubscribe_from_session(client_id, session_id)

    await manager.send_personal(
        {"event": "unsubscribed", "session_id": session_id},
        client_id,
    )


async def handle_start(
    client_id: str,
    data: dict,
    storage: SessionStorage,
):
    """Handle start execution event"""
    session_id = data.get("session_id")
    logger.info(f"🚀 Start request from {client_id[:8]} for session {session_id[:8] if session_id else 'None'}")
    
    if not session_id:
        logger.warning(f"❌ Start failed: no session_id")
        await manager.send_personal(
            {"event": "error", "message": "session_id required"},
            client_id,
        )
        return

    # Verify session exists
    session = await storage.get_session(session_id)
    if not session:
        logger.warning(f"❌ Start failed: session {session_id[:8]} not found")
        await manager.send_personal(
            {"event": "error", "message": f"Session {session_id} not found"},
            client_id,
        )
        return

    # Check session status
    session_status = session.get("status", "created")
    logger.info(f"📊 Session {session_id[:8]} status: {session_status}")
    
    # If session is completed/failed, don't restart
    if session_status in ["completed", "failed"]:
        logger.info(f"ℹ️ Session {session_id[:8]} already {session_status}, not restarting")
        await manager.send_personal(
            {"event": "info", "message": f"Session already {session_status}"},
            client_id,
        )
        return

    # Check if already running in memory
    if session_id in running_engines:
        logger.info(f"ℹ️ Start ignored: session {session_id[:8]} already running (likely duplicate from React.StrictMode)")
        # Silently ignore duplicate start requests - don't send error to avoid user-facing warnings
        return
    
    # If session status is 'running' but not in running_engines (server restart case),
    # reset it to 'created' so we can restart from the beginning
    if session_status == "running":
        logger.warning(f"⚠️ Session {session_id[:8]} was running but engine not found (server restart?). Resetting to created.")
        from creative_autogpt.storage.session import SessionStatus
        await storage.update_session_status(session_id, SessionStatus.CREATED)
        session = await storage.get_session(session_id)

    try:
        logger.info(f"🔧 Creating engine for session {session_id[:8]}")
        
        # Create loop engine
        from creative_autogpt.modes.novel import NovelMode

        mode = NovelMode(config=session.get("config"))

        # Initialize components
        llm_client = MultiLLMClient()
        from creative_autogpt.storage.vector_store import VectorStore
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

        # Set callbacks for real-time updates
        def on_task_start(task):
            """Send task start notification"""
            provider = task.metadata.get("llm_provider", "unknown")
            model = task.metadata.get("llm_model", "unknown")
            logger.info(f"📋 Task started: {task.task_type.value} (using {provider})")
            import asyncio
            asyncio.create_task(
                manager.broadcast_to_session(
                    {
                        "event": "task_start",
                        "session_id": session_id,
                        "task": {
                            "id": task.task_id,  # For frontend key prop
                            "task_id": task.task_id,
                            "task_type": task.task_type.value,
                            "description": task.description,
                            "status": "running",
                            "llm_provider": provider,
                            "llm_model": model,
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    },
                    session_id,
                )
            )

        def on_task_complete(task, result, evaluation):
            """Send task complete notification and save to database"""
            logger.info(f"✅ Task completed: {task.task_type.value}")
            import asyncio
            
            # Save to database for persistence
            async def save_and_broadcast():
                try:
                    # Save task result to database
                    await storage.save_task_result(
                        session_id=session_id,
                        task_id=task.task_id,
                        task_type=task.task_type.value,
                        status="completed",
                        result=result,
                        metadata={
                            "description": task.description,
                            "chapter_index": task.metadata.get("chapter_index"),
                            "started_at": task.started_at,
                            "completed_at": task.completed_at,
                            "execution_time_seconds": task.execution_time_seconds,
                            "total_tokens": task.total_tokens,
                            "prompt_tokens": task.prompt_tokens,
                            "completion_tokens": task.completion_tokens,
                            "cost_usd": round(task.cost_usd, 6) if task.cost_usd else 0,
                            "failed_attempts": task.failed_attempts,
                            "retry_count": task.metadata.get("final_retry_count", 0),
                            "llm_provider": task.metadata.get("llm_provider", "unknown"),
                            "llm_model": task.metadata.get("llm_model", "unknown"),
                        },
                        evaluation=evaluation.to_dict() if evaluation else None,
                    )
                    logger.debug(f"💾 Saved task result to database: {task.task_type.value}")
                except Exception as e:
                    logger.error(f"Failed to save task result: {e}")
                
                # Broadcast to clients
                await manager.broadcast_to_session(
                    {
                        "event": "task_complete",
                        "session_id": session_id,
                        "task": {
                            "id": task.task_id,  # For frontend key prop
                            "task_id": task.task_id,
                            "task_type": task.task_type.value,
                            "description": task.description,
                            "status": "completed",
                            "result": result,  # Send full result for proper display
                            "evaluation": evaluation.to_dict() if evaluation else None,
                            "created_at": datetime.utcnow().isoformat(),
                            # 🔥 添加任务统计信息
                            "started_at": task.started_at,
                            "completed_at": task.completed_at,
                            "execution_time_seconds": task.execution_time_seconds,
                            "total_tokens": task.total_tokens,
                            "prompt_tokens": task.prompt_tokens,
                            "completion_tokens": task.completion_tokens,
                            "cost_usd": round(task.cost_usd, 6) if task.cost_usd else 0,
                            "failed_attempts": task.failed_attempts,
                            "retry_count": task.metadata.get("final_retry_count", 0),
                        },
                    },
                    session_id,
                )
            
            asyncio.create_task(save_and_broadcast())

        def on_progress(progress):
            """Send progress update"""
            logger.info(f"📊 Progress: {progress.get('completed_tasks', 0)}/{progress.get('total_tasks', 0)}")
            # Add session_id and status to progress
            progress["session_id"] = session_id
            progress["status"] = "running"
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

        def on_task_approval_needed(task, result, evaluation):
            """Send task approval request to frontend"""
            logger.info(f"⏸️  Task waiting approval: {task.task_type.value}")
            import asyncio
            asyncio.create_task(
                manager.broadcast_to_session(
                    {
                        "event": "task_approval_needed",
                        "session_id": session_id,
                        "task": {
                            "id": task.task_id,
                            "task_id": task.task_id,
                            "task_type": task.task_type.value,
                            "description": task.description,
                            "status": "pending_approval",
                            "result": result,  # Full result for preview
                            "evaluation": evaluation.to_dict() if evaluation else None,
                            "llm_provider": task.metadata.get("llm_provider", "unknown"),
                            "llm_model": task.metadata.get("llm_model", "unknown"),
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    },
                    session_id,
                )
            )

        def on_task_fail(task, error):
            """Send task failure notification to frontend"""
            logger.error(f"❌ Task failed: {task.task_type.value} - {error}")
            import asyncio
            asyncio.create_task(
                manager.broadcast_to_session(
                    {
                        "event": "task_fail",
                        "session_id": session_id,
                        "task": {
                            "id": task.task_id,
                            "task_id": task.task_id,
                            "task_type": task.task_type.value,
                            "description": task.description,
                            "status": "failed",
                            "error": str(error),
                            "llm_provider": task.metadata.get("llm_provider", "unknown"),
                            "llm_model": task.metadata.get("llm_model", "unknown"),
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    },
                    session_id,
                )
            )

        engine.set_callbacks(
            on_task_start=on_task_start,
            on_task_complete=on_task_complete,
            on_task_fail=on_task_fail,
            on_progress=on_progress,
            on_task_approval_needed=on_task_approval_needed,
        )

        # Store engine
        running_engines[session_id] = engine

        # Update session status
        from creative_autogpt.storage.session import SessionStatus
        await storage.update_session_status(session_id, SessionStatus.RUNNING)

        # Send start confirmation
        await manager.send_personal(
            {
                "event": "started",
                "session_id": session_id,
            },
            client_id,
        )

        # Run engine in background
        import asyncio

        async def run_engine():
            logger.info(f"🏃 run_engine started for session {session_id[:8]}")
            try:
                goal = session.get("goal", {})
                chapter_count = goal.get("chapter_count") or session.get("config", {}).get("chapter_count")
                logger.info(f"📚 Starting engine.run with goal: {goal.get('title', 'Untitled')}, chapters: {chapter_count}")
                
                result = await engine.run(
                    goal=goal,
                    chapter_count=chapter_count,
                )

                # Send completion event based on execution status
                event_type = "completed" if result.status == ExecutionStatus.COMPLETED else "failed"
                
                final_payload = {
                    "event": event_type,
                    "session_id": session_id,
                    "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "stats": result.stats.to_dict() if hasattr(result.stats, 'to_dict') else {},
                }

                # Broadcast to all subscribers
                await manager.broadcast_to_session(final_payload, session_id)

                # Also send directly to initiating client to ensure delivery
                await manager.send_personal(final_payload, client_id)

                # Update session status
                final_status = SessionStatus.COMPLETED if result.status == ExecutionStatus.COMPLETED else SessionStatus.FAILED
                await storage.update_session_status(session_id, final_status)

            except Exception as e:
                logger.error(f"❌ Error in run_engine for session {session_id}: {e}", exc_info=True)
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Still send failed event
                error_payload = {
                    "event": "failed",
                    "session_id": session_id,
                    "error": str(e),
                }
                await manager.broadcast_to_session(error_payload, session_id)
                await manager.send_personal(error_payload, client_id)
                await storage.update_session_status(session_id, SessionStatus.FAILED)
            
            finally:
                # Remove from running engines
                if session_id in running_engines:
                    del running_engines[session_id]

        asyncio.create_task(run_engine())

    except Exception as e:
        logger.error(f"Failed to start session {session_id}: {e}")
        await manager.send_personal(
            {
                "event": "error",
                "message": str(e),
            },
            client_id,
        )


async def handle_pause(client_id: str, data: dict):
    """Handle pause event"""
    session_id = data.get("session_id")
    if not session_id:
        return

    if session_id in running_engines:
        engine = running_engines[session_id]
        engine.pause()

        await manager.broadcast_to_session(
            {
                "event": "paused",
                "session_id": session_id,
            },
            session_id,
        )


async def handle_resume(client_id: str, data: dict):
    """Handle resume event"""
    session_id = data.get("session_id")
    if not session_id:
        return

    if session_id in running_engines:
        engine = running_engines[session_id]
        engine.resume()

        await manager.broadcast_to_session(
            {
                "event": "resumed",
                "session_id": session_id,
            },
            session_id,
        )


async def handle_stop(client_id: str, data: dict):
    """Handle stop event"""
    session_id = data.get("session_id")
    if not session_id:
        return

    if session_id in running_engines:
        engine = running_engines[session_id]
        engine.stop()

        await manager.broadcast_to_session(
            {
                "event": "stopped",
                "session_id": session_id,
            },
            session_id,
        )


async def handle_approve_task(client_id: str, data: dict):
    """Handle task approval event"""
    session_id = data.get("session_id")
    action = data.get("action", "approve")  # approve, reject, regenerate
    feedback = data.get("feedback")
    selected_idea = data.get("selected_idea")  # For brainstorm task: 1-4
    
    if not session_id:
        await manager.send_personal(
            {"event": "error", "message": "session_id required"},
            client_id,
        )
        return
    
    if session_id not in running_engines:
        await manager.send_personal(
            {"event": "error", "message": f"Session {session_id} not running"},
            client_id,
        )
        return
    
    engine = running_engines[session_id]
    engine.approve_task(action=action, feedback=feedback, selected_idea=selected_idea)
    
    logger.info(f"✅ Task approval from {client_id[:8]}: {action}" + 
                (f", selected idea: {selected_idea}" if selected_idea else ""))
    
    # Notify all subscribers
    await manager.broadcast_to_session(
        {
            "event": "task_approved",
            "session_id": session_id,
            "action": action,
            "selected_idea": selected_idea,
        },
        session_id,
    )


async def handle_feedback(client_id: str, data: dict):
    """Handle user feedback event"""
    session_id = data.get("session_id")
    message = data.get("message")
    task_id = data.get("task_id")
    scope = data.get("scope", "current_task")

    if not session_id or not message:
        return

    # Broadcast feedback to all subscribers
    await manager.broadcast_to_session(
        {
            "event": "feedback",
            "session_id": session_id,
            "feedback": {
                "task_id": task_id,
                "message": message,
                "scope": scope,
                "sender": client_id,
            },
        },
        session_id,
    )


async def handle_preview(
    client_id: str,
    data: dict,
    storage: SessionStorage,
):
    """Handle task preview request"""
    session_id = data.get("session_id")
    task_id = data.get("task_id")

    if not session_id or not task_id:
        await manager.send_personal(
            {"event": "error", "message": "session_id and task_id required"},
            client_id,
        )
        return

    # Get task result
    tasks = await storage.get_task_results(session_id)

    # Find the task
    task = None
    for t in tasks:
        if t["task_id"] == task_id:
            task = t
            break

    if not task:
        await manager.send_personal(
            {"event": "error", "message": f"Task {task_id} not found"},
            client_id,
        )
        return

    # Send preview
    await manager.send_personal(
        {
            "event": "preview",
            "session_id": session_id,
            "task_id": task_id,
            "preview": {
                "task_type": task["task_type"],
                "result": task.get("result", "")[:1000],  # Preview first 1000 chars
                "metadata": task.get("metadata", {}),
                "evaluation": task.get("evaluation"),
            },
        },
        client_id,
    )
