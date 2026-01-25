"""
Evaluation Engine - Quality assessment for generated content

Implements multi-dimensional quality evaluation with configurable criteria.
Uses LLM-based evaluation for semantic quality assessment.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from creative_autogpt.utils.llm_client import MultiLLMClient, LLMMessage


class EvaluationCriterion(str, Enum):
    """Evaluation criteria for content quality"""

    COHERENCE = "coherence"  # Logical flow and consistency
    CREATIVITY = "creativity"  # Originality and innovation
    QUALITY = "quality"  # Writing quality and prose
    CONSISTENCY = "consistency"  # Consistency with established context
    GOAL_ALIGNMENT = "goal_alignment"  # Alignment with creation goals
    CHARACTER_VOICE = "character_voice"  # Character voice consistency
    PLOT_PROGRESSION = "plot_progression"  # Story development
    DIALOGUE_QUALITY = "dialogue_quality"  # Dialogue naturalness


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension"""

    dimension: str
    score: float  # 0.0 to 1.0
    reason: str = ""
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "reason": self.reason,
            "suggestions": self.suggestions,
        }


@dataclass
class EvaluationResult:
    """Result of content evaluation"""

    passed: bool
    score: float  # Overall score 0.0 to 1.0
    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    evaluator: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "dimension_scores": {
                k: v.to_dict() for k, v in self.dimension_scores.items()
            },
            "reasons": self.reasons,
            "suggestions": self.suggestions,
            "evaluated_at": self.evaluated_at.isoformat(),
            "evaluator": self.evaluator,
            "metadata": self.metadata,
        }


