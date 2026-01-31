"""
Characters API routes

Provides endpoints for managing character data, including:
- Listing all characters
- Getting character details
- Creating/updating/deleting characters
- Character relationships
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from loguru import logger

from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.plugins.character import CharacterPlugin


router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("/{session_id}")
async def list_characters(
    session_id: str,
    role: Optional[str] = Query(None, description="Filter by role (protagonist, antagonist, supporting, etc.)")
) -> Dict[str, Any]:
    """
    Get all characters for a session

    Returns character list with basic info and metadata
    """
    try:
        session_storage = SessionStorage()

        # Get session data to extract plugin states
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract character plugin state from engine_state or metadata
        plugin_states = {}
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]

        characters_data = plugin_states.get("character", {})

        # Extract characters list
        characters = characters_data.get("characters", {})
        relationships = characters_data.get("relationships", {})
        arcs = characters_data.get("arcs", {})

        # Build character list
        character_list = []
        for char_id, char_data in characters.items():
            # Apply role filter if specified
            if role and char_data.get("role") != role:
                continue

            # Get related info
            char_relationships = relationships.get(char_id, [])
            char_arcs = arcs.get(char_id, [])

            # Count appearances (from arc data)
            appearances = 0
            for arc in char_arcs:
                appearances += arc.get("chapters", [])

            character_list.append({
                "id": char_id,
                "name": char_data.get("name", "Unknown"),
                "role": char_data.get("role", "unspecified"),
                "age": char_data.get("age"),
                "gender": char_data.get("gender"),
                "personality_traits": char_data.get("personality", {}).get("traits", []),
                "background": char_data.get("background", ""),
                "goals": char_data.get("goals", {}).get("main", ""),
                "relationships_count": len(char_relationships),
                "arc_stages": len(char_arcs),
                "appearances": appearances,
            })

        return {
            "success": True,
            "characters": character_list,
            "total": len(character_list)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/{character_id}")
async def get_character_detail(session_id: str, character_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific character

    Includes full profile, relationships, and development arcs
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract character plugin state
        plugin_states = {}
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]

        characters_data = plugin_states.get("character", {})

        characters = characters_data.get("characters", {})
        relationships = characters_data.get("relationships", {})
        arcs = characters_data.get("arcs", {})

        if character_id not in characters:
            raise HTTPException(status_code=404, detail=f"Character {character_id} not found")

        char_data = characters[character_id]
        char_relationships = relationships.get(character_id, [])
        char_arcs = arcs.get(character_id, [])

        return {
            "success": True,
            "character": {
                "id": character_id,
                "name": char_data.get("name"),
                "age": char_data.get("age"),
                "gender": char_data.get("gender"),
                "appearance": char_data.get("appearance", ""),
                "personality": char_data.get("personality", {}),
                "background": char_data.get("background", ""),
                "goals": char_data.get("goals", {}),
                "voice_profile": char_data.get("voice_profile", {}),
                "relationships": char_relationships,
                "development_arcs": char_arcs,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/stats")
async def get_character_stats(session_id: str) -> Dict[str, Any]:
    """
    Get character statistics for the session

    Returns counts by role, total appearances, etc.
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract character plugin state
        plugin_states = {}
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]

        characters_data = plugin_states.get("character", {})

        characters = characters_data.get("characters", {})
        relationships = characters_data.get("relationships", {})
        arcs = characters_data.get("arcs", {})

        # Calculate stats
        role_counts = {}
        total_relationships = 0
        total_appearances = 0

        for char_id, char_data in characters.items():
            role = char_data.get("role", "unspecified")
            role_counts[role] = role_counts.get(role, 0) + 1

            total_relationships += len(relationships.get(char_id, []))

            for arc in arcs.get(char_id, []):
                total_appearances += len(arc.get("chapters", []))

        return {
            "success": True,
            "stats": {
                "total_characters": len(characters),
                "role_counts": role_counts,
                "total_relationships": total_relationships,
                "total_appearances": total_appearances,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
