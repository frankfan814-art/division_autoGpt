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

from creative_autogpt.utils.llm_client import MultiLLMClient


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
    score: float  # Overall score 0.0 to 1.0 (deprecated, use quality_score and consistency_score)
    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    evaluator: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 🔥 新增：分别跟踪质量评分和一致性评分
    quality_score: float = 0.0  # 文学质量评分 (0.0 - 1.0)
    consistency_score: float = 0.0  # 逻辑一致性评分 (0.0 - 1.0)

    # 🔥 新增：详细的问题分类
    quality_issues: List[str] = field(default_factory=list)  # 质量问题列表
    consistency_issues: List[str] = field(default_factory=list)  # 一致性问题列表

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "quality_score": self.quality_score,  # 新增
            "consistency_score": self.consistency_score,  # 新增
            "dimension_scores": {
                k: v.to_dict() for k, v in self.dimension_scores.items()
            },
            "reasons": self.reasons,
            "suggestions": self.suggestions,
            "quality_issues": self.quality_issues,  # 新增
            "consistency_issues": self.consistency_issues,  # 新增
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
        passing_threshold: float = 0.7,  # 🔥 默认阈值 0.7 (7/10) - 符合文档要求
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
        predecessor_contents: Optional[Dict[str, str]] = None,
        chapter_context: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate content quality

        Args:
            task_type: Type of content being evaluated
            content: The content to evaluate
            criteria: Custom criteria for this evaluation
            context: Additional context for evaluation
            goal: Original creation goals
            predecessor_contents: Contents from previous tasks for cross-task consistency check
            chapter_context: Previous chapter contents for continuity check

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
                predecessor_contents=predecessor_contents,
                chapter_context=chapter_context,
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
        predecessor_contents: Optional[Dict[str, str]] = None,
        chapter_context: Optional[str] = None,
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
            predecessor_contents=predecessor_contents,
            chapter_context=chapter_context,
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
        predecessor_contents: Optional[Dict[str, str]] = None,
        chapter_context: Optional[str] = None,
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

        # 🔥 新增：前置任务内容（用于跨任务一致性检查）
        predecessor_section = ""
        if predecessor_contents:
            priority_list = ["人物设计", "世界观规则", "风格元素", "大纲", "伏笔列表", "事件", "场景物品冲突"]
            predecessor_section = "\n\n### 前面任务的核心成果（必须严格保持一致）\n"
            for pred_type in priority_list:
                if pred_type in predecessor_contents:
                    pred_content = predecessor_contents[pred_type]
                    max_len = 4000 if pred_type in ["人物设计", "大纲"] else 2000
                    predecessor_section += f"\n#### {pred_type}\n```\n{pred_content[:max_len]}{'...' if len(pred_content) > max_len else ''}\n```\n"

        # 🔥 新增：章节上下文（用于章节连贯性检查）
        chapter_context_section = ""
        if chapter_context:
            chapter_context_section = f"\n\n### 前面章节内容（章节连贯性检查）\n{chapter_context}"

        # 🔥 根据任务类型提供具体的评估要点
        task_specific_criteria = self._get_task_evaluation_criteria(task_type)

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

## {task_type}具体评估要点
{task_specific_criteria}

## 待评估内容
```
{content[:8000]}
```
{context_section}
{goal_section}
{predecessor_section}
{chapter_context_section}

## 评估要求

### 🔍 用户输入一致性检查（仅针对创意脑暴）

如果前置内容中包含【用户输入】，说明这是创意脑暴任务，请务必检查脑暴结果是否**严格遵循**用户的原始输入：

1. **类型/流派一致性**：
   - 点子是否符合用户指定的【类型/流派】？
   - 如果用户要求"科幻"，点子是否包含科幻元素？

2. **风格一致性**：
   - 点子是否符合用户指定的【写作风格】？
   - 如果用户要求"黑暗风格"，点子是否体现这种风格？

3. **创作要求一致性**：
   - 点子是否满足用户的【创作要求】？
   - 用户要求的关键要素是否都体现在点子中？

4. **规模匹配度**：
   - 点子的规模是否适合【目标字数】和【章节数量】？
   - 如果用户要求100万字，点子是否有足够的扩展空间？

⚠️ **用户输入一致性评判标准**：
- **严重问题**：完全违背用户明确要求的类型/风格/核心设定
- **中等问题**：部分偏离用户要求，但仍可调整
- **小问题**：细节上不够贴合用户要求

---

### 🔍 跨任务一致性检查（重要！）

如果提供了【前面任务的核心成果】，请务必检查当前内容与前面任务的**严格一致性**：

1. **大纲一致性**：
   - 是否紧扣【大纲】中定义的主角目标和核心冲突？
   - 是否服务于大纲的核心情感钩子？

2. **人物一致性**：
   - 如果涉及人物，是否使用了【人物设计】中已有的角色？
   - 人物的性格、背景、目标是否与设计一致？
   - 有没有凭空出现的新角色（应该避免）？

3. **世界观一致性**：
   - 是否符合【世界观规则】中的设定？
   - 有没有违反已设定的规则？
   - 新增的设定是否与已有设定冲突？

