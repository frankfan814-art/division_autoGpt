"""
Self Evaluator - 自我评估系统

用 LLM 评估生成的内容质量，并给出改进建议。
支持记录评估历史，用于提示词自我迭代优化。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class EvaluationResult:
    """评估结果"""
    task_type: str
    overall_score: float  # 0-100
    dimensions: Dict[str, float]  # 各维度评分
    strengths: List[str]  # 优点
    weaknesses: List[str]  # 缺点
    suggestions: List[str]  # 改进建议
    prompt_improvements: List[str]  # 提示词改进建议
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
            "prompt_improvements": self.prompt_improvements,
            "timestamp": self.timestamp,
        }


class SelfEvaluator:
    """
    内容自我评估器
    
    功能：
    1. 评估生成内容的质量
    2. 给出改进建议
    3. 提供提示词优化建议
    4. 记录评估历史用于学习
    """
    
    # 评估维度定义
    EVALUATION_DIMENSIONS = {
        "coherence": "关联性 - 与前置任务的关联是否紧密，是否服务于整体故事",
        "readability": "可读性 - 内容是否通俗易懂、白话文",
        "storytelling": "故事性 - 是否有吸引力、有代入感、像个会讲故事的人写的",
        "consistency": "一致性 - 与前文设定是否一致，有没有自相矛盾",
        "creativity": "创意性 - 是否有新意、不落俗套、有独特的想法",
        "completeness": "完整性 - 是否覆盖了要求的所有内容",
        "structure": "结构性 - 组织是否清晰、逻辑是否通顺",
        "literary": "文学性 - 是否像小说而不是论文，有温度有画面",
    }
    
    # 任务类型特定的评估重点
    TASK_EVALUATION_FOCUS = {
        "创意脑暴": ["creativity", "storytelling", "completeness"],
        "故事核心": ["coherence", "storytelling", "completeness"],
        "风格元素": ["coherence", "readability", "completeness", "literary"],
        "主题确认": ["coherence", "readability", "storytelling", "completeness"],
        "人物设计": ["coherence", "creativity", "completeness", "consistency", "literary"],
        "世界观规则": ["coherence", "readability", "creativity", "completeness"],
        "大纲": ["coherence", "structure", "completeness", "storytelling"],
        "章节大纲": ["coherence", "structure", "consistency", "completeness"],
        "章节内容": ["coherence", "readability", "storytelling", "creativity", "consistency", "literary"],
    }
    
    def __init__(
        self,
        llm_client=None,
        history_dir: Optional[str] = None,
    ):
        """
        初始化评估器
        
        Args:
            llm_client: LLM客户端，用于评估
            history_dir: 评估历史存储目录
        """
        self.llm_client = llm_client
        
        # 设置历史目录
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            self.history_dir = Path.cwd() / "data" / "evaluation_history"
        
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载历史评估数据
        self.evaluation_history: List[EvaluationResult] = []
        self._load_history()
        
        logger.info(f"SelfEvaluator initialized, history dir: {self.history_dir}")
    
    def _load_history(self) -> None:
        """加载历史评估数据"""
        history_file = self.history_dir / "evaluation_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        self.evaluation_history.append(EvaluationResult(**item))
                logger.info(f"Loaded {len(self.evaluation_history)} evaluation records")
            except Exception as e:
                logger.warning(f"Failed to load evaluation history: {e}")
    
    def _save_history(self) -> None:
        """保存评估历史"""
        history_file = self.history_dir / "evaluation_history.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(
                    [r.to_dict() for r in self.evaluation_history[-1000:]],  # 只保留最近1000条
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"Failed to save evaluation history: {e}")
    
    async def evaluate(
        self,
        content: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
        goal: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        评估生成的内容
        
        Args:
            content: 生成的内容
            task_type: 任务类型
            context: 上下文信息
            goal: 创作目标
            
        Returns:
            EvaluationResult 评估结果
        """
        if not self.llm_client:
            return self._basic_evaluation(content, task_type)
        
        # 构建评估提示词
        prompt = self._build_evaluation_prompt(content, task_type, context, goal)
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="评估",
                temperature=0.3,  # 低温度，更稳定的评估
                max_tokens=2000,
            )
            
            result = self._parse_evaluation_response(response.content, task_type)
            
            # 保存到历史
            self.evaluation_history.append(result)
            self._save_history()
            
            return result
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return self._basic_evaluation(content, task_type)
    
    def _build_evaluation_prompt(
        self,
        content: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
        goal: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建评估提示词 - 顶级作家视角"""
        
        # 获取该任务类型的评估重点
        focus_dimensions = self.TASK_EVALUATION_FOCUS.get(
            task_type, 
            list(self.EVALUATION_DIMENSIONS.keys())
        )
        
        dimensions_desc = "\n".join([
            f"- {dim}: {self.EVALUATION_DIMENSIONS[dim]}"
            for dim in focus_dimensions
        ])
        
        goal_info = ""
        if goal:
            goal_info = f"""
### 创作目标
- 类型: {goal.get('genre', '未知')}
- 字数: {goal.get('word_count', '未知')}
- 章节: {goal.get('chapter_count', '未知')}
- 风格: {goal.get('style', '未知')}
"""

        # 构建前置任务上下文（用于检查关联性）
        context_summary = ""
        if context and isinstance(context, dict):
            recent = context.get('recent_results', [])
            if recent:
                context_summary = "\n### 前置任务成果\n"
                for r in recent[-3:]:  # 最近3个任务
                    context_summary += f"- **{r.get('task_type', '未知')}**: {r.get('content', '')[:200]}...\n"

        prompt = f"""## 顶级作家评估

🎭 **角色设定**：你现在是一位获得过茅盾文学奖、雨果奖的顶级作家，同时也是资深出版社编辑。
你见过太多平庸的作品，对好作品有极高的标准。

### 你的评估原则

作为顶级作家，你知道：
1. **人物是灵魂**：没有活的人物，故事就是死的
2. **故事核心要清晰**：读者在任何时候都要知道"这个故事讲什么"
3. **每个任务都要服务整体**：各部分之间必须紧密关联，不能各自为政
4. **通俗不等于肤浅**：最好的故事人人都看得懂，但有深度
5. **拒绝学术腔**：小说不是论文，要有温度、有画面

### 任务类型
{task_type}
{goal_info}
{context_summary}

### 待评估内容
```
{content[:5000]}  
```
{f'（内容过长，已截断，共{len(content)}字）' if len(content) > 5000 else ''}

### 评估维度
{dimensions_desc}

### 评估要点

**作为顶级作家，你要特别关注：**

1. **与前置任务的关联性**（非常重要！）
   - 当前内容是否充分利用了前面任务的成果？
   - 是否与整体故事核心保持一致？
   - 有没有"另起炉灶"、脱离前文的问题？

2. **内容质量**
   - 是否有血有肉，而不是干巴巴的清单？
   - 是否像个会讲故事的人写的，而不是AI生成的模板？
   - 读者会被吸引吗？

3. **专业性**
   - 是否避免了学术论文腔？
   - 是否做到了"通俗易懂"？
   - 是否有小说家的笔触？

### 输出格式

请以 JSON 格式输出：

```json
{{
  "overall_score": 85,
  "dimensions": {{
    "readability": 80,
    "storytelling": 90,
    ...
  }},
  "strengths": [
    "优点1",
    "优点2"
  ],
  "weaknesses": [
    "缺点1",
    "缺点2"
  ],
  "suggestions": [
    "内容改进建议1",
    "内容改进建议2"
  ],
  "prompt_improvements": [
    "提示词改进建议1：...",
    "提示词改进建议2：..."
  ]
}}
```

请直接输出 JSON，不要其他内容。
"""
        return prompt
    
    def _parse_evaluation_response(
        self, 
        response: str, 
        task_type: str
    ) -> EvaluationResult:
        """解析评估响应"""
        try:
            # 提取 JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                return EvaluationResult(
                    task_type=task_type,
                    overall_score=data.get("overall_score", 70),
                    dimensions=data.get("dimensions", {}),
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    suggestions=data.get("suggestions", []),
                    prompt_improvements=data.get("prompt_improvements", []),
                )
        except Exception as e:
            logger.warning(f"Failed to parse evaluation response: {e}")
        
        return self._basic_evaluation("", task_type)
    
    def _basic_evaluation(self, content: str, task_type: str) -> EvaluationResult:
        """基础评估（不使用 LLM）"""
        # 简单的基于规则的评估
        score = 70
        strengths = []
        weaknesses = []
        suggestions = []
        
        # 检查长度
        if len(content) > 500:
            strengths.append("内容有一定篇幅")
        else:
            weaknesses.append("内容较短")
            suggestions.append("增加更多细节")
        
        # 检查是否有学术化倾向
        academic_words = ["综上所述", "本文", "研究表明", "数据显示", "实验证明"]
        if any(word in content for word in academic_words):
            weaknesses.append("存在学术化表达")
            suggestions.append("使用更通俗的语言")
        
        return EvaluationResult(
            task_type=task_type,
            overall_score=score,
            dimensions={},
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            prompt_improvements=[],
        )
    
    def get_improvement_insights(self, task_type: str) -> Dict[str, Any]:
        """
        根据历史评估数据，获取改进洞察
        
        Args:
            task_type: 任务类型
            
        Returns:
            改进洞察
        """
        # 筛选该任务类型的历史数据
        task_history = [
            r for r in self.evaluation_history 
            if r.task_type == task_type
        ]
        
        if not task_history:
            return {
                "message": "暂无历史数据",
                "optimization_recommended": False,
            }
        
        # 计算平均分
        avg_score = sum(r.overall_score for r in task_history) / len(task_history)
        
        # 收集所有弱点和建议
        all_weaknesses = []
        all_improvements = []
        for r in task_history[-20:]:  # 最近20条
            all_weaknesses.extend(r.weaknesses)
            all_improvements.extend(r.prompt_improvements)
        
        # 统计最常见的问题
        from collections import Counter
        weakness_counts = Counter(all_weaknesses)
        improvement_counts = Counter(all_improvements)
        
        # 判断是否应该触发优化
        # 条件：至少10条评估记录，且平均分低于75
        optimization_recommended = (
            len(task_history) >= 10 and avg_score < 75
        )
        
        # 判断趋势
        trend = "stable"
        if len(task_history) > 5:
            recent_avg = sum(r.overall_score for r in task_history[-5:]) / 5
            if recent_avg > avg_score + 5:
                trend = "improving"
            elif recent_avg < avg_score - 5:
                trend = "declining"
        
        return {
            "task_type": task_type,
            "total_evaluations": len(task_history),
            "average_score": round(avg_score, 1),
            "common_weaknesses": weakness_counts.most_common(5),
            "common_improvements": improvement_counts.most_common(5),
            "trend": trend,
            "optimization_recommended": optimization_recommended,
        }
