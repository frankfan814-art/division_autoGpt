"""
Example Extractor Plugin - Extracts and stores high-quality writing examples

Automatically analyzes completed novels and extracts worth-saving content.
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from creative_autogpt.plugins.base import (
    NovelElementPlugin,
    WritingContext,
    PluginConfig,
    ValidationResult,
)
from creative_autogpt.storage.example import ExampleStorage, ExampleType
from creative_autogpt.utils.llm_client import MultiLLMClient


class ExampleExtractorPlugin(NovelElementPlugin):
    """
    Extracts high-quality examples from completed novels

    - Analyzes chapters after completion
    - Extracts good writing, plot, characters, etc.
    - Stores in database for future reference
    - Low coupling: only runs on finalize
    """

    name = "example_extractor"
    version = "1.0.0"
    description = "自动提取和存储高质量写作范例"
    author = "System"

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self.llm_client: Optional[MultiLLMClient] = None
        self.storage: Optional[ExampleStorage] = None

    async def on_init(self, context: WritingContext) -> None:
        """Initialize plugin"""
        logger.info("ExampleExtractorPlugin initialized")

    async def on_finalize(self, context: WritingContext) -> None:
        """
        Called when novel is complete - extract examples

        这是低耦合设计：只在小说完成时运行一次
        不影响正常的创作流程
        """
        logger.info("Novel completed, starting example extraction...")

        try:
            # 获取数据库会话
            from creative_autogpt.storage.session import get_session

            async with get_session() as session:
                self.storage = ExampleStorage(session)

                # 初始化LLM客户端（如果还没有）
                if not self.llm_client:
                    from creative_autogpt.utils.llm_client import MultiLLMClient

                    self.llm_client = MultiLLMClient()

                # 提取范例
                await self._extract_examples(context)

                logger.info("Example extraction completed")

        except Exception as e:
            logger.error(f"Example extraction failed: {e}")

    async def _extract_examples(self, context: WritingContext) -> None:
        """Extract examples from completed novel"""

        session_id = context.session_id
        goal = context.goal
        results = context.results

        # 获取风格信息
        style = goal.get("genre", "")
        author_style = goal.get("author_style", "")

        # 找出所有章节内容
        chapters = []
        for task_id, result_data in results.items():
            if isinstance(result_data, dict):
                task_type = result_data.get("task_type")
                if task_type == "章节内容":
                    chapters.append(result_data)

        if not chapters:
            logger.info("No chapters found, skipping extraction")
            return

        logger.info(f"Found {len(chapters)} chapters, analyzing...")

        # 分析每个章节
        for chapter in chapters:
            await self._analyze_chapter(
                chapter, session_id, style, author_style
            )

    async def _analyze_chapter(
        self,
        chapter: Dict[str, Any],
        session_id: str,
        style: str,
        author_style: str,
    ) -> None:
        """Analyze a chapter and extract examples"""

        content = chapter.get("result", "")
        chapter_index = chapter.get("chapter_index", 0)
        evaluation = chapter.get("evaluation", {})

        if not content:
            return

        # 获取质量分数
        quality_score = 0.7  # 默认
        if evaluation:
            quality_score = evaluation.get("quality_score", 0.7)

        # 如果质量太低，跳过（严格要求：>0.9）
        if quality_score <= 0.9:
            logger.debug(f"Chapter {chapter_index} quality too low, skipping")
            return

        # 用LLM分析提取范例
        extracted = await self._llm_extract_examples(
            content, chapter_index, style, author_style
        )

        if not extracted:
            return

        # 保存提取的范例
        for ex in extracted:
            ex_type = ex.get("type")
            ex_content = ex.get("content", "")
            ex_score = ex.get("score", quality_score)
            ex_tags = ex.get("tags", [])

            if not ex_content or len(ex_content) < 50:
                continue

            await self.storage.save_example(
                session_id=session_id,
                content_type=ex_type,
                content=ex_content,
                quality_score=ex_score,
                style=style,
                author_style=author_style,
                chapter_index=chapter_index,
                tags=ex_tags,
                metadata={"source_chapter": chapter_index},
            )

    async def _llm_extract_examples(
        self,
        content: str,
        chapter_index: int,
        style: str,
        author_style: str,
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract examples from chapter"""

        prompt = f"""分析以下小说章节内容，提取值得借鉴的范例。

## 提取类型

1. **writing** (文笔精华) - 优美的描写段落（环境/心理/对话）
2. **plot** (情节设计) - 有趣的情节安排（转折/冲突/节奏）
3. **character** (人物塑造) - 很好的人物刻画（性格/成长/关系）
4. **worldview** (世界观设定) - 有创意的设定描述
5. **foreshadow** (伏笔技巧) - 巧妙的伏笔埋设/回收

## 章节（第{chapter_index}章）

```
{content[:3000]}
```

## 要求

1. 只提取真正好的内容，宁缺毋滥
2. 每段范例50-300字
3. 给每段范例打分（0-1，0.8以上才算好）
4. 标注范例类型

## 输出格式（JSON）

{{
  "examples": [
    {{
      "type": "writing",
      "content": "范例内容...",
      "score": 0.85,
      "tags": ["环境描写", "氛围"],
      "reason": "为什么这个好"
    }}
  ]
}}

如果没有好的范例，返回 {{"examples": []}}"""

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000,
            )

            # 解析JSON
            result = json.loads(response.content)

            examples = result.get("examples", [])

            if examples:
                logger.info(f"Extracted {len(examples)} examples from chapter {chapter_index}")

            return examples

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return []

    # ========== 以下为插件必须实现的方法 ==========

    def get_schema(self) -> Dict[str, Any]:
        """Get schema (not used for this plugin)"""
        return {"type": "object"}

    def get_prompts(self) -> Dict[str, str]:
        """Get prompts (not used for this plugin)"""
        return {}

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks (not used for this plugin)"""
        return []

    async def validate(
        self, data: Any, context: WritingContext
    ) -> ValidationResult:
        """Validate (not used for this plugin)"""
        return ValidationResult(valid=True)
