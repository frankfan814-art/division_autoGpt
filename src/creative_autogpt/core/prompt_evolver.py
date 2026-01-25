"""
Prompt Evolver - 提示词自我迭代进化系统

根据评估结果自动优化提示词，实现自我学习和改进。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class PromptVersion:
    """提示词版本"""
    task_type: str
    version: int
    prompt_template: str
    avg_score: float
    usage_count: int
    improvements: List[str]  # 相比上一版本的改进点
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "version": self.version,
            "prompt_template": self.prompt_template,
            "avg_score": self.avg_score,
            "usage_count": self.usage_count,
            "improvements": self.improvements,
            "created_at": self.created_at,
        }


@dataclass
class PromptPerformance:
    """提示词性能记录"""
    task_type: str
    prompt_version: int
    score: float
    feedback: List[str]  # 改进建议
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PromptEvolver:
    """
    提示词进化器
    
    功能：
    1. 记录每个提示词版本的表现
    2. 根据评估反馈自动优化提示词
    3. A/B 测试不同版本的提示词
    4. 保留最佳版本
    """
    
    # 提示词优化触发阈值
    OPTIMIZATION_THRESHOLD = 10  # 收集10次评估后考虑优化
    SCORE_THRESHOLD = 75  # 低于75分触发优化
    
    def __init__(
        self,
        llm_client=None,
        data_dir: Optional[str] = None,
    ):
        """
        初始化提示词进化器
        
        Args:
            llm_client: LLM客户端
            data_dir: 数据存储目录
        """
        self.llm_client = llm_client
        
        # 设置数据目录
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path.cwd() / "data" / "prompt_evolution"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前活跃的提示词版本
        self.active_prompts: Dict[str, PromptVersion] = {}
        
        # 所有版本历史
        self.version_history: Dict[str, List[PromptVersion]] = {}
        
        # 性能记录
        self.performance_records: Dict[str, List[PromptPerformance]] = {}
        
        # 加载数据
        self._load_data()
        
        logger.info(f"PromptEvolver initialized, data dir: {self.data_dir}")
    
    def _load_data(self) -> None:
        """加载保存的数据"""
        # 加载活跃提示词
        active_file = self.data_dir / "active_prompts.json"
        if active_file.exists():
            try:
                with open(active_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_type, prompt_data in data.items():
                        self.active_prompts[task_type] = PromptVersion(**prompt_data)
                logger.info(f"Loaded {len(self.active_prompts)} active prompts")
            except Exception as e:
                logger.warning(f"Failed to load active prompts: {e}")
        
        # 加载性能记录
        perf_file = self.data_dir / "performance_records.json"
        if perf_file.exists():
            try:
                with open(perf_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_type, records in data.items():
                        self.performance_records[task_type] = [
                            PromptPerformance(**r) for r in records
                        ]
            except Exception as e:
                logger.warning(f"Failed to load performance records: {e}")
    
    def _save_data(self) -> None:
        """保存数据"""
        # 保存活跃提示词
        active_file = self.data_dir / "active_prompts.json"
        try:
            with open(active_file, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.to_dict() for k, v in self.active_prompts.items()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"Failed to save active prompts: {e}")
        
        # 保存性能记录（只保留最近100条）
        perf_file = self.data_dir / "performance_records.json"
        try:
            with open(perf_file, "w", encoding="utf-8") as f:
                data = {}
                for task_type, records in self.performance_records.items():
                    data[task_type] = [
                        {
                            "task_type": r.task_type,
                            "prompt_version": r.prompt_version,
                            "score": r.score,
                            "feedback": r.feedback,
                            "timestamp": r.timestamp,
                        }
                        for r in records[-100:]
                    ]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save performance records: {e}")
    
    def save_all_data(self) -> None:
        """保存所有数据（公共方法）"""
        self._save_data()
    
    def record_performance(
        self,
        task_type: str,
        score: float,
        feedback: str,
        prompt: Optional[str] = None,
    ) -> None:
        """
        记录提示词的表现
        
        Args:
            task_type: 任务类型
            score: 评估分数
            feedback: 改进建议（字符串格式）
            prompt: 使用的提示词（可选，用于后续分析）
        """
        # 获取当前版本
        current_version = 1
        if task_type in self.active_prompts:
            current_version = self.active_prompts[task_type].version
        
        # 将字符串格式的 feedback 转换为列表
        feedback_list = [feedback] if isinstance(feedback, str) else feedback
        
        # 记录性能
        record = PromptPerformance(
            task_type=task_type,
            prompt_version=current_version,
            score=score,
            feedback=feedback_list,
        )
        
        if task_type not in self.performance_records:
            self.performance_records[task_type] = []
        self.performance_records[task_type].append(record)
        
        # 更新活跃提示词的统计
        if task_type in self.active_prompts:
            prompt = self.active_prompts[task_type]
            prompt.usage_count += 1
            # 更新平均分（指数移动平均）
            alpha = 0.2
            prompt.avg_score = alpha * score + (1 - alpha) * prompt.avg_score
        
        self._save_data()
        
        logger.debug(f"Recorded performance for {task_type}: score={score}")
    
    def should_evolve(self, task_type: str) -> bool:
        """
        判断是否应该进化提示词
        
        Args:
            task_type: 任务类型
            
        Returns:
            是否应该进化
        """
        if task_type not in self.performance_records:
            return False
        
        records = self.performance_records[task_type]
        
        # 检查是否有足够的数据
        if len(records) < self.OPTIMIZATION_THRESHOLD:
            return False
        
        # 计算最近的平均分
        recent_records = records[-self.OPTIMIZATION_THRESHOLD:]
        avg_score = sum(r.score for r in recent_records) / len(recent_records)
        
        # 如果平均分低于阈值，需要优化
        if avg_score < self.SCORE_THRESHOLD:
            logger.info(f"Task {task_type} needs optimization: avg_score={avg_score:.1f}")
            return True
        
        return False
    
    async def evolve_prompt(
        self,
        task_type: str,
        current_prompt: str,
        force: bool = False,
    ) -> Tuple[str, List[str]]:
        """
        进化提示词
        
        Args:
            task_type: 任务类型
            current_prompt: 当前提示词
            force: 是否强制进化
            
        Returns:
            (新提示词, 改进点列表)
        """
        if not self.llm_client:
            return current_prompt, []
        
        if not force and not self.should_evolve(task_type):
            return current_prompt, []
        
        # 收集反馈
        feedback_list = []
        if task_type in self.performance_records:
            for record in self.performance_records[task_type][-20:]:
                feedback_list.extend(record.feedback)
        
        # 去重并统计频率
        from collections import Counter
        feedback_counts = Counter(feedback_list)
        top_feedback = [f for f, _ in feedback_counts.most_common(10)]
        
        # 构建优化提示词
        prompt = self._build_evolution_prompt(task_type, current_prompt, top_feedback)
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="提示词优化",
                temperature=0.7,
                max_tokens=4000,
            )
            
            new_prompt, improvements = self._parse_evolution_response(response.content)
            
            if new_prompt:
                # 保存新版本
                self._save_new_version(task_type, new_prompt, improvements)
                logger.info(f"Evolved prompt for {task_type}, improvements: {improvements}")
                return new_prompt, improvements
            
        except Exception as e:
            logger.error(f"Failed to evolve prompt: {e}")
        
        return current_prompt, []
    
    def _build_evolution_prompt(
        self,
        task_type: str,
        current_prompt: str,
        feedback: List[str],
    ) -> str:
        """构建提示词优化的提示"""
        
        feedback_text = "\n".join([f"- {f}" for f in feedback])
        
        return f"""## 任务：优化提示词