4. **风格一致性**：
   - 写作风格是否符合【风格元素】的要求？
   - 语言调性是否统一？

5. **主题一致性**：
   - 是否围绕【大纲】的核心主题展开？
   - 有没有偏离主题、跑题的内容？

### 📖 章节连贯性检查（如果提供了前面章节内容）

如果提供了【前面章节内容】，请务必检查章节之间的连贯性：

1. **开头衔接**：
   - 本章开头是否自然衔接上一章结尾？
   - 有没有突兀的转换或割裂感？

2. **人物状态延续**：
   - 人物位置、情绪、状态是否与上一章结尾一致？
   - 有没有出现不合理的状态变化？

3. **时间线连贯**：
   - 时间线是否合理？
   - 有没有时间跳跃或矛盾？

4. **整体连贯性**：
   - 本章是否像独立短篇，与前面脱节？
   - 是否保持了叙事的连续性？

⚠️ **一致性检查评判标准**（严格要求）：
- **9-10分**：完美一致，没有任何瑕疵，近乎完美的作品
- **8-9分**：高度一致，有极个别小瑕疵但不影响阅读（优秀作品水平）
- **7-8分**：基本一致，有一些小问题但不严重（合格作品水平）
- **6-7分**：有明显一致性问题，需要修改（勉强及格）
- **6分以下**：一致性很差，必须重写（不通过）

---

## 评估格式要求

请按以下格式返回评估结果（**必须严格遵循此格式**）：

### 综合质量评分：X/10
（给出一个0-10的分数，7分以上为通过，8分以上为优秀）

### 一致性评分：X/10
（给出一个0-10的分数，7分以上为通过，8分以上为优秀）

### 一、文学质量评分

| 维度 | 评分 | 优点 | 不足 |
|------|------|------|------|
| 连贯性 | X/10 | ... | ... |
| 创造性 | X/10 | ... | ... |
| 文笔 | X/10 | ... | ... |

**质量问题总结**：
- 问题1：具体描述...
- 问题2：具体描述...
- 问题3：具体描述...

### 二、逻辑一致性检查

🔴 **严重问题**（必须修复）：
- 具体描述严重的逻辑矛盾或不一致之处...

🟡 **中等问题**（建议修复）：
- 具体描述中等问题...

🟢 **无明显问题**（如果没有严重和中等问题）

### 三、评估结论

**是否通过**：是/否

**一句话评价**：用一句话总结你的评价

**详细理由**：
1. 理由1...
2. 理由2...
3. 理由3...

### 四、改进建议

**必须修改**：
1. [具体修改建议1] - 说明为什么需要这样改，以及具体怎么改
2. [具体修改建议2] - 说明为什么需要这样改，以及具体怎么改

**建议优化**：
1. [具体优化建议1]
2. [具体优化建议2]

### 五、亮点总结
- 亮点1...
- 亮点2...

---

## ⚠️ 关键要求：

1. **具体明确**：每个问题和建议都必须具体，不要用"不错"、"可以改进"等模糊词语
2. **有针对性**：针对{task_type}的特点进行评估
3. **可操作**：建议必须是可以直接执行的，例如"增加主角对未来的恐惧描写"而不是"增加情感描写"
4. **两分法**：明确区分"质量问题"（文学性）和"一致性问题"（逻辑性）
5. **评分说明**：如果评分低于8分，必须在"质量问题总结"和"逻辑一致性检查"中说明具体原因

