"""
Loop Engine - Core execution engine for creative writing

Implements the AutoGPT-inspired agent loop:
Think → Plan → Execute → Evaluate → Memory

Coordinates all components for automated novel creation.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from loguru import logger

from creative_autogpt.core.task_planner import (
    TaskPlanner,
    NovelTaskType,
    Task,
)
from creative_autogpt.core.evaluator import (
    EvaluationEngine,
    EvaluationResult,
)
from creative_autogpt.core.vector_memory import (
    VectorMemoryManager,
    MemoryContext,
    MemoryType,
)
from creative_autogpt.core.self_evaluator import SelfEvaluator
from creative_autogpt.core.prompt_evolver import PromptEvolver, get_prompt_evolver
from creative_autogpt.utils.llm_client import (
    MultiLLMClient,
    LLMResponse,
)
from creative_autogpt.storage.vector_store import MemoryType as VectorMemoryType


class ExecutionStatus(str, Enum):
    """Status of loop engine execution"""

    IDLE = "idle"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"  # Waiting for user to approve task result
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ExecutionStats:
    """Statistics about execution"""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    retried_tasks: int = 0
    total_time: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "retried_tasks": self.retried_tasks,
            "total_time": self.total_time,
            "llm_calls": self.llm_calls,
            "tokens_used": self.tokens_used,
        }


@dataclass
class ExecutionResult:
    """Result of loop engine execution"""

    status: ExecutionStatus
    stats: ExecutionStats
    outputs: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "stats": self.stats.to_dict(),
            "outputs": self.outputs,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class LoopEngine:
    """
    Core execution engine for creative writing

    AutoGPT-style agent loop specialized for novel creation:
    1. Plan - Generate task DAG from goals
    2. Execute - Run tasks in dependency order
    3. Evaluate - Assess quality of results
    4. Rewrite - Retry if quality insufficient
    5. Memory - Store results for context
    """

    def __init__(
        self,
        session_id: str,
        llm_client: MultiLLMClient,
        memory: VectorMemoryManager,
        evaluator: EvaluationEngine,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize loop engine

        Args:
            session_id: Unique session identifier
            llm_client: Multi-LLM client for generation
            memory: Vector memory manager
            evaluator: Quality evaluation engine
            config: Optional configuration
        """
        self.session_id = session_id
        self.llm_client = llm_client
        self.memory = memory
        self.evaluator = evaluator
        self.config = config or {}

        # Create task planner
        self.planner = TaskPlanner(config=config)
        
        # 自我评估和提示词进化系统
        self.self_evaluator = SelfEvaluator(llm_client=llm_client)
        self.prompt_evolver = get_prompt_evolver(llm_client=llm_client)
        
        # 是否启用自我进化（默认启用）
        self.enable_self_evolution = config.get('enable_self_evolution', True)

        # Execution state
        self.status = ExecutionStatus.IDLE
        self.is_running = False
        self.is_paused = False
        self.current_task: Optional[Task] = None

        # Approval mode settings (enabled by default to allow user review)
        self.approval_mode = config.get('approval_mode', True)  # Default to require approval
        self.is_waiting_approval = False
        self.approval_result: Optional[Dict[str, Any]] = None
        self._approval_event = asyncio.Event()

        # Statistics
        self.stats = ExecutionStats()
        
        # 🎯 高分内容示例存储（用于后续任务的参考）
        # 结构: {task_type: {genre: {"score": float, "content": str, "reason": str}}}
        self.best_examples: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # 最低高分阈值（只有超过这个分数的内容才会被记录为示例）
        self.high_score_threshold = config.get('high_score_threshold', 85)

        # Event callbacks
        self._on_task_start: Optional[Callable] = None
        self._on_task_complete: Optional[Callable] = None
        self._on_task_fail: Optional[Callable] = None
        self._on_progress: Optional[Callable] = None
        self._on_task_approval_needed: Optional[Callable] = None

        logger.info(f"LoopEngine initialized for session {session_id}")

    def set_callbacks(
        self,
        on_task_start: Optional[Callable] = None,
        on_task_complete: Optional[Callable] = None,
        on_task_fail: Optional[Callable] = None,
        on_progress: Optional[Callable] = None,
        on_task_approval_needed: Optional[Callable] = None,
    ) -> None:
        """Set event callbacks for execution monitoring"""
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_task_fail = on_task_fail
        self._on_progress = on_progress
        self._on_task_approval_needed = on_task_approval_needed

    async def run(
        self,
        goal: Dict[str, Any],
        chapter_count: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Main execution loop

        Args:
            goal: Creation goal with style, theme, length, etc.
            chapter_count: Number of chapters to create

        Returns:
            ExecutionResult with outputs and statistics
        """
        start_time = time.time()
        started_at = datetime.utcnow()

        self.status = ExecutionStatus.RUNNING
        self.is_running = True
        self.stats = ExecutionStats()

        logger.info(f"Starting execution for session {self.session_id}")
        logger.info(f"Goal: {goal.get('title', 'Untitled')}")

        try:
            # Phase 1: Planning
            self.status = ExecutionStatus.PLANNING
            logger.info("Planning phase: generating task DAG")

            tasks = await self.planner.plan(
                goal=goal,
                chapter_count=chapter_count,
            )

            self.stats.total_tasks = len(tasks)
            logger.info(f"Generated {len(tasks)} tasks")

            # Phase 2: Execute tasks
            self.status = ExecutionStatus.RUNNING

            while self.is_running:
                # Check for pause
                while self.is_paused:
                    await asyncio.sleep(0.1)
                    if not self.is_running:
                        break

                # Get next task
                task = self.planner.get_next_task()
                if task is None:
                    # Check if all tasks are complete
                    if self.planner.is_complete():
                        logger.info("All tasks completed")
                        break
                    # No ready tasks, wait a bit
                    await asyncio.sleep(0.5)
                    continue

                # Execute task
                await self._execute_task(task, goal)

                # Update progress
                if self._on_progress:
                    progress = self.planner.get_progress()
                    await self._safe_callback(
                        self._on_progress,
                        progress,
                    )

            # Phase 3: Complete
            self.status = ExecutionStatus.COMPLETED
            self.stats.total_time = time.time() - start_time

            result = ExecutionResult(
                status=self.status,
                stats=self.stats,
                outputs=self._collect_outputs(),
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Execution completed: {self.stats.completed_tasks}/{self.stats.total_tasks} tasks, "
                f"{self.stats.total_time:.1f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            self.status = ExecutionStatus.FAILED
            self.stats.total_time = time.time() - start_time

            return ExecutionResult(
                status=self.status,
                stats=self.stats,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

        finally:
            self.is_running = False

    async def _execute_task(
        self,
        task: Task,
        goal: Dict[str, Any],
    ) -> None:
        """
        Execute a single task

        Args:
            task: The task to execute
            goal: Original creation goals
        """
        self.current_task = task
        task.status = "running"
        
        # 🔥 记录任务开始时间（用于统计）
        start_time = datetime.utcnow()
        task.started_at = start_time.isoformat()
        task.metadata["started_at"] = task.started_at
        
        # 🔥 初始化 token 和费用统计
        task_total_tokens = 0
        task_prompt_tokens = 0
        task_completion_tokens = 0
        task_cost = 0.0

        logger.info(f"Executing task {task.task_id}: {task.task_type.value}")

        # Determine which provider will be used (for UI display)
        selected_provider = self.llm_client._select_provider(task.task_type.value)
        task.metadata["llm_provider"] = selected_provider.value

        if self._on_task_start:
            await self._safe_callback(self._on_task_start, task)

        try:
            # 1. Get context from memory
            context = await self.memory.get_context(
                task_id=task.task_id,
                task_type=task.task_type.value,
                chapter_index=task.metadata.get("chapter_index"),
            )

            # 2. Build prompt for the task
            prompt = await self._build_prompt(task, context, goal)

            # 3. Call LLM to generate content
            response = await self.llm_client.generate(
                prompt=prompt,
                task_type=task.task_type.value,
                temperature=self._get_temperature_for_task(task.task_type),
                max_tokens=self._get_max_tokens_for_task(task.task_type),
            )

            # Update actual provider and model used (may differ due to fallback)
            task.metadata["llm_provider"] = response.provider.value
            task.metadata["llm_model"] = response.model

            self.stats.llm_calls += 1
            self.stats.tokens_used += response.usage.total_tokens
            
            # 🔥 累计 token 和费用
            task_total_tokens += response.usage.total_tokens
            task_prompt_tokens += response.usage.prompt_tokens
            task_completion_tokens += response.usage.completion_tokens
            task_cost += self._calculate_cost(response.provider.value, response.model, response.usage)

            # 4. Evaluate quality
            evaluation = await self.evaluator.evaluate(
                task_type=task.task_type.value,
                content=response.content,
                context=context.to_dict(),
                goal=goal,
            )

            # 4.5 总览检查：确保任务输出与前面任务保持一致
            consistency_check = await self._check_task_consistency(
                task=task,
                content=response.content,
                context=context,
                goal=goal,
            )
            
            if not consistency_check.get("passed", True):
                logger.warning(
                    f"Task {task.task_id} failed consistency check: {consistency_check.get('issues', [])}"
                )
                # 将一致性问题添加到评估原因和建议中
                issues = consistency_check.get('issues', [])
                suggestions = consistency_check.get('suggestions', [])
                continuity_issues = consistency_check.get('continuity_issues', [])
                
                # 🔥 将完整的一致性检查结果存储到任务元数据中，供重写时使用
                task.metadata["consistency_check_result"] = consistency_check
                
                # 添加到评估原因（区分一致性问题和连贯性问题）
                if issues:
                    evaluation.reasons.append(f"【一致性问题】{chr(10).join(issues)}")
                if continuity_issues:
                    evaluation.reasons.append(f"【章节连贯性问题】{chr(10).join(continuity_issues)}")
                
                # 添加建议
                if suggestions:
                    evaluation.suggestions.extend(suggestions)
                
                evaluation.passed = False

            # 5. Handle evaluation result
            final_content = response.content
            if not evaluation.passed:
                logger.warning(
                    f"Task {task.task_id} failed evaluation (score: {evaluation.score:.3f})"
                )
                # 🔥 传递当前的 token 统计用于累计
                rewrite_token_stats = {
                    "total_tokens": task_total_tokens,
                    "prompt_tokens": task_prompt_tokens,
                    "completion_tokens": task_completion_tokens,
                    "cost": task_cost,
                }
                final_content, rewrite_token_stats = await self._attempt_rewrite(
                    task=task,
                    content=response.content,
                    evaluation=evaluation,
                    context=context,
                    goal=goal,
                    token_stats=rewrite_token_stats,
                )
                # 🔥 更新统计
                task_total_tokens = rewrite_token_stats["total_tokens"]
                task_prompt_tokens = rewrite_token_stats["prompt_tokens"]
                task_completion_tokens = rewrite_token_stats["completion_tokens"]
                task_cost = rewrite_token_stats["cost"]

            # 6. Store in memory
            memory_type = self._get_memory_type_for_task(task.task_type)
            await self.memory.store(
                content=final_content,
                task_id=task.task_id,
                task_type=task.task_type.value,
                memory_type=memory_type,
                metadata=task.metadata,
                chapter_index=task.metadata.get("chapter_index"),
                evaluation=evaluation.to_dict(),
            )
            
            # 6.5 🎯 检查是否为高分内容，记录为示例
            await self._check_and_save_high_score_example(
                task_type=task.task_type.value,
                genre=goal.get('genre', '通用'),
                content=final_content,
                score=evaluation.score,
                evaluation=evaluation,
            )

            # 7. Check if approval is needed
            # 创意脑暴任务始终需要等待用户选择
            requires_approval = self.approval_mode or task.task_type.value == "创意脑暴"
            
            if requires_approval:
                # 为创意脑暴添加特殊标记，告诉前端需要用户选择点子
                is_brainstorm = task.task_type.value == "创意脑暴"
                
                logger.info(f"Task {task.task_id} waiting for approval" + 
                           (" (requires idea selection)" if is_brainstorm else ""))
                self.status = ExecutionStatus.WAITING_APPROVAL
                self.is_waiting_approval = True
                
                # 设置任务元数据，标记需要选择
                if is_brainstorm:
                    task.metadata["requires_selection"] = True
                    task.metadata["selection_type"] = "idea"
                    task.metadata["selection_count"] = 4  # 4个点子供选择
                
                # Notify frontend that approval is needed
                if self._on_task_approval_needed:
                    await self._safe_callback(
                        self._on_task_approval_needed,
                        task,
                        final_content,
                        evaluation,
                    )
                
                # Wait for approval
                self._approval_event.clear()
                await self._approval_event.wait()
                
                # Check approval result
                if not self.approval_result or self.approval_result.get('action') != 'approve':
                    if self.approval_result and self.approval_result.get('action') == 'reject':
                        # User rejected, mark as failed and skip
                        task.status = "skipped"
                        task.error = "Rejected by user"
                        self.planner.update_task_status(task.task_id, "skipped")
                        self.stats.skipped_tasks += 1
                        self.is_waiting_approval = False
                        self.status = ExecutionStatus.RUNNING
                        return
                    elif self.approval_result and self.approval_result.get('action') == 'regenerate':
                        # User wants to regenerate, retry the task
                        logger.info(f"Regenerating task {task.task_id}")
                        self.is_waiting_approval = False
                        self.status = ExecutionStatus.RUNNING
                        await self._execute_task(task, goal)
                        return
                
                # 处理创意脑暴的点子选择
                if is_brainstorm and self.approval_result:
                    selected_idea = self.approval_result.get('selected_idea')
                    if selected_idea:
                        logger.info(f"User selected idea {selected_idea} for brainstorm task")
                        # 将选择的点子编号存入任务元数据，供后续故事核心任务使用
                        task.metadata["selected_idea"] = selected_idea
                        # 更新内存中的内容，标记选中的点子
                        final_content = f"【用户选择】点子{selected_idea}\n\n{final_content}"
                        # 重新存储更新后的内容
                        await self.memory.store(
                            content=final_content,
                            task_id=task.task_id,
                            task_type=task.task_type.value,
                            memory_type=memory_type,
                            metadata=task.metadata,
                            chapter_index=task.metadata.get("chapter_index"),
                            evaluation=evaluation.to_dict(),
                        )
                
                self.is_waiting_approval = False
                self.status = ExecutionStatus.RUNNING

            # 8. Update task status
            task.status = "completed"
            task.result = final_content
            
            # 🔥 记录任务完成时间和统计信息
            end_time = datetime.utcnow()
            task.completed_at = end_time.isoformat()
            task.execution_time_seconds = (end_time - start_time).total_seconds()
            task.total_tokens = task_total_tokens
            task.prompt_tokens = task_prompt_tokens
            task.completion_tokens = task_completion_tokens
            task.cost_usd = task_cost
            
            # 也更新到 metadata 中（方便前端访问）
            task.metadata["completed_at"] = task.completed_at
            task.metadata["execution_time_seconds"] = task.execution_time_seconds
            task.metadata["total_tokens"] = task.total_tokens
            task.metadata["prompt_tokens"] = task.prompt_tokens
            task.metadata["completion_tokens"] = task.completion_tokens
            task.metadata["cost_usd"] = round(task.cost_usd, 6)
            task.metadata["failed_attempts"] = task.failed_attempts
            
            self.planner.update_task_status(
                task.task_id,
                "completed",
                result=final_content,
            )

            self.stats.completed_tasks += 1

            logger.info(
                f"Task {task.task_id} completed: {len(final_content)} chars, "
                f"tokens: {task_total_tokens}, time: {task.execution_time_seconds:.1f}s, cost: ${task.cost_usd:.4f}"
            )

            # 9. 自我评估和提示词进化（异步执行，不阻塞主流程）
            if self.enable_self_evolution:
                asyncio.create_task(
                    self._self_evolution_pipeline(
                        task=task,
                        content=final_content,
                        prompt=prompt,
                        evaluation_score=evaluation.score,
                        context=context,
                        goal=goal,
                    )
                )

            if self._on_task_complete:
                await self._safe_callback(
                    self._on_task_complete,
                    task,
                    final_content,
                    evaluation,
                )

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)

            task.status = "failed"
            task.error = str(e)
            self.planner.update_task_status(
                task.task_id,
                "failed",
                error=str(e),
            )

            self.stats.failed_tasks += 1

            if self._on_task_fail:
                await self._safe_callback(
                    self._on_task_fail,
                    task,
                    str(e),
                )

            # Check if we should continue on error
            if not self.config.get("continue_on_error", False):
                raise

    async def _self_evolution_pipeline(
        self,
        task: Task,
        content: str,
        prompt: str,
        evaluation_score: float,
        context: MemoryContext,
        goal: Dict[str, Any],
    ) -> None:
        """
        自我进化管道：评估内容质量并优化提示词
        
        这是一个后台任务，不会阻塞主流程。
        
        Pipeline 步骤：
        1. 使用 SelfEvaluator 对生成内容进行深度评估
        2. 将评估结果记录到 PromptEvolver
        3. 如果满足条件，触发提示词优化
        
        Args:
            task: 当前任务
            content: 生成的内容
            prompt: 使用的提示词
            evaluation_score: 初步评估分数
            context: 任务上下文
            goal: 创作目标
        """
        task_type = task.task_type.value
        
        try:
            # 1. 深度自我评估
            logger.info(f"🔍 开始自我评估任务: {task_type}")
            
            self_eval_result = await self.self_evaluator.evaluate(
                task_type=task_type,
                content=content,
                context=context.to_dict() if hasattr(context, 'to_dict') else {},
                goal=goal,
            )
            
            # 2. 记录提示词性能
            # 合并初步评估分数和深度评估分数
            combined_score = (evaluation_score * 0.4 + self_eval_result.overall_score / 100 * 0.6)
            
            # 构建反馈信息
            feedback = self._build_evolution_feedback(self_eval_result)
            
            self.prompt_evolver.record_performance(
                task_type=task_type,
                prompt=prompt,
                score=combined_score * 100,  # 转为百分制
                feedback=feedback,
            )
            
            logger.info(
                f"📊 评估完成: {task_type}, 综合分数: {combined_score * 100:.1f}, "
                f"优点: {len(self_eval_result.strengths)}, 不足: {len(self_eval_result.weaknesses)}"
            )
            
            # 3. 检查是否需要触发提示词优化
            # 只在分数较低时考虑优化
            if combined_score < 0.75:
                logger.info(f"⚠️ {task_type} 任务分数较低 ({combined_score * 100:.1f})，考虑优化提示词")
                
                # 获取改进见解
                insights = self.self_evaluator.get_improvement_insights(task_type)
                
                if insights.get("optimization_recommended"):
                    logger.info(f"🚀 触发提示词优化: {task_type}")
                    await self.prompt_evolver.evolve_prompt(
                        task_type=task_type,
                        current_prompt=prompt,
                    )
            
            # 4. 将评估历史保存（用于后续分析）
            # 评估结果在 evaluate() 方法中已自动保存
            self.prompt_evolver.save_all_data()
            
        except Exception as e:
            # 自我进化失败不应该影响主流程
            logger.warning(f"⚠️ 自我进化管道异常: {e}", exc_info=True)

    def _build_evolution_feedback(self, eval_result) -> str:
        """
        根据评估结果构建进化反馈
        
        Args:
            eval_result: SelfEvaluator 的评估结果
            
        Returns:
            结构化的反馈文本，用于提示词优化
        """
        feedback_parts = []
        
        # 添加维度分数
        if eval_result.dimensions:
            score_summary = "维度分数: " + ", ".join(
                f"{k}={v:.0f}" for k, v in eval_result.dimensions.items()
            )
            feedback_parts.append(score_summary)
        
        # 添加优点（简化）
        if eval_result.strengths:
            feedback_parts.append(f"优点: {'; '.join(eval_result.strengths[:3])}")
        
        # 添加不足（更详细，因为这是需要改进的）
        if eval_result.weaknesses:
            feedback_parts.append(f"不足: {'; '.join(eval_result.weaknesses)}")
        
        # 添加改进建议
        if eval_result.suggestions:
            feedback_parts.append(f"建议: {'; '.join(eval_result.suggestions[:3])}")
        
        return "\n".join(feedback_parts)

    async def _check_task_consistency(
        self,
        task: Task,
        content: str,
        context: MemoryContext,
        goal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        检查任务输出与前面任务的一致性
        使用Qwen的长上下文能力进行全面检查，确保没有偏离已有设定
        
        关键增强：
        1. 利用Qwen 128K上下文能力，带入更多参考内容
        2. 对于章节内容，带入章节大纲和前面章节内容进行对比
        3. 返回详细的问题描述和修改建议
        
        Returns:
            dict with keys: passed (bool), issues (list of str), suggestions (list of str)
        """
        task_type = task.task_type.value
        chapter_index = task.metadata.get("chapter_index", None)
        
        # 不需要一致性检查的任务
        # - 创意脑暴：第一个任务，没有前置内容可参照
        # - 故事核心：基于脑暴结果选择，用户已经手动选择了
        if task_type in ["创意脑暴", "故事核心"]:
            return {"passed": True, "issues": [], "suggestions": []}
        
        # 获取前置任务内容
        predecessor_contents = self._get_predecessor_contents(task_type, context)
        
        if not predecessor_contents:
            return {"passed": True, "issues": [], "suggestions": []}
        
        # 🔥 对于章节相关任务，额外获取章节大纲和前面章节内容
        chapter_context = ""
        if task_type in ["章节内容", "章节润色"] and chapter_index and isinstance(chapter_index, int):
            # 获取前面的章节
            previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=3)
            outline_content = predecessor_contents.get("大纲", "")
            
            # 构建章节上下文（用于一致性检查）
            chapter_context = self._build_consistency_check_context(
                chapter_index,
                previous_chapters,
                outline_content,
                task_type,
            )
        
        # 构建一致性检查提示词
        check_prompt = f"""## 任务一致性检查 🔍

你是一位**顶级畅销小说**的资深编辑，负责确保创作内容的严格一致性。

⚠️ **这是一个关键检查点**：任何与前面任务不一致的内容都会破坏整个故事的完整性！

### 当前任务
- 任务类型：{task_type}
{f"- 章节：第{chapter_index}章" if chapter_index else ""}

### 当前任务的输出内容
```
{content[:8000]}{"..." if len(content) > 8000 else ""}
```

{chapter_context}

### 前面任务的核心成果（必须严格保持一致）
"""
        # 按重要性添加前置内容
        priority_list = ["故事核心", "人物设计", "世界观规则", "风格元素", "大纲", "伏笔列表", "事件", "场景物品冲突"]
        for pred_type in priority_list:
            if pred_type in predecessor_contents:
                pred_content = predecessor_contents[pred_type]
                # 对于关键内容给予更多空间
                max_len = 4000 if pred_type in ["故事核心", "人物设计", "大纲"] else 2000
                check_prompt += f"\n#### {pred_type}\n```\n{pred_content[:max_len]}{'...' if len(pred_content) > max_len else ''}\n```\n"
        
        check_prompt += f"""

### 检查要求（请严格执行！）

请检查当前任务的输出是否与前面的任务**严格保持一致**，重点检查：

1. **故事核心一致性**（最重要！）
   - 是否紧扣【故事核心】中定义的主角目标和核心冲突？
   - 是否服务于故事的核心情感钩子？

2. **人物一致性**
   - 如果涉及人物，是否使用了【人物设计】中已有的角色？
   - 人物的性格、背景、目标是否与设计一致？
   - 有没有凭空出现的新角色（应该避免）？

3. **世界观一致性**
   - 是否符合【世界观规则】中的设定？
   - 有没有违反已设定的规则？
   - 新增的设定是否与已有设定冲突？

4. **风格一致性**
   - 写作风格是否符合【风格元素】的要求？
   - 语言调性是否统一？

5. **主题一致性**
   - 是否围绕【故事核心】和【主题确认】的核心主题展开？
   - 有没有偏离主题、跑题的内容？

6. **逻辑一致性**
   - 与前面的内容是否存在逻辑矛盾？
   - 时间线是否合理？

{f'''7. **章节连贯性**（针对第{chapter_index}章）
   - 本章开头是否自然衔接上一章结尾？
   - 人物状态、位置、情绪是否延续？
   - 时间线是否连贯？
   - 有没有像独立短篇，与前面脱节？
''' if chapter_index and chapter_index > 1 else ''}

### ⚠️ 评判标准（请严格执行）
- 只要发现**任何一个**上述问题，就必须将 `passed` 设为 `false`
- 评分标准：0.9+（完全一致）、0.7-0.9（小问题）、0.7以下（严重问题）
- 章节连贯性问题必须严格判定！脱节的章节必须判为不通过！

### 输出格式
请严格按照以下JSON格式输出：
```json
{{
  "passed": true/false,
  "score": 0.0-1.0,
  "issues": ["具体问题描述1", "具体问题描述2"],
  "suggestions": ["如何修改的具体建议1", "如何修改的具体建议2"],
  "continuity_issues": ["章节连贯性问题1", "章节连贯性问题2"]
}}
```

如果没有发现问题，passed为true，issues为空数组。
如果发现问题，passed为false，列出**具体的**问题和**可操作的**修改建议。

请直接输出JSON，不要有其他内容。
"""
        
        try:
            # 🔥 使用 Qwen-long 进行评估（利用其128K上下文能力）
            # 通过指定 model_type 为 LONG_CONTEXT 来确保使用 Qwen
            response = await self.llm_client.generate(
                prompt=check_prompt,
                task_type="一致性检查",  # 会路由到支持长上下文的模型
                temperature=0.2,  # 降低温度，让检查更严格
                max_tokens=2000,  # 增加token，确保能输出完整的问题描述
            )
            
            # 解析响应
            import json
            import re
            
            # 尝试从响应中提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "passed": result.get("passed", True),
                    "score": result.get("score", 1.0),
                    "issues": result.get("issues", []),
                    "suggestions": result.get("suggestions", []),
                    "continuity_issues": result.get("continuity_issues", []),
                }
            else:
                logger.warning(f"Could not parse consistency check response: {response.content[:200]}")
                return {"passed": True, "issues": [], "suggestions": []}
                
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            # 如果检查失败，默认通过（不阻塞流程）
            return {"passed": True, "issues": [], "suggestions": []}

    def _get_predecessor_contents(
        self,
        task_type: str,
        context: MemoryContext,
    ) -> Dict[str, str]:
        """
        获取当前任务所需的前置任务内容
        
        Args:
            task_type: 当前任务类型
            context: 任务上下文，包含前面任务的结果
            
        Returns:
            前置任务内容的字典，key 是任务类型，value 是任务输出内容
        """
        # 定义每个任务需要的前置任务（布兰登·桑德森式流程）
        # 流程：创意脑暴 → 故事核心 → 大纲 → 世界观规则 → 人物设计 → 主题确认/风格元素 → 市场定位 → 事件 → 场景物品冲突 → 伏笔列表 → 一致性检查
        task_dependencies = {
            # Phase 0: 创意脑暴阶段
            "创意脑暴": [],  # 第一个任务，无依赖
            "故事核心": ["创意脑暴"],  # 必须基于脑暴结果
            
            # Phase 1: 大纲设计（结构优先！）
            "大纲": ["故事核心"],  # 🔥 大纲紧跟故事核心，先搭骨架
            
            # Phase 2: 世界观规则（在人物之前！）
            # 布兰登·桑德森的方法：先建立世界规则，人物才能在规则内行动
            "世界观规则": ["故事核心", "大纲"],  # 世界观服务于大纲
            
            # Phase 3: 人物设计（基于大纲和世界观）
            "人物设计": ["故事核心", "大纲", "世界观规则"],  # 人物在世界规则内完成大纲
            
            # Phase 4: 主题与风格（从故事中提炼）
            "主题确认": ["故事核心", "大纲", "世界观规则", "人物设计"],  # 主题从人物选择中涌现
            "风格元素": ["故事核心", "大纲", "世界观规则", "人物设计"],  # 风格服务于故事
            "市场定位": ["故事核心", "大纲", "人物设计", "风格元素"],  # 综合所有元素
            
            # Phase 5: 细节填充（为大纲添加血肉）
            "事件": ["故事核心", "大纲", "世界观规则", "人物设计", "市场定位"],
            "场景物品冲突": ["故事核心", "大纲", "世界观规则", "人物设计", "事件"],
            "伏笔列表": ["故事核心", "大纲", "人物设计", "事件", "场景物品冲突"],
            
            # Phase 6: 一致性检查
            "一致性检查": ["故事核心", "大纲", "世界观规则", "人物设计", "事件", "场景物品冲突", "伏笔列表"],
            
            # Phase 7: 章节创作 - 🔴 必须包含所有基础设定 + 风格元素！
            # 基础设定 = 故事核心 + 大纲 + 世界观规则 + 人物设计 + 事件 + 场景物品冲突 + 伏笔列表
            # 上一章内容通过 _get_previous_chapters() 单独获取
            "章节大纲": ["故事核心", "大纲", "世界观规则", "人物设计", "风格元素", "事件", "场景物品冲突", "伏笔列表"],
            "场景生成": ["故事核心", "大纲", "世界观规则", "人物设计", "风格元素", "事件", "场景物品冲突", "伏笔列表"],
            "章节内容": ["故事核心", "大纲", "世界观规则", "人物设计", "风格元素", "事件", "场景物品冲突", "伏笔列表"],
            "章节润色": ["故事核心", "大纲", "世界观规则", "人物设计", "风格元素", "事件", "场景物品冲突", "伏笔列表"],
        }
        
        needed_tasks = task_dependencies.get(task_type, [])
        predecessor_contents = {}
        
        # 从 recent_results 中提取前置任务内容
        if context.recent_results:
            for result in context.recent_results:
                result_type = result.get("task_type", "")
                if result_type in needed_tasks:
                    predecessor_contents[result_type] = result.get("content", "")
        
        # 从 relevant_memories 中补充
        if context.relevant_memories:
            for mem in context.relevant_memories:
                # 尝试从 content 中识别任务类型
                mem_type = mem.get("memory_type", "")
                content = mem.get("content", "")
                # 检查是否是需要的任务类型（通过 memory_type 或内容匹配）
                for needed in needed_tasks:
                    if needed not in predecessor_contents and needed.lower() in mem_type.lower():
                        predecessor_contents[needed] = content
        
        return predecessor_contents

    async def _analyze_context_needs(
        self,
        task: Task,
        goal: Dict[str, Any],
        predecessor_contents: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        使用LLM动态分析当前任务需要哪些上下文信息
        
        让LLM自己决定需要参考哪些内容，而不是使用固定规则。
        这样可以更智能地选择相关上下文，避免信息过载。
        
        Args:
            task: 当前任务
            goal: 创作目标
            predecessor_contents: 所有可用的前置任务内容
            
        Returns:
            包含选择的上下文和理由的字典：
            {
                "selected_contexts": ["故事核心", "人物设计", ...],
                "context_focus": {"故事核心": "需要关注主角动机", ...},
                "reasoning": "选择理由"
            }
        """
        task_type = task.task_type.value
        chapter_index = task.metadata.get("chapter_index", None)
        
        # 构建可用上下文列表
        available_contexts = list(predecessor_contents.keys())
        if not available_contexts:
            return {
                "selected_contexts": [],
                "context_focus": {},
                "reasoning": "没有可用的前置任务内容"
            }
        
        # 构建分析提示词
        analysis_prompt = f"""
你是一位经验丰富的小说创作顾问。你正在帮助一位作家完成创作任务。

## 当前任务信息
- **任务类型**: {task_type}
- **章节**: {f"第{chapter_index}章" if chapter_index else "非章节任务"}
- **创作目标**: {goal.get('theme', '未指定主题')}

## 可用的参考资料

以下是你可以参考的前置任务成果（按重要性排序）：

{chr(10).join([f"- **{name}**: {len(content)}字" for name, content in predecessor_contents.items()])}

## 你的任务

请分析当前任务（{task_type}）最需要参考哪些内容，以及需要重点关注什么。

**注意**：
1. 不要选择所有内容！只选择**真正必要**的
2. 对于章节创作，前面章节的内容和大纲是必需的
3. 说明每个选择需要关注的**具体方面**

请用JSON格式输出：
```json
{{
    "selected_contexts": ["需要的内容1", "需要的内容2"],
    "context_focus": {{
        "需要的内容1": "需要关注的具体方面",
        "需要的内容2": "需要关注的具体方面"
    }},
    "reasoning": "为什么选择这些内容的简短理由"
}}
```
"""
        
        try:
            # 使用LLM进行分析
            response = await self.llm_client.generate(
                prompt=analysis_prompt,
                task_type="上下文分析",
                temperature=0.3,  # 低温度，更确定性
                max_tokens=1000,
            )
            
            # 解析JSON响应
            import re
            import json
            
            response_text = response.content  # 从 LLMResponse 对象获取内容
            
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # 尝试直接解析整个响应
                result = json.loads(response_text)
            
            # 验证选择的上下文是否有效
            valid_contexts = [ctx for ctx in result.get("selected_contexts", []) if ctx in predecessor_contents]
            result["selected_contexts"] = valid_contexts
            
            logger.info(f"🧠 动态上下文分析完成: 选择了 {len(valid_contexts)} 个上下文 - {valid_contexts}")
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 动态上下文分析失败，使用默认规则: {e}")
            # 失败时返回所有内容（降级策略）
            return {
                "selected_contexts": list(predecessor_contents.keys()),
                "context_focus": {},
                "reasoning": f"分析失败，使用全部内容: {str(e)}"
            }

    def _build_focused_context_section(
        self,
        predecessor_contents: Dict[str, str],
        context_analysis: Dict[str, Any],
    ) -> str:
        """
        根据动态分析结果构建聚焦的上下文部分
        
        Args:
            predecessor_contents: 所有前置任务内容
            context_analysis: 动态分析结果
            
        Returns:
            聚焦的上下文提示词
        """
        selected = context_analysis.get("selected_contexts", [])
        focus = context_analysis.get("context_focus", {})
        reasoning = context_analysis.get("reasoning", "")
        
        if not selected:
            return ""
        
        sections = []
        
        sections.append(f"""
╔══════════════════════════════════════════════════════════════════╗
║  🎯 聚焦参考资料 - 经过智能分析后的必要信息                     ║
╚══════════════════════════════════════════════════════════════════╝

📝 **选择理由**: {reasoning}

---

""")
        
        # 按选择顺序展示内容
        for ctx_name in selected:
            if ctx_name not in predecessor_contents:
                continue
                
            content = predecessor_contents[ctx_name]
            focus_point = focus.get(ctx_name, "")
            
            # 根据是否有焦点来决定展示多少内容
            if focus_point:
                # 有明确焦点，截取更短
                max_len = 1500
                sections.append(f"\n### 📌 {ctx_name}\n")
                sections.append(f"**关注重点**: {focus_point}\n\n")
            else:
                # 没有明确焦点，展示更多
                max_len = 2500
                sections.append(f"\n### {ctx_name}\n")
            
            # 截取内容
            if len(content) > max_len:
                content = content[:max_len] + "\n...\n（内容已截断，请聚焦上述要点）"
            
            sections.append(f"```\n{content}\n```\n")
        
        sections.append("""
---

💡 **使用指南**：
- 以上是经过分析后认为对当前任务最重要的参考资料
- 请特别关注标注的"关注重点"
- 确保你的创作与这些内容保持一致

""")
        
        return "".join(sections)

    async def _get_previous_chapters(
        self,
        current_chapter: int,
        context: MemoryContext,
        max_chapters: int = 3,
    ) -> Dict[int, Dict[str, str]]:
        """
        获取前面章节的内容，用于保持故事连贯性
        
        Args:
            current_chapter: 当前章节号
            context: 记忆上下文
            max_chapters: 最多获取多少章（默认前3章，避免上下文过长）
            
        Returns:
            字典，key是章节号，value是包含outline和content的字典
        """
        previous_chapters = {}
        
        # 从 recent_results 中查找前面章节
        if context.recent_results:
            for result in context.recent_results:
                task_type = result.get("task_type", "")
                chapter_index = result.get("chapter_index")
                
                if chapter_index is not None and chapter_index < current_chapter:
                    if chapter_index not in previous_chapters:
                        previous_chapters[chapter_index] = {}
                    
                    if task_type == "章节大纲":
                        previous_chapters[chapter_index]["outline"] = result.get("content", "")
                    elif task_type in ("章节内容", "章节润色"):
                        # 优先使用润色后的内容
                        if task_type == "章节润色" or "content" not in previous_chapters[chapter_index]:
                            previous_chapters[chapter_index]["content"] = result.get("content", "")
        
        # 从 relevant_memories 中补充
        if context.relevant_memories:
            for mem in context.relevant_memories:
                chapter_index = mem.get("chapter_index")
                mem_type = mem.get("memory_type", "").lower()
                
                if chapter_index is not None and chapter_index < current_chapter:
                    if chapter_index not in previous_chapters:
                        previous_chapters[chapter_index] = {}
                    
                    content = mem.get("content", "")
                    if "章节大纲" in mem_type and "outline" not in previous_chapters[chapter_index]:
                        previous_chapters[chapter_index]["outline"] = content
                    elif ("章节内容" in mem_type or "章节润色" in mem_type) and "content" not in previous_chapters[chapter_index]:
                        previous_chapters[chapter_index]["content"] = content
        
        # 只保留最近的 max_chapters 章
        if len(previous_chapters) > max_chapters:
            sorted_chapters = sorted(previous_chapters.keys(), reverse=True)[:max_chapters]
            previous_chapters = {k: previous_chapters[k] for k in sorted_chapters}
        
        return previous_chapters

    def _build_chapter_continuity_context(
        self,
        current_chapter: int,
        previous_chapters: Dict[int, Dict[str, str]],
        outline_content: str,
    ) -> str:
        """
        构建章节连贯性上下文
        
        Args:
            current_chapter: 当前章节号
            previous_chapters: 前面章节的内容
            outline_content: 总大纲内容
            
        Returns:
            连贯性上下文字符串
        """
        if not previous_chapters and not outline_content:
            return ""
        
        sections = []
        
        sections.append("""
╔══════════════════════════════════════════════════════════════════╗
║  🔗 故事连贯性约束 - 必须与前面章节紧密衔接！                  ║
╚══════════════════════════════════════════════════════════════════╝

⚠️ **核心要求**：
- 当前章节必须**承接前面的情节**，不能像独立的小故事
- 人物状态、情感、位置必须**延续**前一章结尾
- 悬念、伏笔必须**有回应**或**继续铺垫**
- 时间线必须**连贯**，不能出现跳跃或矛盾

""")
        
        # 添加总大纲摘要（帮助理解整体走向）
        if outline_content:
            sections.append(f"""
### 📋 故事总大纲（参考整体走向）

```
{outline_content[:2000]}{"..." if len(outline_content) > 2000 else ""}
```

""")
        
        # 添加前面章节的内容
        if previous_chapters:
            sorted_chapters = sorted(previous_chapters.keys())
            
            for chapter_num in sorted_chapters:
                chapter_data = previous_chapters[chapter_num]
                
                sections.append(f"""
### 📖 第{chapter_num}章 回顾

""")
                
                if chapter_data.get("outline"):
                    sections.append(f"""
**章节大纲**：
```
{chapter_data["outline"][:800]}{"..." if len(chapter_data.get("outline", "")) > 800 else ""}
```

""")
                
                if chapter_data.get("content"):
                    content = chapter_data["content"]
                    # 提取结尾部分（最后500字左右），这对衔接最重要
                    ending = content[-800:] if len(content) > 800 else content
                    sections.append(f"""
**章节结尾**（必须从这里衔接！）：
```
{ending}
```

""")
        
        # 添加连贯性检查清单
        sections.append(f"""
### ✅ 连贯性检查清单（写作时必须确认）

- [ ] **人物状态**：第{current_chapter}章开头的人物状态是否与前一章结尾一致？
- [ ] **时间连续**：时间是否连贯？如有跳跃是否交代清楚？
- [ ] **空间连续**：人物位置是否合理过渡？
- [ ] **情节承接**：是否回应了前面的悬念/冲突？
- [ ] **情感延续**：人物情绪是否有合理的延续或转变？
- [ ] **伏笔处理**：是否有伏笔需要揭示或继续铺垫？

""")
        
        return "\n".join(sections)

    def _build_consistency_check_context(
        self,
        current_chapter: int,
        previous_chapters: Dict[int, Dict[str, str]],
        outline_content: str,
        task_type: str,
    ) -> str:
        """
        构建一致性检查专用的上下文
        
        与 _build_chapter_continuity_context 类似，但专门用于一致性检查，
        会包含更详细的内容以便检查连贯性问题。
        
        Args:
            current_chapter: 当前章节号
            previous_chapters: 前面章节的内容
            outline_content: 总大纲内容
            task_type: 当前任务类型
            
        Returns:
            一致性检查上下文字符串
        """
        if not previous_chapters and not outline_content:
            return ""
        
        sections = []
        
        sections.append(f"""
### 🔗 章节连贯性检查参考（针对第{current_chapter}章）

""")
        
        # 添加总大纲（完整版，利用 Qwen 的长上下文）
        if outline_content:
            sections.append(f"""
#### 📋 故事总大纲
```
{outline_content[:6000]}{"..." if len(outline_content) > 6000 else ""}
```

""")
        
        # 添加前面章节的内容（尽量完整）
        if previous_chapters:
            sorted_chapters = sorted(previous_chapters.keys())
            
            for chapter_num in sorted_chapters:
                chapter_data = previous_chapters[chapter_num]
                
                sections.append(f"""
#### 📖 第{chapter_num}章

""")
                
                if chapter_data.get("outline"):
                    outline = chapter_data["outline"]
                    sections.append(f"""
**大纲**：
```
{outline[:1500]}{"..." if len(outline) > 1500 else ""}
```

""")
                
                if chapter_data.get("content"):
                    content = chapter_data["content"]
                    # 对于一致性检查，给更多内容（特别是前一章的结尾部分）
                    if chapter_num == current_chapter - 1:
                        # 前一章，给更多结尾内容
                        ending = content[-2000:] if len(content) > 2000 else content
                        sections.append(f"""
**结尾部分**（必须衔接）：
```
{ending}
```

""")
                    else:
                        # 更早的章节，给简短摘要
                        ending = content[-800:] if len(content) > 800 else content
                        sections.append(f"""
**结尾摘要**：
```
{ending}
```

""")
        
        sections.append(f"""
#### ⚠️ 一致性检查重点

请特别检查第{current_chapter}章：
1. **开头衔接**：是否自然承接第{current_chapter - 1}章的结尾？
2. **人物状态**：人物的位置、情绪、状态是否延续？
3. **时间线**：时间是否连贯，有无跳跃或矛盾？
4. **情节连贯**：是否像一个完整故事的一部分，而非独立短篇？

""")
        
        return "\n".join(sections)

    def _build_foundation_reference(
        self,
        predecessor_contents: Dict[str, str],
        task_type: str,
    ) -> str:
        """
        构建基础设定参考部分 - 章节创作必看！
        
        基础设定（is_foundation=True的任务）是整个故事的锚点：
        - 故事核心：一句话概括，不能偏离
        - 大纲：故事骨架，必须按此推进
        - 世界观规则：世界运作的限制，不能违反
        - 人物设计：角色设定，行为必须符合性格
        - 事件：具体发生什么
        - 场景物品冲突：在哪里发生，用什么
        - 伏笔列表：埋设和回收，必须遵守
        
        Args:
            predecessor_contents: 前置任务内容
            task_type: 当前任务类型
            
        Returns:
            基础设定参考字符串
        """
        if not predecessor_contents:
            return ""
        
        # 定义基础设定任务（与 task_planner.py 中 is_foundation=True 的任务对应）
        foundation_tasks = ["故事核心", "大纲", "世界观规则", "人物设计", "事件", "场景物品冲突", "伏笔列表"]
        
        # 提取存在的基础设定内容
        foundation_contents = {
            k: v for k, v in predecessor_contents.items() 
            if k in foundation_tasks
        }
        
        if not foundation_contents:
            return ""
        
        sections = []
        
        sections.append("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔴 【基础设定参考 - 绝对不能违反！】                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  以下内容是整个故事的"宪法"，章节创作必须严格遵守！                         ║
║  任何偏离都会导致故事不连贯、人物崩坏、世界观矛盾！                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

⚠️ 警告：写作前请仔细阅读以下基础设定，写作中请反复对照确认！

""")
        
        # 按重要程度排序展示基础设定
        priority_order = [
            ("故事核心", "🎯 故事核心（最重要的锚点）", "所有创作必须围绕这个核心展开"),
            ("大纲", "📋 故事大纲（章节规划）", "本章内容必须符合大纲中的规划"),
            ("世界观规则", "🌍 世界观规则（运作限制）", "所有行为和事件必须符合世界规则"),
            ("人物设计", "👤 人物设计（角色设定）", "人物言行必须符合性格，不能崩人设"),
            ("事件", "⚡ 事件（具体发生什么）", "本章应包含相应的事件"),
            ("场景物品冲突", "🏠 场景物品冲突（在哪里发生）", "场景描写要符合设定"),
            ("伏笔列表", "🔮 伏笔列表（埋设和回收）", "本章应埋设或回收相应伏笔"),
        ]
        
        for task_name, title, tip in priority_order:
            if task_name in foundation_contents:
                content = foundation_contents[task_name]
                # 基础设定内容要尽量完整，利用长上下文
                max_len = 3500 if task_name in ["故事核心", "大纲", "人物设计", "世界观规则"] else 2000
                if len(content) > max_len:
                    content = content[:max_len] + "\n...\n（内容已截断，核心要点如上）"
                
                sections.append(f"""
### {title}

💡 **使用提示**：{tip}

```
{content}
```

""")
        
        sections.append(f"""
═══════════════════════════════════════════════════════════════════════════════

📌 **创作检查清单**（写完后请逐一确认）：

✅ 本章内容是否紧扣【故事核心】？
✅ 本章是否按照【大纲】规划推进？
✅ 人物言行是否符合【人物设计】的性格？
✅ 世界运作是否符合【世界观规则】？
✅ 本章是否正确处理了【伏笔】（埋设或回收）？
✅ 场景描写是否符合【场景物品冲突】设定？

❌ **绝对禁止**：
- 禁止偏离故事核心，写成另一个故事
- 禁止让人物做出不符合性格的行为
- 禁止违反世界观规则
- 禁止遗忘已埋设的伏笔
- 禁止与前面章节脱节

═══════════════════════════════════════════════════════════════════════════════

""")
        
        return "".join(sections)

    def _build_dynamic_context_section(
        self,
        task_type: str,
        predecessor_contents: Dict[str, str],
        goal: Dict[str, Any],
    ) -> str:
        """
        根据前置任务内容动态构建上下文部分
        
        Args:
            task_type: 当前任务类型
            predecessor_contents: 前置任务内容
            goal: 创作目标
            
        Returns:
            动态生成的上下文提示词
        """
        if not predecessor_contents:
            return ""
        
        sections = []
        
        # 强调关联性的开头
        sections.append("""
╔══════════════════════════════════════════════════════════════════╗
║  📚 前置任务成果 - 你必须基于这些内容创作，保持紧密关联！      ║
╚══════════════════════════════════════════════════════════════════╝

⚠️ **重要提醒**：
- 当前任务必须与以下内容**紧密关联**
- 不要"另起炉灶"，要在前面的基础上**延伸和深化**
- 评估时会检查你与前置任务的**关联程度**

""")
        
        # 按新的重要程度排序展示前置内容（故事核心最重要）
        priority_order = [
            "创意脑暴", "故事核心",  # 最重要的根基
            "人物设计", "世界观规则",  # 核心元素
            "主题确认", "风格元素", "市场定位",  # 风格定位
            "事件", "场景物品冲突", "伏笔列表",  # 情节元素
            "大纲"  # 整合
        ]
        
        for task_name in priority_order:
            if task_name in predecessor_contents:
                content = predecessor_contents[task_name]
                # 截取合理长度（避免超长）
                max_len = 2500 if task_name in ["故事核心", "大纲", "人物设计", "世界观规则"] else 1200
                if len(content) > max_len:
                    content = content[:max_len] + "...\n（内容已截断，请参考要点）"
                
                # 为重要任务添加特殊标记
                if task_name in ["故事核心", "人物设计"]:
                    sections.append(f"\n### 🎯 {task_name}（核心参考）\n")
                else:
                    sections.append(f"\n### {task_name}\n")
                sections.append(f"{content}\n")
        
        sections.append("""
---

📌 **你的任务**：在以上基础上继续创作，确保：
1. 与【故事核心】保持一致
2. 人物行为符合【人物设计】
3. 世界运作符合【世界观规则】
4. 风格符合【风格元素】（如已确定）

""")
        
        return "".join(sections)

    async def _build_prompt(
        self,
        task: Task,
        context: MemoryContext,
        goal: Dict[str, Any],
    ) -> str:
        """Build prompt for a task"""

        # Base prompt sections
        sections = []
        
        # Get task type value for matching
        task_type = task.task_type.value
        
        # 🔥 首先构建配置约束部分 - 所有任务都需要看到这些硬性约束
        word_count = goal.get("word_count", 50000)
        chapter_count = goal.get("chapter_count", 10)
        words_per_chapter = word_count // max(chapter_count, 1)
        genre = goal.get("genre", "")
        style = goal.get("style", "")
        
        # 根据字数显示不同格式
        if word_count >= 10000:
            word_display = f"{word_count // 10000}万字"
        else:
            word_display = f"{word_count}字"
        
        config_constraints = f"""
════════════════════════════════════════════════════════════════
📋 【核心配置约束 - 必须严格遵守】
════════════════════════════════════════════════════════════════

🎯 总字数限制：{word_display}（这是硬性要求，不能超出！）
📚 章节数量：{chapter_count}章（严格按此规划，不多不少！）
📝 每章字数：约{words_per_chapter}字

⚠️ 重要：所有规划、设计、创作都必须在这个框架内进行！
   不要超出字数限制，不要规划超出指定的章节数！

════════════════════════════════════════════════════════════════

"""
        sections.append(config_constraints)
        
        # 🎯 添加类型特定的创作指南（仙侠、科幻、言情等各不相同）
        genre_guide = self.get_genre_specific_guide(genre)
        sections.append(genre_guide)

        # Determine if this is a planning/analysis task or a content generation task
        planning_tasks = ["风格元素", "主题确认", "市场定位"]
        element_tasks = ["人物设计", "世界观规则", "事件设定", "场景物品冲突", "伏笔列表", "事件"]
        content_tasks = ["大纲", "章节大纲", "章节内容", "场景生成", "章节润色"]
        
        # 通用的白话文写作风格要求（所有任务都适用）
        colloquial_style_guide = """
🚨 **核心写作要求：白话文、接地气、通俗易懂**

你是一位擅长讲故事的作家，不是在写学术论文！
请像和朋友聊天一样写作，让高中生也能轻松看懂。

✅ **正确示范（白话文）**：
- ❌ "该角色具有内向型人格特质，在社交场合中呈现回避性行为模式"
- ✅ "他不太爱说话，人多的时候总喜欢躲在角落"

- ❌ "此设定构建了一个以科技发展为核心驱动力的叙事框架"
- ✅ "这个世界因为科技发达，发生了很多有意思的变化"

- ❌ "主角的内在驱动力源于童年创伤所形成的心理补偿机制"
- ✅ "他小时候受过伤，所以长大后特别想证明自己"

🚫 **绝对禁止（这些词看到就改！）**：
- 禁止用词："驱动力"、"机制"、"框架"、"模式"、"特质"、"维度"、"层面"、"范畴"
- 禁止用词："呈现"、"构建"、"探讨"、"阐述"、"论述"、"概述"、"综述"
- 禁止用词："基于"、"鉴于"、"关于"、"就...而言"、"从...角度"
- 禁止用词："具有...特征"、"表现出...倾向"、"体现了...精神"
- 禁止格式：一、二、三的正式大纲格式（可以用但不要过度）
- 禁止格式："首先...其次...最后..."的论文式写法

✅ **推荐写法**：
- 说人话：用"因为...所以..."而不是"鉴于...因此..."
- 用比喻：复杂概念用生活中的例子解释
- 讲故事：用叙事的方式而不是说明文的方式
- 接地气：想象你在给朋友讲一个好玩的故事

"""
        
        # Build goal section based on task type
        if task_type in planning_tasks:
            # Planning/analysis tasks - structured output
            goal_section = f"""## 任务背景

你正在为一部小说做**前期规划和分析**工作。
这个阶段的任务是帮助明确小说的方向，而不是直接写小说内容。

{colloquial_style_guide}
"""
        elif task_type in element_tasks:
            # Element creation tasks - semi-structured output  
            goal_section = f"""## 任务背景

你正在为一部小说**设计创作元素**。
这些元素将用于后续的章节创作，需要既有结构性又有文学性。

{colloquial_style_guide}
"""
        else:
            # Content generation tasks - narrative output
            goal_section = f"""## 创作目标

⚠️ 核心要求：你正在创作一部**小说**，请使用小说的叙事语言和文学手法。

{colloquial_style_guide}

📚 写作标准（参考《三体》《流浪地球》等大众科幻作品）：
✅ 必须做到：
- 故事性优先：一切设定服务于故事情节
- **通俗易懂**：面向大众读者，用白话文写作，让普通人都能看懂
- 文学性强：使用生动的叙事语言和文学手法
- 科学融入：科技设定通过对话、情节自然呈现，不堆砌术语
- 沉浸感：让读者身临其境，而不是在读技术文档
- **接地气**：用日常生活中的语言和比喻来解释复杂概念

❌ 严格禁止：
- 学术论文格式（摘要、引言、方法论、参考文献等）
- 纯公式推导或数学方程式罗列
- 面向专业研究者的学术写作风格
- 科研报告式的技术叙述
- 大量术语堆砌而不解释
- **看不懂的专业名词**（如果必须用，要用通俗语言解释）

💡 科幻小说要点：
- 科学设定要用故事讲出来（像刘慈欣的写法）
- 技术细节融入对话、情节、场景描写中
- 复杂概念用通俗易懂的方式解释
- 你的目标读者是科幻爱好者，不是物理学家

"""

        if goal.get("title"):
            goal_section += f"小说标题: {goal['title']}\n"
        if goal.get("genre"):
            goal_section += f"小说类型: {goal['genre']}\n"
        if goal.get("theme"):
            goal_section += f"小说主题: {goal['theme']}\n"
        if goal.get("style"):
            goal_section += f"写作风格: {goal['style']}\n"
        if goal.get("length"):
            goal_section += f"预计篇幅: {goal['length']}\n"
        if goal.get("word_count"):
            word_count = goal['word_count']
            if word_count >= 10000:
                goal_section += f"目标字数: {word_count // 10000}万字\n"
            else:
                goal_section += f"目标字数: {word_count}字\n"
        if goal.get("chapter_count"):
            goal_section += f"章节数量: {goal['chapter_count']}章\n"
        sections.append(goal_section)

        # 🔥 动态获取前置任务内容并构建上下文
        predecessor_contents = self._get_predecessor_contents(task_type, context)
        
        # 🧠 对于复杂任务（章节相关），使用动态上下文选择
        chapter_related_tasks = ["章节大纲", "章节内容", "章节润色", "场景生成"]
        use_dynamic_context = (
            predecessor_contents 
            and task_type in chapter_related_tasks
            and self.config.get("dynamic_context_selection", True)  # 配置开关，默认开启
        )
        
        # 🔴 对于章节相关任务，首先添加基础设定参考（最重要！）
        if task_type in chapter_related_tasks and predecessor_contents:
            foundation_reference = self._build_foundation_reference(predecessor_contents, task_type)
            if foundation_reference:
                sections.append(foundation_reference)
                logger.info(f"🔴 已添加基础设定参考到 {task_type} 的 prompt 中")
        
        if use_dynamic_context:
            # 动态分析需要哪些上下文
            try:
                context_analysis = await self._analyze_context_needs(task, goal, predecessor_contents)
                dynamic_context = self._build_focused_context_section(predecessor_contents, context_analysis)
                logger.info(f"🧠 使用动态上下文选择: 从{len(predecessor_contents)}个上下文中选择了{len(context_analysis.get('selected_contexts', []))}个")
            except Exception as e:
                logger.warning(f"⚠️ 动态上下文选择失败，使用默认方式: {e}")
                dynamic_context = self._build_dynamic_context_section(task_type, predecessor_contents, goal)
            sections.append(dynamic_context)
        elif predecessor_contents:
            # 对于其他任务，使用原有的固定规则
            dynamic_context = self._build_dynamic_context_section(task_type, predecessor_contents, goal)
            sections.append(dynamic_context)

        # Task-specific instruction based on task type
        # ============ Phase 0: 创意脑暴阶段 ============
        if task_type == "创意脑暴":
            genre = goal.get('genre', '科幻')
            task_section = f"""
## 当前任务：{task_type} 🎯

你现在是一个**顶级畅销小说家**，正在为新书进行创意脑暴。

📌 **脑暴目标**：为一部{genre}小说产生 **4 个独特的故事点子**，并从中推荐最佳的一个

### 每个点子必须包含：

1. **故事概念**（2-3句话）
   - 用"如果...会怎样"的方式描述
   - 必须有一个独特的、吸引人的核心设定

2. **核心冲突**
   - 主角面对什么困境/挑战？
   - 什么东西阻止主角得到他想要的？

3. **情感钩子**
   - 这个故事能触动读者什么情感？
   - 为什么读者会在意这个故事？

4. **独特卖点**
   - 这个故事与市面上其他{genre}小说有什么不同？
   - 一句话能让人记住的特点是什么？

5. **潜力评估**（简短）
   - 这个点子适合发展成多长的小说？
   - 可能的受众是谁？

### 脑暴原则

✅ **要做到**：
- 点子要大胆、新奇，不要老套
- 每个点子之间要有差异性，不要太相似
- 想想读者看到这个设定会不会眼前一亮
- 考虑故事的"可展开性"——能支撑起完整的小说吗？

❌ **要避免**：
- 不要写成长篇大纲，每个点子控制在 200-300 字
- 不要学术化，用讲故事的语气
- 不要太平庸，那种"一看就知道结局"的故事不要

### 输出格式

请用以下格式输出（**必须严格按照此格式**）：

---
## 💡 点子一：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 💡 点子二：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 💡 点子三：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 💡 点子四：[一句话概念]

**故事设定**：...

**核心冲突**：...

**情感钩子**：...

**独特卖点**：...

**潜力评估**：...

---
## 🏆 AI推荐

**推荐点子**：点子[X]

**推荐理由**：
（从以下维度分析为什么这个点子最有潜力：新颖程度、情感共鸣、市场潜力、可展开性）

---

⚠️ **重要**：用户将从这4个点子中选择一个作为后续创作的基础，请确保每个点子都有足够的质量和差异性！
"""
        elif task_type == "故事核心":
            # 获取用户选择的点子编号
            selected_idea_info = ""
            if predecessor_contents.get("创意脑暴"):
                brainstorm_content = predecessor_contents["创意脑暴"]
                # 从内容开头提取用户选择的点子
                if brainstorm_content.startswith("【用户选择】点子"):
                    import re
                    match = re.search(r"【用户选择】点子(\d+)", brainstorm_content)
                    if match:
                        selected_num = match.group(1)
                        selected_idea_info = f"""
---
### ⚠️ 重要：用户已选择点子{selected_num}

用户在上一轮创意脑暴中已经选择了「点子{selected_num}」作为本小说的基础。
**你必须基于点子{selected_num}来发展故事核心，不要选择其他点子！**

---
"""
            
            task_section = f"""
## 当前任务：{task_type} 🎯

你是一位畅销小说家，正在进行创作前最关键的一步：**确定故事核心**。

> "每一个伟大的故事都可以用一句话概括。如果你做不到，说明你还不知道自己在写什么。" — 斯蒂芬·金
{selected_idea_info}
---

### 📌 任务说明

基于用户在「创意脑暴」中**选择的点子**，将其打磨成完整的故事核心。

⚠️ **这不是写章节内容！** 这是战略规划阶段，你要确定故事的"心脏"。

---

### 🏆 顶级作家的故事核心法则

**法则一：好故事必须能用一句话说清楚**
- 《教父》：一个黑帮家族的继承人试图让家族合法化，却发现自己变成了比父亲更冷酷的人
- 《三体》：人类发现宇宙并不友善，文明的生存需要做出残酷的选择
- 《肖申克的救赎》：一个被冤枉的银行家用27年证明希望是关不住的

**法则二：故事的动力来自"欲望+阻碍"**
- 主角必须**极度渴望**某样东西
- 必须有**强大的阻碍**让他得不到
- 读者必须**在意**主角能否成功

**法则三：真正抓住读者的是情感，不是设定**
- 科幻设定再酷，没有情感就是技术文档
- 读者记住的是人物的选择和牺牲，不是世界观

---

### 📋 请输出以下内容

#### 一、选择的点子回顾

1. **选中的点子**：[用户选择的点子编号及核心概念]
2. **点子优势**：[这个点子的最大亮点是什么？用 2-3 句话说明]

#### 二、一句话故事（Logline）

用 **30字以内** 概括整个故事，格式：
> "[主角是谁] 必须 [做什么]，否则 [会发生什么后果]，但 [面临什么阻碍]"

写 2-3 个版本，然后选出最好的那个。

#### 三、故事引擎

**1. 主角核心**
| 要素 | 内容 |
|------|------|
| 身份设定 | [简洁说明] |
| 表面欲望 | [故事层面想要什么？] |
| 深层需求 | [主题层面真正需要什么？] |
| 致命缺陷 | [什么弱点会害他？] |

**2. 核心冲突**
- 外部障碍：[谁或什么在阻止主角？]
- 内心挣扎：[主角内心在纠结什么？]
- 赌注是什么：[如果失败会失去什么？这个后果要够重！]

**3. 冲突升级路径**（简述三幕）
- **第一幕**：[打破平衡，进入冒险]
- **第二幕**：[困难加剧，内外交困]
- **第三幕**：[最终抉择，高潮收尾]

#### 四、读者体验设计

1. **情感承诺**：读者读这个故事会体验什么情感？（紧张？感动？震撼？）
2. **核心悬念**：什么问题会让读者一直想知道答案？
3. **共鸣点**：读者会在什么地方产生强烈代入感？

#### 五、主题种子

用一句话描述这个故事想探讨的人生问题：
> "这是一个关于 ______ 的故事"

（例如：关于选择的代价 / 关于人性的复杂 / 关于爱与牺牲）

---

### ❌ 禁止事项

- **禁止写章节内容或正文**，这只是规划阶段
- **禁止长篇大论**，每个部分简洁有力
- **禁止空洞描述**，要具体，让人能"看到"这个故事
- **禁止复制脑暴内容**，要在此基础上深化和聚焦

---

📝 **输出长度**：800-1500字，清晰、结构化、有洞察力
"""
        elif task_type == "风格元素":
            genre = goal.get('genre', '')
            # 科幻类型特别强调通俗易懂
            sci_fi_note = ""
            if genre == "科幻":
                sci_fi_note = """
🔔 **科幻小说特别提醒**：
- 科幻不等于学术论文！要用故事讲科学，不是写科普文章
- 参考《三体》《流浪地球》的写法：科技元素融入情节，而不是堆砌术语
- 让不懂科学的读者也能看懂、也能感动
- 避免大段的技术说明，用对话、情节来展现科技
"""
            
            task_section = f"""
## 当前任务：{task_type} 🎨

你是一位顶级畅销小说家，正在为新书确定**最合适的文学风格**。

> "风格不是装饰，而是讲故事的方式。选错了风格，再好的故事也会被毁掉。" — 斯蒂芬·金

---

### 📌 任务说明

基于前面确定的**故事核心**，定义最能展现这个故事魅力的风格元素。

⚠️ **风格必须服务于故事！** 不同的故事需要不同的讲述方式。

---

### 🏆 顶级作家的风格法则

**法则一：风格要与故事内核匹配**
- 《三体》用冷峻克制的语言讲宇宙的残酷
- 《追风筝的人》用温暖细腻的文字讲救赎
- 《教父》用沉稳老练的笔调讲家族传承

**法则二：风格要考虑目标读者**
- 网文读者喜欢爽快节奏
- 文学读者欣赏精致文字
- 大众读者需要通俗易懂

**法则三：风格要始终如一**
- 一旦确定风格，全书要保持一致
- 风格不一致会让读者出戏
{sci_fi_note}
---

### 📋 请输出以下内容

#### 一、叙事视角选择

1. **选择的视角**：[第几人称？全知/限制/多视角？]
2. **选择理由**：[为什么这个视角最适合讲述这个故事？2-3句话]
3. **参考作品**：[有哪些成功作品用了类似视角？]

#### 二、语言风格定位

1. **风格关键词**：[3个词概括，如"简洁、有力、画面感强"]
2. **具体说明**：
   - 句子长度偏好：长句/短句/混合
   - 用词倾向：口语化/书面化/诗意化
   - 修辞偏好：多用比喻/少用修辞/适度点缀
3. **风格示例**：[写2-3句示例句子，展示这种风格]

⚠️ 必须是**通俗易懂的白话文**！

#### 三、叙事节奏设计

1. **整体节奏**：[快节奏/中速/慢节奏]
2. **节奏变化规律**：
   - 什么时候加速？（紧张场面、动作戏）
   - 什么时候放缓？（情感戏、铺垫）
3. **章节长度倾向**：[长章节/短章节/混合]

#### 四、氛围基调

1. **主导氛围**：[一个词概括，如"紧张""温暖""压抑"]
2. **氛围层次**：
   - 底色氛围：贯穿全书的基调
   - 情绪高点：什么氛围？
   - 情绪低点：什么氛围？

#### 五、文学技巧选择

| 技巧类型 | 使用频率 | 使用场景 |
|---------|---------|---------|
| 对话 | 高/中/低 | 什么时候用？ |
| 内心独白 | 高/中/低 | 什么时候用？ |
| 环境描写 | 高/中/低 | 什么时候用？ |
| 动作场面 | 高/中/低 | 什么时候用？ |
| 闪回/插叙 | 高/中/低 | 什么时候用？ |

---

### ❌ 禁止事项

- 禁止写成小说正文，这是规划阶段
- 禁止堆砌专业术语
- 禁止脱离故事核心空谈风格

📝 **输出长度**：500-800字，清晰、实用
"""
        elif task_type == "主题确认":
            task_section = f"""
## 当前任务：{task_type} 💎

你是一位顶级畅销小说家，正在提炼新书的**核心主题**。

> "主题不是你想讲什么道理，而是故事本身在说什么。好的主题从人物的挣扎中自然涌现。" — 罗伯特·麦基

---

### 📌 任务说明

基于**故事核心、人物和世界观**，提炼这部小说的核心主题。

⚠️ **顶级作家的秘密**：主题不是预设的，而是从故事中**涌现**的。

---

### 🏆 顶级作家的主题法则

**法则一：主题藏在人物的选择里**
- 《教父》主题不是"黑帮"，而是"家族vs个人的挣扎"
- 《三体》主题不是"外星人"，而是"文明的生存选择"
- 《肖申克的救赎》主题是"希望"，通过安迪的行动体现

**法则二：主题要能用一个词/短语概括**
- 复杂的主题不是好主题
- 能一句话说清的主题才有力量

**法则三：主题要引发共鸣，不要说教**
- 让读者自己领悟，而不是灌输
- 通过故事展示，而不是用嘴说

---

### 📋 请输出以下内容

#### 一、主题提炼

1. **核心主题**：用 **5个字以内** 概括
   - 例如：救赎、选择的代价、人性的复杂、爱与牺牲

2. **主题陈述**：用一句话展开（20字以内）
   - 格式："这是一个关于 ______ 的故事"
   - 例如："这是一个关于在绝望中坚守希望的故事"

3. **主题的普世性**
   - 这个主题触及了什么人类共同的困境/渴望？
   - 为什么读者会在意这个主题？

#### 二、主题与故事的关系

1. **主角如何体现主题？**
   - 主角的内心旅程如何与主题呼应？
   - 主角的选择如何揭示主题？

2. **核心冲突如何承载主题？**
   - 冲突的本质与主题有什么关联？

3. **结局如何升华主题？**
   - 故事结局如何回应主题？
   - 读者最终会得到什么启示？

#### 三、主题表达策略

⚠️ **绝对禁止说教！** 主题要通过以下方式自然呈现：

1. **通过人物行动**：哪些行动体现主题？
2. **通过关键对话**：哪些对话触及主题？（不要直接说出主题）
3. **通过场景象征**：哪些场景暗示主题？
4. **通过情节设计**：哪些情节推进主题？

#### 四、主题验证

回答以下问题确认主题成立：
- [ ] 主题是否与故事核心一致？
- [ ] 主题是否能引起读者共鸣？
- [ ] 主题是否避免了说教？
- [ ] 主题是否贯穿了整个故事？

---

### ❌ 禁止事项

- 禁止把主题写成论文观点
- 禁止说教式的表达
- 禁止脱离故事空谈主题

📝 **输出长度**：400-600字
"""
        elif task_type == "市场定位":
            task_section = f"""
## 当前任务：{task_type} 📊

你是一位既懂创作又懂市场的**畅销书作家**，正在为新书做市场定位。

> "写作是艺术，出版是生意。好作家两者都懂。" — 尼尔·盖曼

---

### 📌 任务说明

综合前面所有元素，确定这部小说的**市场定位和商业策略**。

⚠️ **这不是妥协艺术，而是让好故事找到对的读者。**

---

### 🏆 畅销书的市场法则

**法则一：知道你在为谁写**
- 《三体》：硬核科幻爱好者 + 想探索深刻问题的读者
- 《斗破苍穹》：喜欢爽文、追求成长快感的年轻读者
- 《人民的名义》：关注社会现实的中年读者

**法则二：有清晰的卖点**
- 一句话能让人决定是否想看
- 卖点要与众不同

**法则三：了解市场趋势但不盲从**
- 追热点容易过时
- 有独特性才有生命力

---

### 📋 请输出以下内容

#### 一、目标读者画像

1. **核心读者**（最可能喜欢的人）
   - 年龄范围：
   - 性别倾向：
   - 阅读习惯：[网文党/实体书爱好者/碎片化阅读]
   - 阅读场景：[通勤/睡前/周末沉浸]

2. **拓展读者**（可能被吸引的人）
   - 什么人群可能成为潜在读者？

3. **读者需求分析**
   - 他们为什么读这类书？[解压/思考/消遣/寻找共鸣]
   - 他们希望从书中得到什么？

#### 二、市场竞品分析

1. **同类成功作品**（3-5部）
   | 作品名 | 相似点 | 不同点 | 市场表现 |
   |-------|-------|-------|---------|
   | | | | |

2. **本作的差异化优势**
   - 与竞品相比，我们的独特卖点是什么？
   - 读者为什么选我们而不选竞品？

#### 三、卖点提炼

1. **核心卖点**（最打动人的1个）
   - 用一句话概括（15字以内）

2. **支撑卖点**（2-3个）
   - 卖点1：
   - 卖点2：
   - 卖点3：

3. **宣传语设计**
   - 封面宣传语：（一句话，吸引眼球）
   - 简介第一句：（钩子，让人想往下看）

#### 四、发布策略建议

1. **适合的平台/渠道**
   - 首发平台建议：[起点/番茄/微信读书/实体出版...]
   - 理由：

2. **更新节奏建议**（如果是连载）
   - 建议每日/周更新字数：
   - 理由：

3. **营销切入点**
   - 可以借势的话题/热点：
   - 适合的推广方式：

---

### ❌ 禁止事项

- 禁止过度商业化忘记内容
- 禁止不切实际的预期
- 禁止完全脱离已有的故事核心

📝 **输出长度**：500-800字
"""
        elif task_type == "人物设计":
            # 根据字数估算需要的人物数量
            word_count = goal.get("word_count", 50000)
            chapter_count = goal.get("chapter_count", 10)
            genre = goal.get("genre", "通用")
            
            # 根据字数动态调整人物数量 - 长篇需要更多人物来支撑故事
            if word_count >= 1000000:  # 100万字以上
                main_chars = "2-4"
                support_chars = "12-18"
                minor_chars = "25-40"
                char_note = "超长篇需要丰富的人物群像，多条支线需要各自的人物来承载。"
            elif word_count >= 500000:  # 50万字以上
                main_chars = "2-3"
                support_chars = "8-12"
                minor_chars = "15-25"
                char_note = "长篇小说需要足够的人物来支撑复杂的故事线。"
            elif word_count >= 200000:  # 20万字以上
                main_chars = "1-2"
                support_chars = "5-8"
                minor_chars = "10-15"
                char_note = "中长篇需要适量的配角来丰富故事世界。"
            elif word_count >= 100000:  # 10万字以上
                main_chars = "1-2"
                support_chars = "4-6"
                minor_chars = "6-10"
                char_note = "中篇小说人物要精简，每个人物都要有存在价值。"
            else:  # 10万字以下
                main_chars = "1"
                support_chars = "2-4"
                minor_chars = "3-5"
                char_note = "短篇小说人物要少而精，避免角色过多分散焦点。"
            
            task_section = f"""
## 当前任务：{task_type} 🎭

你是一位顶级畅销小说家，正在为新书设计人物。

> "情节是人物的证明。读者不记得情节，但永远记得人物。" — 斯蒂芬·金

---

### 📌 任务说明

⚠️ **重要**：请参考【大纲】中列出的人物列表，为每个人物进行详细设计！

📊 **本书规模**：目标 **{word_count//10000}万字**，共 **{chapter_count}章**
💡 **人物规模建议**：{char_note}

---

### 🏆 顶级作家的人物法则

**法则一：人物即故事**
- 情节不是发生在人物身上的事，而是人物性格导致的必然
- 《教父》的麦克不是被动卷入，是他的性格让他必然成为教父

**法则二：欲望+缺陷=动力**
- 人物必须极度渴望某样东西（欲望）
- 人物必须有阻碍他得到的内在弱点（缺陷）
- 这两者的碰撞产生故事

**法则三：每个人物都认为自己是主角**
- 反派也有他的逻辑和理由
- 配角有自己的人生，不只是主角的工具

---

### 📋 请输出以下内容

---

## 一、主角设计（{main_chars}人）

主角是故事核心的**化身**。设计时必须回答：**为什么必须是他/她来经历这个故事？**

### 主角：[姓名]

#### 1. 基本信息
| 项目 | 内容 |
|-----|------|
| 姓名 | （含名字的含义或由来）|
| 年龄 | |
| 性别 | |
| 身份/职业 | |
| 外貌特征 | （2-3个让人记住的特点）|

#### 2. 性格内核（最重要！）

**人物三角**：
- **想要什么（Want）**：表面目标，故事层面的追求
- **需要什么（Need）**：深层需求，主题层面的真相
- **致命缺陷（Flaw）**：什么性格弱点会阻碍他？

**人物谎言**：
- 主角相信的一个关于世界/自己的错误信念是什么？
- 这个谎言如何影响他的行为？
- 故事中何时/如何打破这个谎言？

#### 3. 人物小传（重要！500-800字）

⚠️ **用故事的方式讲述这个人物的过去**，不要写档案式的条目！

请用叙事的方式描述：
- 他/她的童年是怎样的？（家庭环境、重要经历）
- 什么事件塑造了他/她现在的性格？（关键创伤或转折）
- 在故事开始前，他/她过着怎样的生活？
- 他/她有什么执念或心结？
- 他/她最珍视什么？最害怕什么？

[请写一段500-800字的人物小传，像在讲一个人的故事]

#### 4. 基于世界观的能力（如有）

⚠️ **参考【世界观规则】设计人物能力**，确保能力符合世界规则！

| 项目 | 内容 |
|-----|------|
| 能力名称 | |
| 能力来源 | [根据世界观设定] |
| 能力效果 | |
| 使用限制/代价 | [每个能力都应该有代价] |
| 在故事中的作用 | [这个能力如何推动剧情？] |

**能力设计原则**：
- 能力必须符合世界观规则
- 能力要有明确的限制和代价
- 能力要为故事服务，不是炫技

#### 5. 人物弧光
| 阶段 | 状态 | 触发事件 |
|-----|------|---------|
| 开始 | [性格状态] | - |
| 考验 | [面对什么挑战] | [什么事件] |
| 转变 | [如何改变] | [什么事件] |
| 结局 | [最终状态] | - |

#### 6. 标志性特征
- 口头禅/说话方式：
- 习惯性动作：
- 独特的小细节：

---

## 二、重要配角（{support_chars}人）

⚠️ **配角存在的唯一理由**：推动或阻碍主角的旅程。

### 配角设计模板（每人填写）

**[姓名]** - [一句话定义：身份+与主角的关系]

| 项目 | 内容 |
|-----|------|
| 与主角关系 | [盟友/对手/导师/恋人/镜像] |
| 故事功能 | [这个人物为什么必须存在？] |
| 性格关键词 | [2-3个词] |
| 个人目标 | [他自己想要什么？] |
| 外貌特征 | [1-2个记忆点] |

**人物小传**（200-300字）：
[用叙事方式描述这个人物的背景故事]

**能力设定**（如有，参考世界观规则）：
- 能力：
- 限制/代价：

**配角类型参考**：
- 🤝 **盟友**：帮助主角，但可能有自己的议程
- ⚔️ **对手/反派**：阻碍主角（注意：反派也认为自己是对的）
- 🎓 **导师**：提供智慧或技能，可能需要被超越
- 🪞 **镜像人物**：与主角形成对比，展示另一条路
- 💕 **情感纽带**：给主角提供情感动力

---

## 三、次要人物（{minor_chars}人）

简要列出，每人一行：

| 姓名 | 身份 | 出场章节 | 作用 | 能力（如有）|
|-----|------|---------|-----|----------|
| | | 约第X章 | [一句话说明] | |

---

## 四、人物关系网

用文字描述人物之间的关系：

**主要关系线**：
- [人物A] ←→ [人物B]：[关系性质 + 关系如何变化]
- ...

**隐藏关系**（如果有）：
- [什么关系是隐藏的？什么时候揭示？]

**冲突关系**：
- [谁和谁有冲突？为什么？]

---

## 五、人物出场规划（重要！）

⚠️ **这是给后续章节创作的重要参考**，请认真规划每个人物的出场节奏。

### 章节出场分布表

📊 本书共 **{chapter_count}章**，请规划每个人物在哪些章节出场：

| 人物 | 出场章节（列出所有章节编号） | 首次出场 | 高光章节 | 退场/结局 |
|-----|--------------------------|---------|---------|---------|
| [主角名] | 1-{chapter_count}（全书贯穿） | 第1章 | 第X、X、X章 | 第{chapter_count}章 |
| [配角1] | 第2、5、8、12、...章 | 第2章 | 第X章 | 第X章 |
| [配角2] | 第3、6、9、15章 | 第3章 | 第X章 | - |
| ... | ... | ... | ... | ... |

### 出场规划原则

1. **主角**：应贯穿全书，每章都有出场
2. **重要配角**：出场率约50-70%的章节，要有节奏感
3. **次要人物**：出场率约20-40%的章节，按需出场
4. **过场人物**：仅在必要章节出场

### 人物密度建议

| 章节阶段 | 建议同时在场人物数 | 说明 |
|---------|------------------|-----|
| 开篇（1-3章）| 2-4人 | 建立核心关系 |
| 发展期 | 4-6人 | 逐步引入配角 |
| 高潮期 | 5-8人 | 人物汇聚 |
| 结局 | 3-5人 | 收束 |

---

### ❌ 禁止事项

- 禁止写成档案表格，人物要**活**
- 禁止人物没有缺点（完美人物不真实）
- 禁止配角只是工具人（每个人都有自己的人生）
- 禁止人物数量超出规模建议太多
- 禁止人物出场规划模糊不清（必须明确到具体章节）

📝 **输出长度**：1500-2500字（根据字数规模调整）
"""
        elif task_type == "世界观规则":
            genre = goal.get('genre', '科幻')
            word_count = goal.get("word_count", 50000)
            
            # 根据字数调整世界观复杂度
            if word_count >= 500000:
                complexity = "高复杂度"
                detail_note = "长篇需要完整的世界观体系，但仍需确保读者能理解。"
            elif word_count >= 200000:
                complexity = "中等复杂度"
                detail_note = "中长篇可以有较完整的设定，但要避免设定过载。"
            else:
                complexity = "简洁"
                detail_note = "短中篇世界观要精简，只保留故事必需的设定。"
            
            # 科幻类型特别提醒
            sci_fi_worldview_note = ""
            if genre == "科幻":
                sci_fi_worldview_note = """
🔔 **科幻世界观特别提醒**：
- 世界观是给你自己参考的，不是给读者看的学术论文
- 设定要**能用故事讲出来**，不是干巴巴的规则罗列
- 科技设定要**通俗易懂**，用生活中的比喻来解释
- 参考《三体》：复杂的科学概念用简单的比喻解释（如"二向箔像一张纸"）
"""
            
            task_section = f"""
## 当前任务：{task_type} 🌍

你是一位顶级畅销小说家，正在为新书构建**完整的故事世界**。

> "世界观的目的不是展示你有多聪明，而是让故事发生在一个让人信服的地方。" — 布兰登·桑德森

---

### 📌 任务说明

基于**故事核心和大纲**，构建一个**完整、独特、有特色**的世界。

📊 **本书规模**：{word_count//10000}万字 → 世界观复杂度：**{complexity}**
💡 {detail_note}
{sci_fi_worldview_note}

⚠️ **重要**：
1. 世界观要**完整详细**，是后续人物设计和章节创作的基础！
2. 世界要有**独特/特殊的部分**，让故事有新鲜感！
3. 设计要服务于故事，但也要足够详细，让创作有据可依！

---

### 🏆 顶级作家的世界观法则

**法则一：冰山理论**
- 作者要知道100%，但只展示给读者10-20%
- 设定在后台支撑，不要全部塞给读者

**法则二：设定要能被打破**
- 最精彩的情节往往是打破/利用世界规则
- 《三体》的水滴打破了人类的自信

**法则三：设定通过故事展现**
- 不要写百科全书，要通过人物的经历展示世界
- 读者通过人物的眼睛看世界

---

### 📋 请输出以下内容

---

## 一、世界基础设定

### 1. 时空背景
| 项目 | 设定 | 对故事的影响 |
|-----|------|------------|
| 时代 | [什么年代/纪元] | |
| 地点 | [主要发生在哪里] | |
| 历史背景 | [重要的历史事件] | |
| 与现实的差异 | [一句话说明] | |

### 2. 社会结构
| 项目 | 设定 |
|-----|------|
| 政治体制 | [什么样的政府/统治方式] |
| 社会阶层 | [有哪些阶层？如何划分？] |
| 经济体系 | [使用什么货币？经济模式？] |
| 文化习俗 | [重要的节日、礼仪、禁忌] |

### 3. 主角的位置
- 主角在这个社会中处于什么位置？
- 什么社会因素会成为故事的阻力？

---

## 二、世界的独特/特殊之处（重要！）

⚠️ **这是让你的世界与众不同的关键！** 每个好的世界都有独特的设定。

### 🌟 特殊设定1：[名称]

**设定内容**（详细描述）：
[这个特殊设定是什么？详细说明]

**运作规则**：
- 这个设定是如何运作的？
- 有什么限制和代价？
- 谁可以使用/获得？

**对故事的影响**：
- 这个设定如何推动剧情？
- 主角如何与这个设定互动？

**展示方式**：
- 如何在故事中自然展示这个设定？
- 在哪些章节重点展现？

---

### 🌟 特殊设定2：[名称]

[同上格式]

---

### 🌟 特殊设定3：[名称]

[同上格式]

---

## 三、核心规则体系

### 1. 这个世界与现实的关键差异

| 差异点 | 具体设定 | 如何在故事中呈现 |
|-------|---------|---------------|
| | | 通过什么场景/对话展示 |
| | | |
| | | |

### 2. 能力/魔法/科技体系（如有）

⚠️ **这是人物设计能力的基础！**

| 项目 | 内容 |
|-----|------|
| 体系名称 | |
| 能力来源 | [能力从哪里来？] |
| 激活/获得条件 | [如何获得这种能力？] |
| 能力等级 | [有没有等级划分？] |
| 使用代价 | [使用能力要付出什么？] |
| 能力限制 | [什么是做不到的？] |

**能力分类**（如有多种能力）：
| 能力类型 | 效果 | 获得方式 | 限制 |
|---------|-----|---------|-----|
| | | | |

### 3. 核心规则（最多5条）

每条规则必须回答：
- 规则是什么？
- 为什么需要这条规则？（对故事有什么用）
- 这条规则能怎么被利用/打破？

| 规则 | 内容 | 故事功能 | 可能的破例 |
|-----|------|---------|----------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## 四、日常生活细节

描述普通人在这个世界的日常：

| 方面 | 设定 |
|-----|------|
| 衣 | [人们穿什么？有什么讲究？] |
| 食 | [吃什么？有什么特色食物？] |
| 住 | [住在什么样的地方？] |
| 行 | [如何出行？交通工具？] |
| 娱乐 | [人们如何消遣？] |
| 工作 | [主要的职业有哪些？] |

---

## 五、重要组织/势力

列出故事中会出现的主要势力：

### 势力1：[名称]
| 项目 | 内容 |
|-----|------|
| 性质 | [政府/帮派/公司/门派...] |
| 核心理念/目标 | |
| 实力规模 | |
| 与主角的关系 | |
| 内部结构 | |

### 势力2：[名称]
[同上]

---

## 六、世界观词典

列出这个世界的专有名词（10-20个）：

| 名词 | 解释（用比喻或日常语言） | 首次出现时机 |
|-----|----------------------|------------|
| | | 约第X章 |

---

## 七、与故事核心的关联

请明确说明：

1. **世界观如何服务于核心冲突？**
   - 主角面临的外部阻碍来自这个世界的什么方面？

2. **世界观如何强化主题？**
   - 这个世界的设定如何体现故事想探讨的问题？

3. **世界观如何为人物提供舞台？**
   - 人物如何在这个世界中行动？

---

### ❌ 禁止事项

- ❌ 写成百科全书式的设定集
- ❌ 罗列大量与故事无关的细节
- ❌ 使用学术论文的语气
- ❌ 创造复杂的术语体系让读者困惑
- ❌ 设定没有代价/限制（太完美的设定没有戏剧性）
- ❌ 世界太普通，没有特殊/独特的地方

📝 **输出长度**：1500-3000字（根据复杂度调整）

⚠️ **重要提醒**：
1. 必须详细设计**特殊/独特的世界设定**！
2. 所有设定都要用**白话文**描述！
3. 这份世界观是后续人物能力设计的基础！
"""
        elif task_type in ["事件设定", "事件"]:
            chapter_count = goal.get("chapter_count", 10)
            word_count = goal.get("word_count", 50000)
            
            # 根据章节数调整事件数量
            if chapter_count >= 30:
                event_count = "10-15"
            elif chapter_count >= 15:
                event_count = "7-10"
            else:
                event_count = "5-8"
                
            task_section = f"""
## 当前任务：{task_type} ⚡

你是一位顶级畅销小说家，正在为新书规划**关键转折事件**。

> "故事就是一系列有因果关系的事件，每个事件都让情况变得更好或更糟。" — 罗伯特·麦基

---

### 📌 任务说明

设计推动故事发展的**核心转折事件**。

📊 **本书规模**：{chapter_count}章，约{word_count//10000}万字
💡 **建议事件数**：{event_count}个关键转折点

---

### 🏆 顶级作家的事件法则

**法则一：事件必须改变现状**
- 好的事件让事情变得更好或更糟，不能是无关紧要的
- 每个事件后，人物的处境必须不同于之前

**法则二：事件必须有因果关系**
- 事件A导致事件B，事件B导致事件C
- 不是"然后发生了..."，而是"因为...所以..."

**法则三：事件要考验人物**
- 好的事件迫使人物做出选择
- 选择揭示性格，性格决定命运

---

### 📋 请输出以下内容

---

## 一、核心冲突定义

**主要矛盾**：
1. **冲突本质**：[一句话概括]
2. **冲突双方**：[谁vs谁/什么]
3. **赌注**：[如果失败会失去什么？要够重！]
4. **为何难解**：[为什么不能轻易解决？]

---

## 二、故事结构（三幕式）

### 第一幕：建立 → 进入（约占20%，第1-{max(1, chapter_count//5)}章）

**目标**：建立世界、人物、日常，然后打破日常

| 事件 | 章节 | 功能 | 描述 |
|-----|-----|-----|-----|
| 开场状态 | 第1章 | 展示日常 | |
| 触发事件 | 第X章 | 打破日常 | |
| 跨越门槛 | 第X章 | 进入主线 | |

### 第二幕：对抗 → 升级（约占60%，第{max(2, chapter_count//5+1)}-{max(3, int(chapter_count*0.8))}章）

**目标**：冲突升级，人物成长，困难加剧

| 事件 | 章节 | 功能 | 描述 |
|-----|-----|-----|-----|
| 第一考验 | 第X章 | 初次挫折 | |
| 小胜利 | 第X章 | 虚假希望 | |
| 中点反转 | 约第{chapter_count//2}章 | 重大转折 | |
| 困境加深 | 第X章 | 形势恶化 | |
| 黑暗时刻 | 第X章 | 最低谷 | |

### 第三幕：决战 → 结局（约占20%，第{max(4, int(chapter_count*0.8)+1)}-{chapter_count}章）

| 事件 | 章节 | 功能 | 描述 |
|-----|-----|-----|-----|
| 觉醒/准备 | 第X章 | 重新振作 | |
| 最终对决 | 第X章 | 高潮 | |
| 结局 | 第{chapter_count}章 | 收尾 | |

---

## 三、关键转折事件详解（{event_count}个）

每个事件详细描述：

### 事件1：[事件名称]

| 项目 | 内容 |
|-----|------|
| 发生章节 | 约第X章 |
| 事件类型 | [触发/发展/转折/高潮/结局] |
| 参与人物 | |

**事件描述**（100-150字）：
[具体发生什么]

**因果关系**：
- 因为什么导致这个事件？
- 这个事件导致什么后果？

**人物选择**：
- 主角必须做什么选择？
- 这个选择揭示了什么性格？

**情绪效果**：
- 读者会有什么感受？

---

### 事件2：[事件名称]
[同上格式...]

---

## 四、支线冲突（2-3条）

| 支线 | 涉及人物 | 与主线关系 | 起止章节 |
|-----|---------|----------|---------|
| | | [平行/辅助/对照] | 第X-X章 |

---

## 五、事件时间线总览

| 章节 | 主线事件 | 支线事件 | 情绪曲线 |
|-----|---------|---------|---------|
| 1 | | | ⬛⬛⬛⬜⬜ |
| 2 | | | |
| ... | | | |
| {chapter_count} | | | |

---

### ❌ 禁止事项

- 禁止事件之间没有因果关系
- 禁止事件不改变现状
- 禁止所有事件都是打斗/灾难（要有情感戏）
- 禁止写成小说正文

📝 **输出长度**：1200-2000字
"""
        elif task_type == "伏笔列表":
            chapter_count = goal.get("chapter_count", 10)
            word_count = goal.get("word_count", 50000)
            
            # 根据章节数/字数调整伏笔数量
            if chapter_count >= 30:
                main_foreshadow = "5-8"
                char_foreshadow = "2-3"
            elif chapter_count >= 15:
                main_foreshadow = "4-6"
                char_foreshadow = "1-2"
            else:
                main_foreshadow = "3-4"
                char_foreshadow = "1"
                
            task_section = f"""
## 当前任务：{task_type} 🔮

你是一位顶级畅销小说家，正在为新书设计**伏笔系统**。

> "伏笔是作者与读者之间的秘密游戏——埋下时不动声色，揭晓时恍然大悟。" — 阿加莎·克里斯蒂

---

### 📌 任务说明

设计故事中的**伏笔网络**——那些看似不经意的细节，在后文中会产生重要意义。

📊 **本书规模**：{chapter_count}章，约{word_count//10000}万字
💡 **建议伏笔数**：主线伏笔{main_foreshadow}个，人物伏笔每人{char_foreshadow}个

---

### 🏆 顶级作家的伏笔法则

**法则一：伏笔要"藏在眼皮底下"**
- 最好的伏笔是读者看到了但没当回事
- 可以藏在对话中、环境描写中、角色习惯中
- 例：《哈利波特》中斯内普对莉莉的感情线索

**法则二：揭晓要有"啊哈！"时刻**
- 读者看到揭晓时应该有恍然大悟的感觉
- 回看时能发现所有线索都在那里
- 不能太早揭晓（失去悬念）也不能太晚（读者忘了）

**法则三：伏笔必须回收**
- 埋下的伏笔一定要揭示，否则是欺骗读者
- 每个伏笔的回收要有足够的冲击力
- 多个伏笔可以连锁揭示，制造高潮

---

### 📋 请输出以下内容

---

## 一、主线伏笔（{main_foreshadow}个）

这些伏笔直接关系到故事核心，揭示时会产生重大剧情转折。

### 伏笔1：[伏笔名称]

| 项目 | 内容 |
|-----|------|
| 伏笔内容 | [什么细节/台词/物品/行为] |
| 真正含义 | [这个细节背后的真相是什么] |

**埋设设计**：
- 埋设位置：第X章，[什么场景]
- 埋设方式：[对话/描写/行动/背景]
- 伪装技巧：[如何让读者看到但不起疑]

**揭示设计**：
- 揭示位置：第X章，[什么事件中]
- 揭示方式：[如何揭晓真相]
- 冲击效果：[读者会有什么反应]

**线索链**：
- 第一次暗示（埋设）：第X章
- 第二次呼应（强化）：第X章
- 最终揭示：第X章

---

### 伏笔2：[伏笔名称]
[同上格式...]

---

## 二、人物伏笔

每个主要人物的隐藏信息：

| 人物 | 隐藏内容 | 伏笔类型 | 埋设章节 | 揭示章节 | 揭示影响 |
|-----|---------|---------|---------|---------|---------|
| | | [身份/动机/秘密/能力/关系] | 第X章 | 第X章 | |

**人物伏笔详解**（选2-3个重要的展开）：

### [人物名]的隐藏

**伏笔内容**：
- 隐藏的是什么：
- 为什么要隐藏：

**埋设线索**：
1. 第X章：[什么细节暗示]
2. 第X章：[什么行为可疑]
3. 第X章：[什么对话有深意]

**揭示时刻**：
- 如何揭晓：
- 对其他人物的影响：
- 对剧情的影响：

---

## 三、世界观伏笔（2-3个）

关于设定的隐藏规则，后面会变得重要：

| 伏笔 | 表面理解 | 真正含义 | 埋设/揭示 |
|-----|---------|---------|----------|
| | [读者一开始以为] | [实际上是] | 第X/X章 |

---

## 四、红鲱鱼（1-2个）

故意误导读者的假线索：

| 误导内容 | 让读者以为 | 实际真相 | 揭穿章节 | 设计目的 |
|---------|----------|---------|---------|---------|
| | | | 第X章 | [转移注意力/制造意外] |

---

## 五、伏笔时间线

| 章节 | 埋设的伏笔 | 呼应/强化 | 揭示的伏笔 |
|-----|----------|----------|----------|
| 第1章 | | | |
| 第2章 | | | |
| ... | | | |
| 第{chapter_count}章 | | | |

---

## 六、伏笔关联图

```
伏笔A ─────┐
          ├──→ 揭示X（第Y章）──→ 连锁揭示
伏笔B ─────┘
         ↑
伏笔C ────┘
```

**关联说明**：
- [伏笔A]和[伏笔B]互相印证
- [伏笔C]的揭示触发[伏笔D]的揭示

---

### ❌ 禁止事项

- 禁止伏笔埋了不揭示
- 禁止揭示时机不当（太早或太晚）
- 禁止伏笔太明显（读者一看就猜到）
- 禁止伏笔和主线无关

📝 **输出长度**：1000-1500字
"""
        elif task_type == "场景物品冲突":
            word_count = goal.get("word_count", 50000)
            chapter_count = goal.get("chapter_count", 10)
            # 根据字数估算场景数量
            if word_count >= 500000:
                scene_count = "20-30"
                item_count = "10-15"
                core_scene = "5-8"
            elif word_count >= 200000:
                scene_count = "15-20"
                item_count = "8-12"
                core_scene = "4-6"
            elif word_count >= 100000:
                scene_count = "10-15"
                item_count = "6-10"
                core_scene = "3-5"
            else:
                scene_count = "8-12"
                item_count = "5-8"
                core_scene = "2-4"
                
            task_section = f"""
## 当前任务：{task_type} 🏔️

你是一位顶级畅销小说家，正在为新书设计**场景系统、重要道具和冲突层次**。

> "场景不只是故事发生的地方，它本身就是故事的一部分，像另一个角色一样影响着情节。" — 斯蒂芬·金

---

### 📌 任务说明

设计故事的**舞台**——场景让世界观有血有肉，道具推动剧情发展，冲突制造戏剧张力。

📊 **本书规模**：{chapter_count}章，约{word_count//10000}万字
💡 **建议数量**：核心场景{core_scene}个，总场景{scene_count}个，关键道具{item_count}个

---

### 🏆 顶级作家的场景法则

**法则一：场景要有"性格"**
- 好的场景有自己的气质，影响人物的行为和情绪
- 同一个场景在不同情境下可以呈现不同面貌
- 例：《了不起的盖茨比》中的码头绿灯

**法则二：道具要有"分量"**
- 关键道具应该多次出现，每次出现都有意义
- 道具的归属变化可以推动剧情
- 例：《教父》中的橙子，《哈利波特》中的魂器

**法则三：冲突要有"层次"**
- 外部冲突（人vs人/环境/命运）
- 内部冲突（人vs自己）
- 两种冲突互相影响，层层递进

---

### 📋 请输出以下内容

---

## 一、核心场景（{core_scene}个）

故事最重要的发生地，会反复出现。

### 场景1：[场景名称]

| 项目 | 内容 |
|-----|------|
| 地理位置 | |
| 重要程度 | ⭐⭐⭐⭐⭐ |
| 出现章节 | 第X、X、X章 |

**环境细节**（五感描写）：
- 👁️ 视觉：[看到什么？光线、颜色、布局]
- 👂 听觉：[有什么声音？]
- 👃 嗅觉：[有什么气味？]
- ✋ 触觉：[温度、质感？]
- 🌟 特殊元素：[独特的标志性事物]

**氛围变化**：
| 情境 | 氛围描写 |
|-----|---------|
| 日常状态 | |
| 紧张时刻 | |
| 高潮场景 | |

**叙事功能**：
- 会发生的事件：
- 与人物的关系：
- 象征意义：

---

### 场景2：[场景名称]
[同上格式...]

---

## 二、重要场景（5-8个）

关键事件发生地：

| 场景名 | 简述 | 氛围关键词 | 关联事件 | 出场章节 |
|-------|-----|----------|---------|---------|
| | | | | 第X章 |

**每个场景的一句话描写**：
1. [场景名]：[一句话画面感描写]
2. ...

---

## 三、过渡场景（5-10个）

连接场景、日常场景：

| 场景名 | 场景类型 | 用途 | 简述 |
|-------|---------|-----|-----|
| | [街道/交通/公共场所] | | |

---

## 四、关键道具（{item_count}个）

### 道具1：[道具名称]

| 项目 | 内容 |
|-----|------|
| 外观 | [大小、形状、材质、颜色] |
| 来源 | [从哪来的？有什么历史？] |
| 功能 | [能做什么？有什么限制？] |

**剧情作用**：
- 首次出现：第X章，[情境]
- 关键使用：第X章，[如何推动剧情]
- 归属变化：[谁拥有 → 谁拥有]

**道具时间线**：
| 章节 | 状态 | 持有者 |
|-----|-----|-------|
| 第X章 | 出现 | |
| 第X章 | 使用 | |
| 第X章 | 结局 | |

---

### 道具2：[道具名称]
[同上格式...]

---

## 五、象征物品（2-3个）

| 物品 | 象征含义 | 出场时机 | 与主题关系 |
|-----|---------|---------|----------|
| | | 第X、X章 | |

---

## 六、冲突层次设计

### 外部冲突

**人与人**：
| 冲突方A | 冲突方B | 冲突焦点 | 激化节点 | 解决/结果 |
|--------|--------|---------|---------|----------|
| | | | 第X章 | |

**人与环境**：
- 自然环境挑战：
- 社会环境压力：

**人与命运**：
- 不可抗力：
- 宿命感元素：

### 内部冲突

| 人物 | 内心矛盾 | 外在表现 | 转变节点 |
|-----|---------|---------|---------|
| | [想要A vs 需要B] | | 第X章 |

### 冲突升级曲线

```
第1章 ⬜⬜⬜⬜⬜ 平静
第X章 ⬛⬜⬜⬜⬜ 萌芽
第X章 ⬛⬛⬜⬜⬜ 发展
第X章 ⬛⬛⬛⬜⬜ 激化
第X章 ⬛⬛⬛⬛⬜ 爆发
第X章 ⬛⬛⬛⬛⬛ 高潮
第{chapter_count}章 ⬛⬛⬜⬜⬜ 解决
```

---

## 七、场景-事件-人物对照表

| 事件 | 场景 | 人物 | 道具 | 章节 |
|-----|-----|-----|-----|-----|
| | | | | 第X章 |

---

### ❌ 禁止事项

- 禁止场景描写空洞无特色
- 禁止道具出现后不再使用
- 禁止冲突平铺直叙不升级
- 禁止场景与剧情无关

📝 **输出长度**：1500-2500字
"""
        elif task_type == "大纲":
            chapter_count = goal.get('chapter_count', 20)
            word_count = goal.get('word_count', 50000)
            words_per_chapter = word_count // max(chapter_count, 1)
            
            # 根据字数显示
            if word_count >= 10000:
                word_display = f"{word_count // 10000}万字"
            else:
                word_display = f"{word_count}字"
            
            task_section = f"""
## 当前任务：{task_type} 📋

你是一位顶级畅销小说家，正在为新书创建**完整故事大纲**。

> "大纲是故事的骨架，它决定了一本书能否站起来。好的大纲让写作变得顺畅，差的大纲让写作变成噩梦。" — 詹姆斯·斯科特·贝尔

---

### 📌 重要约束 - 必须遵守

| 项目 | 要求 |
|-----|------|
| 总字数 | **{word_display}** |
| 章节数 | **正好 {chapter_count} 章**（不多不少！） |
| 每章字数 | 约 **{words_per_chapter}** 字 |

⚠️ **你必须规划正好 {chapter_count} 章！**

---

### 🏆 顶级作家的大纲法则

**法则一：每一章都有"钩子"**
- 章节开头要抓住读者，结尾要让读者想继续
- 最好的章节结尾是：问题解决了一半，新问题又来了

**法则二：中点反转是关键**
- 故事中点（约第{chapter_count//2}章）必须有重大转折
- 中点前是"追逐"，中点后是"被追"

**法则三：黑暗时刻必不可少**
- 在高潮前（约第{int(chapter_count*0.75)}章），主角要到最低谷
- 黑暗时刻越深，高潮越有力

---

### 📋 请输出以下内容

---

## 一、故事完整概览（重要！）

### 1. 一句话概括（Logline）
[用一句话概括整个故事：谁+想要什么+面临什么阻碍+赌注是什么]

### 2. 故事梗概（500-800字）
用**吸引人的方式**概述整个故事，从开始到结束。这段话要能让人读完就想看这本书！

**开端**：（100-150字）
[故事开始时的状态，主角是谁，世界是怎样的]

**发展**：（200-300字）
[主角遭遇什么变故，如何一步步深入困境，遇到了谁，经历了什么]

**高潮**：（100-150字）
[最大的冲突如何爆发，主角做出什么选择]

**结局**：（100-150字）
[故事如何收尾，主角最终的命运]

---

## 二、需要的人物列表（重要！人物设计任务将基于此）

⚠️ **请列出这个故事需要的所有人物**，后续【人物设计】任务会基于这个列表详细设计每个人物。

### 主要人物（1-3人）
| 人物代号 | 身份/角色 | 在故事中的作用 | 重要章节 |
|---------|---------|--------------|---------|
| [暂定名/代号] | [是什么人] | [推动什么情节] | 第X-X章 |

### 重要配角（3-8人）
| 人物代号 | 身份/角色 | 与主角关系 | 在故事中的作用 |
|---------|---------|----------|--------------|
| | | | |

### 次要人物（5-15人）
| 人物代号 | 身份 | 出场章节 | 作用 |
|---------|-----|---------|-----|
| | | 约第X章 | |

---

## 三、三幕结构总览

### 第一幕：建立与进入（第1-{max(1, chapter_count//5)}章，约占20%）

| 章节 | 功能 | 一句话描述 |
|-----|------|----------|
| 第1章 | 日常展示 | |
| 第X章 | 触发事件 | |
| 第X章 | 跨越门槛 | |

**第一幕要完成**：
- 读者了解主角是谁
- 读者关心主角的目标
- 故事正式开始

### 第二幕：对抗与发展（第{max(2, chapter_count//5+1)}-{max(3, int(chapter_count*0.8))}章，约占60%）

| 章节 | 功能 | 一句话描述 |
|-----|------|----------|
| 第X章 | 第一考验 | |
| 第X章 | 小胜利 | |
| 第{chapter_count//2}章 | **中点反转** | |
| 第X章 | 困境加深 | |
| 第{int(chapter_count*0.75)}章 | **黑暗时刻** | |

**第二幕要完成**：
- 冲突不断升级
- 人物成长变化
- 赌注越来越高

### 第三幕：高潮与结局（第{max(4, int(chapter_count*0.8)+1)}-{chapter_count}章，约占20%）

| 章节 | 功能 | 一句话描述 |
|-----|------|----------|
| 第X章 | 觉醒/准备 | |
| 第X章 | 最终对决 | |
| 第{chapter_count}章 | 结局 | |

**第三幕要完成**：
- 主要冲突解决
- 主题得到升华
- 人物完成蜕变

---

## 四、详细章节规划

⚠️ **必须规划全部 {chapter_count} 章，每章都要详细！**

### 第1章：[章节标题]

| 项目 | 内容 |
|-----|------|
| 叙事功能 | [这章要完成什么] |
| 情绪曲线 | [平静→紧张/开心→失落...] |

**章节概要**（100-150字）：
[具体发生什么]

**出场人物**：
- 主要：
- 次要：

**场景**：
- 场景1：
- 场景2：

**关键事件**：
-

**伏笔操作**：
- 埋设：
- 揭示：

**章节结尾钩子**：
[留下什么悬念让读者继续？]

---

### 第2章：[章节标题]
[同上格式...]

### 第3章：[章节标题]
[继续...]

...

### 第{chapter_count}章：[章节标题]
[最后一章]

---

## 四、人物出场规划

| 人物 | 首次出场 | 重要章节 | 关键变化 |
|-----|---------|---------|---------|
| | 第X章 | 第X、X、X章 | 第X章[什么变化] |

---

## 五、伏笔埋设与揭示

| 伏笔 | 埋设 | 强化 | 揭示 |
|-----|-----|-----|-----|
| | 第X章 | 第X章 | 第X章 |

---

## 六、情绪节奏图

```
第1章  ⬛⬛⬜⬜⬜ 平静开场
第X章  ⬛⬛⬛⬜⬜ 触发事件
第X章  ⬛⬛⬛⬛⬜ 上升行动
第{chapter_count//2}章  ⬛⬛⬛⬛⬛ 中点高潮
第X章  ⬛⬛⬜⬜⬜ 反转低落
第{int(chapter_count*0.75)}章  ⬛⬜⬜⬜⬜ 黑暗时刻
第X章  ⬛⬛⬛⬛⬜ 重新振作
第{chapter_count}章  ⬛⬛⬛⬛⬛ 最终高潮
```

---

## 七、主题贯穿

| 阶段 | 章节 | 主题如何体现 |
|-----|-----|-------------|
| 提出 | 第X章 | |
| 质疑 | 第X章 | |
| 否定 | 第X章 | |
| 升华 | 第X章 | |

---

### ✅ 检查清单

- [ ] 章节数正好是 **{chapter_count}** 章
- [ ] 每章都有明确的叙事功能
- [ ] 中点反转设计有力
- [ ] 黑暗时刻足够低
- [ ] 所有人物有出场安排
- [ ] 所有伏笔有埋设和揭示
- [ ] 章节之间衔接流畅
- [ ] 整体节奏有起有伏

📝 **输出长度**：2000-4000字（根据章节数调整）
"""
        elif task_type == "章节大纲":
            chapter_index = task.metadata.get("chapter_index", "未知")
            chapter_count = goal.get("chapter_count", 10)
            word_count = goal.get("word_count", 50000)
            words_per_chapter = word_count // max(chapter_count, 1)
            
            # 🔥 获取前面章节内容，构建连贯性上下文
            chapter_continuity = ""
            if isinstance(chapter_index, int) and chapter_index > 1:
                previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=2)
                outline_content = predecessor_contents.get("大纲", "")
                chapter_continuity = self._build_chapter_continuity_context(
                    chapter_index, previous_chapters, outline_content
                )
            
            task_section = f"""
{chapter_continuity}

## 当前任务：第{chapter_index}章 - 详细章节大纲 📝

你是一位顶级畅销小说家，正在为第{chapter_index}章创建**详细写作蓝图**。

> "好的章节像一部微型电影——有开场、有发展、有高潮、有余韵。每一章都应该让读者感到值得。" — 布兰登·桑德森

---

### ⚠️ 连贯性要求（第{chapter_index}章必须做到）

{"**这是第一章**，是故事的开端。需要：引入主角、建立世界、制造钩子。" if chapter_index == 1 else f"**必须承接第{chapter_index-1}章的结尾**！开场要从上一章结束的地方自然过渡，不能像另一个故事。"}

---

### 📌 章节信息

| 项目 | 内容 |
|-----|------|
| 章节位置 | 第 **{chapter_index}** / {chapter_count} 章 |
| 目标字数 | 约 **{words_per_chapter}** 字 |
| 建议场景数 | **4-6** 个场景 |

---

### 🏆 顶级作家的章节法则

**法则一：开头要抓人**
- 前100字必须让读者想继续读
- 可以用悬念、冲突、有趣的画面开场

**法则二：每个场景要有"转变"**
- 进入场景时的状态 ≠ 离开时的状态
- 信息变了、关系变了、或情绪变了

**法则三：结尾要有钩子**
- 章节结尾要让读者舍不得放下书
- 可以用悬念、转折、或情感冲击

---

### 📋 请输出以下内容

---

## 一、章节概览

**章节标题**：[吸引人的标题]

| 项目 | 内容 |
|-----|------|
| 叙事阶段 | [开端/发展/高潮/收尾] |
| 主要POV | [谁的视角] |
| 情绪基调 | [紧张/温馨/压抑/...] |

**本章目标**（必须完成）：
1. 📖 情节目标：[推进什么剧情]
2. 👤 人物目标：[展现/发展谁]
3. 💡 信息目标：[告诉读者什么]
4. 💗 情感目标：[让读者感到什么]

---

## 二、场景分解（4-6个场景）

### 场景1：[场景名/一句话概括]

| 项目 | 内容 |
|-----|------|
| 地点 | [参考【场景物品冲突】] |
| 时间 | [具体时间/天气] |
| 氛围 | [一个词概括] |

**出场人物**：
| 人物 | 状态 | 这场景的目标 |
|-----|-----|-------------|
| | [情绪/状态] | [想要什么] |

**场景内容**（200-300字）：

**开场**：
[如何进入这个场景？第一个画面是什么？]

**发展**：
[发生什么？对话/行动的要点]

**冲突/转变**：
[这个场景的张力点是什么？发生了什么变化？]

**结束**：
[如何过渡到下一场景？]

**关键对话要点**：
- [对话1要传达的信息]
- [对话2要传达的信息]

---

### 场景2：[场景名]
[同上格式...]

### 场景3：[场景名]
[同上格式...]

### 场景4：[场景名]
[同上格式...]

（继续到4-6个场景...）

---

## 三、伏笔操作

**本章埋设**：
| 伏笔 | 埋设方式 | 将在哪揭示 |
|-----|---------|----------|
| | [对话/描写/行动] | 第X章 |

**本章揭示**：
| 伏笔 | 揭示方式 | 读者反应 |
|-----|---------|---------|
| | | [恍然大悟/震惊/感动] |

---

## 四、情绪节奏

**本章情绪曲线**：

```
开头 [情绪] ──→ 场景2 [情绪] ──→ 中间 [情绪] ──→ 场景4 [情绪] ──→ 结尾 [情绪]
         ↗︎              ↘︎                ↗︎              ↘︎
```

**节奏控制**：
| 场景 | 节奏 | 原因 |
|-----|-----|-----|
| 场景1 | 快/中/慢 | |
| 场景2 | | |
| ... | | |

---

## 五、章节衔接

**承上**：
- 时间：[紧接上章/过了X时间]
- 情绪：[延续/转换]
- 信息：[承接什么]

**启下**：
- 悬念：[留下什么钩子]
- 铺垫：[为下章埋什么线]

---

## 六、写作备忘

**必须写好**：
- [本章最重要的场景/对话]

**避免问题**：
- [需要注意的一致性]

---

### ❌ 禁止事项

- 禁止场景之间跳跃突兀
- 禁止章节没有情绪起伏
- 禁止开头平淡无味
- 禁止结尾没有钩子

📝 **输出长度**：800-1200字
"""
        elif task_type == "场景生成":
            chapter_index = task.metadata.get("chapter_index", "未知")
            scene_index = task.metadata.get("scene_index", "未知")
            task_section = f"""
## 当前任务：第{chapter_index}章 - 场景{scene_index} 🎬

你是一位顶级畅销小说家，正在创作第{chapter_index}章的场景{scene_index}。

> "好的场景就像电影画面，读者能'看到'发生了什么。" — 詹姆斯·斯科特·贝尔

---

### 📌 场景写作要求

**核心原则**：让读者身临其境

**必须包含**：
1. **环境渲染**：用五感细节（视/听/嗅/触/味）营造氛围
2. **人物动作**：具体的行动而非笼统的描述
3. **自然对话**：符合人物性格，推动剧情
4. **情绪张力**：场景要有起伏和变化

---

### 🏆 顶级作家的场景法则

**法则一：进入场景要快**
- 直接进入动作或对话
- 不要用大段环境描写开场

**法则二：展示而非告诉**
- ❌ "他很紧张"
- ✅ "他的手指不自觉地敲着桌面，目光在门口和窗户之间来回游移"

**法则三：对话要有潜台词**
- 人物说的不一定是想的
- 对话背后要有情感和目的

---

### ❌ 禁止事项

- 禁止标注"场景X"等标记
- 禁止大段心理独白
- 禁止对话无意义的寒暄
- 禁止纯描写无动作
- 禁止违反已设定的人物性格

📝 **输出**：直接输出小说正文，800-1500字
"""
        elif task_type == "章节内容":
            chapter_index = task.metadata.get("chapter_index", "未知")
            # 计算每章目标字数
            word_count = goal.get("word_count", 50000)
            chapter_count = goal.get("chapter_count", 10)
            words_per_chapter = word_count // chapter_count
            # 设置合理的范围
            min_words = max(2000, int(words_per_chapter * 0.8))
            max_words = int(words_per_chapter * 1.2)
            
            # 🔥 获取前面章节内容，构建连贯性上下文
            chapter_continuity = ""
            if isinstance(chapter_index, int) and chapter_index > 1:
                previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=2)
                outline_content = predecessor_contents.get("大纲", "")
                chapter_continuity = self._build_chapter_continuity_context(
                    chapter_index, previous_chapters, outline_content
                )
            
            task_section = f"""
{chapter_continuity}

## 当前任务：第{chapter_index}章 - 章节内容 ✍️

你是一位顶级畅销小说家，正在创作第{chapter_index}章的**完整正文**。

> "写作的秘诀是把每一个句子都写得让读者想读下一句。" — 约翰·格里森

---

### ⚠️ 连贯性要求（最重要！）

{"**这是第一章**，是读者接触故事的第一印象。需要：吸引人的开场、引入主角、建立世界观基调、制造悬念钩子。" if chapter_index == 1 else f'''**必须从第{chapter_index-1}章结尾处衔接！**

本章开头必须：
1. 自然承接上一章的结尾场景/情绪/悬念
2. 人物状态与上一章结尾保持一致
3. 时间线和空间位置要连贯
4. 如果有时间跳跃，必须用过渡语句交代

❌ **绝对禁止**：本章开头像另一个独立的故事，与前面毫无关联'''}

---

### 📌 写作要求

| 项目 | 要求 |
|-----|------|
| 目标字数 | **{min_words}-{max_words}** 字 |
| 叙事视角 | [根据风格元素设定] |
| 语言风格 | [根据风格元素设定] |

---

### 🏆 顶级作家的写作法则

**法则一：展示，不要告诉（Show, Don't Tell）**
- ❌ "他很生气"
- ✅ "他的手指收紧，指节发白，咬着牙一字一顿地说……"

**法则二：对话要推动剧情**
- 每句对话都要有目的：揭示信息/制造冲突/展现性格
- 避免无意义的寒暄和废话

**法则三：场景转换要流畅**
- 场景之间需要过渡，不能生硬跳切
- 可以用时间跳跃、空间移动、或情绪转换

**法则四：五感细节要丰富**
- 不只是"看到"，还有听到、闻到、触到、尝到
- 细节要服务于氛围和情绪

**法则五：保持故事线索连贯**
- 每一章都是整体故事的一部分，不是独立短篇
- 前面埋的伏笔要有回应或继续铺垫
- 人物弧线要有连续性发展

---

### 📋 写作指南

**基于章节大纲，创作完整的章节正文**

**内容要求**：
1. {"从引人入胜的场景开始" if chapter_index == 1 else "从上一章结尾自然衔接开始"}
2. 按场景顺序自然展开
3. 场景之间有流畅过渡
4. 人物性格保持一致
5. 世界观设定保持一致
6. 节奏有张有弛
7. **与前面章节保持情节连贯**

**格式要求**：
- 直接输出小说正文
- 以章节标题开头（如："第{chapter_index}章 [标题]"）
- 不要输出"场景1"、"场景2"之类的标记
- 段落分明，对话独立成行

**质量标准**：
- {"开头100字要抓住读者，建立第一印象" if chapter_index == 1 else "开头要自然衔接上一章"}
- 对话要自然有节奏
- 描写要有画面感
- 结尾要有钩子，让读者想读下一章

---

### ❌ 禁止事项

- 禁止大段心理独白（要化为行动和对话）
- 禁止信息堆砌式描写
- 禁止对话冗长无重点
- 禁止场景转换生硬
- 禁止输出写作说明或注释
- **禁止与前面章节脱节，像独立短篇**

📝 **输出**：完整的章节正文，{min_words}-{max_words}字
"""
        elif task_type == "章节润色":
            chapter_index = task.metadata.get("chapter_index", "未知")
            
            # 🔥 获取前面章节内容，确保润色时保持连贯性
            chapter_continuity = ""
            if isinstance(chapter_index, int) and chapter_index > 1:
                previous_chapters = await self._get_previous_chapters(chapter_index, context, max_chapters=2)
                outline_content = predecessor_contents.get("大纲", "")
                chapter_continuity = self._build_chapter_continuity_context(
                    chapter_index, previous_chapters, outline_content
                )
            
            task_section = f"""
{chapter_continuity}

## 当前任务：第{chapter_index}章 - 章节润色 ✨

你是一位顶级文学编辑，正在为第{chapter_index}章进行**精细润色**。

> "好的写作是改出来的。第一稿是把沙子倒出来，修改是从沙子里淘金。" — 欧内斯特·海明威

---

### 📌 润色目标

把一份"好"的稿子变成"优秀"的稿子。

---

### 🏆 顶级编辑的润色法则

**法则一：删掉所有不必要的词**
- 每个形容词、每个副词都要质问：真的需要吗？
- "非常美丽的花" → "绚烂的花"

**法则二：加强动词的力度**
- 弱动词换强动词："他走过去" → "他冲过去/踱过去/溜过去"
- 动词承载情绪

**法则三：对话要能"听出"性格**
- 不同人物说话方式应该不同
- 读对话时能分辨是谁在说

**法则四：节奏感要体现在句子长度**
- 紧张时用短句
- 抒情时可以用长句
- 避免句式单调

---

### 📋 润色方向

**1. 文字层面**
- [ ] 删除冗余词汇
- [ ] 替换弱动词为强动词
- [ ] 优化形容词使用
- [ ] 调整句子节奏

**2. 描写层面**
- [ ] 补充必要的感官细节
- [ ] 强化有画面感的描写
- [ ] 删除无意义的环境描写

**3. 对话层面**
- [ ] 让对话更符合人物性格
- [ ] 删除无意义的对话
- [ ] 对话标签多样化（不只是"说"）

**4. 结构层面**
- [ ] 检查场景过渡是否流畅
- [ ] 检查节奏起伏是否合适
- [ ] 检查开头是否抓人
- [ ] 检查结尾是否有钩子

**5. 一致性检查**
- [ ] 人物性格是否一致
- [ ] 设定是否一致
- [ ] 与前后章节是否衔接

---

### ❌ 禁止事项

- 禁止改变情节走向
- 禁止改变人物关系
- 禁止添加新的剧情元素
- 禁止输出修改说明（只输出润色后的正文）

---

### 📝 输出要求

直接输出**润色后的完整章节内容**
- 不要输出对比说明
- 不要标注修改位置
- 不要写"修改前/修改后"
- 只输出最终版本
"""
        elif task_type == "一致性检查":
            task_section = f"""
## 当前任务：{task_type} 🔍

🚨🚨🚨 **极其重要的警告** 🚨🚨🚨

你是一位**质量检查员**，正在做**检查报告**，而不是写小说！！！

❌ **绝对禁止**：输出任何小说内容、故事情节、人物对话
✅ **你的任务**：只输出问题清单和评估报告

如果你输出了小说内容，说明你完全理解错了任务！这是**检查任务**，不是**创作任务**！

---

> "读者会原谅作者的写作瑕疵，但不会原谅逻辑漏洞。" — 布兰登·桑德森

---

### 📌 检查维度

**1. 人物一致性**
| 检查项 | 要点 |
|-------|------|
| 性格一致 | 人物行为是否前后矛盾 |
| 外貌一致 | 外貌描写有无冲突 |
| 背景一致 | 人物背景有无自相矛盾 |
| 关系一致 | 人物关系有无错乱 |

**2. 世界观一致性**
| 检查项 | 要点 |
|-------|------|
| 规则一致 | 设定的规则是否被违反 |
| 时间线 | 时间顺序有无矛盾 |
| 空间 | 地理/距离有无冲突 |
| 科技/魔法 | 能力体系是否自洽 |

**3. 情节一致性**
| 检查项 | 要点 |
|-------|------|
| 伏笔回收 | 埋下的伏笔是否揭示 |
| 因果关系 | 事件之间因果是否成立 |
| 情节漏洞 | 有无逻辑问题 |

---

### 📋 输出格式

**问题清单**（按严重程度排序）：

| 严重度 | 位置 | 问题描述 | 修改建议 |
|-------|-----|---------|---------|
| 🔴严重 | 第X章 | | |
| 🟡中等 | 第X章 | | |
| 🟢轻微 | 第X章 | | |

**总体评估**：
- 一致性评分：X/10
- 主要问题：
- 整体评价：

🚨🚨🚨 **再次强调** 🚨🚨🚨
- 这是**检查报告**任务
- 只输出上面格式的**问题清单**和**总体评估**
- **绝对不要**输出任何小说内容、故事情节、人物描写
- 如果检查发现没有问题，就写"未发现明显问题"
"""
        elif task_type == "评估":
            task_section = f"""
## 当前任务：{task_type} 📊

你是一位资深的文学评论家和编辑，正在对创作内容进行**专业评估**。

> "好的编辑不只是挑毛病，而是帮助作品成为它本该成为的样子。" — 罗伯特·戈特利布

---

### 📌 评估维度

| 维度 | 评分 | 说明 |
|-----|-----|------|
| **故事性** | X/10 | 情节是否吸引人？有无让人想继续读的欲望？ |
| **人物** | X/10 | 人物是否立体？有无让人记住的角色？ |
| **文学性** | X/10 | 文字是否有美感？语言是否得当？ |
| **可读性** | X/10 | 是否通俗易懂？节奏是否合适？ |
| **完整性** | X/10 | 结构是否完整？有无遗漏？ |
| **创意性** | X/10 | 有无新意？是否有独特之处？ |

---

### 📋 请输出以下内容

**一、各维度详细评分**

| 维度 | 评分 | 优点 | 不足 |
|-----|-----|-----|-----|
| 故事性 | /10 | | |
| 人物 | /10 | | |
| 文学性 | /10 | | |
| 可读性 | /10 | | |
| 完整性 | /10 | | |
| 创意性 | /10 | | |

**二、亮点总结**（3-5条）
- 

**三、待改进**（3-5条）
- 

**四、修改建议**（按优先级）
1. 🔴 必须改：
2. 🟡 建议改：
3. 🟢 可以改：

**五、总体评价**
- 综合评分：X/10
- 一句话评价：

⚠️ 这是评估报告，请客观专业。不要输出小说内容。
"""
        elif task_type == "修订":
            task_section = f"""
## 当前任务：{task_type} ✏️

你是创作这部小说的顶级畅销小说家，现在需要根据反馈**修订内容**。

> "写作是改出来的。第一稿是把沙子倒出来，修改是从沙子里淘金。" — 海明威

---

### 📌 修订原则

**优先级**：
1. 🔴 **先修逻辑**：情节漏洞、设定矛盾
2. 🟡 **再改结构**：节奏问题、结构松散
3. 🟢 **最后润色**：文字质量、细节描写

**守则**：
- 保持原有风格和基调
- 不过度改写，保留原作特点
- 确保与整体设定一致
- 改善但不改变故事核心

---

### ❌ 禁止事项

- 禁止改变已确定的情节走向
- 禁止改变人物基本性格
- 禁止添加未经规划的新元素
- 禁止输出修订说明（只输出最终内容）

---

### 📝 输出要求

直接输出**修订后的完整内容**
- 不要输出"修改前/修改后"
- 不要标注修改位置
- 不要写修改说明
- 只输出最终版本
"""
        else:
            # Default for other tasks
            task_section = f"\n## 当前任务\n{task.description}\n\n"
            task_section += f"任务类型: {task.task_type.value}\n"

            if task.metadata.get("chapter_index"):
                task_section += f"章节: 第{task.metadata['chapter_index']}章\n"
            if task.metadata.get("scene_index"):
                task_section += f"场景: {task.metadata['scene_index']}\n"

        sections.append(task_section)
        
        # 🎯 添加高分示例参考（如果有的话）
        best_example = self._get_best_example_for_task(task_type, genre)
        if best_example:
            sections.append(best_example)
            logger.info(f"📌 为任务 {task_type} 添加了高分示例参考")

        # Output format instruction based on task type
        if task_type in planning_tasks:
            sections.append("""
## 输出要求
- 使用结构化的格式输出（标题+内容）
- 语言简洁明了，每项1-3句话
- 这是规划文档，不是小说正文
- 不要写成学术论文，用通俗的语言
""")
        elif task_type in element_tasks:
            sections.append("""
## 输出要求
- 结构清晰，便于后续参考
- 描述要有文学性，但也要实用
- 这是创作素材，不是小说正文
- 适度使用描述性语言，让素材生动
""")
        elif task_type == "大纲":
            sections.append("""
## 输出要求
- 完整输出故事大纲
- 章节规划要覆盖所有章节
- 用叙事性的语言，让大纲本身也有可读性
- 不要输出标题或额外说明，直接输出大纲内容
""")
        else:
            # Content generation tasks
            sections.append("""
## 输出要求
请直接输出小说内容，使用文学化的语言：
- 必须是故事性的、叙事性的内容
- 使用生动、形象的文学语言
- 内容应该适合普通读者阅读
- 不需要额外的说明、标题或标注

📖 科幻小说要点：
- 科学概念要通过故事情节呈现，不是写技术文档
- 复杂设定用对话、场景、隐喻等方式自然融入
- 技术细节服务于氛围和情节，不是详尽罗列
- 参考刘慈欣的手法：用通俗的方式讲复杂的科学

你在写给科幻爱好者看的小说，不是写给研究者看的论文！
""")

        prompt = "".join(sections)
        
        # 🧬 检查是否有进化后的更优提示词片段
        if self.enable_self_evolution:
            evolved_prompt = self.prompt_evolver.get_best_prompt(task_type)
            if evolved_prompt:
                # 将进化后的优化建议添加到提示词末尾
                prompt += f"""

════════════════════════════════════════════════════════════════
🧬 【提示词进化优化 - 基于历史反馈】
════════════════════════════════════════════════════════════════

根据以往的评估反馈，请特别注意以下优化建议：

{evolved_prompt}

════════════════════════════════════════════════════════════════
"""
                logger.info(f"📈 已加载进化提示词: {task_type}")
        
        return prompt

    async def _attempt_rewrite(
        self,
        task: Task,
        content: str,
        evaluation: EvaluationResult,
        context: MemoryContext,
        goal: Dict[str, Any],
        max_retries: int = 999,  # 不限制次数，直到通过为止
        token_stats: Dict[str, int] = None,  # 🔥 用于累计 token 统计
    ) -> tuple:
        """
        Attempt to rewrite content based on evaluation feedback until it passes
        
        Returns:
            tuple: (final_content, token_stats_dict)
            token_stats_dict 包含: total_tokens, prompt_tokens, completion_tokens, cost
        """

        logger.info(f"🔄 开始重写任务 {task.task_id}，直到评估通过为止")

        # 初始化统计
        if token_stats is None:
            token_stats = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}

        attempt = 0
        current_content = content
        current_evaluation = evaluation
        
        # 🔥 获取一致性检查结果（如果有的话）
        consistency_result = task.metadata.get("consistency_check_result", None)
        
        while attempt < max_retries:
            attempt += 1
            logger.info(f"🔄 重写尝试 #{attempt} - 任务: {task.task_type.value}")
            
            # 通知前端重试状态
            if self._on_task_start:
                task.metadata["retry_count"] = attempt
                task.metadata["retry_reason"] = f"评估未通过 (得分: {current_evaluation.score:.2f})"
                await self._safe_callback(self._on_task_start, task)

            # Build improved prompt with feedback
            # 🔥 传递一致性检查结果
            feedback_prompt = self._build_rewrite_prompt(
                task=task,
                original_content=current_content,
                evaluation=current_evaluation,
                context=context,
                goal=goal,
                attempt=attempt,
                consistency_result=consistency_result,  # 传递一致性检查结果
            )

            try:
                response = await self.llm_client.generate(
                    prompt=feedback_prompt,
                    task_type=task.task_type.value,
                    temperature=min(0.7 + attempt * 0.05, 1.0),  # 逐渐提高温度增加变化
                    max_tokens=self._get_max_tokens_for_task(task.task_type),
                )
                
                # 🔥 累计重写过程中的 token 消耗
                token_stats["total_tokens"] += response.usage.total_tokens
                token_stats["prompt_tokens"] += response.usage.prompt_tokens
                token_stats["completion_tokens"] += response.usage.completion_tokens
                token_stats["cost"] += self._calculate_cost(
                    response.provider.value, response.model, response.usage
                )

                # Re-evaluate
                new_evaluation = await self.evaluator.evaluate(
                    task_type=task.task_type.value,
                    content=response.content,
                    context=context.to_dict(),
                    goal=goal,
                )

                if new_evaluation.passed:
                    logger.info(f"✅ 重写成功！尝试 #{attempt}，得分: {new_evaluation.score:.2f}")
                    self.stats.retried_tasks += 1
                    task.metadata["final_retry_count"] = attempt
                    return response.content, token_stats

                # Update for next retry
                current_content = response.content
                current_evaluation = new_evaluation
                
                # 🔥 记录失败尝试次数
                task.failed_attempts += 1
                
                logger.warning(
                    f"⚠️ 尝试 #{attempt} 未通过评估，得分: {new_evaluation.score:.2f}，继续重试..."
                )
                
                # 每5次重试暂停一下，避免过快请求
                if attempt % 5 == 0:
                    logger.info(f"⏸️ 已重试 {attempt} 次，暂停2秒后继续...")
                    await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ 重写尝试 #{attempt} 失败: {e}")
                task.failed_attempts += 1
                # 出错后等待一下再重试
                await asyncio.sleep(1)
                continue

        # 理论上不应该到达这里（max_retries=999）
        logger.warning(f"⚠️ 任务 {task.task_id} 达到最大重试次数 {max_retries}")
        task.metadata["final_retry_count"] = attempt
        return current_content, token_stats

    def _build_rewrite_prompt(
        self,
        task: Task,
        original_content: str,
        evaluation: EvaluationResult,
        context: MemoryContext,
        goal: Dict[str, Any],
        attempt: int = 1,
        consistency_result: Dict[str, Any] = None,  # 🔥 新增参数
    ) -> str:
        """Build prompt for content rewriting with retry information and consistency feedback"""
        
        task_type = task.task_type.value
        chapter_index = task.metadata.get("chapter_index", None)
        
        # 根据重试次数调整提示强度
        urgency = ""
        if attempt >= 3:
            urgency = f"""
⚠️ **警告**：这是第 {attempt} 次重写尝试！
请认真阅读评估反馈，针对性地修改问题。不要只是小修小补，要从根本上解决问题。
"""
        if attempt >= 5:
            urgency = f"""
🚨 **紧急**：这是第 {attempt} 次重写尝试！
之前的修改显然没有解决核心问题。请：
1. 仔细阅读每一条反馈
2. 思考为什么之前的修改没有效果
3. 尝试完全不同的写作方式
"""

        # 🔥 构建一致性问题部分（如果有一致性检查失败）
        consistency_section = ""
        if consistency_result and not consistency_result.get("passed", True):
            issues = consistency_result.get("issues", [])
            suggestions = consistency_result.get("suggestions", [])
            continuity_issues = consistency_result.get("continuity_issues", [])
            score = consistency_result.get("score", 0)
            
            consistency_section = f"""
## 🚨 一致性检查失败（必须修复！）

一致性评分：{score:.2f}/1.00

"""
            if issues:
                consistency_section += f"""### ❌ 发现的一致性问题
{chr(10).join(f'- {issue}' for issue in issues)}

"""
            
            if continuity_issues:
                consistency_section += f"""### ❌ 章节连贯性问题（非常重要！）
{chr(10).join(f'- {issue}' for issue in continuity_issues)}

**重要**：这些连贯性问题说明当前章节像独立短篇，与前面章节脱节！
必须确保：
1. 开头自然衔接上一章结尾
2. 人物状态延续（位置、情绪、正在做的事）
3. 时间线连贯
4. 情节有承接关系

"""
            
            if suggestions:
                consistency_section += f"""### 💡 修改建议
{chr(10).join(f'- {s}' for s in suggestions)}

"""

        prompt = f"""## 重写任务（第 {attempt} 次尝试）

任务类型: {task_type}
{f"章节: 第{chapter_index}章" if chapter_index else ""}
描述: {task.description}
{urgency}

{consistency_section}

## 原始内容
```
{original_content[:3000]}
```

## 评估反馈
总体评分: {evaluation.score:.2f}/1.00
状态: {'未通过' if not evaluation.passed else '通过'}

### 问题原因（必须解决）:
{chr(10).join(f'❌ {r}' for r in evaluation.reasons[:5])}

改进建议:
{chr(10).join(f'- {s}' for s in evaluation.suggestions[:5])}

## 重写要求
请根据评估反馈改进内容，**必须解决所有一致性和连贯性问题**。

{"特别注意：确保本章开头与前一章结尾自然衔接，不要像另一个独立故事！" if chapter_index and chapter_index > 1 else ""}

## 输出要求
请直接输出改进后的内容，不需要解释或说明。
"""

        return prompt

    def _calculate_cost(self, provider: str, model: str, usage) -> float:
        """
        计算 API 调用的费用（美元）
        
        基于不同提供商和模型的定价计算。
        
        Args:
            provider: LLM 提供商（deepseek, aliyun, ark 等）
            model: 模型名称
            usage: token 使用统计对象
            
        Returns:
            费用（美元）
        """
        # 定价表（每百万 token 的价格，美元）
        # 注意：这些价格可能会变化，需要定期更新
        pricing = {
            # DeepSeek 定价（很便宜）
            "deepseek": {
                "deepseek-chat": {"input": 0.14, "output": 0.28},
                "deepseek-reasoner": {"input": 0.55, "output": 2.19},
                "default": {"input": 0.14, "output": 0.28},
            },
            # 阿里云通义千问定价（人民币转美元，汇率约 7.2）
            "aliyun": {
                "qwen-long": {"input": 0.07, "output": 0.28},  # 0.5/3.5M tokens CNY
                "qwen-max": {"input": 2.78, "output": 8.33},  # 20/60 CNY per M
                "qwen-plus": {"input": 0.56, "output": 1.39},  # 4/10 CNY per M
                "qwen-turbo": {"input": 0.14, "output": 0.28},
                "default": {"input": 0.07, "output": 0.28},
            },
            # 火山引擎 Ark (豆包) 定价
            "ark": {
                "doubao-pro": {"input": 0.11, "output": 0.28},  # 0.8/2 CNY per M
                "doubao-lite": {"input": 0.04, "output": 0.14},
                "default": {"input": 0.11, "output": 0.28},
            },
            # 默认定价（保守估计）
            "default": {"input": 0.50, "output": 1.00},
        }
        
        # 获取提供商定价
        provider_pricing = pricing.get(provider, pricing["default"])
        
        # 获取模型定价
        if isinstance(provider_pricing, dict) and "input" in provider_pricing:
            model_pricing = provider_pricing
        else:
            # 尝试匹配模型名称
            model_pricing = None
            for key in provider_pricing:
                if key != "default" and key in model.lower():
                    model_pricing = provider_pricing[key]
                    break
            if not model_pricing:
                model_pricing = provider_pricing.get("default", pricing["default"])
        
        # 计算费用
        input_cost = (usage.prompt_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (usage.completion_tokens / 1_000_000) * model_pricing["output"]
        
        return input_cost + output_cost

    def _get_temperature_for_task(self, task_type: NovelTaskType) -> float:
        """Get appropriate temperature for a task type"""
        # Creative tasks need higher temperature
        high_temp_tasks = {
            NovelTaskType.CHAPTER_CONTENT,
            NovelTaskType.SCENE_GENERATION,
            NovelTaskType.REVISION,
        }

        # Structured tasks need lower temperature
        low_temp_tasks = {
            NovelTaskType.OUTLINE,
            NovelTaskType.CHARACTER_DESIGN,
            NovelTaskType.WORLDVIEW_RULES,
            NovelTaskType.CONSISTENCY_CHECK,
        }

        if task_type in high_temp_tasks:
            return 0.8
        elif task_type in low_temp_tasks:
            return 0.5
        else:
            return 0.7

    def _get_max_tokens_for_task(self, task_type: NovelTaskType) -> int:
        """Get appropriate max tokens for a task type"""
        # 章节内容需要最多 tokens
        if task_type == NovelTaskType.CHAPTER_CONTENT:
            return 16000  # 约 12000 字中文
        
        # 大纲和场景生成需要较多 tokens
        elif task_type in {NovelTaskType.OUTLINE, NovelTaskType.SCENE_GENERATION, NovelTaskType.CHAPTER_OUTLINE}:
            return 8000  # 约 6000 字中文
        
        # 规划类任务需要足够空间
        elif task_type in {NovelTaskType.CHARACTER_DESIGN, NovelTaskType.WORLDVIEW_RULES, 
                           NovelTaskType.EVENTS, NovelTaskType.SCENES_ITEMS_CONFLICTS, NovelTaskType.FORESHADOW_LIST}:
            return 8000  # 约 6000 字中文
        
        # 其他任务
        else:
            return 4000  # 约 3000 字中文
    
    async def _check_and_save_high_score_example(
        self, 
        task_type: str, 
        genre: str, 
        content: str, 
        score: float,
        evaluation: Any
    ) -> bool:
        """
        🎯 检查内容是否为高分，如果是则保存为示例供后续任务参考
        
        Args:
            task_type: 任务类型
            genre: 小说类型（仙侠、科幻、言情等）
            content: 生成的内容
            score: 评分（0-1）
            evaluation: 评估结果对象
            
        Returns:
            bool: 是否保存为高分示例
        """
        score_100 = int(score * 100)
        
        # 只有超过阈值的内容才考虑保存
        if score_100 < self.high_score_threshold:
            return False
        
        # 初始化存储结构
        if task_type not in self.best_examples:
            self.best_examples[task_type] = {}
        
        # 检查该类型+题材是否已有更高分的示例
        current_best = self.best_examples[task_type].get(genre)
        
        if current_best is None or score_100 > current_best.get("score", 0):
            # 截取内容摘要（不超过2000字）
            content_summary = content[:2000] + "..." if len(content) > 2000 else content
            
            # 提取评估中的优点（如果有的话）
            strengths = []
            if hasattr(evaluation, 'dimension_scores') and evaluation.dimension_scores:
                for dim, data in evaluation.dimension_scores.items():
                    if isinstance(data, dict) and data.get('score', 0) >= 80:
                        strengths.append(f"{dim}: {data.get('reason', '表现优秀')}")
            
            # 保存为最佳示例
            self.best_examples[task_type][genre] = {
                "score": score_100,
                "content": content_summary,
                "strengths": strengths,
                "saved_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"🏆 记录高分示例: {task_type}/{genre} 得分 {score_100}/100")
            return True
        
        return False
    
    def _get_best_example_for_task(self, task_type: str, genre: str) -> Optional[str]:
        """
        🎯 获取该任务类型和题材的最佳示例（用于提示词参考）
        
        Returns:
            Optional[str]: 格式化的示例文本，如果没有则返回 None
        """
        if task_type not in self.best_examples:
            return None
        
        # 优先获取同题材的示例
        example = self.best_examples[task_type].get(genre)
        
        # 如果没有同题材的，尝试获取通用的
        if not example and genre != "通用":
            example = self.best_examples[task_type].get("通用")
        
        if not example:
            return None
        
        strengths_text = ""
        if example.get("strengths"):
            strengths_text = "\n**优点**:\n" + "\n".join(f"- {s}" for s in example["strengths"])
        
        return f"""
---
📌 **高分参考示例**（评分: {example['score']}/100）
{strengths_text}

**内容摘要**:
{example['content']}
---
"""

    def _get_memory_type_for_task(self, task_type: NovelTaskType) -> MemoryType:
        """Map task type to memory type for storage
        
        所有核心任务都需要被正确分类存储到向量数据库，
        方便后续章节创作时能够检索到相关内容。
        """
        mapping = {
            # 核心创意阶段 - 使用 GENERAL（最重要，会被频繁检索）
            NovelTaskType.CREATIVE_BRAINSTORM: MemoryType.GENERAL,
            NovelTaskType.STORY_CORE: MemoryType.GENERAL,
            
            # 元素创建阶段
            NovelTaskType.CHARACTER_DESIGN: MemoryType.CHARACTER,
            NovelTaskType.WORLDVIEW_RULES: MemoryType.WORLDVIEW,
            
            # 风格定位阶段
            NovelTaskType.THEME_CONFIRMATION: MemoryType.GENERAL,
            NovelTaskType.STYLE_ELEMENTS: MemoryType.GENERAL,
            NovelTaskType.MARKET_POSITIONING: MemoryType.GENERAL,
            
            # 情节阶段
            NovelTaskType.EVENTS: MemoryType.PLOT,
            NovelTaskType.SCENES_ITEMS_CONFLICTS: MemoryType.SCENE,
            NovelTaskType.FORESHADOW_LIST: MemoryType.FORESHADOW,
            
            # 大纲阶段
            NovelTaskType.OUTLINE: MemoryType.OUTLINE,
            NovelTaskType.CONSISTENCY_CHECK: MemoryType.GENERAL,
            
            # 章节阶段
            NovelTaskType.CHAPTER_OUTLINE: MemoryType.CHAPTER,
            NovelTaskType.SCENE_GENERATION: MemoryType.SCENE,
            NovelTaskType.CHAPTER_CONTENT: MemoryType.CHAPTER,
            NovelTaskType.CHAPTER_POLISH: MemoryType.CHAPTER,
        }

        return mapping.get(task_type, MemoryType.GENERAL)

    def _collect_outputs(self) -> Dict[str, str]:
        """Collect all task outputs"""
        outputs = {}

        # Get completed tasks from planner
        for task in self.planner.get_tasks_by_status("completed"):
            if task.result:
                key = f"{task.task_type.value}"
                if task.metadata.get("chapter_index"):
                    key += f"_ch{task.metadata['chapter_index']}"
                outputs[key] = task.result

        return outputs

    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Safely execute a callback"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    # Control methods

    def pause(self) -> None:
        """Pause execution"""
        self.is_paused = True
        self.status = ExecutionStatus.PAUSED
        logger.info(f"Paused execution for session {self.session_id}")

    def resume(self) -> None:
        """Resume execution"""
        self.is_paused = False
        self.status = ExecutionStatus.RUNNING
        logger.info(f"Resumed execution for session {self.session_id}")

    def stop(self) -> None:
        """Stop execution"""
        self.is_running = False
        self.status = ExecutionStatus.STOPPED
        logger.info(f"Stopped execution for session {self.session_id}")

    def approve_task(self, action: str = 'approve', feedback: Optional[str] = None, selected_idea: Optional[int] = None) -> None:
        """
        Approve or reject the current task result
        
        Args:
            action: 'approve', 'reject', or 'regenerate'
            feedback: Optional feedback for regeneration
            selected_idea: For brainstorm tasks, the number of the selected idea (1-4)
        """
        if not self.is_waiting_approval:
            logger.warning("No task is waiting for approval")
            return
        
        self.approval_result = {
            'action': action,
            'feedback': feedback,
            'selected_idea': selected_idea
        }
        self._approval_event.set()
        logger.info(f"Task approval: {action}" + (f", selected idea: {selected_idea}" if selected_idea else ""))

    def get_status(self) -> ExecutionStatus:
        """Get current execution status"""
        return self.status

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress"""
        return self.planner.get_progress()

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.stats.to_dict()
    
    @staticmethod
    def get_genre_specific_guide(genre: str) -> str:
        """
        🎯 获取针对特定小说类型的创作指南
        
        不同类型的小说有不同的创作要点和禁忌，
        这个方法返回类型特定的提示词，帮助AI写出符合类型特点的内容。
        
        Args:
            genre: 小说类型
            
        Returns:
            str: 类型特定的创作指南
        """
        genre_guides = {
            "科幻": """
🔬 **科幻小说创作要点**

**类型特色**：
- 以科学或技术设定为核心驱动故事
- 探讨科技对人类/社会的影响
- 创造令人惊叹的未来/平行世界

**必须做到**：
- 科学设定要自洽（不需要完全准确，但要能自圆其说）
- 用故事讲科学，而非科普式解释
- 技术细节融入情节，不要单独讲解
- 人物情感和科技设定同样重要

**经典参考**：《三体》《流浪地球》《银河帝国》《沙丘》

**常见问题**：
- ❌ 大段技术原理解释
- ❌ 过于追求"硬核"而牺牲可读性
- ❌ 人物只是展示科技的工具
- ✅ 用角色的眼睛展示世界
""",
            "仙侠": """
⚔️ **仙侠小说创作要点**

**类型特色**：
- 修仙求道的主线
- 江湖恩怨、门派争斗
- 天道规则、境界突破

**必须做到**：
- 修炼体系设定清晰（炼气→筑基→金丹...）
- 突出快意恩仇的江湖气
- 人物要有"道心"和追求
- 打斗描写要有画面感

**经典参考**：《凡人修仙传》《遮天》《仙逆》《诛仙》

**常见问题**：
- ❌ 境界划分混乱
- ❌ 主角金手指过于离谱
- ❌ 配角智商下线
- ✅ 注重修炼过程的合理性
""",
            "玄幻": """
✨ **玄幻小说创作要点**

**类型特色**：
- 自由度高，设定可以天马行空
- 强调"爽感"和主角成长
- 异世界冒险、升级打怪

**必须做到**：
- 力量体系设定明确
- 主角的"金手指"要有代价或限制
- 升级节奏要有松有紧
- 要有让读者期待的长期目标

**经典参考**：《斗破苍穹》《斗罗大陆》《完美世界》《武动乾坤》

**常见问题**：
- ❌ 主角无脑碾压没有挑战
- ❌ 配角全是衬托主角的工具人
- ❌ 升级太快缺乏积累感
- ✅ 每个强敌都让读者印象深刻
""",
            "言情": """
💕 **言情小说创作要点**

**类型特色**：
- 以感情线为核心
- 男女主的情感发展是主线
- 强调情感的细腻表达

**必须做到**：
- 男女主人设要立体、有魅力
- 感情发展要有层次，不能太突兀
- 注重细节描写和氛围营造
- 误会/阻碍要合理，不能太刻意

**经典参考**：《何以笙箫默》《微微一笑很倾城》《你好，旧时光》

**常见问题**：
- ❌ 为虐而虐，误会太牵强
- ❌ 男/女主人设崩塌
- ❌ 配角刻意制造矛盾
- ✅ 甜与虐的节奏要平衡
""",
            "悬疑": """
🔍 **悬疑小说创作要点**

**类型特色**：
- 以解谜、查案为核心
- 设置悬念吸引读者
- 层层剥茧、逻辑推理

**必须做到**：
- 线索要公平，不能藏着关键信息
- 推理逻辑要严密
- 节奏要紧凑，保持紧张感
- 反转要在情理之中

**经典参考**：《白夜行》《嫌疑人X的献身》《福尔摩斯》《坏小孩》

**常见问题**：
- ❌ 关键线索没给读者就揭晓答案
- ❌ 推理过程有明显漏洞
- ❌ 为反转而反转，不合逻辑
- ✅ 让读者可以一起推理
""",
            "都市": """
🏙️ **都市小说创作要点**

**类型特色**：
- 现代都市为背景
- 贴近现实生活
- 职场、商战、人际关系

**必须做到**：
- 设定要贴合现实（除非是都市异能类）
- 人物职业、生活要真实可信
- 对话要有现代感
- 情节要接地气

**经典参考**：《遥远的救世主》《余罪》《杜拉拉升职记》

**常见问题**：
- ❌ 主角开局就是顶级大佬
- ❌ 对职业/行业描写不专业
- ❌ 人物言行脱离现实
- ✅ 让读者有代入感
""",
            "武侠": """
🗡️ **武侠小说创作要点**

**类型特色**：
- 江湖侠客、快意恩仇
- 武功招式、武林门派
- 侠之大者，为国为民

**必须做到**：
- 武功招式描写要有画面感
- 江湖规矩、门派设定要合理
- 人物要有侠义精神
- 情节要有武侠的氛围感

**经典参考**：金庸系列、古龙系列、《雪中悍刀行》

**常见问题**：
- ❌ 武功越写越离谱
- ❌ 侠义精神空洞
- ❌ 江湖味不够
- ✅ 注重"侠"的内涵
""",
            "历史": """
📜 **历史小说创作要点**

**类型特色**：
- 以历史事件/人物为背景
- 还原历史氛围
- 可以是架空但要有历史感

**必须做到**：
- 重大历史事件要有据可查
- 人物言行要符合时代
- 器物、服饰、习俗要考究
- 即使架空也要有历史质感

**经典参考**：《明朝那些事儿》《大明王朝1566》《庆余年》

**常见问题**：
- ❌ 明显的历史错误
- ❌ 人物思维太现代
- ❌ 细节穿帮
- ✅ 让读者感受到时代氛围
""",
        }
        
        # 获取类型指南，如果没有特定类型则返回通用指南
        guide = genre_guides.get(genre, f"""
📚 **{genre}小说创作要点**

**通用原则**：
- 遵循{genre}类型的惯例和读者期待
- 人物塑造要立体真实
- 情节发展要有逻辑
- 保持类型的核心吸引力

请发挥你对{genre}类型的理解，创作符合类型特色的内容。
""")
        
        return guide
