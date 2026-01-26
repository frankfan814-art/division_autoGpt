"""
Example Storage - Manages writing examples extraction and storage

Stores high-quality content excerpts for future reference and learning.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float, Index, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from creative_autogpt.storage.session import Base_Model


class ExampleType(str, Enum):
    """Types of writing examples"""

    WRITING = "writing"  # 文笔精华 - 好的描写段落
    PLOT = "plot"  # 情节设计 - 有趣的情节结构
    CHARACTER = "character"  # 人物塑造 - 人物刻画方法
    WORLDVIEW = "worldview"  # 世界观设定 - 有创意的设定
    FORESHADOW = "foreshadow"  # 伏笔技巧 - 伏笔埋设/回收方法


class WritingExampleModel(Base_Model):
    """SQLAlchemy model for writing examples"""

    __tablename__ = "writing_examples"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)  # 来源小说ID
    chapter_index = Column(Integer, nullable=True)  # 来源章节

    # 内容分类
    content_type = Column(String, nullable=False, index=True)  # ExampleType
    content = Column(Text, nullable=False)  # 内容

    # 风格标签
    style = Column(String, nullable=True, index=True)  # 风格：科幻/玄幻/都市...
    author_style = Column(String, nullable=True)  # 作者风格：liucixin/jiangnan...

    # 质量评估
    quality_score = Column(Float, default=0.0)  # 质量评分 0-1
    evaluation = Column(JSON, nullable=True)  # 完整评估结果

    # 标签和元数据
    tags = Column(JSON, nullable=True)  # 标签数组：战斗/情感/转折...
    meta_data = Column(JSON, nullable=True)  # 其他元数据

    # 使用统计
    usage_count = Column(Integer, default=0)  # 被使用次数
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 复合索引，方便查询
    __table_args__ = (
        Index('idx_style_type_quality', 'style', 'content_type', 'quality_score'),
        Index('idx_author_type', 'author_style', 'content_type'),
    )


class ExampleStorage:
    """Storage manager for writing examples"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_example(
        self,
        session_id: str,
        content_type: str,
        content: str,
        quality_score: float = 0.0,
        style: Optional[str] = None,
        author_style: Optional[str] = None,
        chapter_index: Optional[int] = None,
        tags: Optional[List[str]] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        evaluation: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Save a writing example

        Args:
            session_id: Source session ID
            content_type: Type of example (writing/plot/character/etc)
            content: The content excerpt
            quality_score: Quality score 0-1
            style: Style tag (scifi/fantasy/urban/etc)
            author_style: Author style (liucixin/jiangnan/etc)
            chapter_index: Source chapter index
            tags: Tags for categorization
            metadata: Additional metadata
            evaluation: Full evaluation result

        Returns:
            Example ID if saved, None if quality too low
        """
        # 质量阈值：低于0.9不存（严格要求）
        if quality_score < 0.9:
            logger.debug(f"Example quality too low ({quality_score}), skipping save")
            return None

        try:
            example = WritingExampleModel(
                session_id=session_id,
                chapter_index=chapter_index,
                content_type=content_type,
                content=content,
                style=style,
                author_style=author_style,
                quality_score=quality_score,
                tags=tags or [],
                meta_data=meta_data or {},
                evaluation=evaluation,
            )

            self.session.add(example)
            await self.session.flush()

            logger.info(f"Saved example: {content_type} from session {session_id}, score: {quality_score}")
            return example.id

        except Exception as e:
            logger.error(f"Failed to save example: {e}")
            await self.session.rollback()
            return None

    async def get_examples(
        self,
        content_type: Optional[str] = None,
        style: Optional[str] = None,
        author_style: Optional[str] = None,
        min_quality: float = 0.9,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve examples by criteria

        Args:
            content_type: Filter by content type
            style: Filter by style
            author_style: Filter by author style
            min_quality: Minimum quality score
            limit: Max number of examples

        Returns:
            List of examples
        """
        try:
            query = select(WritingExampleModel).where(
                WritingExampleModel.quality_score >= min_quality
            )

            if content_type:
                query = query.where(WritingExampleModel.content_type == content_type)

            if style:
                query = query.where(WritingExampleModel.style == style)

            if author_style:
                query = query.where(WritingExampleModel.author_style == author_style)

            # 按质量和使用次数排序
            query = query.order_by(
                WritingExampleModel.quality_score.desc(),
                WritingExampleModel.usage_count.desc()
            ).limit(limit)

            result = await self.session.execute(query)
            examples = result.scalars().all()

            return [
                {
                    "id": ex.id,
                    "content_type": ex.content_type,
                    "content": ex.content,
                    "style": ex.style,
                    "author_style": ex.author_style,
                    "quality_score": ex.quality_score,
                    "tags": ex.tags,
                    "chapter_index": ex.chapter_index,
                }
                for ex in examples
            ]

        except Exception as e:
            logger.error(f"Failed to get examples: {e}")
            return []

    async def record_usage(self, example_id: str) -> None:
        """
        Record that an example was used

        Args:
            example_id: Example ID
        """
        try:
            query = select(WritingExampleModel).where(
                WritingExampleModel.id == example_id
            )
            result = await self.session.execute(query)
            example = result.scalar_one_or_none()

            if example:
                example.usage_count += 1
                example.last_used_at = datetime.utcnow()
                await self.session.flush()

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")

    async def cleanup_unused(self, days: int = 30, min_usage: int = 0) -> int:
        """
        Clean up unused examples

        Args:
            days: Delete examples older than this many days
            min_usage: Delete examples with usage count <= this

        Returns:
            Number of examples deleted
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # 这里先不实际删除，只返回数量
            # 真实删除可以用 execute(delete()...)
            query = select(WritingExampleModel).where(
                WritingExampleModel.created_at < cutoff_date,
                WritingExampleModel.usage_count <= min_usage
            )

            result = await self.session.execute(query)
            count = len(result.all())

            logger.info(f"Found {count} unused examples to clean up")
            return count

        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")
            return 0
