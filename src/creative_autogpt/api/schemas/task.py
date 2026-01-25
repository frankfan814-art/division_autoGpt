"""
API Schemas for Task management
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TaskResultResponse(BaseModel):
    """Schema for task result response"""

    id: str
    task_id: str
    task_type: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    evaluation: Optional[Dict[str, Any]] = None
    created_at: datetime
    chapter_index: Optional[int] = None

    class Config:
        from_attributes = True


class TaskPreviewRequest(BaseModel):
    """Schema for task preview request"""

    task_id: str
    feedback: Optional[str] = Field(None, description="User feedback for modification")


class TaskPreviewResponse(BaseModel):
    """Schema for task preview response"""

    task_id: str
    task_type: str
    description: str
    preview: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    can_modify: bool = True
    estimated_time: Optional[int] = None  # in seconds


class ChatMessage(BaseModel):
    """Schema for chat message"""

    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatFeedbackRequest(BaseModel):
    """Schema for chat feedback request"""

    session_id: str
    task_id: Optional[str] = None
    message: str = Field(..., description="User feedback message")
    scope: Optional[str] = Field(None, description="Feedback scope (current_task, chapter, all)")
