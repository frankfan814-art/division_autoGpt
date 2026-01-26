"""
API Schemas for Session management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """Status of a writing session"""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionCreate(BaseModel):
    """Schema for creating a new session"""

    title: str = Field(..., description="Session title", min_length=1, max_length=200)
    mode: str = Field(default="novel", description="Writing mode")
    goal: Dict[str, Any] = Field(default_factory=dict, description="Creation goal")
    config: Dict[str, Any] = Field(default_factory=dict, description="Session configuration")


class SessionUpdate(BaseModel):
    """Schema for updating a session"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[SessionStatus] = None
    goal: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class SessionResponse(BaseModel):
    """Schema for session response"""

    id: str
    title: str
    mode: str
    status: SessionStatus
    goal: Dict[str, Any]
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    llm_calls: int = 0
    tokens_used: int = 0
    # 🔥 新增：重写状态字段
    is_rewriting: bool = False
    rewrite_attempt: Optional[int] = None
    rewrite_task_id: Optional[str] = None
    rewrite_task_type: Optional[str] = None

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Schema for session list response"""

    items: List[SessionResponse]
    total: int
    page: int
    page_size: int


class SessionProgress(BaseModel):
    """Schema for session progress"""

    session_id: str
    status: SessionStatus
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    percentage: float
    current_task: Optional[str] = None
    estimated_remaining: Optional[int] = None  # in seconds
    # 🔥 新增：重写状态字段
    is_rewriting: bool = False
    rewrite_attempt: Optional[int] = None
    rewrite_task_type: Optional[str] = None


class SessionExportRequest(BaseModel):
    """Schema for export request"""

    format: str = Field(default="txt", description="Export format (txt, json, md)")
    include_metadata: bool = Field(default=True, description="Include metadata")
    chapter_range: Optional[tuple[int, int]] = Field(None, description="Chapter range (start, end)")
