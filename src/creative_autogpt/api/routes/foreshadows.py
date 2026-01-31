"""
Foreshadows API routes

Provides endpoints for managing foreshadowing elements, including:
- Listing all foreshadow elements
- Getting foreshadow details
- Creating, updating, deleting foreshadow elements
- Filtering by status (planted, paid_off, pending)
- Warning alerts for approaching deadlines
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from loguru import logger

from creative_autogpt.storage.session import SessionStorage


router = APIRouter(prefix="/foreshadows", tags=["foreshadows"])


# Pydantic models for request/response
class ForeshadowCreate(BaseModel):
    """Model for creating a new foreshadow element"""
    name: str
    type: str = "plot"
    importance: str = "minor"
    description: str = ""
    plant_chapter: Optional[int] = None
    payoff_chapter: Optional[int] = None


class ForeshadowUpdate(BaseModel):
    """Model for updating an existing foreshadow element"""
    name: Optional[str] = None
    type: Optional[str] = None
    importance: Optional[str] = None
    description: Optional[str] = None
    plant_chapter: Optional[int] = None
    payoff_chapter: Optional[int] = None


@router.get("/{session_id}")
async def list_foreshadows(
    session_id: str,
    status: Optional[str] = Query(None, description="Filter by status: planted, paid_off, pending"),
    importance: Optional[str] = Query(None, description="Filter by importance: critical, major, minor")
) -> Dict[str, Any]:
    """
    Get all foreshadow elements for a session

    Supports filtering by status and importance
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract foreshadow plugin state
        plugin_states = {}
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]

        foreshadow_data = plugin_states.get("foreshadow", {})

        elements = foreshadow_data.get("elements", [])
        plants = foreshadow_data.get("plants", {})
        payoffs = foreshadow_data.get("payoffs", {})

        # Build foreshadow list with status
        foreshadow_list = []
        warnings = []

        for element in elements:
            element_id = element.get("element_id", "")
            name = element.get("name", "Unknown")
            element_type = element.get("type", "plot")
            importance_level = element.get("importance", "minor")
            description = element.get("description", "")
            plant_chapter = element.get("plant_chapter")
            payoff_chapter = element.get("payoff_chapter")

            # Determine status
            has_plant = element_id in plants and len(plants[element_id]) > 0
            has_payoff = element_id in payoffs and len(payoffs[element_id]) > 0

            if has_payoff:
                status_val = "paid_off"
            elif has_plant:
                status_val = "planted"
            else:
                status_val = "pending"

            # Apply filters
            if status and status_val != status:
                continue
            if importance and importance_level != importance:
                continue

            # Check for warnings
            current_chapter = session_data.get("current_task_index", 0)
            warning = None
            if has_plant and not has_payoff and payoff_chapter:
                chapters_until = payoff_chapter - current_chapter
                if chapters_until <= 0:
                    warning = f"已超过预计回收章节 {abs(chapters_until)} 章"
                    warnings.append({
                        "element_id": element_id,
                        "name": name,
                        "type": "overdue",
                        "severity": "high",
                        "message": warning
                    })
                elif chapters_until <= 5:
                    warning = f"距离预计回收章节还有 {chapters_until} 章"
                    warnings.append({
                        "element_id": element_id,
                        "name": name,
                        "type": "approaching",
                        "severity": "medium" if chapters_until <= 3 else "low",
                        "message": warning
                    })

            foreshadow_list.append({
                "id": element_id,
                "name": name,
                "type": element_type,
                "importance": importance_level,
                "description": description,
                "status": status_val,
                "plant_chapter": plant_chapter,
                "payoff_chapter": payoff_chapter,
                "warning": warning,
            })

        # Sort by importance and chapter
        importance_order = {"critical": 0, "major": 1, "minor": 2}
        foreshadow_list.sort(key=lambda x: (importance_order.get(x["importance"], 3), x["plant_chapter"] or 999))

        return {
            "success": True,
            "foreshadows": foreshadow_list,
            "total": len(foreshadow_list),
            "warnings": warnings if not status else []  # Only include warnings when not filtering
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing foreshadows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/stats")
async def get_foreshadow_stats(session_id: str) -> Dict[str, Any]:
    """
    Get foreshadow statistics for the session

    Returns counts by status, importance, and warnings
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract foreshadow plugin state
        plugin_states = {}
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]

        foreshadow_data = plugin_states.get("foreshadow", {})

        elements = foreshadow_data.get("elements", [])
        plants = foreshadow_data.get("plants", {})
        payoffs = foreshadow_data.get("payoffs", {})

        current_chapter = session_data.get("current_task_index", 0)

        # Calculate stats
        status_counts = {"planted": 0, "paid_off": 0, "pending": 0}
        importance_counts = {"critical": 0, "major": 0, "minor": 0}
        warning_count = 0

        for element in elements:
            element_id = element.get("element_id", "")
            importance_level = element.get("importance", "minor")

            importance_counts[importance_level] = importance_counts.get(importance_level, 0) + 1

            has_plant = element_id in plants and len(plants[element_id]) > 0
            has_payoff = element_id in payoffs and len(payoffs[element_id]) > 0

            if has_payoff:
                status_counts["paid_off"] += 1
            elif has_plant:
                status_counts["planted"] += 1
            else:
                status_counts["pending"] += 1

            # Check warnings
            payoff_chapter = element.get("payoff_chapter")
            if has_plant and not has_payoff and payoff_chapter:
                chapters_until = payoff_chapter - current_chapter
                if chapters_until <= 5:
                    warning_count += 1

        return {
            "success": True,
            "stats": {
                "total_elements": len(elements),
                "status_counts": status_counts,
                "importance_counts": importance_counts,
                "warning_count": warning_count,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting foreshadow stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/warnings")
async def get_foreshadow_warnings(session_id: str) -> Dict[str, Any]:
    """
    Get foreshadow warnings for the session

    Returns alerts for overdue or approaching payoffs
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract foreshadow plugin state
        plugin_states = {}
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]

        foreshadow_data = plugin_states.get("foreshadow", {})

        elements = foreshadow_data.get("elements", [])
        plants = foreshadow_data.get("plants", {})
        payoffs = foreshadow_data.get("payoffs", {})

        current_chapter = session_data.get("current_task_index", 0)

        warnings = []

        for element in elements:
            element_id = element.get("element_id", "")
            name = element.get("name", "Unknown")
            importance_level = element.get("importance", "minor")
            payoff_chapter = element.get("payoff_chapter")

            has_plant = element_id in plants and len(plants[element_id]) > 0
            has_payoff = element_id in payoffs and len(payoffs[element_id]) > 0

            if has_plant and not has_payoff and payoff_chapter:
                chapters_until = payoff_chapter - current_chapter

                if chapters_until <= 0:
                    warnings.append({
                        "element_id": element_id,
                        "name": name,
                        "importance": importance_level,
                        "type": "overdue",
                        "severity": "high",
                        "message": f"已超过预计回收章节 {abs(chapters_until)} 章",
                        "payoff_chapter": payoff_chapter,
                        "current_chapter": current_chapter,
                    })
                elif chapters_until <= 5:
                    severity = "high" if chapters_until <= 2 else "medium"
                    warnings.append({
                        "element_id": element_id,
                        "name": name,
                        "importance": importance_level,
                        "type": "approaching",
                        "severity": severity,
                        "message": f"距离预计回收章节还有 {chapters_until} 章",
                        "payoff_chapter": payoff_chapter,
                        "current_chapter": current_chapter,
                    })

        # Sort by severity and overdue first
        severity_order = {"high": 0, "medium": 1, "low": 2}
        warnings.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["type"] == "overdue"))

        return {
            "success": True,
            "warnings": warnings,
            "total": len(warnings)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting foreshadow warnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/{element_id}")
async def get_foreshadow_detail(session_id: str, element_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific foreshadow element

    Includes plant locations, payoff locations, and related context
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract foreshadow plugin state
        plugin_states = {}
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]

        foreshadow_data = plugin_states.get("foreshadow", {})

        elements = foreshadow_data.get("elements", [])
        plants = foreshadow_data.get("plants", {})
        payoffs = foreshadow_data.get("payoffs", {})

        # Find element
        element = None
        for el in elements:
            if el.get("element_id") == element_id:
                element = el
                break

        if not element:
            raise HTTPException(status_code=404, detail=f"Foreshadow element {element_id} not found")

        element_plants = plants.get(element_id, [])
        element_payoffs = payoffs.get(element_id, [])

        return {
            "success": True,
            "foreshadow": {
                "id": element_id,
                "name": element.get("name"),
                "type": element.get("type"),
                "importance": element.get("importance"),
                "description": element.get("description"),
                "plant_chapter": element.get("plant_chapter"),
                "payoff_chapter": element.get("payoff_chapter"),
                "plants": element_plants,
                "payoffs": element_payoffs,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting foreshadow detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}")
async def create_foreshadow(session_id: str, data: ForeshadowCreate) -> Dict[str, Any]:
    """
    Create a new foreshadow element
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract foreshadow plugin state
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
            # Need to update engine_state
            update_engine_state = True
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]
            update_engine_state = False
        else:
            plugin_states = {}
            update_engine_state = True

        foreshadow_data = plugin_states.get("foreshadow", {})
        elements = foreshadow_data.get("elements", [])

        # Generate unique element_id
        element_id = f"foreshadow_{len(elements) + 1}_{hash(data.name)}"[:50]

        # Create new element
        new_element = {
            "element_id": element_id,
            "name": data.name,
            "type": data.type,
            "importance": data.importance,
            "description": data.description,
            "plant_chapter": data.plant_chapter,
            "payoff_chapter": data.payoff_chapter,
        }

        elements.append(new_element)
        foreshadow_data["elements"] = elements
        plugin_states["foreshadow"] = foreshadow_data

        # Update session data
        if update_engine_state:
            session_data["engine_state"]["plugin_states"] = plugin_states
        else:
            session_data["goal"]["metadata"] = plugin_states

        await session_storage.update_session(session_id, session_data)

        return {
            "success": True,
            "element_id": element_id,
            "foreshadow": new_element
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating foreshadow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}/{element_id}")
async def update_foreshadow(
    session_id: str,
    element_id: str,
    data: ForeshadowUpdate
) -> Dict[str, Any]:
    """
    Update an existing foreshadow element
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract foreshadow plugin state
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
            update_engine_state = True
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]
            update_engine_state = False
        else:
            raise HTTPException(status_code=404, detail=f"Foreshadow plugin state not found")

        foreshadow_data = plugin_states.get("foreshadow", {})
        elements = foreshadow_data.get("elements", [])

        # Find and update element
        element_found = False
        for element in elements:
            if element.get("element_id") == element_id:
                if data.name is not None:
                    element["name"] = data.name
                if data.type is not None:
                    element["type"] = data.type
                if data.importance is not None:
                    element["importance"] = data.importance
                if data.description is not None:
                    element["description"] = data.description
                if data.plant_chapter is not None:
                    element["plant_chapter"] = data.plant_chapter
                if data.payoff_chapter is not None:
                    element["payoff_chapter"] = data.payoff_chapter
                element_found = True
                break

        if not element_found:
            raise HTTPException(status_code=404, detail=f"Foreshadow element {element_id} not found")

        foreshadow_data["elements"] = elements
        plugin_states["foreshadow"] = foreshadow_data

        # Update session data
        if update_engine_state:
            session_data["engine_state"]["plugin_states"] = plugin_states
        else:
            session_data["goal"]["metadata"] = plugin_states

        await session_storage.update_session(session_id, session_data)

        return {
            "success": True,
            "element_id": element_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating foreshadow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}/{element_id}")
async def delete_foreshadow(session_id: str, element_id: str) -> Dict[str, Any]:
    """
    Delete a foreshadow element
    """
    try:
        session_storage = SessionStorage()

        # Get session data
        session_data = await session_storage.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract foreshadow plugin state
        if session_data.get("engine_state"):
            plugin_states = session_data["engine_state"].get("plugin_states", {})
            update_engine_state = True
        elif session_data.get("goal", {}).get("metadata"):
            plugin_states = session_data["goal"]["metadata"]
            update_engine_state = False
        else:
            raise HTTPException(status_code=404, detail=f"Foreshadow plugin state not found")

        foreshadow_data = plugin_states.get("foreshadow", {})
        elements = foreshadow_data.get("elements", [])
        plants = foreshadow_data.get("plants", {})
        payoffs = foreshadow_data.get("payoffs", {})

        # Find and remove element
        original_length = len(elements)
        elements = [el for el in elements if el.get("element_id") != element_id]

        if len(elements) == original_length:
            raise HTTPException(status_code=404, detail=f"Foreshadow element {element_id} not found")

        # Remove from plants and payoffs
        if element_id in plants:
            del plants[element_id]
        if element_id in payoffs:
            del payoffs[element_id]

        foreshadow_data["elements"] = elements
        foreshadow_data["plants"] = plants
        foreshadow_data["payoffs"] = payoffs
        plugin_states["foreshadow"] = foreshadow_data

        # Update session data
        if update_engine_state:
            session_data["engine_state"]["plugin_states"] = plugin_states
        else:
            session_data["goal"]["metadata"] = plugin_states

        await session_storage.update_session(session_id, session_data)

        return {
            "success": True,
            "message": f"Foreshadow element {element_id} deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting foreshadow: {e}")
        raise HTTPException(status_code=500, detail=str(e))
