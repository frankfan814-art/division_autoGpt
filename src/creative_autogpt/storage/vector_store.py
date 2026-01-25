"""
Vector store for semantic memory and context retrieval

Uses ChromaDB for vector storage and retrieval with configurable embeddings.
Supports Aliyun embeddings as the primary provider.
"""

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from loguru import logger

from creative_autogpt.utils.config import get_settings


class MemoryType(str, Enum):
    """Types of memory entries"""

    CHARACTER = "character"
    PLOT = "plot"
    SETTING = "setting"
    DIALOGUE = "dialogue"
    WORLDVIEW = "worldview"
    FORESHADOW = "foreshadow"
    SCENE = "scene"
    CHAPTER = "chapter"
    OUTLINE = "outline"
    GENERAL = "general"


@dataclass
class VectorMemoryItem:
    """An item stored in vector memory"""

    id: str
    content: str
    memory_type: MemoryType
    metadata: Dict[str, Any] = field(default_factory=dict)
    task_id: Optional[str] = None
    chapter_index: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "metadata": self.metadata,
            "task_id": self.task_id,
            "chapter_index": self.chapter_index,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SearchResult:
    """A search result from vector memory"""

    item: VectorMemoryItem
    score: float
    distance: Optional[float] = None


class VectorStore:
    """
    Vector store for semantic memory using ChromaDB

    Provides:
    - Storage of text with vector embeddings
    - Semantic search/retrieval
    - Context-aware memory management
    - Chapter-scoped memory isolation
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "creative_autogpt",
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize vector store

        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the ChromaDB collection
            embedding_model: Name/path of embedding model
        """
        settings = get_settings()

        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model or settings.embedding_model

        # Ensure persist directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Initialize embedding function
        self.embedding_function = self._create_embedding_function()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Creative AutoGPT memory collection"},
        )

        logger.info(
            f"VectorStore initialized with {self.collection.count()} existing items"
        )

    def _create_embedding_function(self):
        """Create embedding function based on configuration"""
        settings = get_settings()

        # Try to use Aliyun embeddings if API key is available
        if settings.aliyun_api_key and settings.aliyun_embedding_base_url:
            try:
                # Create a custom embedding function for Aliyun
                import dashscope

                class AliyunEmbeddingFunction(embedding_functions.EmbeddingFunction):
                    def __init__(self, api_key: str, model: str = "text-embedding-v3"):
                        self.api_key = api_key
                        self.model = model
                        dashscope.api_key = api_key

                    def __call__(self, texts: List[str]) -> List[List[float]]:
                        """Generate embeddings for texts"""
                        import numpy as np

                        embeddings = []
                        for text in texts:
                            try:
                                response = dashscope.TextEmbedding.call(
                                    model=self.model,
                                    input=text,
                                    text_type="document",
                                )
                                if response.status_code == 200:
                                    emb = response.output["embeddings"][0]["embedding"]
                                    embeddings.append(emb)
                                else:
                                    logger.warning(
                                        f"Aliyun embedding failed: {response.message}"
                                    )
                                    # Fallback to zeros
                                    embeddings.append([0.0] * 1024)
                            except Exception as e:
                                logger.error(f"Aliyun embedding error: {e}")
                                embeddings.append([0.0] * 1024)

                        return embeddings

                return AliyunEmbeddingFunction(
                    api_key=settings.aliyun_api_key,
                    model=settings.aliyun_embedding_model,
                )

            except ImportError:
                logger.warning("DashScope not available, falling back to sentence-transformers")
            except Exception as e:
                logger.warning(f"Aliyun embedding setup failed: {e}, falling back")

        # Default to sentence-transformers
        try:
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model,
                device="cpu",
            )
        except Exception as e:
            logger.error(f"Failed to initialize embedding function: {e}")
            # Fallback to a simple function
            class DummyEmbeddingFunction(embedding_functions.EmbeddingFunction):
                def __call__(self, texts: List[str]) -> List[List[float]]:
                    # Return zero vectors as fallback
                    return [[0.0] * 384 for _ in texts]

            return DummyEmbeddingFunction()

    async def add(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        chapter_index: Optional[int] = None,
        item_id: Optional[str] = None,
    ) -> str:
        """
        Add an item to vector memory

        Args:
            content: The text content to store
            memory_type: Type of memory
            metadata: Additional metadata
            task_id: Associated task ID
            chapter_index: Associated chapter index
            item_id: Custom ID (auto-generated if None)

        Returns:
            The ID of the added item
        """
        item_id = item_id or str(uuid.uuid4())

        # Prepare metadata
        item_metadata = {
            "memory_type": memory_type.value,
            "created_at": datetime.utcnow().isoformat(),
        }

        if metadata:
            # Filter out None values and complex types (dict, list) as Chroma only accepts str, int, float, bool
            for k, v in metadata.items():
                if v is None:
                    continue
                # Chroma 只支持 str, int, float, bool 类型
                if isinstance(v, (str, int, float, bool)):
                    item_metadata[k] = v
                elif isinstance(v, (dict, list)):
                    # 复杂类型转为 JSON 字符串存储
                    import json
                    try:
                        item_metadata[k] = json.dumps(v, ensure_ascii=False)
                    except:
                        logger.warning(f"Could not serialize metadata key '{k}', skipping")
                else:
                    # 其他类型尝试转为字符串
                    try:
                        item_metadata[k] = str(v)
                    except:
                        logger.warning(f"Could not convert metadata key '{k}' to string, skipping")

        if task_id:
            item_metadata["task_id"] = task_id

        if chapter_index is not None:
            item_metadata["chapter_index"] = chapter_index

        # Add to collection
        try:
            self.collection.add(
                ids=[item_id],
                documents=[content],
                metadatas=[item_metadata],
            )

            logger.debug(
                f"Added item {item_id} to vector store (type: {memory_type.value})"
            )
            return item_id

        except Exception as e:
            logger.error(f"Failed to add item to vector store: {e}")
            raise

    async def add_batch(
        self,
        items: List[Tuple[str, MemoryType, Dict[str, Any]]],
    ) -> List[str]:
        """
        Add multiple items to vector memory

        Args:
            items: List of (content, memory_type, metadata) tuples

        Returns:
            List of item IDs
        """
        ids = []
        documents = []
        metadatas = []

        for content, memory_type, metadata in items:
            item_id = str(uuid.uuid4())
            ids.append(item_id)
            documents.append(content)

            item_metadata = {
                "memory_type": memory_type.value,
                "created_at": datetime.utcnow().isoformat(),
            }
            # Filter out None values as Chroma doesn't accept them
            item_metadata.update({k: v for k, v in metadata.items() if v is not None})
            metadatas.append(item_metadata)

        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(f"Added {len(ids)} items to vector store")
            return ids

        except Exception as e:
            logger.error(f"Failed to add batch to vector store: {e}")
            raise

    async def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[MemoryType] = None,
        chapter_index: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search vector memory for similar items

        Args:
            query: Search query text
            top_k: Number of results to return
            memory_type: Filter by memory type
            chapter_index: Filter by chapter index
            where: Additional metadata filters
            min_score: Minimum similarity score (0-1)

        Returns:
            List of search results with scores
        """
        start_time = time.time()

        # Build where clause
        where_clause = {}
        if memory_type:
            where_clause["memory_type"] = memory_type.value
        if chapter_index is not None:
            where_clause["chapter_index"] = chapter_index
        if where:
            where_clause.update(where)

        # Query collection
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause if where_clause else None,
            )

            # Convert to SearchResult objects
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, item_id in enumerate(results["ids"][0]):
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    distance = results["distances"][0][i] if results["distances"] else None
                    score = 1.0 / (1.0 + distance) if distance is not None else 0.0

                    # Filter by minimum score
                    if score < min_score:
                        continue

                    item = VectorMemoryItem(
                        id=item_id,
                        content=results["documents"][0][i],
                        memory_type=MemoryType(
                            results["metadatas"][0][i].get("memory_type", "general")
                        ),
                        metadata=results["metadatas"][0][i],
                        task_id=results["metadatas"][0][i].get("task_id"),
                        chapter_index=results["metadatas"][0][i].get("chapter_index"),
                    )

                    search_results.append(
                        SearchResult(item=item, score=score, distance=distance)
                    )

            elapsed = time.time() - start_time
            logger.debug(
                f"Vector search returned {len(search_results)} results in {elapsed:.3f}s"
            )

            return search_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def get_by_id(self, item_id: str) -> Optional[VectorMemoryItem]:
        """
        Get an item by its ID

        Args:
            item_id: The item ID

        Returns:
            The item if found, None otherwise
        """
        try:
            results = self.collection.get(ids=[item_id])

            if results["ids"] and results["ids"][0]:
                return VectorMemoryItem(
                    id=results["ids"][0],
                    content=results["documents"][0],
                    memory_type=MemoryType(
                        results["metadatas"][0].get("memory_type", "general")
                    ),
                    metadata=results["metadatas"][0],
                    task_id=results["metadatas"][0].get("task_id"),
                    chapter_index=results["metadatas"][0].get("chapter_index"),
                )

            return None

        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {e}")
            return None

    async def get_by_task(self, task_id: str) -> List[VectorMemoryItem]:
        """
        Get all items associated with a task

        Args:
            task_id: The task ID

        Returns:
            List of items
        """
        try:
            results = self.collection.get(
                where={"task_id": task_id},
            )

            items = []
            if results["ids"]:
                for i, item_id in enumerate(results["ids"]):
                    items.append(
                        VectorMemoryItem(
                            id=item_id,
                            content=results["documents"][i],
                            memory_type=MemoryType(
                                results["metadatas"][i].get("memory_type", "general")
                            ),
                            metadata=results["metadatas"][i],
                            task_id=results["metadatas"][i].get("task_id"),
                            chapter_index=results["metadatas"][i].get("chapter_index"),
                        )
                    )

            return items

        except Exception as e:
            logger.error(f"Failed to get items for task {task_id}: {e}")
            return []

    async def update(
        self,
        item_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing item

        Args:
            item_id: The item ID
            content: New content (if updating)
            metadata: New metadata (will be merged with existing)

        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {"ids": [item_id]}

            if content:
                update_data["documents"] = [content]

            if metadata:
                # Get existing metadata first
                existing = self.collection.get(ids=[item_id])
                if existing["metadatas"]:
                    merged_metadata = existing["metadatas"][0].copy()
                    merged_metadata.update(metadata)
                    update_data["metadatas"] = [merged_metadata]
                else:
                    update_data["metadatas"] = [metadata]

            self.collection.update(**update_data)

            logger.debug(f"Updated item {item_id} in vector store")
            return True

        except Exception as e:
            logger.error(f"Failed to update item {item_id}: {e}")
            return False

    async def delete(self, item_id: str) -> bool:
        """
        Delete an item from vector memory

        Args:
            item_id: The item ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[item_id])
            logger.debug(f"Deleted item {item_id} from vector store")
            return True

        except Exception as e:
            logger.error(f"Failed to delete item {item_id}: {e}")
            return False

    async def delete_by_task(self, task_id: str) -> int:
        """
        Delete all items associated with a task

        Args:
            task_id: The task ID

        Returns:
            Number of items deleted
        """
        try:
            # Get items first to count them
            items = await self.get_by_task(task_id)
            item_ids = [item.id for item in items]

            if item_ids:
                self.collection.delete(ids=item_ids)
                logger.info(f"Deleted {len(item_ids)} items for task {task_id}")

            return len(item_ids)

        except Exception as e:
            logger.error(f"Failed to delete items for task {task_id}: {e}")
            return 0

    async def get_recent(
        self,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
    ) -> List[VectorMemoryItem]:
        """
        Get recent items from memory

        Args:
            limit: Maximum number of items to return
            memory_type: Filter by memory type

        Returns:
            List of recent items
        """
        try:
            where_clause = {"memory_type": memory_type.value} if memory_type else None

            results = self.collection.get(
                where=where_clause,
                limit=limit,
            )

            items = []
            if results["ids"]:
                for i, item_id in enumerate(results["ids"]):
                    items.append(
                        VectorMemoryItem(
                            id=item_id,
                            content=results["documents"][i],
                            memory_type=MemoryType(
                                results["metadatas"][i].get("memory_type", "general")
                            ),
                            metadata=results["metadatas"][i],
                            task_id=results["metadatas"][i].get("task_id"),
                            chapter_index=results["metadatas"][i].get("chapter_index"),
                        )
                    )

            # Sort by created_at descending
            items.sort(key=lambda x: x.created_at, reverse=True)

            return items[:limit]

        except Exception as e:
            logger.error(f"Failed to get recent items: {e}")
            return []

    def count(self) -> int:
        """Get total number of items in the store"""
        return self.collection.count()

    async def clear(self) -> bool:
        """
        Clear all items from the store

        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
            )
            logger.info(f"Cleared vector store '{self.collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store

        Returns:
            Dictionary with stats
        """
        try:
            # Count by memory type
            all_items = self.collection.get()
            type_counts = {}

            if all_items["metadatas"]:
                for metadata in all_items["metadatas"]:
                    memory_type = metadata.get("memory_type", "general")
                    type_counts[memory_type] = type_counts.get(memory_type, 0) + 1

            return {
                "total_items": self.count(),
                "type_counts": type_counts,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_items": 0,
                "type_counts": {},
                "error": str(e),
            }