## 评分标准参考：
- 9-10分：优秀，仅有微不足道的小问题
- 8-9分：良好，有小问题但不影响整体
- 6-8分：及格，有明显问题需要修改
- 4-6分：不及格，有重大问题需要重写
- 0-4分：完全不合格，完全不符合要求
"""

        return prompt

    def _parse_evaluation_response(
        self,
        response: str,
        criteria: Dict[EvaluationCriterion, float],
        task_type: str,
    ) -> EvaluationResult:
        """Parse LLM evaluation response

        支持两种格式:
        1. JSON格式 (旧格式)
        2. 新格式 (质量+一致性评分)
        """

        try:
            # 🔥 优先尝试解析新格式 (质量+一致性评分)
            new_format_result = self._try_parse_new_format(response, task_type)
            if new_format_result:
                return new_format_result

            # 回退到旧JSON格式
            return self._parse_json_format(response, criteria, task_type)

        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            # Return a default result
            return EvaluationResult(
                passed=False,  # 解析失败时默认不通过
                score=0.7,
                quality_score=0.7,
                consistency_score=0.7,
                dimension_scores={},
                reasons=[f"评估解析失败: {str(e)}"],
                suggestions=["请重新生成"],
                quality_issues=[],
                consistency_issues=[],
                evaluator="parse_error",
                metadata={"task_type": task_type, "error": str(e)},
            )

    def _try_parse_new_format(
        self, response: str, task_type: str
    ) -> Optional[EvaluationResult]:
        """
        尝试解析新格式 (质量+一致性评分)
        新格式使用结构化文本而非JSON，更容易被LLM正确生成
        """

        import re

        # 提取综合质量评分
        quality_match = re.search(r"综合质量评分[：:]\s*(\d+(?:\.\d+)?)[/／]10", response)
        quality_score = float(quality_match.group(1)) / 10.0 if quality_match else None

        # 提取一致性评分
        consistency_match = re.search(r"一致性评分[：:]\s*(\d+(?:\.\d+)?)[/／]10", response)
        consistency_score = (
            float(consistency_match.group(1)) / 10.0 if consistency_match else None
        )

        # 如果都没有提取到，返回None (使用旧格式)
        if quality_score is None and consistency_score is None:
            return None

        # 如果只有一个有值，另一个使用默认值
        if quality_score is None:
            quality_score = consistency_score if consistency_score else 0.7
        if consistency_score is None:
            consistency_score = quality_score if quality_score else 0.7

        # 🔥 提取质量问题 - 改进版
        quality_issues = []

        # 方法1: 从"质量问题总结"部分提取
        quality_summary_section = re.search(
            r"\*\*质量问题总结\*\*[：:]?\s*\n((?:[-•]\s*.*?\n)+)", response, re.MULTILINE
        )
        if quality_summary_section:
            for line in quality_summary_section.group(1).split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("•"):
                    # 提取"问题X："后面的内容
                    issue = re.sub(r"^问题\d+[：:]\s*", "", line.lstrip("-•*").strip())
                    if issue and len(issue) > 5:
                        quality_issues.append(issue)

        # 方法2: 如果没有找到，从"不足"列提取
        if not quality_issues:
            quality_section = re.search(
                r"###?\s*一、文学质量评分.*?(?=###?\s*二、|###?\s*逻辑一致性|\Z)", response, re.DOTALL
            )
            if quality_section:
                # 在表格中查找"不足"列的内容
                lines = quality_section.group(0).split("\n")
                for i, line in enumerate(lines):
                    if "不足" in line:
                        # 找到不足列的索引
                        cells = [c.strip() for c in line.split("|")]
                        try:
                            shortage_idx = cells.index("不足")
                            # 读取下一行的不足内容
                            if i + 1 < len(lines):
                                next_cells = [c.strip() for c in lines[i + 1].split("|")]
                                if shortage_idx < len(next_cells):
                                    issue = next_cells[shortage_idx].strip()
                                    if issue and len(issue) > 3 and issue != "...":
                                        quality_issues.append(issue)
                        except ValueError:
                            pass

        # 方法3: 查找文本中的质量问题列表
        if not quality_issues:
            quality_list_patterns = [
                r"(?:质量问题|不足|缺点)[：:]?\s*\n((?:[-•]\s*.*?\n){1,5})",
                r"(?:质量|文学)[^。]*?问题[：:]\s*([^\n]+)",
            ]
            for pattern in quality_list_patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    text = match.group(1)
                    for line in text.split("\n"):
                        line = line.strip()
                        if line.startswith("-") or line.startswith("•"):
                            issue = line.lstrip("-•*").strip()
                            if issue and len(issue) > 5:
                                quality_issues.append(issue)
                    if quality_issues:
                        break

        # 🔥 提取一致性问题 - 改进版
        consistency_issues = []

        # 提取严重问题
        critical_section = re.search(
            r"🔴\s*\*\*严重问题\*\*.*?(?=🟡|🟢|✅|###?\s*三、|###?\s*评估结论|\Z)", response, re.DOTALL
        )
        if critical_section:
            for line in critical_section.group(0).split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("•"):
                    issue = line.lstrip("-•*").strip()
                    if issue and len(issue) > 5:
                        consistency_issues.append(f"[严重] {issue}")

        # 提取中等问题
        medium_section = re.search(
            r"🟡\s*\*\*中等问题\*\*.*?(?=🟢|✅|###?\s*三、|###?\s*评估结论|\Z)", response, re.DOTALL
        )
        if medium_section:
            for line in medium_section.group(0).split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("•"):
                    issue = line.lstrip("-•*").strip()
                    if issue and len(issue) > 5:
                        consistency_issues.append(f"[中等] {issue}")

        # 🔥 提取总体评价
        overall_comment = ""
        comment_match = re.search(r"一句话评价[：:]\s*(.+?)(?:\n|$)", response)
        if comment_match:
            overall_comment = comment_match.group(1).strip()

        # 🔥 提取详细理由
        detailed_reasons = []
        reasons_section = re.search(
            r"\*\*详细理由\*\*[：:]?\s*\n((?:\d+[\.、]\s*.*?\n)+)", response, re.MULTILINE
        )
        if reasons_section:
            for line in reasons_section.group(1).split("\n"):
                line = line.strip()
                # 提取编号列表
                match = re.match(r"\d+[\.、]\s*(.+)", line)
                if match:
                    reason = match.group(1).strip()
                    if reason and len(reason) > 5:
                        detailed_reasons.append(reason)

        # 🔥 提取亮点
        highlights = []
        highlight_section = re.search(
            r"###?\s*五、亮点总结.*?(?=---|\Z)", response, re.DOTALL
        )
        if highlight_section:
            for line in highlight_section.group(0).split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("•") or line.startswith("—"):
                    highlight = line.lstrip("-—•*").strip()
                    if highlight and len(highlight) > 5:
                        highlights.append(highlight)

        # 🔥 提取改进建议
        suggestions = []

        # 提取"必须修改"
        must_fix_section = re.search(
            r"\*\*必须修改\*\*[：:]?\s*\n((?:\d+[\.、]\s*.*?\n)+)", response, re.MULTILINE
        )
        if must_fix_section:
            for line in must_fix_section.group(1).split("\n"):
                line = line.strip()
                match = re.match(r"\d+[\.、]\s*(.+)", line)
                if match:
                    suggestion = match.group(1).strip()
                    if suggestion and len(suggestion) > 10:
                        suggestions.append(f"[必须] {suggestion}")

        # 提取"建议优化"
        should_optimize_section = re.search(
            r"\*\*建议优化\*\*[：:]?\s*\n((?:\d+[\.、]\s*.*?\n)+)", response, re.MULTILINE
        )
        if should_optimize_section:
            for line in should_optimize_section.group(1).split("\n"):
                line = line.strip()
                match = re.match(r"\d+[\.、]\s*(.+)", line)
                if match:
                    suggestion = match.group(1).strip()
                    if suggestion and len(suggestion) > 10:
                        suggestions.append(f"[建议] {suggestion}")

        # 🔥 构建reasons
        reasons = []

        if overall_comment:
            reasons.append(overall_comment)

        if detailed_reasons:
            reasons.extend(detailed_reasons[:3])

        if highlights:
            reasons.append("亮点: " + "; ".join(highlights[:3]))

        # 如果没有提取到具体建议，使用质量问题和一致性问题作为建议
        if not suggestions:
            # 质量问题作为建议
            if quality_issues:
                suggestions.extend([f"质量改进: {issue}" for issue in quality_issues[:3]])

            # 一致性问题作为建议
            if consistency_issues:
                suggestions.extend(
                    [f"一致性修复: {issue}" for issue in consistency_issues[:3]]
                )

        # 🔥 判断是否通过：两个分数都需要 >= passing_threshold
        passed = quality_score >= self.passing_threshold and consistency_score >= self.passing_threshold

        # 构建dimension_scores (兼容旧格式)
        dimension_scores = {
            "文学质量": DimensionScore(
                dimension="文学质量",
                score=quality_score,
                reason=f"质量评分: {quality_score * 10:.1f}/10",
                suggestions=[f"质量改进: {issue}" for issue in quality_issues[:3]],
            ),
            "逻辑一致性": DimensionScore(
                dimension="逻辑一致性",
                score=consistency_score,
                reason=f"一致性评分: {consistency_score * 10:.1f}/10",
                suggestions=[f"一致性修复: {issue}" for issue in consistency_issues[:3]],
            ),
        }

        return EvaluationResult(
            passed=passed,
            score=(quality_score + consistency_score) / 2,  # 平均分
            quality_score=quality_score,
            consistency_score=consistency_score,
            dimension_scores=dimension_scores,
            reasons=reasons,
            suggestions=suggestions,
            quality_issues=quality_issues,
            consistency_issues=consistency_issues,
            evaluator="llm_new_format",
            metadata={"task_type": task_type},
        )

    def _parse_json_format(
        self, response: str, criteria: Dict[EvaluationCriterion, float], task_type: str
    ) -> EvaluationResult:
        """解析旧JSON格式"""

        # 🔥 改进 JSON 提取方法：尝试多种方式
        data = None
        json_error = None
        original_response = response

        # 方法1: 尝试直接解析整个响应（如果纯JSON）
        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError as e:
            json_error = str(e)

        # 方法2: 尝试提取 JSON 代码块
        if data is None:
            # 查找 ```json ... ``` 代码块
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_block_match:
                try:
                    data = json.loads(json_block_match.group(1))
                    json_error = None
                except json.JSONDecodeError as e:
                    json_error = str(e)

        # 方法3: 尝试匹配最外层的 { ... } (使用括号匹配)
        if data is None:
            try:
                # 找到第一个 { 和对应的 }
                start = response.find("{")
                if start >= 0:
                    brace_count = 0
                    in_string = False
                    escape_next = False
                    for i in range(start, len(response)):
                        char = response[i]
                        if escape_next:
                            escape_next = False
                            continue
                        if char == "\\":
                            escape_next = True
                            continue
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        if not in_string:
                            if char == "{":
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    # 找到匹配的括号
                                    json_str = response[start:i+1]
                                    data = json.loads(json_str)
                                    json_error = None
                                    break
            except (json.JSONDecodeError, ValueError) as e:
                json_error = str(e)

        # 🔥 如果所有方法都失败，尝试从原始响应中提取有用信息
        if data is None:
            logger.warning(f"Failed to parse JSON response: {json_error}")
            logger.warning(f"Original response (first 500 chars): {response[:500]}")

            # 🔥 尝试从非 JSON 格式中提取建议
            suggestions = self._extract_suggestions_from_text(response)
            reasons = self._extract_reasons_from_text(response)

            # 🔥 尝试提取评分
            score_match = re.search(r'(?:评分|得分|分数)[：:\s]*(\d+(?:\.\d+)?)[/／]?(?:10|100)?', response)
            extracted_score = float(score_match.group(1)) / 10.0 if score_match else None
            overall_score = extracted_score if extracted_score else 0.7

            # 🔥 检查是否明确表示"需要改进"或类似表述
            passed = overall_score >= self.passing_threshold
            needs_rewrite = re.search(r'(需要改进|请重写|不符合要求|未达到标准|建议重新)', response, re.IGNORECASE)
            if needs_rewrite and overall_score >= self.passing_threshold:
                overall_score = 0.7  # 明确表示需要改进，降低分数
                passed = False

            # 🔥 构建更详细的建议
            if not suggestions:
                if task_type == "世界观规则":
                    suggestions = [
                        "请确保世界观规则完整且自洽",
                        "力量体系要有明确的规则和限制",
                        "世界背景要与故事类型相符",
                        "避免规则之间的矛盾"
                    ]
                elif task_type == "人物设计":
                    suggestions = [
                        "请确保人物性格鲜明且有发展空间",
                        "人物背景要与世界观相符",
                        "人物关系要清晰合理",
                        "主角要有明确的动机和目标"
                    ]
                elif task_type == "大纲":
                    suggestions = [
                        "请确保大纲结构完整",
                        "情节发展要合乎逻辑",
                        "要有明确的三幕结构",
                        "高潮部分要足够精彩"
                    ]
                else:
                    suggestions = [
                        "请根据任务要求重新生成内容",
                        "确保内容符合创作目标",
                        "注意与前面内容的一致性"
                    ]

            # 🔥 从响应中提取具体问题
            issues = self._extract_issues_from_text(response)
            quality_issues = issues.get("quality", [])
            consistency_issues = issues.get("consistency", [])

            # 🔥 构建维度分数
            dimension_scores = {
                "quality": DimensionScore(
                    dimension="quality",
                    score=overall_score,
                    reason=reasons[0] if reasons else "基于文本内容的评估",
                    suggestions=suggestions,
                )
            }

            # 🔥 如果没有提取到评分，使用默认分数但不通过
            if extracted_score is None:
                overall_score = 0.7
                passed = False

            return EvaluationResult(
                passed=passed,
                score=overall_score,
                quality_score=overall_score,
                consistency_score=overall_score,
                dimension_scores=dimension_scores,
                reasons=reasons if reasons else ["JSON解析失败，基于文本内容评估"],
                suggestions=suggestions,
                quality_issues=quality_issues,
                consistency_issues=consistency_issues,
                evaluator="text_fallback",
                metadata={"task_type": task_type, "parse_error": json_error}
            )

        # JSON 解析成功，继续正常流程
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

        # 🔥 旧格式也使用新的通过标准
        passed = overall_score >= self.passing_threshold

        return EvaluationResult(
            passed=passed,
            score=overall_score,
            quality_score=overall_score,  # 旧格式只有一个分数
            consistency_score=overall_score,  # 假设一致性相同
            dimension_scores=dimension_scores,
            reasons=all_reasons,
            suggestions=all_suggestions,
            quality_issues=[],  # 旧格式不区分
            consistency_issues=[],
            evaluator="llm_json_format",
            metadata={"task_type": task_type},
        )

    def _extract_suggestions_from_text(self, text: str) -> List[str]:
        """🔥 从文本中提取建议"""
        suggestions = []

        # 查找"建议"、"改进"、"修改"等关键词后面的内容
        patterns = [
            r'(?:建议|改进|修改|需要)[：:]\s*([^\n]+)',
            r'(?:建议|改进|修改)[1-9][：:]\s*([^\n]+)',
            r'[-•]\s*(.*?(?:建议|改进|修改|优化|调整)[^\n]*)',
            r'>(\d+)[\.、]\s*([^\n]+)',  # HTML list
            r'(\d+)[\.、]\s*(.*?(?:建议|改进))',  # Numbered list
            r'【.*?】\s*([^\n]+)',  # Brackets
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    suggestion = match[1] if len(match) > 1 else match[0]
                else:
                    suggestion = match

                suggestion = suggestion.strip()
                if suggestion and len(suggestion) > 3 and suggestion not in suggestions:
                    # 移除过长的建议
                    if len(suggestion) < 200:
                        suggestions.append(suggestion)

        return list(set(suggestions))[:10]  # 去重并限制数量

    def _extract_reasons_from_text(self, text: str) -> List[str]:
        """🔥 从文本中提取原因/评价"""
        reasons = []

        # 查找评价性语句
        patterns = [
            r'(?:评价|评估|总体|结论)[：:]\s*([^\n]+)',
            r'(?:优点|亮点|好处)[：:]\s*([^\n]+)',
            r'(?:缺点|不足|问题)[：:]\s*([^\n]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                reason = match.strip()
                if reason and len(reason) > 3 and reason not in reasons:
                    if len(reason) < 200:
                        reasons.append(reason)

        # 如果没有找到，尝试提取第一段
        if not reasons:
            first_para = re.split(r'\n\n+', text.strip())[0]
            if len(first_para) < 200 and len(first_para) > 10:
                reasons.append(first_para)

        return list(set(reasons))[:5]

    def _extract_issues_from_text(self, text: str) -> Dict[str, List[str]]:
        """🔥 从文本中提取质量问题"""
        quality_issues = []
        consistency_issues = []

        # 查找质量问题
        quality_patterns = [
            r'(?:质量|文学性|文笔|表达|描写)[^\n]*?(?:问题|不足|缺点|需改进)[：:]\s*([^\n]+)',
            r'(?:故事|情节|人物|对话)[^\n]*?(?:问题|不足|缺点)[：:]\s*([^\n]+)',
        ]

        for pattern in quality_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                issue = match.strip()
                if issue and len(issue) > 3 and issue not in quality_issues:
                    if len(issue) < 200:
                        quality_issues.append(issue)

        # 查找一致性问题
        consistency_patterns = [
            r'(?:一致性|逻辑|矛盾|冲突)[^\n]*?(?:问题|不足|缺点|需改进)[：:]\s*([^\n]+)',
            r'(?:前后|矛盾|不符)[^\n]*?(?:问题|不足)[：:]\s*([^\n]+)',
            r'(?:人物|世界观|设定)[^\n]*?(?:不一致|矛盾|冲突)[^\n]*?(?:[：:])\s*([^\n]+)',
        ]

        for pattern in consistency_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                issue = match.strip()
                if issue and len(issue) > 3 and issue not in consistency_issues:
                    if len(issue) < 200:
                        consistency_issues.append(issue)

        # 查找通用的"问题"列表
        problem_section = re.search(r'(?:问题|不足|缺点)[：:]\s*\n((?:[-•].*\n)+)', text, re.MULTILINE)
        if problem_section:
            for line in problem_section.group(1).split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    issue = line.lstrip('-•*').strip()
                    if issue and len(issue) > 3:
                        # 简单分类：包含"一致"、"逻辑"、"矛盾"的归类为一致性问题
                        if any(kw in issue for kw in ['一致', '逻辑', '矛盾', '前后', '冲突']):
                            if issue not in consistency_issues:
                                consistency_issues.append(issue)
                        else:
                            if issue not in quality_issues:
                                quality_issues.append(issue)

        return {
            "quality": list(set(quality_issues))[:5],
            "consistency": list(set(consistency_issues))[:5]
        }

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
        # 🔥 根据任务类型提供更具体的建议
        task_specific_suggestions = self._get_task_specific_suggestions(task_type, content)

        for criterion in [EvaluationCriterion.CONSISTENCY, EvaluationCriterion.GOAL_ALIGNMENT]:
            if criterion in criteria:
                default_score = 0.7
                dimension_scores[criterion.value] = DimensionScore(
                    dimension=criterion.value,
                    score=default_score,
                    reason="基于规则的默认评估",
                    suggestions=task_specific_suggestions,  # 🔥 使用任务特定的建议
                )
                total_score += default_score * criteria[criterion]
                total_weight += criteria[criterion]

        # Calculate overall score
        overall_score = total_score / total_weight if total_weight > 0 else 0.7

        all_reasons = [f"{d.dimension}: {d.reason}" for d in dimension_scores.values()]
        all_suggestions = []
        for d in dimension_scores.values():
            all_suggestions.extend(d.suggestions)

        # 🔥 更新：使用新的0.8阈值和分别的质量/一致性评分
        # 规则评估无法区分质量和一致性，使用相同分数
        return EvaluationResult(
            passed=overall_score >= self.passing_threshold,  # 🔥 使用配置的阈值
            score=overall_score,
            quality_score=overall_score,
            consistency_score=overall_score,
            dimension_scores=dimension_scores,
            reasons=all_reasons,
            suggestions=all_suggestions,
            quality_issues=[],
            consistency_issues=[],
            evaluator="rule_based",
            metadata={"task_type": task_type},
        )

    def _get_task_evaluation_criteria(self, task_type: str) -> str:
        """
        🔥 根据任务类型返回具体的评估要点
        这些要点会包含在评估提示词中，引导LLM生成更具体的建议
        """
        criteria_map = {
            "创意脑暴": """
