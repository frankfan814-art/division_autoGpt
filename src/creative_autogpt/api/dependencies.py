"""
API dependencies for FastAPI
"""

from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.core.vector_memory import VectorMemoryManager
from creative_autogpt.core.evaluator import EvaluationEngine
from creative_autogpt.prompts.manager import PromptManager
from creative_autogpt.plugins.manager import PluginManager
from creative_autogpt.utils.config import get_settings

security = HTTPBearer(auto_error=False)


# Global dependencies
_session_storage: Optional[SessionStorage] = None
_llm_client: Optional[MultiLLMClient] = None
_memory_manager: Optional[VectorMemoryManager] = None
_evaluator: Optional[EvaluationEngine] = None
_prompt_manager: Optional[PromptManager] = None
_plugin_manager: Optional[PluginManager] = None


async def get_session_storage() -> SessionStorage:
    """Get session storage instance"""
    global _session_storage
    if _session_storage is None:
        _session_storage = SessionStorage()
        await _session_storage.initialize()
    return _session_storage


async def get_llm_client() -> MultiLLMClient:
    """Get LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiLLMClient()
    return _llm_client


async def get_memory_manager() -> VectorMemoryManager:
    """Get memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        from creative_autogpt.storage.vector_store import VectorStore
        vector_store = VectorStore()
        _memory_manager = VectorMemoryManager(vector_store=vector_store)
    return _memory_manager


async def get_evaluator(
    llm_client: MultiLLMClient = Depends(get_llm_client),
) -> EvaluationEngine:
    """Get evaluator instance"""
    global _evaluator
    if _evaluator is None:
        _evaluator = EvaluationEngine(llm_client=llm_client)
    return _evaluator


async def get_prompt_manager() -> PromptManager:
    """Get prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


async def get_plugin_manager() -> PluginManager:
    """Get plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


async def verify_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
) -> Dict[str, Any]:
    """
    Verify that a session exists

    Args:
        session_id: The session ID
        storage: Session storage

    Returns:
        Session data

    Raises:
        HTTPException: If session not found
    """
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return session


async def get_active_session(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
) -> Dict[str, Any]:
    """
    Get an active (running or paused) session

    Args:
        session_id: The session ID
        storage: Session storage

    Returns:
        Session data

    Raises:
        HTTPException: If session not active
    """
    session = await verify_session(session_id, storage)

    from creative_autogpt.api.schemas.session import SessionStatus

    if session["status"] not in (SessionStatus.RUNNING, SessionStatus.PAUSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not active (status: {session['status']})"
        )

    return session


# Optional authentication
async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Optional authentication dependency

    Args:
        credentials: Optional HTTP authorization credentials

    Returns:
        User ID if authenticated, None otherwise
    """
    if credentials is None:
        return None

    settings = get_settings()
    if credentials.credentials != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )

    return "authenticated"
