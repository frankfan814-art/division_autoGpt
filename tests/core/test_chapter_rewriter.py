"""
ChapterRewriter 单元测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from creative_autogpt.core.chapter_rewriter import ChapterRewriter


class TestChapterRewriter:
    """ChapterRewriter 测试"""

    @pytest.fixture
    def mock_storage(self):
        """模拟存储"""
        storage = AsyncMock()
        storage.get_session = AsyncMock(return_value={
            "id": "session_001",
            "goal": {
                "genre": "玄幻",
                "theme": "修仙",
                "style": "古典"
            }
        })
        storage.get_task_results = AsyncMock(return_value=[
            {
                "task_id": "task_001",
                "result": "原始章节内容",
                "chapter_index": 1
            }
        ])
        storage.get_chapter_versions = AsyncMock(return_value=[])
        storage.create_chapter_version = AsyncMock(return_value="version_001")
        storage.restore_chapter_version = AsyncMock(return_value=True)
        storage.update_task_version_count = AsyncMock(return_value=True)
        return storage

    @pytest.fixture
    def mock_llm_client(self):
        """模拟 LLM 客户端"""
        client = AsyncMock()
        client.generate = AsyncMock(return_value=Mock(
            content="重写后的章节内容",
            usage=Mock(
                total_tokens=2000,
                prompt_tokens=1000,
                completion_tokens=1000
            )
        ))
        return client

    @pytest.fixture
    def mock_memory(self):
        """模拟记忆管理器"""
        memory = AsyncMock()
        memory.get_context = AsyncMock(return_value=Mock(
            predecessor_results={
                "大纲": {"content": "大纲内容"},
                "人物设计": {"content": "人物信息"}
            },
            related_memories=[]
        ))
        return memory

    @pytest.fixture
    def mock_evaluator(self):
        """模拟评估器"""
        evaluator = AsyncMock()
        evaluator.evaluate = AsyncMock(return_value=Mock(
            passed=True,
            score=0.85,
            to_dict=lambda: {
                "passed": True,
                "score": 0.85,
                "quality_score": 0.85,
                "consistency_score": 0.90
            }
        ))
        return evaluator

    @pytest.fixture
    def rewriter(self, mock_storage, mock_llm_client, mock_memory, mock_evaluator):
        """创建 ChapterRewriter 实例"""
        return ChapterRewriter(
            session_id="session_001",
            storage=mock_storage,
            llm_client=mock_llm_client,
            memory=mock_memory,
            evaluator=mock_evaluator
        )

    @pytest.mark.asyncio
    async def test_rewrite_chapter_success(self, rewriter, mock_storage, mock_llm_client, mock_evaluator):
        """测试章节重写成功"""
        result = await rewriter.rewrite_chapter(
            chapter_index=1,
            reason="质量不够好",
            max_retries=1
        )

        assert result["passed"] is True
        assert result["version_number"] == 1
        assert result["score"] == 0.85
        assert "重写后的章节内容" in result["content"]

        # 验证调用
        mock_llm_client.generate.assert_called_once()
        mock_evaluator.evaluate.assert_called_once()
        mock_storage.create_chapter_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_rewrite_chapter_with_retries(self, rewriter, mock_evaluator, mock_storage):
        """测试章节重写带重试"""
        # 第一次评估不通过，第二次通过
        mock_evaluator.evaluate.side_effect = [
            Mock(passed=False, score=0.6),
            Mock(passed=True, score=0.85, to_dict=lambda: {"passed": True, "score": 0.85})
        ]

        result = await rewriter.rewrite_chapter(
            chapter_index=1,
            max_retries=2
        )

        assert result["passed"] is True
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_build_rewrite_prompt(self, rewriter, mock_storage):
        """测试构建重写提示词"""
        prompt = await rewriter._build_rewrite_prompt(
            chapter_index=1,
            context=Mock(
                predecessor_results={},
                related_memories=[]
            ),
            old_content="旧内容",
            reason="需要更生动的描写",
            feedback="人物对话不够自然",
            attempt=1,
            previous_evaluation=Mock(score=0.6)
        )

        assert "重写第 1 章" in prompt
        assert "旧内容" in prompt
        assert "需要更生动的描写" in prompt
        assert "人物对话不够自然" in prompt

    @pytest.mark.asyncio
    async def test_chapter_not_found(self, rewriter, mock_storage):
        """测试章节不存在的情况"""
        mock_storage.get_task_results.return_value = []

        with pytest.raises(ValueError, match="Chapter 1 not found"):
            await rewriter.rewrite_chapter(chapter_index=1)

    @pytest.mark.asyncio
    async def test_session_not_found(self, rewriter, mock_storage):
        """测试会话不存在的情况"""
        mock_storage.get_session.return_value = None

        with pytest.raises(ValueError, match="Session session_001 not found"):
            await rewriter.rewrite_chapter(chapter_index=1)

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, rewriter, mock_evaluator):
        """测试达到最大重试次数"""
        # 所有评估都不通过
        mock_evaluator.evaluate.return_value = Mock(
            passed=False,
            score=0.6,
            to_dict=lambda: {"passed": False, "score": 0.6}
        )

        result = await rewriter.rewrite_chapter(
            chapter_index=1,
            max_retries=2
        )

        assert result["passed"] is False
        assert result["retry_count"] == 1  # 最后一次不计数


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