你是一个提示词工程专家。请根据用户反馈，优化以下提示词。

### 当前提示词
```
{current_prompt[:3000]}
```

### 用户反馈（按频率排序）
{feedback_text}

### 优化目标

1. **解决用户反馈中的问题**
2. **保持提示词的核心功能**
3. **让生成的内容更加**：
   - 通俗易懂（白话文）
   - 有故事性和吸引力
   - 避免学术化
   - 符合小说的风格

### 优化原则

1. 不要过度修改，只针对反馈中的问题进行优化
2. 保留原有提示词中有效的部分
3. 增加更明确的约束和示例
4. 使用更具体、更易懂的指令

### 输出格式

请输出优化后的提示词，并列出改进点：

```
【改进点】
1. ...
2. ...
3. ...

【优化后的提示词】
...
```
"""
    
    def _parse_evolution_response(self, response: str) -> Tuple[Optional[str], List[str]]:
        """解析进化响应"""
        improvements = []
        new_prompt = None
        
        try:
            # 提取改进点
            if "【改进点】" in response:
                imp_start = response.find("【改进点】") + len("【改进点】")
                imp_end = response.find("【优化后的提示词】")
                if imp_end > imp_start:
                    imp_text = response[imp_start:imp_end].strip()
                    improvements = [
                        line.strip().lstrip("0123456789.-) ")
                        for line in imp_text.split("\n")
                        if line.strip() and not line.strip().startswith("【")
                    ]
            
            # 提取新提示词
            if "【优化后的提示词】" in response:
                prompt_start = response.find("【优化后的提示词】") + len("【优化后的提示词】")
                new_prompt = response[prompt_start:].strip()
                
                # 清理可能的代码块标记
                if new_prompt.startswith("```"):
                    new_prompt = new_prompt[3:]
                if new_prompt.endswith("```"):
                    new_prompt = new_prompt[:-3]
                new_prompt = new_prompt.strip()
                
        except Exception as e:
            logger.warning(f"Failed to parse evolution response: {e}")
        
        return new_prompt, improvements
    
    def _save_new_version(
        self,
        task_type: str,
        new_prompt: str,
        improvements: List[str],
    ) -> None:
        """保存新版本"""
        # 获取当前版本号
        current_version = 0
        if task_type in self.active_prompts:
            current_version = self.active_prompts[task_type].version
        
        new_version = PromptVersion(
            task_type=task_type,
            version=current_version + 1,
            prompt_template=new_prompt,
            avg_score=75.0,  # 初始分数
            usage_count=0,
            improvements=improvements,
        )
        
        # 保存到历史
        if task_type not in self.version_history:
            self.version_history[task_type] = []
        self.version_history[task_type].append(new_version)
        
        # 设为活跃版本
        self.active_prompts[task_type] = new_version
        
        # 保存历史版本文件
        history_file = self.data_dir / f"{task_type}_history.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(
                    [v.to_dict() for v in self.version_history[task_type]],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"Failed to save version history: {e}")
        
        self._save_data()
    
    def get_best_prompt(self, task_type: str) -> Optional[str]:
        """
        获取任务类型的最佳提示词
        
        Args:
            task_type: 任务类型
            
        Returns:
            最佳提示词模板，如果没有则返回 None
        """
        if task_type in self.active_prompts:
            return self.active_prompts[task_type].prompt_template
        return None
    
    def get_evolution_stats(self, task_type: str) -> Dict[str, Any]:
        """
        获取提示词进化统计
        
        Args:
            task_type: 任务类型
            
        Returns:
            统计信息
        """
        stats = {
            "task_type": task_type,
            "current_version": 0,
            "total_versions": 0,
            "avg_score": 0,
            "usage_count": 0,
            "recent_improvements": [],
        }
        
        if task_type in self.active_prompts:
            prompt = self.active_prompts[task_type]
            stats["current_version"] = prompt.version
            stats["avg_score"] = round(prompt.avg_score, 1)
            stats["usage_count"] = prompt.usage_count
            stats["recent_improvements"] = prompt.improvements
        
        if task_type in self.version_history:
            stats["total_versions"] = len(self.version_history[task_type])
        
        return stats


# 全局实例（延迟初始化）
_prompt_evolver: Optional[PromptEvolver] = None


def get_prompt_evolver(llm_client=None) -> PromptEvolver:
    """获取全局 PromptEvolver 实例"""
    global _prompt_evolver
    if _prompt_evolver is None:
        _prompt_evolver = PromptEvolver(llm_client=llm_client)
    return _prompt_evolver
