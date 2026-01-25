"""
API Response schemas
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Schema for error response"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")


class SuccessResponse(BaseModel):
    """Schema for success response"""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    """Schema for health check response"""

    status: str = "healthy"
    version: str
    llm_providers: List[str] = Field(default_factory=list)
    storage_status: str = "ok"
    memory_status: str = "ok"


class StreamChunk(BaseModel):
    """Schema for streaming content chunk"""

    content: str
    done: bool = False
    metadata: Optional[Dict[str, Any]] = None