**请重点评估以下方面**：
1. **世界观一致性**（最重要！）：是否遵守用户输入中的时代/朝代设定
   - ⛔ 严重错误：宋朝出现秦始皇、唐朝出现朱元璋等跨时代人物
   - ⛔ 严重错误：现代都市设定出现古代人物
   - ⛔ 严重错误：明确朝代设定下出现其他朝代标志性元素
   - ✅ 正确：宋朝故事只有宋朝人物和事件
   - ✅ 正确：现代都市故事符合现代设定

2. **创意独特性**：点子是否有新意，避免套路和俗套
   - 是否拒绝"废柴逆袭""退婚流"等老套路
   - 每个点子是否有自己的"灵魂"

3. **点子多样性**：多个点子之间是否有明显差异
   - 风格是否雷同
   - 人物动机是否复杂
   - 冲突是否新颖

4. **完整性**：每个点子是否包含核心概念、冲突、情感钩子
5. **可行性**：创意是否可以被扩展成完整故事

**常见严重问题**（直接判为不通过）：
- ❌ 跨时代错误：宋朝故事出现秦始皇、唐朝出现朱元璋
- ❌ 套路重复：3个点子都是"废柴逆袭""打脸复仇"
- ❌ 设定矛盾：现代都市突然出现修仙元素且无解释
""",
            "世界观规则": """
