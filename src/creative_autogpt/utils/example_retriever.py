"""
Example Retriever - Retrieves relevant writing examples for reference

Queries stored examples and formats them for use in prompts.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from creative_autogpt.storage.example import ExampleStorage, ExampleType


class ExampleRetriever:
    """
    检索写作范例

    - 根据风格和类型检索范例
    - 格式化为提示词可用格式
    - 记录使用情况
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = ExampleStorage(session)

    async def get_examples_for_prompt(
        self,
        style: str,
        author_style: Optional[str] = None,
        max_examples: int = 3,
    ) -> str:
        """
        获取范例并格式化为提示词

        Args:
            style: 风格（科幻/玄幻/都市...）
            author_style: 作者风格（可选）
            max_examples: 最多几个范例

        Returns:
            格式化的范例文本
        """
        examples = await self.storage.get_examples(
            style=style,
            author_style=author_style,
            min_quality=0.75,
            limit=max_examples,
        )

        if not examples:
            return ""

        # 按类型分组
        by_type: Dict[str, List[Dict]] = {}
        for ex in examples:
            ex_type = ex.get("content_type", "writing")
            if ex_type not in by_type:
                by_type[ex_type] = []
            by_type[ex_type].append(ex)

        # 格式化输出
        result = "### 📚 参考范例（来自系统生成的高质量内容）\n\n"

        # 文笔范例
        if "writing" in by_type:
            result += "#### ✍️ 文笔范例\n\n"
            for ex in by_type["writing"][:2]:
                result += f"```\n{ex['content'][:200]}\n```\n\n"
                # 记录使用
                await self.storage.record_usage(ex["id"])

        # 情节范例
        if "plot" in by_type:
            result += "#### 📖 情节范例\n\n"
            for ex in by_type["plot"][:1]:
                result += f"```\n{ex['content'][:200]}\n```\n\n"
                await self.storage.record_usage(ex["id"])

        # 人物范例
        if "character" in by_type:
            result += "#### 👤 人物刻画范例\n\n"
            for ex in by_type["character"][:1]:
                result += f"```\n{ex['content'][:200]}\n```\n\n"
                await self.storage.record_usage(ex["id"])

        result += "---\n\n"
        result += "**提示**：请参考这些范例的风格和写法，但内容要原创，不要照搬。\n\n"

        return result

    async def get_examples_by_type(
        self,
        content_type: str,
        style: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        按类型获取范例

        Args:
            content_type: 范例类型 (writing/plot/character/etc)
            style: 风格过滤
            limit: 数量限制

        Returns:
            范例列表
        """
        return await self.storage.get_examples(
            content_type=content_type,
            style=style,
            min_quality=0.7,
            limit=limit,
        )

    async def record_usage(self, example_id: str) -> None:
        """记录范例使用"""
        await self.storage.record_usage(example_id)


async def get_retriever() -> Optional[ExampleRetriever]:
    """
    获取范例检索器实例

    Returns:
        ExampleRetriever instance or None
    """
    try:
        from creative_autogpt.storage.session import get_session

        session = await get_session().__aenter__()
        return ExampleRetriever(session)

    except Exception as e:
        logger.error(f"Failed to create retriever: {e}")
        return None
