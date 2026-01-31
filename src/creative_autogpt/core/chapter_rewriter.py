"""
Chapter Rewriter - Single chapter rewrite service

负责单章重写的完整流程：
1. 加载章节上下文（前面章节、人物、世界观、伏笔）
2. 重新生成章节内容
3. 质量评估
4. 保存新版本到版本历史
"""
from loguru import logger
from typing import Dict, Any, Optional

from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.core.vector_memory import VectorMemoryManager, MemoryContext
from creative_autogpt.core.evaluator import EvaluationEngine


class ChapterRewriter:
    """
    单章重写服务

    功能：
    1. 加载章节上下文（前面章节、人物、世界观、伏笔）
    2. 重新生成章节内容
    3. 质量评估
    4. 保存新版本到版本历史
    """

    def __init__(
        self,
        session_id: str,
        storage: SessionStorage,
        llm_client: MultiLLMClient,
        memory: VectorMemoryManager,
        evaluator: EvaluationEngine,
    ):
        """
        初始化章节重写器

        Args:
            session_id: 会话ID
            storage: 会话存储
            llm_client: 多LLM客户端
            memory: 向量记忆管理器
            evaluator: 质量评估器
        """
        self.session_id = session_id
        self.storage = storage
        self.llm_client = llm_client
        self.memory = memory
        self.evaluator = evaluator

    async def rewrite_chapter(
        self,
        chapter_index: int,
        reason: Optional[str] = None,
        feedback: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        重写指定章节

        Args:
            chapter_index: 章节索引
            reason: 重写原因
            feedback: 用户反馈
            max_retries: 最大重试次数（质量不通过时自动重写）

        Returns:
            Dict with:
                - version_number: 新版本号
                - version_id: 版本ID
                - score: 质量分数
                - passed: 是否通过评估
                - content: 章节内容
                - evaluation: 完整评估结果
                - retry_count: 重试次数
        """
        logger.info(f"🔄 开始重写第 {chapter_index} 章")

        # 1. 获取章节任务
        tasks = await self.storage.get_task_results(
            self.session_id,
            chapter_index=chapter_index,
        )

        if not tasks:
            raise ValueError(f"Chapter {chapter_index} not found in session {self.session_id}")

        task = tasks[0]
        task_id = task["task_id"]

        # 2. 获取会话信息
        session = await self.storage.get_session(self.session_id)
        if not session:
            raise ValueError(f"Session {self.session_id} not found")

        goal = session.get("goal", {})

        # 3. 获取现有版本数
        versions = await self.storage.get_chapter_versions(self.session_id, chapter_index)
        next_version = len(versions) + 1

        # 4. 获取上下文
        context = await self.memory.get_context(
            task_id=task_id,
            task_type="章节内容",
            chapter_index=chapter_index,
            recent_count=10,  # 获取前10章
        )

        # 5. 重写循环（最多 max_retries 次重试）
        best_content = None
        best_evaluation = None
        best_score = 0.0
        passed = False
        retry_count = 0

        for attempt in range(max_retries):
            retry_count = attempt

            # 构建重写提示词
            prompt = await self._build_rewrite_prompt(
                chapter_index=chapter_index,
                context=context,
                old_content=task["result"],
                reason=reason,
                feedback=feedback,
                attempt=attempt,
                previous_evaluation=best_evaluation,
            )

            # 调用 LLM 生成新内容
            response = await self.llm_client.generate(
                task_type="章节内容",
                prompt=prompt,
            )

            # 评估新内容
            evaluation = await self.evaluator.evaluate(
                content=response.content,
                task_type="章节内容",
                context=context,
                goal=goal,
            )

            # 记录分数
            score = evaluation.score
            logger.info(f"📊 第 {chapter_index} 章重写 (尝试 {attempt + 1}/{max_retries}) 得分: {score:.2f}")

            # 保存这个版本
            token_stats = {
                "total_tokens": response.usage.get("total_tokens", 0) if response.usage else 0,
                "prompt_tokens": response.usage.get("prompt_tokens", 0) if response.usage else 0,
                "completion_tokens": response.usage.get("completion_tokens", 0) if response.usage else 0,
                "cost": response.usage.get("cost_usd", 0.0) if response.usage else 0.0,
            }

            version_id = await self.storage.create_chapter_version(
                session_id=self.session_id,
                task_id=task_id,
                chapter_index=chapter_index,
                content=response.content,
                version_number=next_version + attempt,
                is_current=evaluation.passed,  # 如果通过则设为当前版本
                evaluation=evaluation.to_dict(),
                created_by="manual" if attempt == 0 else "rewrite",
                rewrite_reason=reason or feedback or "用户手动重写",
                token_stats=token_stats,
            )

            # 更新最佳版本
            if score > best_score:
                best_content = response.content
                best_evaluation = evaluation
                best_score = score

                # 如果这是更好的版本，标记为当前
                await self.storage.restore_chapter_version(
                    session_id=self.session_id,
                    task_id=task_id,
                    version_id=version_id,
                )

            # 如果通过评估，结束重写
            if evaluation.passed:
                passed = True
                logger.info(f"✅ 第 {chapter_index} 章重写通过评估 (分数: {score:.2f})")
                break

            logger.warning(f"⚠️ 第 {chapter_index} 章重写未通过评估 (分数: {score:.2f})")

        # 如果都不通过，保留最后一次
        if not passed:
            logger.warning(f"❌ 第 {chapter_index} 章经过 {max_retries} 次重写仍未通过评估")

        # 更新版本计数
        await self.storage.update_task_version_count(
            task_id=task_id,
            version_count=next_version + retry_count,
        )

        return {
            "version_number": next_version + retry_count,
            "version_id": version_id,
            "score": best_score,
            "passed": passed,
            "content": best_content,
            "evaluation": best_evaluation.to_dict() if best_evaluation else None,
            "retry_count": retry_count,
        }

    async def _build_rewrite_prompt(
        self,
        chapter_index: int,
        context: MemoryContext,
        old_content: str,
        reason: Optional[str],
        feedback: Optional[str],
        attempt: int = 0,
        previous_evaluation: Optional[Any] = None,
    ) -> str:
        """
        构建重写提示词

        Args:
            chapter_index: 章节索引
            context: 记忆上下文
            old_content: 原有内容
            reason: 重写原因
            feedback: 用户反馈
            attempt: 当前尝试次数
            previous_evaluation: 之前的评估结果

        Returns:
            完整的重写提示词
        """
        # 获取 session goal
        session = await self.storage.get_session(self.session_id)
        goal = session.get("goal", {})

        prompt_parts = [
            f"# 任务：重写第 {chapter_index} 章\n",
        ]

        # 添加创作目标
        if goal:
            prompt_parts.append("## 创作目标\n")
            if goal.get("genre"):
                prompt_parts.append(f"- 类型：{goal['genre']}")
            if goal.get("theme"):
                prompt_parts.append(f"- 主题：{goal['theme']}")
            if goal.get("style"):
                prompt_parts.append(f"- 风格：{goal['style']}")
            prompt_parts.append("")

        # 添加原有内容
        prompt_parts.extend([
            "## 原有内容\n",
            old_content[:2000] + "..." if len(old_content) > 2000 else old_content,
            "\n",
        ])

        # 添加重写原因
        if reason:
            prompt_parts.extend([
                "## 重写原因\n",
                reason,
                "\n",
            ])

        # 添加用户反馈
        if feedback:
            prompt_parts.extend([
                "## 用户反馈\n",
                feedback,
                "\n",
            ])

        # 添加之前的评估问题
        if previous_evaluation and attempt > 0:
            prompt_parts.extend([
                "## 上次评估问题\n",
                f"得分：{previous_evaluation.score:.2f}\n",
            ])
            if previous_evaluation.issues:
                prompt_parts.append("问题：\n")
                for issue in previous_evaluation.issues:
                    prompt_parts.append(f"- {issue}\n")
            prompt_parts.append("\n")

        # 添加上下文信息
        prompt_parts.extend([
            "## 上下文信息\n",
            "请根据以下上下文信息重写章节：\n",
        ])

        # 添加前置任务结果
        if context.predecessor_results:
            prompt_parts.append("\n### 前置任务结果\n")
            for task_type, result in list(context.predecessor_results.items())[:5]:
                prompt_parts.append(f"**{task_type}**:\n")
                content = result.get("content", "")[:500]
                prompt_parts.append(content + "...\n" if len(result.get("content", "")) > 500 else content + "\n")

        # 添加相关记忆
        if context.related_memories:
            prompt_parts.append("\n### 相关记忆\n")
            for memory in context.related_memories[:5]:
                prompt_parts.append(f"- {memory.item.content[:200]}...\n")

        prompt_parts.extend([
            "\n## 要求\n",
            "1. 保持与原有内容的基本情节一致\n",
            "2. 根据重写原因和用户反馈进行改进\n",
            "3. 确保与前置章节的内容衔接自然\n",
            "4. 保持人物性格和世界观规则的一致性\n",
            "5. 提升文笔和描写质量\n",
            "\n请重写第 {} 章：\n".format(chapter_index)
        ])

        return "\n".join(prompt_parts)