**请重点评估以下方面**：
1. **完整性**：世界观是否包含核心要素（力量体系、世界背景、社会规则等）
2. **自洽性**：规则之间是否存在逻辑矛盾
3. **故事性**：世界观是否服务于故事发展，而非纯设定堆砌
4. **创新性**：是否有独特的创意，而非套用常见套路
5. **可执行性**：设定是否可以被后续内容实际执行

**常见问题示例**：
- ❌ "力量体系很强大" → ✅ "力量体系分5个等级，每级的能力和限制都很明确"
- ❌ "世界观完整" → ✅ "包含3个大陆、5个国家、2种力量体系"
""",
            "人物设计": """
**请重点评估以下方面**：
1. **立体性**：人物是否有鲜明的性格、动机、目标
2. **发展空间**：人物是否有成长和变化的可能性
3. **独特性**：人物是否有独特的特质，而非刻板印象
4. **与世界观的关系**：人物背景是否符合世界观设定
5. **人物关系**：人物之间的关系是否清晰合理

**常见问题示例**：
- ❌ "主角很勇敢" → ✅ "主角为了拯救妹妹而克服恐惧，展现了内在冲突"
- ❌ "人物形象鲜明" → ✅ "主角外表冷漠但内心善良，通过冒险逐渐打开心扉"
""",
            "大纲": """
