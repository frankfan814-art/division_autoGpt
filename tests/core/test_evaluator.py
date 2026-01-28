"""
评估器直接修改模式的单元测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from creative_autogpt.core.evaluator import EvaluationEngine, EvaluationResult


class TestDirectEditMode:
    """直接修改模式测试"""

    @pytest.fixture
    def mock_llm_client(self):
        """模拟 LLM 客户端"""
        client = Mock()
        client.generate = AsyncMock()
        return client

    @pytest.fixture
    def evaluation_engine(self, mock_llm_client):
        """创建评估引擎实例"""
        return EvaluationEngine(llm_client=mock_llm_client)

    def test_parse_direct_edit_response_passed(self, evaluation_engine):
        """测试解析直接修改模式响应 - 内容通过"""
        response = "✅ CONTENT_PASSED"

        result = evaluation_engine._parse_direct_edit_response(
            response=response,
            criteria={},
            task_type="章节内容"
        )

        assert result.passed is True
        assert result.score == 0.85
        assert result.quality_score == 0.85
        assert result.consistency_score == 0.90
        assert result.metadata.get("direct_edit_mode") is True
        assert result.metadata.get("auto_passed") is True

    def test_parse_direct_edit_response_modified(self, evaluation_engine):
        """测试解析直接修改模式响应 - 内容被修改"""
        modified_content = "这是修改后的内容。\n\n第二段。"
        response = f"```{modified_content}```"

        result = evaluation_engine._parse_direct_edit_response(
            response=response,
            criteria={},
            task_type="章节内容"
        )

        assert result.passed is False
        assert result.score == 0.0
        assert result.metadata.get("direct_edit_mode") is True
        assert result.metadata.get("modified_content") == modified_content.strip()
        assert result.metadata.get("requires_re_evaluation") is True

    def test_parse_direct_edit_response_with_code_block(self, evaluation_engine):
        """测试解析带代码块的响应"""
        modified_content = "这是修改后的内容"
        response = f"```json\n{modified_content}\n```"

        result = evaluation_engine._parse_direct_edit_response(
            response=response,
            criteria={},
            task_type="章节内容"
        )

        assert result.metadata.get("modified_content") == modified_content

    @pytest.mark.asyncio
    async def test_evaluate_with_direct_edit_mode(self, evaluation_engine, mock_llm_client):
        """测试在直接修改模式下评估"""
        # 设置模拟响应 - 直接修改内容
        modified_content = "这是评估者修改后的内容"
        mock_llm_client.generate.return_value = Mock(
            content=modified_content,
            usage=Mock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        )

        result = await evaluation_engine.evaluate(
            task_type="章节内容",
            content="原始内容",
            context={},
            goal={},
            attempt=2  # 触发直接修改模式
        )

        # 验证结果包含直接修改模式标记
        assert result.metadata.get("direct_edit_mode") is True
        assert result.metadata.get("modified_content") == modified_content

    @pytest.mark.asyncio
    async def test_evaluate_without_direct_edit_mode(self, evaluation_engine, mock_llm_client):
        """测试普通评估模式（不使用直接修改）"""
        # 设置模拟响应 - JSON 评估结果
        json_response = '''{
            "passed": true,
            "quality_score": 0.8,
            "consistency_score": 0.9,
            "reasons": ["内容质量良好"],
            "suggestions": []
        }'''
        mock_llm_client.generate.return_value = Mock(
            content=json_response,
            usage=Mock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        )

        result = await evaluation_engine.evaluate(
            task_type="章节内容",
            content="原始内容",
            context={},
            goal={},
            attempt=0  # 不触发直接修改模式
        )

        # 验证结果不包含直接修改模式标记
        assert result.metadata.get("direct_edit_mode") is not True
        assert result.passed is True

    def test_direct_edit_threshold_default(self, evaluation_engine):
        """测试默认的直接修改模式阈值"""
        # 默认阈值应该是 2
        # 这个测试验证了直接修改模式在第2次重写时启用
        assert evaluation_engine.direct_edit_threshold == 2


class TestEvaluationResult:
    """评估结果测试"""

    def test_evaluation_result_to_dict(self):
        """测试评估结果转换为字典"""
        result = EvaluationResult(
            passed=True,
            score=0.8,
            quality_score=0.85,
            consistency_score=0.9,
            reasons=["原因1", "原因2"],
            suggestions=["建议1"],
            quality_issues=["质量问题1"],
            consistency_issues=["一致性问题1"]
        )

        result_dict = result.to_dict()

        assert result_dict["passed"] is True
        assert result_dict["score"] == 0.8
        assert result_dict["quality_score"] == 0.85
        assert result_dict["consistency_score"] == 0.9
        assert result_dict["quality_issues"] == ["质量问题1"]
        assert result_dict["consistency_issues"] == ["一致性问题1"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
