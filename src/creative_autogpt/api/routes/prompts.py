"""
Prompts API routes

Provides endpoints for smart prompt enhancement and feedback transformation.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from loguru import logger

from creative_autogpt.api.dependencies import (
    get_llm_client,
    get_prompt_manager,
)
from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.prompts.manager import PromptEnhancer, FeedbackTransformer, PromptManager


router = APIRouter(prefix="/prompts", tags=["prompts"])


class SmartEnhanceRequest(BaseModel):
    """Request schema for smart enhancement"""

    input: str = Field(..., description="User input text to enhance")
    current_config: Optional[Dict[str, Any]] = Field(None, description="Existing config to merge/update")


class SmartEnhanceResponse(BaseModel):
    """Response schema for smart enhancement"""

    config: Dict[str, Any]


class FeedbackTransformRequest(BaseModel):
    """Request schema for feedback transformation"""

    feedback: str = Field(..., description="User feedback text")
    task_type: str = Field(..., description="Task type context for transformation")
    current_content: str = Field(..., description="Current content to be modified")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context info")


class FeedbackTransformResponse(BaseModel):
    """Response schema for feedback transformation"""

    instruction: str


@router.post("/smart-enhance", response_model=SmartEnhanceResponse)
async def smart_enhance(
    data: SmartEnhanceRequest,
    llm_client: MultiLLMClient = Depends(get_llm_client),
):
    """
    Enhance a simple user input into a detailed creative configuration.

    - input: Required user input text
    - current_config: Optional existing configuration to merge
    """
    try:
        enhancer = PromptEnhancer(llm_client=llm_client)
        enhanced = await enhancer.enhance(
            user_input=data.input,
            current_config=data.current_config,
        )
        return SmartEnhanceResponse(config=enhanced)
    except Exception as e:
        logger.error(f"Smart enhance failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/feedback-transform", response_model=FeedbackTransformResponse)
async def feedback_transform(
    data: FeedbackTransformRequest,
    llm_client: MultiLLMClient = Depends(get_llm_client),
):
    """
    Transform casual user feedback into a professional modification instruction.
    """
    try:
        transformer = FeedbackTransformer(llm_client=llm_client)
        instruction = await transformer.transform(
            feedback=data.feedback,
            task_type=data.task_type,
            current_content=data.current_content,
            context=data.context,
        )
        return FeedbackTransformResponse(instruction=instruction)
    except Exception as e:
        logger.error(f"Feedback transform failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/styles", response_model=list[str])
async def list_styles(
    manager: PromptManager = Depends(get_prompt_manager),
):
    """List available style configuration names"""
    return manager.get_available_styles()


@router.get("/templates", response_model=list[str])
async def list_templates(
    manager: PromptManager = Depends(get_prompt_manager),
):
    """List available prompt template names"""
    return manager.get_available_templates()
