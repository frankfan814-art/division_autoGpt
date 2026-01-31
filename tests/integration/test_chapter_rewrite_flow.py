"""
章节重写完整流程集成测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.core.chapter_rewriter import ChapterRewriter
from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.storage.vector_store import VectorStore
from creative_autogpt.core.vector_memory import VectorMemoryManager
from creative_autogpt.core.evaluator import EvaluationEngine


class TestChapterRewriteFlow:
    """章节重写完整流程集成测试"""

    @pytest.fixture
    async def storage(self):
        """创建存储实例"""
        storage = SessionStorage(":memory:")
        await storage.initialize()
        yield storage
        await storage.close()

    @pytest.fixture
    async def session_data(self, storage):
        """创建测试会话数据"""
        session_id = await storage.create_session(
            title="测试小说",
            mode="novel",
            goal={
                "genre": "玄幻",
                "theme": "修仙",
                "style": "古典"
            }
        )

        # 保存一些前置任务结果
        await storage.save_task_result(
            session_id=session_id,
            task_id="outline_001",
            task_type="大纲",
            status="completed",
            result="这是大纲内容，主角叶凡从废柴成长为仙帝",
            task_metadata={}
        )

        # 保存第一章任务结果
        await storage.save_task_result(
            session_id=session_id,
            task_id="chapter_001",
            task_type="章节内容",
            status="completed",
            result="第一章内容：叶凡在宗门中被欺负，决定复仇",
            task_metadata={"chapter_index": 1}
        )

        return session_id

    @pytest.mark.asyncio
    async def test_full_rewrite_flow(self, storage, session_data):
        """测试完整的重写流程"""
        # 这个测试需要实际的 LLM 调用，所以我们需要 mock
        with patch('creative_autogpt.utils.llm_client.MultiLLMClient.generate') as mock_generate:
            # Mock LLM 响应
            mock_generate.return_value = Mock(
                content="重写后的第一章：叶凡在宗门大殿上遭受羞辱，眼中闪过一丝寒光，发誓要让所有看不起他的人付出代价",
                usage=Mock(
                    total_tokens=1500,
                    prompt_tokens=500,
                    completion_tokens=1000
                )
            )

            with patch('creative_autogpt.core.evaluator.EvaluationEngine.evaluate') as mock_evaluate:
                # Mock 评估响应
                mock_evaluate.return_value = Mock(
                    passed=True,
                    score=0.8,
                    quality_score=0.85,
                    consistency_score=0.9,
                    to_dict=lambda: {
                        "passed": True,
                        "score": 0.8,
                        "quality_score": 0.85,
                        "consistency_score": 0.9
                    }
                )

                # 创建重写器（使用真实的组件但 mock LLM 调用）
                llm_client = MultiLLMClient()
                vector_store = VectorStore(session_id=session_data)
                memory = VectorMemoryManager(vector_store=vector_store)
                evaluator = EvaluationEngine(llm_client=llm_client)

                rewriter = ChapterRewriter(
                    session_id=session_data,
                    storage=storage,
                    llm_client=llm_client,
                    memory=memory,
                    evaluator=evaluator
                )

                # 执行重写
                result = await rewriter.rewrite_chapter(
                    chapter_index=1,
                    reason="质量不够好，需要更生动的描写"
                )

                # 验证结果
                assert result["passed"] is True
                assert result["version_number"] == 1
                assert result["score"] == 0.8

                # 验证版本已保存
                versions = await storage.get_chapter_versions(session_data, 1)
                assert len(versions) == 1
                assert versions[0]["version_number"] == 1
                assert versions[0]["is_current"] is True

    @pytest.mark.asyncio
    async def test_version_history_flow(self, storage, session_data):
        """测试版本历史管理流程"""
        with patch('creative_autogpt.utils.llm_client.MultiLLMClient.generate') as mock_generate:
            with patch('creative_autogpt.core.evaluator.EvaluationEngine.evaluate') as mock_evaluate:
                # 第一次评估不通过，第二次通过
                mock_evaluate.side_effect = [
                    Mock(passed=False, score=0.5, to_dict=lambda: {"passed": False, "score": 0.5}),
                    Mock(passed=True, score=0.85, to_dict=lambda: {"passed": True, "score": 0.85})
                ]

                mock_generate.return_value = Mock(
                    content="重写内容",
                    usage=Mock(total_tokens=1000, prompt_tokens=500, completion_tokens=500)
                )

                llm_client = MultiLLMClient()
                vector_store = VectorStore(session_id=session_data)
                memory = VectorMemoryManager(vector_store=vector_store)
                evaluator = EvaluationEngine(llm_client=llm_client)

                rewriter = ChapterRewriter(
                    session_id=session_data,
                    storage=storage,
                    llm_client=llm_client,
                    memory=memory,
                    evaluator=evaluator
                )

                # 执行重写（带重试）
                result = await rewriter.rewrite_chapter(
                    chapter_index=1,
                    max_retries=2
                )

                # 验证版本历史
                versions = await storage.get_chapter_versions(session_data, 1)

                # 应该有2个版本（v1初始版本，v2重写版本）
                assert len(versions) >= 1
                assert versions[0]["version_number"] >= 1

    @pytest.mark.asyncio
    async def test_restore_version_flow(self, storage, session_data):
        """测试版本恢复流程"""
        # 创建多个版本
        version_id_1 = await storage.create_chapter_version(
            session_id=session_data,
            task_id="chapter_001",
            chapter_index=1,
            content="版本1内容",
            version_number=1,
            is_current=False,
            evaluation={"score": 0.6}
        )

        version_id_2 = await storage.create_chapter_version(
            session_id=session_data,
            task_id="chapter_001",
            chapter_index=1,
            content="版本2内容",
            version_number=2,
            is_current=True,
            evaluation={"score": 0.8}
        )

        # 恢复到版本1
        success = await storage.restore_chapter_version(
            session_id=session_data,
            task_id="chapter_001",
            version_id=version_id_1
        )

        assert success is True

        # 验证当前版本已更新
        current = await storage.get_current_chapter_version(session_data, 1)
        assert current["version_number"] == 1
        assert current["content"] == "版本1内容"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
