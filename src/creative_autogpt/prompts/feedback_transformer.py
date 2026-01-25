"""
Feedback Transformer - Transforms user feedback into prompt modifications

Converts casual user feedback into structured prompt improvements.
"""

from typing import Any, Dict, List, Optional

from loguru import logger


class FeedbackTransformer:
    """
    Transforms user feedback into professional prompt modifications

    Converts casual user feedback like "主角太软弱" into structured
    prompt modifications that guide LLM to make specific improvements.
    """

    # Common feedback patterns and their transformations
    FEEDBACK_PATTERNS = {
        # Character-related feedback
        "主角.*太.*弱": {
            "issue": "主角性格不够强势",
            "direction": "增强主角的主角气场和决断力",
            "suggestions": [
                "增加主角主动做决策的情节",
                "让主角在关键时刻展现霸气",
                "减少犹豫和依赖他人的描写",
                "增加主角的内心强大描写",
            ],
        },
        "主角.*太.*强": {
            "issue": "主角过于强大，缺乏成长空间",
            "direction": "适当增加主角的挫折和成长",
            "suggestions": [
                "设置主角能力无法解决的困境",
                "增加主角内心的矛盾和挣扎",
                "让主角经历失败并从中学习",
                "平衡主角与配角的实力对比",
            ],
        },
        "人物.*不.*生动": {
            "issue": "人物形象单薄",
            "direction": "增加人物细节描写和个性特征",
            "suggestions": [
                "增加人物的外貌和动作细节",
                "通过对话展现人物性格",
                "增加人物的心理活动描写",
                "设置人物习惯性语言或动作",
            ],
        },

        # Plot-related feedback
        "情节.*太.*慢": {
            "issue": "故事节奏拖沓",
            "direction": "加快情节推进速度",
            "suggestions": [
                "减少冗长的环境描写",
                "增加冲突和转折",
                "快速推进主线剧情",
                "减少不必要的支线",
            ],
        },
        "情节.*太.*快": {
            "issue": "情节发展过快",
            "direction": "放慢节奏，增加铺垫",
            "suggestions": [
                "增加场景和对话描写",
                "深化人物关系发展",
                "增加情节铺垫和伏笔",
                "扩展关键情节的细节",
            ],
        },
        "逻辑.*问题": {
            "issue": "情节存在逻辑漏洞",
            "direction": "修复逻辑问题，确保合理性",
            "suggestions": [
                "检查因果关系是否合理",
                "确保人物行为符合其性格",
                "检查时间线是否连贯",
                "补充必要的过渡说明",
            ],
        },

        # Writing quality feedback
        "文笔.*差": {
            "issue": "文字表达需要改进",
            "direction": "提升文笔质量",
            "suggestions": [
                "使用更生动的词汇和比喻",
                "增加感官细节描写",
                "优化句式结构",
                "增强情感表达力度",
            ],
        },
        "对话.*不.*自然": {
            "issue": "人物对话不够自然",
            "direction": "使对话更符合人物身份和场景",
            "suggestions": [
                "根据人物性格设计对话风格",
                "增加口语化表达",
                "减少生硬的说教式对话",
                "通过对话展现情节而非说明",
            ],
        },
    }

    def __init__(self):
        """Initialize feedback transformer"""
        logger.info("FeedbackTransformer initialized")

    async def transform(
        self,
        feedback: str,
        task_type: str,
        current_content: str,
        context: Optional[Dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
    ) -> str:
        """
        Transform user feedback into prompt modification

        Args:
            feedback: User's feedback (e.g., "主角太软弱了")
            task_type: Type of task being modified
            current_content: Current content being modified
            context: Additional context (genre, characters, etc.)
            llm_client: Optional LLM client for intelligent transformation

        Returns:
            Transformed prompt instruction
        """
        # Try pattern matching first
        pattern_result = self._match_patterns(feedback, context)
        if pattern_result:
            return self._format_instruction(pattern_result, current_content)

        # Use LLM for transformation if available
        if llm_client:
            return await self._llm_transform(
                feedback,
                task_type,
                current_content,
                context,
                llm_client,
            )

        # Fallback to basic transformation
        return self._basic_transformation(feedback, current_content)

    def _match_patterns(
        self,
        feedback: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Try to match feedback against known patterns"""
        import re

        for pattern, result in self.FEEDBACK_PATTERNS.items():
            if re.search(pattern, feedback):
                return result

        return None

    def _format_instruction(
        self,
        pattern_result: Dict[str, Any],
        current_content: str,
    ) -> str:
        """Format pattern result into instruction"""
        instruction = f"""## 修改要求

### 问题识别
{pattern_result['issue']}

### 修改方向
{pattern_result['direction']}

### 具体建议
"""

        for i, suggestion in enumerate(pattern_result['suggestions'], 1):
            instruction += f"{i}. {suggestion}\n"

        instruction += """
### 实施要求
1. 保持原有结构和核心情节
2. 针对上述问题进行修改
3. 确保修改后与整体风格一致
4. 不要添加新的无关情节

请直接输出修改后的内容。
"""

        return instruction

    async def _llm_transform(
        self,
        feedback: str,
        task_type: str,
        current_content: str,
        context: Optional[Dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
    ) -> str:
        """Use LLM to transform feedback"""
        import json

        context_section = ""
        if context:
            context_section = f"\n### 上下文信息\n```json\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```\n"

        prompt = f"""## 任务: 反馈意见转换

请将用户的反馈意见转换为专业的修改指令。

### 任务类型
{task_type}

### 用户反馈
{feedback}
{context_section}
### 当前内容（前500字）
```
{current_content[:500]}
```

### 输出要求

请分析用户反馈并输出具体的修改指令，包含以下部分：

1. **问题识别**: 明确指出问题所在
2. **修改方向**: 具体的改进方向
3. **实施建议**: 3-5条可操作的修改建议
4. **注意事项**: 修改时需要注意的点

请以清晰的结构输出修改指令，不要输出修改后的内容。
"""

        try:
            response = await llm_client.generate(
                prompt=prompt,
                task_type="修订",
                temperature=0.7,
                max_tokens=1500,
            )

            return response.content

        except Exception as e:
            logger.error(f"LLM feedback transformation failed: {e}")
            return self._basic_transformation(feedback, current_content)

    def _basic_transformation(
        self,
        feedback: str,
        current_content: str,
    ) -> str:
        """Basic feedback transformation without LLM"""
        return f"""## 修改要求

### 用户反馈
{feedback}

### 修改要求
1. 针对上述反馈意见进行修改
2. 保持原有的结构和核心情节
3. 确保修改后与整体风格一致
4. 只修改需要改进的部分

请直接输出修改后的内容。
"""

    def add_pattern(
        self,
        pattern: str,
        issue: str,
        direction: str,
        suggestions: List[str],
    ) -> None:
        """
        Add a new feedback pattern

        Args:
            pattern: Regex pattern to match feedback
            issue: Description of the issue
            direction: Modification direction
            suggestions: List of specific suggestions
        """
        self.FEEDBACK_PATTERNS[pattern] = {
            "issue": issue,
            "direction": direction,
            "suggestions": suggestions,
        }
        logger.info(f"Added feedback pattern: {pattern}")

    def get_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get all feedback patterns"""
        return self.FEEDBACK_PATTERNS.copy()
