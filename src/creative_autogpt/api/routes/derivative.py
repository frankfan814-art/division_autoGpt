"""
Derivative Config API routes

Provides endpoints for managing derivative creation configuration (sequels, prequels, spinoffs, etc.)
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from loguru import logger

from creative_autogpt.storage.session import SessionStorage


router = APIRouter(prefix="/derivative", tags=["derivative"])


# Pydantic models for request/response
class DerivativeConfigCreate(BaseModel):
    """Model for creating derivative configuration"""
    type: str  # sequel, prequel, spinoff, adaptation, fanfic, rewrite
    title: str
    target_chapter_count: int
    target_word_count: int
    tone: str  # serious, lighthearted, dark, comedy, romance, epic
    writing_style: str
    original_elements: list[str]
    new_elements: list[str]
    keep_original_characters: bool
    new_character_count: int
    keep_original_worldview: bool
    world_changes: str
    plot_direction: str
    main_conflict: str
    notes: str


class DerivativeConfigUpdate(BaseModel):
    """Model for updating derivative configuration"""
    type: Optional[str] = None
    title: Optional[str] = None
    target_chapter_count: Optional[int] = None
    target_word_count: Optional[int] = None
    tone: Optional[str] = None
    writing_style: Optional[str] = None
    original_elements: Optional[list[str]] = None
    new_elements: Optional[list[str]] = None
    keep_original_characters: Optional[bool] = None
    new_character_count: Optional[int] = None
    keep_original_worldview: Optional[bool] = None
    world_changes: Optional[str] = None
    plot_direction: Optional[str] = None
    main_conflict: Optional[str] = None
    notes: Optional[str] = None


@router.get("/{session_id}")
async def get_derivative_config(session_id: str) -> Dict[str, Any]:
    """
    Get derivative configuration for a session
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract derivative config from session config
        config = session_data.get("config", {})
        derivative_config = config.get("derivative", {})

        if not derivative_config:
            return {
                "success": True,
                "config": None,
                "message": "No derivative configuration found"
            }

        return {
            "success": True,
            "config": derivative_config
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting derivative config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}")
async def create_derivative_config(
    session_id: str,
    data: DerivativeConfigCreate
) -> Dict[str, Any]:
    """
    Create derivative configuration for a session
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Check if derivative config already exists
        config = session_data.get("config", {})
        if config.get("derivative"):
            raise HTTPException(
                status_code=400,
                detail="Derivative configuration already exists. Use PUT to update."
            )

        # Create derivative config
        derivative_config = data.model_dump()

        # Update session config
        config["derivative"] = derivative_config
        session_data["config"] = config

        await session_storage.update_session(session_id, session_data)

        return {
            "success": True,
            "config": derivative_config
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating derivative config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}")
async def update_derivative_config(
    session_id: str,
    data: DerivativeConfigUpdate
) -> Dict[str, Any]:
    """
    Update derivative configuration for a session
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Get existing derivative config
        config = session_data.get("config", {})
        derivative_config = config.get("derivative", {})

        if not derivative_config:
            # Create new config if doesn't exist
            derivative_config = {}

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        derivative_config.update(update_data)

        # Update session config
        config["derivative"] = derivative_config
        session_data["config"] = config

        await session_storage.update_session(session_id, session_data)

        return {
            "success": True,
            "config": derivative_config
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating derivative config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_derivative_config(session_id: str) -> Dict[str, Any]:
    """
    Delete derivative configuration for a session
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Get existing config
        config = session_data.get("config", {})
        if not config.get("derivative"):
            raise HTTPException(
                status_code=404,
                detail="No derivative configuration found"
            )

        # Remove derivative config
        del config["derivative"]
        session_data["config"] = config

        await session_storage.update_session(session_id, session_data)

        return {
            "success": True,
            "message": "Derivative configuration deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting derivative config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/generate")
async def generate_derivative(session_id: str) -> Dict[str, Any]:
    """
    Start derivative creation process based on configuration
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Get derivative config
        config = session_data.get("config", {})
        derivative_config = config.get("derivative")

        if not derivative_config:
            raise HTTPException(
                status_code=400,
                detail="No derivative configuration found. Please configure first."
            )

        # TODO: Implement derivative generation logic
        # This would involve:
        # 1. Creating a new session for the derivative work
        # 2. Copying relevant data from original session
        # 3. Setting up the goal with derivative parameters
        # 4. Starting the loop engine

        logger.info(f"Derivative generation requested for session {session_id}")

        return {
            "success": True,
            "message": "Derivative generation started",
            "derivative_session_id": None  # Would be the new session ID
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating derivative: {e}")
        raise HTTPException(status_code=500, detail=str(e))
