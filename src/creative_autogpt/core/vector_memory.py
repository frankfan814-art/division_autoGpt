"""
Vector Memory Manager - High-level memory management for creative writing

Provides intelligent context retrieval and memory organization for long-form
novel writing with support for:
- Recent context (last N tasks)
- Semantic search (vector similarity)
- Chapter-scoped memory
- Task-specific memory
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import deque

from loguru import logger

from creative_autogpt.storage.vector_store import (
    VectorStore,
    VectorMemoryItem,
    MemoryType,
    SearchResult,
)


# 🔥 任务类型到所需上下文类型的映射
TASK_CONTEXT_MAPPING: Dict[str, Set[str]] = {
    "世界观规则": {"大纲"},  # 基于大纲构建世界观
    "人物设计": {"大纲"},  # 基于大纲设计人物
    "事件": {"大纲", "世界观规则"},  # 基于前面内容设计事件
    "场景物品冲突": {"大纲", "世界观规则", "事件"},  # 综合前面内容
    "伏笔列表": {"大纲", "世界观规则", "事件", "人物设计", "场景物品冲突"},
    "章节大纲": {"大纲", "世界观规则", "事件", "人物设计", "伏笔列表", "场景物品冲突"},
    "场景生成": {"章节大纲", "大纲", "人物设计", "世界观规则", "事件"},
    # 🔥 章节内容：需要前几章的内容来保证连贯性！
    "章节内容": {"大纲", "世界观规则", "事件", "人物设计"},
    "章节润色": {"大纲", "世界观规则", "事件", "人物设计", "伏笔列表", "场景物品冲突", "章节大纲", "场景生成", "章节内容"},
    "润色": {"大纲", "世界观规则", "事件", "人物设计", "伏笔列表", "场景物品冲突", "章节大纲", "场景生成", "章节内容"},
}


@dataclass
class MemoryContext:
    """Context information for a task"""

    task_id: str
    task_type: str
    recent_results: List[Dict[str, Any]] = field(default_factory=list)
    relevant_memories: List[Dict[str, Any]] = field(default_factory=list)
    chapter_context: List[Dict[str, Any]] = field(default_factory=list)
    task_memories: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "recent_results": self.recent_results,
            "relevant_memories": self.relevant_memories,
            "chapter_context": self.chapter_context,
            "task_memories": self.task_memories,
        }


@dataclass
class TaskResult:
    """Result of a completed task"""

    task_id: str
    task_type: str
    content: str
    memory_type: MemoryType
    metadata: Dict[str, Any] = field(default_factory=dict)
    chapter_index: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    evaluation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "metadata": self.metadata,
            "chapter_index": self.chapter_index,
            "created_at": self.created_at.isoformat(),
            "evaluation": self.evaluation,
        }


class VectorMemoryManager:
    """
    High-level memory manager for creative writing

    Manages:
    - Short-term memory (recent task results)
    - Long-term memory (vector-based semantic storage)
    - Context retrieval for tasks
    - Chapter-scoped memory
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        short_term_size: int = 10,
    ):
        """
        Initialize memory manager

        Args:
            vector_store: VectorStore instance (created if None)
            short_term_size: Number of recent results to keep in memory
        """
        self.vector_store = vector_store or VectorStore()
        self.short_term_size = short_term_size

        # Short-term memory (deque for efficient pops)
        self._short_term: deque = deque(maxlen=short_term_size)

        # Task results cache (task_id -> TaskResult)
        self._task_results: Dict[str, TaskResult] = {}

        # Current chapter index
        self._current_chapter: Optional[int] = None

        logger.info(
            f"VectorMemoryManager initialized (short_term_size={short_term_size})"
        )

    async def store(
        self,
        content: str,
        task_id: str,
        task_type: str,
        memory_type: MemoryType = MemoryType.GENERAL,
        metadata: Optional[Dict[str, Any]] = None,
        chapter_index: Optional[int] = None,
        evaluation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a result in both short-term and long-term memory

        Args:
            content: The content to store
            task_id: Associated task ID
            task_type: Type of task
            memory_type: Type of memory
            metadata: Additional metadata
            chapter_index: Associated chapter index
            evaluation: Evaluation results

        Returns:
            The ID of the stored item
        """
        # Create task result
        result = TaskResult(
            task_id=task_id,
            task_type=task_type,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
            chapter_index=chapter_index,
            evaluation=evaluation,
        )

        # Store in short-term memory
        self._short_term.append(result)
        self._task_results[task_id] = result

        # Store in vector store
        vector_metadata = {
            "task_type": task_type,
            **metadata,
        }

        if evaluation:
            import json
            vector_metadata["evaluation"] = json.dumps(evaluation, ensure_ascii=False)

        item_id = await self.vector_store.add(
            content=content,
            memory_type=memory_type,
            metadata=vector_metadata,
            task_id=task_id,
            chapter_index=chapter_index,
        )

        logger.debug(
            f"Stored result for task {task_id} (type: {task_type}, "
            f"memory_type: {memory_type.value})"
        )

        return item_id

    async def get_context(
        self,
        task_id: str,
        task_type: str,
        query: Optional[str] = None,
        chapter_index: Optional[int] = None,
        top_k: int = 5,
        recent_count: int = 3,
        include_chapter_context: bool = True,
    ) -> MemoryContext:
        """
        Get context for a task from memory

        Args:
            task_id: The task ID
            task_type: Type of task
            query: Search query for relevant memories (uses task_type if None)
            chapter_index: Chapter index for scoped context
            top_k: Number of relevant memories to retrieve
            recent_count: Number of recent results to include
            include_chapter_context: Whether to include chapter-scoped context

        Returns:
            MemoryContext with all relevant information
        """
        context = MemoryContext(task_id=task_id, task_type=task_type)

        # 1. Recent results from short-term memory
        recent = list(self._short_term)[-recent_count:]
        context.recent_results = [r.to_dict() for r in recent if r.task_id != task_id]

        # 🔥 2. 根据任务类型检索特定上下文
        required_context_types = TASK_CONTEXT_MAPPING.get(task_type, None)

        if required_context_types:
            # 🔥 新逻辑：根据映射检索特定任务类型的内容
            logger.info(f"🔍 为任务 {task_type} 检索特定上下文: {required_context_types}")

            for context_type in required_context_types:
                # 从短期内存中查找匹配的任务类型
                matching_results = []
                for result in self._short_term:
                    if result.task_id != task_id and result.task_type == context_type:
                        matching_results.append({
                            "content": result.content,
                            "memory_type": result.memory_type.value,
                            "task_id": result.task_id,
                            "task_type": result.task_type,
                        })

                # 如果短期内存中没有，从向量存储中搜索
                if not matching_results:
                    try:
                        search_results = await self.vector_store.search(
                            query=context_type,  # 使用任务类型作为查询
                            top_k=3,
                        )
                        matching_results = [
                            {
                                "content": r.item.content,
                                "memory_type": r.item.memory_type.value,
                                "task_id": r.item.task_id,
                                "task_type": r.item.metadata.get("task_type", ""),  # 从 metadata 获取
                                "score": r.score,
                            }
                            for r in search_results
                            if r.item.metadata.get("task_type") == context_type and r.item.task_id != task_id
                        ]
                    except Exception as e:
                        logger.warning(f"搜索 {context_type} 上下文失败: {e}")

                # 添加到相关记忆中
                if matching_results:
                    context.relevant_memories.extend(matching_results)
                    logger.debug(f"✅ 找到 {len(matching_results)} 个 {context_type} 上下文")
                else:
                    logger.warning(f"⚠️ 未找到 {context_type} 上下文")

            # 去重（按 task_id）
            seen_ids = set()
            unique_memories = []
            for memory in context.relevant_memories:
                memory_id = memory.get("task_id") or memory.get("content", "")[:100]
                if memory_id not in seen_ids:
                    seen_ids.add(memory_id)
                    unique_memories.append(memory)

            context.relevant_memories = unique_memories[:top_k * 2]  # 限制数量
        else:
            # 🔥 原逻辑：如果没有特定映射，使用语义搜索
            search_query = query or task_type
            relevant_results = await self.vector_store.search(
                query=search_query,
                top_k=top_k,
                chapter_index=chapter_index if include_chapter_context else None,
            )
            context.relevant_memories = [
                {
                    "content": r.item.content,
                    "memory_type": r.item.memory_type.value,
                    "score": r.score,
                    "task_id": r.item.task_id,
                    "task_type": r.item.metadata.get("task_type", ""),  # 🔥 从 metadata 获取
                }
                for r in relevant_results
                if r.item.task_id != task_id
            ]

        # 3. Chapter-specific context
        if include_chapter_context and chapter_index is not None:
            chapter_results = await self.vector_store.search(
                query=task_type,
                top_k=3,
                chapter_index=chapter_index,
            )
            context.chapter_context = [
                {
                    "content": r.item.content,
                    "memory_type": r.item.memory_type.value,
                    "score": r.score,
                }
                for r in chapter_results
            ]

        # 4. Task-specific memories (if this is a retry)
        if task_id in self._task_results:
            context.task_memories = [self._task_results[task_id].to_dict()]

        logger.info(
            f"📊 上下文检索完成 for {task_type}: "
            f"{len(context.recent_results)} recent, "
            f"{len(context.relevant_memories)} relevant"
        )

        return context

    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Get a stored task result

        Args:
            task_id: The task ID

        Returns:
            TaskResult if found, None otherwise
        """
        return self._task_results.get(task_id)

    async def get_recent_results(
        self,
        limit: Optional[int] = None,
    ) -> List[TaskResult]:
        """
        Get recent task results

        Args:
            limit: Maximum number to return (all if None)

        Returns:
            List of recent results
        """
        results = list(reversed(self._short_term))
        if limit:
            return results[:limit]
        return results

    async def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        chapter_index: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Search vector memory

        Args:
            query: Search query
            top_k: Number of results
            memory_type: Filter by memory type
            chapter_index: Filter by chapter

        Returns:
            List of search results
        """
        return await self.vector_store.search(
            query=query,
            top_k=top_k,
            memory_type=memory_type,
            chapter_index=chapter_index,
        )

    async def get_by_memory_type(
        self,
        memory_type: MemoryType,
        limit: int = 20,
    ) -> List[VectorMemoryItem]:
        """
        Get all memories of a specific type

        Args:
            memory_type: The memory type
            limit: Maximum number to return

        Returns:
            List of memory items
        """
        results = await self.vector_store.search(
            query="",  # Empty query to get all
            top_k=limit,
            memory_type=memory_type,
        )
        return [r.item for r in results]

    async def get_chapter_memories(
        self,
        chapter_index: int,
        memory_type: Optional[MemoryType] = None,
    ) -> List[VectorMemoryItem]:
        """
        Get all memories for a specific chapter

        Args:
            chapter_index: The chapter index
            memory_type: Optional filter by memory type

        Returns:
            List of memory items
        """
        results = await self.vector_store.search(
            query="",
            top_k=100,
            chapter_index=chapter_index,
            memory_type=memory_type,
        )
        return [r.item for r in results]

    async def update_task_result(
        self,
        task_id: str,
        content: Optional[str] = None,
        evaluation: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing task result

        Args:
            task_id: The task ID
            content: New content (optional)
            evaluation: New evaluation (optional)

        Returns:
            True if successful
        """
        if task_id not in self._task_results:
            return False

        result = self._task_results[task_id]

        if content:
            result.content = content

        if evaluation:
            result.evaluation = evaluation

        # Update in vector store
        await self.vector_store.update(
            item_id=task_id,
            content=content,
            metadata={"evaluation": evaluation} if evaluation else None,
        )

        return True

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete all memories associated with a task

        Args:
            task_id: The task ID

        Returns:
            True if successful
        """
        # Remove from short-term memory
        self._short_term = deque(
            [r for r in self._short_term if r.task_id != task_id],
            maxlen=self.short_term_size,
        )

        # Remove from cache
        self._task_results.pop(task_id, None)

        # Remove from vector store
        count = await self.vector_store.delete_by_task(task_id)

        logger.info(f"Deleted task {task_id} and {count} associated memories")
        return True

    async def clear_short_term(self) -> None:
        """Clear short-term memory"""
        self._short_term.clear()
        logger.info("Cleared short-term memory")

    async def clear_all(self) -> bool:
        """
        Clear all memory (both short-term and long-term)

        Returns:
            True if successful
        """
        self._short_term.clear()
        self._task_results.clear()
        return await self.vector_store.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "short_term_size": len(self._short_term),
            "short_term_max": self.short_term_size,
            "cached_results": len(self._task_results),
            "vector_store_count": self.vector_store.count(),
            "current_chapter": self._current_chapter,
        }

    def set_current_chapter(self, chapter_index: int) -> None:
        """Set the current chapter index"""
        self._current_chapter = chapter_index
        logger.debug(f"Set current chapter to {chapter_index}")

    def get_current_chapter(self) -> Optional[int]:
        """Get the current chapter index"""
        return self._current_chapter

    async def get_character_memories(self) -> List[VectorMemoryItem]:
        """Get all character-related memories"""
        return await self.get_by_memory_type(MemoryType.CHARACTER)

    async def get_plot_memories(self) -> List[VectorMemoryItem]:
        """Get all plot-related memories"""
        return await self.get_by_memory_type(MemoryType.PLOT)

    async def get_worldview_memories(self) -> List[VectorMemoryItem]:
        """Get all worldview-related memories"""
        return await self.get_by_memory_type(MemoryType.WORLDVIEW)

    async def get_foreshadow_memories(self) -> List[VectorMemoryItem]:
        """Get all foreshadow-related memories"""
        return await self.get_by_memory_type(MemoryType.FORESHADOW)

    async def export_memories(
        self,
        chapter_index: Optional[int] = None,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Export memories in a structured format

        Args:
            chapter_index: Filter by chapter (None for all)
            memory_types: Filter by memory types (None for all)

        Returns:
            List of exported memory dictionaries
        """
        exports = []

        # Get all recent results
        for result in self._task_results.values():
            if chapter_index is not None and result.chapter_index != chapter_index:
                continue
            if memory_types and result.memory_type not in memory_types:
                continue

            exports.append(result.to_dict())

        return exports
