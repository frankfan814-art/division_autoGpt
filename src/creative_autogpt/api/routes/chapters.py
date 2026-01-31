"""
Chapter API routes - Chapter rewrite and version management
"""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from loguru import logger

from creative_autogpt.api.schemas.response import SuccessResponse
from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.api.dependencies import get_session_storage

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.post("/{session_id}/rewrite")
async def rewrite_chapter(
    session_id: str,
    chapter_index: int,
    reason: Optional[str] = None,
    feedback: Optional[str] = None,
    max_retries: int = 3,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    重写指定章节

    - **session_id**: 会话ID
    - **chapter_index**: 章节索引
    - **reason**: 重写原因（可选）
    - **feedback**: 用户反馈（可选）
    - **max_retries**: 最大重试次数（默认3次）
    """
    # 验证会话存在
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    # 验证章节存在
    tasks = await storage.get_task_results(
        session_id,
        chapter_index=chapter_index,
    )

    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_index} not found in session {session_id}"
        )

    try:
        # 导入重写器（避免循环导入）
        from creative_autogpt.core.chapter_rewriter import ChapterRewriter
        from creative_autogpt.utils.llm_client import MultiLLMClient
        from creative_autogpt.storage.vector_store import VectorStore
        from creative_autogpt.core.vector_memory import VectorMemoryManager
        from creative_autogpt.core.evaluator import EvaluationEngine

        # 创建重写器
        llm_client = MultiLLMClient()
        vector_store = VectorStore(session_id=session_id)
        memory = VectorMemoryManager(vector_store=vector_store)
        evaluator = EvaluationEngine(llm_client=llm_client)

        rewriter = ChapterRewriter(
            session_id=session_id,
            storage=storage,
            llm_client=llm_client,
            memory=memory,
            evaluator=evaluator,
        )

        # 执行重写
        result = await rewriter.rewrite_chapter(
            chapter_index=chapter_index,
            reason=reason,
            feedback=feedback,
            max_retries=max_retries,
        )

        return {
            "success": True,
            "chapter_index": chapter_index,
            "version_number": result["version_number"],
            "score": result["score"],
            "passed": result["passed"],
            "retry_count": result["retry_count"],
            "content_preview": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"],
        }

    except ValueError as e:
        logger.error(f"Failed to rewrite chapter: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to rewrite chapter: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rewrite chapter: {str(e)}"
        )


@router.get("/{session_id}/versions")
async def list_chapters(
    session_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    获取会话中所有章节的版本信息

    - **session_id**: 会话ID
    """
    # 验证会话存在
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # 获取所有任务结果
        tasks = await storage.get_task_results(session_id)

        # 按章节索引分组
        chapters: Dict[int, List[Dict]] = {}
        for task in tasks:
            chapter_index = task.get("chapter_index")
            if chapter_index is not None:
                if chapter_index not in chapters:
                    chapters[chapter_index] = []
                chapters[chapter_index].append(task)

        # 获取每个章节的版本信息
        result = []
        for chapter_index in sorted(chapters.keys()):
            versions = await storage.get_chapter_versions(session_id, chapter_index)
            current_version = await storage.get_current_chapter_version(session_id, chapter_index)

            result.append({
                "chapter_index": chapter_index,
                "total_versions": len(versions),
                "current_version": current_version,
                "versions": versions[:3],  # 只返回最近3个版本
            })

        return {
            "success": True,
            "chapters": result,
        }

    except Exception as e:
        logger.error(f"Failed to list chapters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chapters: {str(e)}"
        )


@router.get("/{session_id}/chapters/{chapter_index}/versions")
async def get_chapter_versions(
    session_id: str,
    chapter_index: int,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    获取指定章节的所有版本

    - **session_id**: 会话ID
    - **chapter_index**: 章节索引
    """
    # 验证会话存在
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        versions = await storage.get_chapter_versions(session_id, chapter_index)

        return {
            "success": True,
            "chapter_index": chapter_index,
            "total_versions": len(versions),
            "versions": versions,
        }

    except Exception as e:
        logger.error(f"Failed to get chapter versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chapter versions: {str(e)}"
        )


@router.post("/{session_id}/chapters/{chapter_index}/versions/{version_id}/restore")
async def restore_chapter_version(
    session_id: str,
    chapter_index: int,
    version_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    恢复到指定版本

    - **session_id**: 会话ID
    - **chapter_index**: 章节索引
    - **version_id**: 版本ID
    """
    # 验证会话存在
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # 获取任务ID
        tasks = await storage.get_task_results(
            session_id,
            chapter_index=chapter_index,
        )

        if not tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chapter {chapter_index} not found"
            )

        task_id = tasks[0]["task_id"]

        # 恢复版本
        success = await storage.restore_chapter_version(
            session_id=session_id,
            task_id=task_id,
            version_id=version_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to restore version {version_id}"
            )

        return {
            "success": True,
            "message": f"Restored chapter {chapter_index} to version {version_id}",
            "chapter_index": chapter_index,
            "version_id": version_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore chapter version: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore chapter version: {str(e)}"
        )


@router.get("/{session_id}/chapters/{chapter_index}/versions/{version_id}")
async def get_chapter_version_detail(
    session_id: str,
    chapter_index: int,
    version_id: str,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    获取指定版本的详细信息

    - **session_id**: 会话ID
    - **chapter_index**: 章节索引
    - **version_id**: 版本ID
    """
    # 验证会话存在
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # 获取所有版本
        versions = await storage.get_chapter_versions(session_id, chapter_index)

        # 查找指定版本
        version = None
        for v in versions:
            if v["id"] == version_id:
                version = v
                break

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_id} not found"
            )

        return {
            "success": True,
            "version": version,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chapter version detail: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chapter version detail: {str(e)}"
        )


@router.get("/{session_id}/chapters/{chapter_index}/context")
async def get_chapter_context(
    session_id: str,
    chapter_index: int,
    storage: SessionStorage = Depends(get_session_storage),
):
    """
    获取章节的上下文信息（相关人物、门派、伏笔等）

    - **session_id**: 会话ID
    - **chapter_index**: 章节索引
    """
    # 验证会话存在
    session = await storage.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    try:
        # 获取会话数据中的插件状态
        plugin_states = {}
        if session.get("engine_state"):
            plugin_states = session["engine_state"].get("plugin_states", {})
        elif session.get("goal", {}).get("metadata"):
            plugin_states = session["goal"]["metadata"]

        # 提取人物信息
        character_data = plugin_states.get("character", {})
        characters = character_data.get("characters", {})
        relationships = character_data.get("relationships", {})

        # 提取伏笔信息
        foreshadow_data = plugin_states.get("foreshadow", {})
        elements = foreshadow_data.get("elements", [])
        plants = foreshadow_data.get("plants", {})
        payoffs = foreshadow_data.get("payoffs", {})

        # 找出本章相关的人物（简化逻辑：返回主要人物）
        relevant_characters = []
        for char_id, char_data in list(characters.items())[:10]:  # 限制数量
            char_relationships = relationships.get(char_id, [])
            relevant_characters.append({
                "id": char_id,
                "name": char_data.get("name", "Unknown"),
                "role": char_data.get("role", "unspecified"),
                "personality_traits": char_data.get("personality", {}).get("traits", [])[:5],
            })

        # 找出本章相关的伏笔（需要在本章回收或附近埋设的）
        relevant_foreshadows = []
        for element in elements:
            element_id = element.get("element_id", "")
            plant_chapter = element.get("plant_chapter")
            payoff_chapter = element.get("payoff_chapter")

            # 如果伏笔在当前章节附近（前后5章）
            if plant_chapter and abs(plant_chapter - chapter_index) <= 5:
                has_plant = element_id in plants and len(plants[element_id]) > 0
                has_payoff = element_id in payoffs and len(payoffs[element_id]) > 0
                status = "paid_off" if has_payoff else "planted" if has_plant else "pending"
                relevant_foreshadows.append({
                    "id": element_id,
                    "name": element.get("name"),
                    "importance": element.get("importance"),
                    "status": status,
                    "plant_chapter": plant_chapter,
                    "payoff_chapter": payoff_chapter,
                    "relation": "埋设" if plant_chapter == chapter_index else
                                 "回收" if payoff_chapter == chapter_index else
                                 "附近",
                })

        # 获取前一章和后一章的信息
        previous_chapter = None
        next_chapter = None

        all_tasks = await storage.get_task_results(session_id)
        chapter_tasks = [t for t in all_tasks if t.get("chapter_index") is not None]

        if chapter_index > 0:
            prev_tasks = [t for t in chapter_tasks if t.get("chapter_index") == chapter_index - 1]
            if prev_tasks:
                previous_chapter = {
                    "chapter_index": chapter_index - 1,
                    "has_content": any(t.get("result") for t in prev_tasks),
                }

        next_tasks = [t for t in chapter_tasks if t.get("chapter_index") == chapter_index + 1]
        if next_tasks:
            next_chapter = {
                "chapter_index": chapter_index + 1,
                "has_content": any(t.get("result") for t in next_tasks),
            }

        return {
            "success": True,
            "context": {
                "chapter_index": chapter_index,
                "characters": relevant_characters,
                "foreshadows": relevant_foreshadows[:5],  # 限制数量
                "previous_chapter": previous_chapter,
                "next_chapter": next_chapter,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chapter context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chapter context: {str(e)}"
        )