**请重点评估以下方面**：
1. **结构完整性**：是否有清晰的开端、发展、高潮、结局
2. **情节逻辑**：事件之间是否有合理的因果关系
3. **节奏控制**：情节发展是否张弛有度
4. **吸引力**：是否能持续吸引读者阅读
5. **可执行性**：大纲是否可以被拆分成具体的章节

**常见问题示例**：
- ❌ "情节有趣" → ✅ "第3章的悬念设计很好，但第5-7章节奏过慢"
- ❌ "结构完整" → ✅ "三幕结构清晰，但高潮部分可以更激烈"
""",
            "事件": """
**请重点评估以下方面**：
1. **因果关系**：事件的发生是否有合理的起因
2. **影响深度**：事件是否对后续情节产生实质性影响
3. **冲突性**：事件是否包含足够的戏剧冲突
4. **与人物的关系**：事件是否推动人物发展
5. **与世界观的关系**：事件是否符合世界观规则

**常见问题示例**：
- ❌ "事件精彩" → ✅ "主角与反派的初次冲突暴露了力量体系的限制规则"
- ❌ "情节合理" → ✅ "事件A导致了事件B，符合人物性格和世界观设定"
""",
            "伏笔列表": """
**请重点评估以下方面**：
1. **重要性**：伏笔是否与主线剧情相关
2. **隐蔽性**：伏笔是否足够隐蔽，不会过早暴露
3. **可回收性**：伏笔是否有明确的回收计划
4. **合理性**：伏笔是否符合故事逻辑
5. **分布性**：伏笔是否合理分布，而非集中堆砌