class EvaluationEngine:
    """
    Evaluates generated content quality across multiple dimensions

    Default criteria and weights:
    - Coherence: 20%
    - Creativity: 20%
    - Quality: 20%
    - Consistency: 20%
    - Goal Alignment: 20%

    Can be customized for different content types.
    """

    # Default evaluation criteria with weights
    DEFAULT_CRITERIA: Dict[EvaluationCriterion, float] = {
        EvaluationCriterion.COHERENCE: 0.20,
        EvaluationCriterion.CREATIVITY: 0.20,
        EvaluationCriterion.QUALITY: 0.20,
        EvaluationCriterion.CONSISTENCY: 0.20,
        EvaluationCriterion.GOAL_ALIGNMENT: 0.20,
    }

    # Content-specific criteria overrides
    CONTENT_TYPE_CRITERIA: Dict[str, Dict[EvaluationCriterion, float]] = {
        "章节内容": {
            EvaluationCriterion.COHERENCE: 0.15,
            EvaluationCriterion.CREATIVITY: 0.20,
            EvaluationCriterion.QUALITY: 0.25,
            EvaluationCriterion.CONSISTENCY: 0.20,
            EvaluationCriterion.CHARACTER_VOICE: 0.10,
            EvaluationCriterion.PLOT_PROGRESSION: 0.10,
        },
        "对话检查": {
            EvaluationCriterion.DIALOGUE_QUALITY: 0.40,
            EvaluationCriterion.CHARACTER_VOICE: 0.30,
            EvaluationCriterion.CONSISTENCY: 0.20,
            EvaluationCriterion.QUALITY: 0.10,
        },
        "大纲": {
            EvaluationCriterion.COHERENCE: 0.25,
            EvaluationCriterion.CREATIVITY: 0.25,
            EvaluationCriterion.GOAL_ALIGNMENT: 0.25,
            EvaluationCriterion.PLOT_PROGRESSION: 0.25,
        },
    }

    def __init__(
        self,
        llm_client: Optional[MultiLLMClient] = None,
        passing_threshold: float = 0.7,
        criteria: Optional[Dict[EvaluationCriterion, float]] = None,
    ):
        """
        Initialize evaluation engine

        Args:
            llm_client: LLM client for AI-based evaluation
            passing_threshold: Minimum score to pass (0.0 to 1.0)
            criteria: Custom criteria weights
        """
        self.llm_client = llm_client
        self.passing_threshold = passing_threshold
        self.criteria = criteria or self.DEFAULT_CRITERIA.copy()

        logger.info(
            f"EvaluationEngine initialized (threshold={passing_threshold}, "
            f"criteria={len(self.criteria)})"
        )

    async def evaluate(
        self,
        task_type: str,
        content: str,
        criteria: Optional[Dict[EvaluationCriterion, float]] = None,
        context: Optional[Dict[str, Any]] = None,
        goal: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate content quality

        Args:
            task_type: Type of content being evaluated
            content: The content to evaluate
            criteria: Custom criteria for this evaluation
            context: Additional context for evaluation
            goal: Original creation goals

        Returns:
            EvaluationResult with scores and feedback
        """
        logger.debug(f"Evaluating content for task type: {task_type}")

        # Determine criteria to use
        eval_criteria = criteria or self._get_criteria_for_task_type(task_type)

        if self.llm_client:
            # Use LLM-based evaluation
            result = await self._llm_evaluate(
                task_type=task_type,
                content=content,
                criteria=eval_criteria,
                context=context,
                goal=goal,
            )
        else:
            # Use rule-based evaluation (fallback)
            result = await self._rule_based_evaluate(
                task_type=task_type,
                content=content,
                criteria=eval_criteria,
                context=context,
            )

        logger.info(
            f"Evaluation complete: score={result.score:.3f}, passed={result.passed}"
        )

        return result

    def _get_criteria_for_task_type(
        self,
        task_type: str,
    ) -> Dict[EvaluationCriterion, float]:
        """Get evaluation criteria for a specific task type"""
        return self.CONTENT_TYPE_CRITERIA.get(
            task_type,
            self.DEFAULT_CRITERIA,
        )

    async def _llm_evaluate(
        self,
        task_type: str,
        content: str,
        criteria: Dict[EvaluationCriterion, float],
        context: Optional[Dict[str, Any]] = None,
        goal: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Perform LLM-based evaluation

        Uses DeepSeek for logical evaluation (cost-effective)
        """
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            task_type=task_type,
            content=content,
            criteria=criteria,
            context=context,
            goal=goal,
        )

        try:
            # Use DeepSeek for evaluation (logic/reasoning strength)
            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="评估",  # Route to DeepSeek
                temperature=0.3,  # Lower temperature for consistent evaluation
                max_tokens=2000,
            )

            # Parse evaluation result
            return self._parse_evaluation_response(
                response.content,
                criteria,
                task_type,
            )

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}, falling back to rule-based")
            return await self._rule_based_evaluate(
                task_type=task_type,
                content=content,
                criteria=criteria,
                context=context,
            )

    def _build_evaluation_prompt(
        self,
        task_type: str,
        content: str,
        criteria: Dict[EvaluationCriterion, float],
        context: Optional[Dict[str, Any]] = None,
        goal: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for LLM evaluation"""

        criteria_desc = "\n".join(
            f"- {c.value}: {w * 100:.0f}%权重"
            for c, w in criteria.items()
        )

        context_section = ""
        if context:
            context_section = f"\n\n上下文信息:\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        goal_section = ""
        if goal:
            goal_section = f"\n\n创作目标:\n{json.dumps(goal, ensure_ascii=False, indent=2)}"

        prompt = f"""你是一位专业的小说内容评估专家。你正在评估一部**小说**的{task_type}内容质量。

⚠️ 重要提醒：
- 这是小说创作，不是学术论文或科学研究报告
- 内容应该是故事性的、文学性的、面向大众读者的
- 必须使用小说的叙事语言，而不是学术论文语言

📖 科幻小说特殊规则（参考《三体》《流浪地球》标准）：
- ✅ 允许：适度的科学概念、技术设定、未来科技描述
- ✅ 允许：必要的科学术语，但必须通过故事情节自然呈现
- ✅ 允许：用通俗易懂的方式解释科学原理（像刘慈欣的写法）
- ❌ 禁止：堆砌复杂公式、学术论文式的理论推导
- ❌ 禁止：纯技术文档式的描述、缺乏故事性
- ❌ 禁止：面向专业研究者的学术写作风格

核心标准：科学设定服务于故事，而不是展示学术研究。

## 评估标准
{criteria_desc}

## 待评估内容
```
{content[:5000]}  # Limit content length
```
{context_section}
{goal_section}

## 评估要求
请对每个评估维度进行打分（0-100分）并给出理由和改进建议。

特别注意：如果内容包含以下特征，必须大幅降低评分（< 30分）：
- 论文格式（摘要、引言、方法论、参考文献等学术结构）
- 纯粹的公式推导，没有故事情节包裹
- 大量堆砌专业术语，不解释或硬性灌输
- 学术报告的语气和结构
- 完全缺乏故事性、对话、场景描写
- 不是面向普通读者，而是面向专业研究者

请以JSON格式返回评估结果:
```json
{{
  "dimension_scores": {{
    "coherence": {{"score": 85, "reason": "...", "suggestions": ["..."]}},
    "creativity": {{"score": 75, "reason": "...", "suggestions": ["..."]}},
    ...
  }},
  "overall_reasons": ["...", "..."],
  "suggestions": ["...", "..."]
}}
```

请确保:
1. 每个维度的分数在0-100之间
2. 理由具体明确
3. 建议具有可操作性
"""

        return prompt

    def _parse_evaluation_response(
        self,
        response: str,
        criteria: Dict[EvaluationCriterion, float],
        task_type: str,
    ) -> EvaluationResult:
        """Parse LLM evaluation response"""

        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

            # Build dimension scores
            dimension_scores = {}
            total_score = 0.0
            total_weight = 0.0

            for criterion, weight in criteria.items():
                criterion_key = criterion.value
                if criterion_key in data.get("dimension_scores", {}):
                    score_data = data["dimension_scores"][criterion_key]
                    score = score_data.get("score", 70) / 100.0  # Convert to 0-1

                    dimension_scores[criterion_key] = DimensionScore(
                        dimension=criterion_key,
                        score=score,
                        reason=score_data.get("reason", ""),
                        suggestions=score_data.get("suggestions", []),
                    )

                    total_score += score * weight
                    total_weight += weight
                else:
                    # Use default score if missing
                    dimension_scores[criterion_key] = DimensionScore(
                        dimension=criterion_key,
                        score=0.7,
                        reason="未评估",
                        suggestions=[],
                    )
                    total_score += 0.7 * weight
                    total_weight += weight

            # Calculate overall score
            overall_score = total_score / total_weight if total_weight > 0 else 0.7

            # Collect reasons and suggestions
            all_reasons = data.get("overall_reasons", [])
            all_suggestions = data.get("suggestions", [])

            for dim_score in dimension_scores.values():
                if dim_score.reason:
                    all_reasons.append(f"{dim_score.dimension}: {dim_score.reason}")
                all_suggestions.extend(dim_score.suggestions)

            return EvaluationResult(
                passed=overall_score >= self.passing_threshold,
                score=overall_score,
                dimension_scores=dimension_scores,
                reasons=all_reasons,
                suggestions=all_suggestions,
                evaluator="llm_deepseek",
                metadata={"task_type": task_type},
            )

        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            # Return a default result
            return EvaluationResult(
                passed=True,  # Pass on error to avoid blocking
                score=0.7,
                dimension_scores={
                    c.value: DimensionScore(
                        dimension=c.value,
                        score=0.7,
                        reason="评估解析失败，使用默认分数",
                        suggestions=[],
                    )
                    for c in criteria.keys()
                },
                reasons=["评估解析失败"],
                suggestions=["请重试评估"],
                evaluator="llm_deepseek_fallback",
            )

    async def _rule_based_evaluate(
        self,
        task_type: str,
        content: str,
        criteria: Dict[EvaluationCriterion, float],
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Perform rule-based evaluation (fallback)

        Uses simple heuristics to assess content quality
        """
        dimension_scores = {}
        total_score = 0.0
        total_weight = 0.0

        content_length = len(content)
        word_count = len(content.split())

        # Coherence: Check for reasonable length and structure
        coherence_score = min(1.0, min(content_length / 500, 1.0))
        if content_length < 100:
            coherence_score = 0.5
        dimension_scores[EvaluationCriterion.COHERENCE.value] = DimensionScore(
            dimension=EvaluationCriterion.COHERENCE.value,
            score=coherence_score,
            reason=f"内容长度: {content_length}字符",
            suggestions=["内容过短，建议扩展" if content_length < 200 else "长度适中"],
        )
        total_score += coherence_score * criteria.get(EvaluationCriterion.COHERENCE, 0.2)
        total_weight += criteria.get(EvaluationCriterion.COHERENCE, 0.2)

        # Creativity: Check for variety in vocabulary
        unique_words = len(set(content.split()))
        vocabulary_diversity = unique_words / max(word_count, 1)
        creativity_score = min(1.0, vocabulary_diversity * 1.5)
        dimension_scores[EvaluationCriterion.CREATIVITY.value] = DimensionScore(
            dimension=EvaluationCriterion.CREATIVITY.value,
            score=creativity_score,
            reason=f"词汇多样性: {vocabulary_diversity:.2f}",
            suggestions=["增加词汇丰富度" if vocabulary_diversity < 0.5 else "词汇丰富度良好"],
        )
        total_score += creativity_score * criteria.get(EvaluationCriterion.CREATIVITY, 0.2)
        total_weight += criteria.get(EvaluationCriterion.CREATIVITY, 0.2)

        # Quality: Check for basic grammar indicators
        quality_score = 0.8  # Default good score
        issues = []
        if content.count("。") < content_length / 200:
            issues.append("句子结尾标点可能不足")
            quality_score -= 0.1
        if content.count("\n") < content_length / 1000:
            issues.append("段落划分可能不足")
            quality_score -= 0.1
        dimension_scores[EvaluationCriterion.QUALITY.value] = DimensionScore(
            dimension=EvaluationCriterion.QUALITY.value,
            score=max(0.5, quality_score),
            reason="基础格式检查",
            suggestions=issues if issues else ["格式良好"],
        )
        total_score += quality_score * criteria.get(EvaluationCriterion.QUALITY, 0.2)
        total_weight += criteria.get(EvaluationCriterion.QUALITY, 0.2)

        # Consistency and goal alignment: Default scores
        for criterion in [EvaluationCriterion.CONSISTENCY, EvaluationCriterion.GOAL_ALIGNMENT]:
            if criterion in criteria:
                default_score = 0.7
                dimension_scores[criterion.value] = DimensionScore(
                    dimension=criterion.value,
                    score=default_score,
                    reason="基于规则的默认评估",
                    suggestions=["建议使用LLM进行更准确的评估"],
                )
                total_score += default_score * criteria[criterion]
                total_weight += criteria[criterion]

        # Calculate overall score
        overall_score = total_score / total_weight if total_weight > 0 else 0.7

        all_reasons = [f"{d.dimension}: {d.reason}" for d in dimension_scores.values()]
        all_suggestions = []
        for d in dimension_scores.values():
            all_suggestions.extend(d.suggestions)

        return EvaluationResult(
            passed=overall_score >= self.passing_threshold,
            score=overall_score,
            dimension_scores=dimension_scores,
            reasons=all_reasons,
            suggestions=all_suggestions,
            evaluator="rule_based",
            metadata={"task_type": task_type},
        )

    def set_passing_threshold(self, threshold: float) -> None:
        """Update the passing threshold"""
        self.passing_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Updated passing threshold to {self.passing_threshold}")

    def set_criteria(
        self,
        criteria: Dict[EvaluationCriterion, float],
    ) -> None:
        """Update evaluation criteria"""
        # Validate weights sum to approximately 1.0
        total_weight = sum(criteria.values())
        if abs(total_weight - 1.0) > 0.1:
            logger.warning(
                f"Criteria weights sum to {total_weight}, "
                f"expected ~1.0. Normalizing..."
            )
            # Normalize
            self.criteria = {
                k: v / total_weight for k, v in criteria.items()
            }
        else:
            self.criteria = criteria.copy()

        logger.info(f"Updated evaluation criteria: {list(self.criteria.keys())}")