**常见问题示例**：
- ❌ "伏笔巧妙" → ✅ "第3章提到的神秘物品将在第15章揭示其真正用途"
- ❌ "伏笔合理" → ✅ "主角身世的线索分布在第5、8、12章，逐步揭示"
""",
            "章节内容": """
**请重点评估以下方面**：
1. **与大纲的一致性**：内容是否符合章节大纲要求
2. **场景描写**：是否有生动的场景描写
3. **对话质量**：对话是否符合人物性格
4. **情节推进**：是否有效推进故事发展
5. **文笔质量**：语言是否流畅、有感染力

**常见问题示例**：
- ❌ "内容精彩" → ✅ "战斗场景描写紧张激烈，但人物对话略显生硬"
- ❌ "文笔流畅" → ✅ "环境描写细致，但节奏略慢，建议精简中间部分"
""",
            "章节润色": """
**请重点评估以下方面**：
1. **改进效果**：润色是否解决了初稿的问题
2. **语言流畅度**：语言是否更加流畅自然
3. **细节丰富度**：是否增加了有价值的细节
4. **情感共鸣**：是否增强了读者的情感体验
5. **一致性**：是否保持了与前文的一致性

**常见问题示例**：
- ❌ "润色有效" → ✅ "增加了主角内心的矛盾描写，使人物更立体"
- ❌ "文笔提升" → ✅ "对话更自然了，但部分场景描写仍需加强"
""",
            "风格元素": """
**请重点评估以下方面**：
1. **独特性**：风格元素是否具有辨识度
2. **一致性**：风格是否在全书中保持一致
3. **适配性**：风格是否适合故事类型和目标读者
4. **执行性**：风格元素是否能在后续内容中持续执行

**常见问题示例**：
- ❌ "风格独特" → ✅ "使用第一人称视角，语言风格偏向黑色幽默"
- ❌ "风格一致" → ✅ "采用冷硬派侦探小说风格，短句为主，少用形容词"
""",
            "主题确认": """
**请重点评估以下方面**：
1. **清晰度**：主题是否清晰明确
2. **深度**：主题是否有深度和思考价值
3. **可执行性**：主题是否能在故事中得到体现
4. **一致性**：主题是否与世界观、人物、情节相一致

**常见问题示例**：
- ❌ "主题明确" → ✅ "主题是'科技发展与人性的冲突'，通过主角的两难选择体现"
- ❌ "主题深刻" → ✅ "探讨了人工智能是否应该拥有权利，具有现实意义"
""",
            "场景物品": """
**请重点评估以下方面**：
1. **功能性**：场景/物品是否服务于情节或人物发展
2. **描写质量**：描写是否生动具体
3. **一致性**：是否符合世界观设定
4. **象征意义**：是否具有象征或隐喻意义

**常见问题示例**：
- ❌ "场景描写好" → ✅ "废弃实验室场景营造了悬疑氛围，暗示了科技的危险"
- ❌ "物品设定有趣" → ✅ "神秘怀表不仅是关键道具，也象征着时间的流逝"
""",
            "对话检查": """
**请重点评估以下方面**：
1. **人物声音**：每个角色的对话是否符合其性格
2. **自然度**：对话是否自然流畅，像真实对话
3. **信息量**：对话是否传达了必要信息
4. **推动作用**：对话是否推动情节或展现人物

**常见问题示例**：
- ❌ "对话自然" → ✅ "主角的口语化表达符合其出身，但反派过于正式"
- ❌ "对话生动" → ✅ "对话展现了人物关系，但部分台词略显生硬"
""",
        }

        return criteria_map.get(task_type, """
**请重点评估以下方面**：
1. **完整性**：内容是否完整
2. **准确性**：内容是否符合任务要求
3. **质量**：内容质量是否达到可接受水平
4. **一致性**：内容是否与前面内容保持一致
5. **可执行性**：内容是否可以被后续内容使用

**请提供具体的、可操作的建议**，避免模糊的评价。
""")

    def _get_task_specific_suggestions(self, task_type: str, content: str) -> List[str]:
        """🔥 根据任务类型获取具体的改进建议（仅用于规则评估回退）"""
        content_lower = content.lower()
        suggestions = []

        if task_type == "世界观规则":
            suggestions = [
                "请确保世界观规则完整且自洽",
                "力量体系要有明确的规则和限制",
                "世界背景要与故事类型相符",
                "避免规则之间的矛盾"
            ]
            # 检查内容是否过短
            if len(content) < 300:
                suggestions.append("世界观规则过于简单，请详细展开")
            # 检查是否包含关键要素
            required_keywords = ["力量", "规则", "限制", "世界"]
            for keyword in required_keywords:
                if keyword not in content_lower:
                    suggestions.append(f"请补充关于{keyword}的设定")
                    break

        elif task_type == "人物设计":
            suggestions = [
                "请确保人物性格鲜明且有发展空间",
                "人物背景要与世界观相符",
                "人物关系要清晰合理",
                "主角要有明确的动机和目标"
            ]
            if len(content) < 300:
                suggestions.append("人物描述过于简单，请补充更多细节")
            # 检查是否包含关键要素
            required_keywords = ["性格", "背景", "动机", "目标"]
            for keyword in required_keywords:
                if keyword not in content_lower:
                    suggestions.append(f"请补充人物的{keyword}")
                    break

        elif task_type == "大纲":
            suggestions = [
                "请确保大纲结构完整",
                "情节发展要合乎逻辑",
                "要有明确的三幕结构",
                "高潮部分要足够精彩"
            ]
            # 检查章节结构
            chapter_count = len(re.findall(r"第[一二三四五六七八九十\d]+章", content))
            if chapter_count < 3:
                suggestions.append("大纲结构过于简单，请详细规划各章节内容")

        elif task_type == "事件":
            suggestions = [
                "请确保事件与世界观和人物相符",
                "事件要有起承转合",
                "事件之间要有逻辑关联",
                "重要事件要有伏笔铺垫"
            ]

        elif task_type == "伏笔列表":
            suggestions = [
                "伏笔要与主线剧情相关",
                "伏笔要有明确的回收计划",
                "伏笔分布要合理，不要集中",
                "重要伏笔要在早期埋设"
            ]

        elif task_type in ["章节内容", "章节润色"]:
            suggestions = [
                "请确保章节内容与大纲一致",
                "注意人物性格和对话的一致性",
                "场景描写要生动具体",
                "章节结尾要有吸引力"
            ]

        else:
            suggestions = [
                "请根据任务要求重新生成内容",
                "确保内容符合创作目标",
                "注意与前面内容的一致性"
            ]

        return suggestions[:8]  # 限制数量

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
