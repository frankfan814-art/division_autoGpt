"""
自动化测试：生成 4000 字科幻小说并验证质量标准

测试流程：
1. 初始化创作会话
2. 生成风格定义
3. 生成大纲
4. 生成人物设定
5. 生成章节内容（直到达到 4000 字）
6. 质量验证

验收标准：
- 总字数 ≥ 4000 字
- 整体质量评分 ≥ 0.7
- 所有维度评分 ≥ 0.6
- 文本连贯性良好
- 符合科幻风格要求
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.core.vector_memory import VectorMemoryManager
from creative_autogpt.core.task_planner import TaskPlanner, NovelTaskType
from creative_autogpt.core.evaluator import EvaluationEngine, EvaluationCriterion
from creative_autogpt.core.loop_engine import LoopEngine, ExecutionStatus
from creative_autogpt.modes.novel import NovelMode
from creative_autogpt.storage.vector_store import VectorStore, MemoryType
from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.utils.logger import setup_logger, logger
from creative_autogpt.utils.config import get_settings


# 测试配置
TEST_CONFIG = {
    "genre": "科幻",
    "target_words": 4000,
    "min_quality_score": 0.7,
    "min_dimension_score": 0.6,
    "max_retry_per_task": 2,
    "chapter_word_count": 800,  # 每章约 800 字
}


class SciFiNovelTest:
    """科幻小说生成测试类"""

    def __init__(self):
        self.session_id = f"test_scifi_{int(time.time())}"
        self.test_results = {
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "config": TEST_CONFIG,
            "stages": {},
            "content": {},
            "quality_scores": {},
            "passed": False,
            "errors": [],
        }

        # Initialize components
        self.llm_client = MultiLLMClient()
        self.vector_store = VectorStore()
        self.memory = VectorMemoryManager(vector_store=self.vector_store)
        self.evaluator = EvaluationEngine(llm_client=self.llm_client)
        self.session_storage = SessionStorage()
        self.novel_mode = NovelMode()

        # Task tracking
        self.total_word_count = 0
        self.generated_chapters = []

    async def initialize(self):
        """初始化测试环境"""
        logger.info("=" * 80)
        logger.info("📚 科幻小说自动化测试开始")
        logger.info("=" * 80)
        logger.info(f"会话 ID: {self.session_id}")
        logger.info(f"目标字数: {TEST_CONFIG['target_words']} 字")
        logger.info(f"最低质量分: {TEST_CONFIG['min_quality_score']}")
        logger.info("=" * 80)

        try:
            # Create session
            session_goal = {
                "genre": TEST_CONFIG["genre"],
                "scope": "short",
                "target_words": TEST_CONFIG["target_words"],
                "theme": "星际探索与人工智能",
                "style_elements": ["硬核科幻", "太空歌剧", "技术奇点"],
            }
            
            session_config = {
                "max_retry": TEST_CONFIG["max_retry_per_task"],
                "chapter_word_count": TEST_CONFIG["chapter_word_count"],
            }

            created_session_id = await self.session_storage.create_session(
                title=f"科幻小说测试 - {TEST_CONFIG['genre']}",
                mode="novel",
                goal=session_goal,
                config=session_config,
            )
            
            # Use the created session_id
            self.session_id = created_session_id

            logger.info("✓ 会话创建成功")
            self.test_results["stages"]["initialization"] = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }
            return True

        except Exception as e:
            logger.error(f"✗ 初始化失败: {e}")
            self.test_results["errors"].append(f"Initialization error: {str(e)}")
            self.test_results["stages"]["initialization"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            return False

    async def generate_style(self) -> bool:
        """生成风格定义"""
        logger.info("\n" + "=" * 80)
        logger.info("📝 阶段 1: 生成风格定义")
        logger.info("=" * 80)

        try:
            prompt = """请为以下科幻小说创作定义写作风格：

主题：星际探索与人工智能
元素：硬核科幻、太空歌剧、技术奇点

要求：
1. 明确写作风格（如：理性冷静、宏大史诗等）
2. 定义叙事手法（如：第三人称全知视角）
3. 确定语言特色（如：技术细节丰富、描写精确）
4. 约 200 字

请直接输出风格定义，不要包含其他说明。"""

            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="风格元素",
                temperature=0.8,
                max_tokens=500,
            )

            content = response.content.strip()
            self.test_results["content"]["style"] = content

            # Store in memory
            await self.memory.store(
                content=content,
                task_id=f"{self.session_id}_style",
                task_type="风格元素",
                memory_type=MemoryType.GENERAL,
                metadata={
                    "session_id": self.session_id,
                    "stage": "style_definition",
                    "content_type": "style",
                },
            )

            logger.info(f"✓ 风格定义生成完成")
            logger.info(f"内容预览: {content[:100]}...")
            logger.info(f"字数: {len(content)}")

            self.test_results["stages"]["style"] = {
                "status": "success",
                "word_count": len(content),
                "provider": response.provider.value,
                "timestamp": datetime.now().isoformat(),
            }
            return True

        except Exception as e:
            logger.error(f"✗ 风格定义生成失败: {e}")
            self.test_results["errors"].append(f"Style generation error: {str(e)}")
            self.test_results["stages"]["style"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            return False

    async def generate_outline(self) -> bool:
        """生成小说大纲"""
        logger.info("\n" + "=" * 80)
        logger.info("📋 阶段 2: 生成小说大纲")
        logger.info("=" * 80)

        try:
            # Retrieve style from memory
            style_memories = await self.memory.search(
                query="风格定义",
                memory_type=MemoryType.GENERAL,
                top_k=1,
            )
            style_context = style_memories[0].item.content if style_memories else ""

            prompt = f"""请为以下科幻小说创作大纲：

【风格定义】
{style_context}

【小说设定】
- 类型：科幻小说
- 主题：星际探索与人工智能
- 目标字数：约 4000 字
- 章节数：5 章

【大纲要求】
1. 列出 5 个章节的标题和主要情节
2. 每章情节描述 100-150 字
3. 确保情节连贯，有起承转合
4. 体现科幻元素和主题

请按以下格式输出：

第一章：[标题]
[情节描述]

第二章：[标题]
[情节描述]

...

直接输出大纲，不要其他说明。"""

            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="大纲",
                temperature=0.8,
                max_tokens=1500,
            )

            content = response.content.strip()
            self.test_results["content"]["outline"] = content

            # Store in memory
            await self.memory.store(
                content=content,
                task_id=f"{self.session_id}_outline",
                task_type="大纲",
                memory_type=MemoryType.OUTLINE,
                metadata={
                    "session_id": self.session_id,
                    "stage": "outline",
                },
            )

            logger.info(f"✓ 大纲生成完成")
            logger.info(f"内容预览:\n{content[:300]}...")
            logger.info(f"字数: {len(content)}")

            self.test_results["stages"]["outline"] = {
                "status": "success",
                "word_count": len(content),
                "provider": response.provider.value,
                "timestamp": datetime.now().isoformat(),
            }
            return True

        except Exception as e:
            logger.error(f"✗ 大纲生成失败: {e}")
            self.test_results["errors"].append(f"Outline generation error: {str(e)}")
            self.test_results["stages"]["outline"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            return False

    async def generate_characters(self) -> bool:
        """生成人物设定"""
        logger.info("\n" + "=" * 80)
        logger.info("👥 阶段 3: 生成人物设定")
        logger.info("=" * 80)

        try:
            # Retrieve context
            outline_memories = await self.memory.search(
                query="大纲",
                memory_type=MemoryType.OUTLINE,
                top_k=1,
            )
            outline_context = outline_memories[0].item.content if outline_memories else ""

            prompt = f"""请为以下科幻小说创作主要人物设定：

【小说大纲】
{outline_context[:500]}...

【人物要求】
1. 设计 3-4 个主要人物
2. 每个人物包含：姓名、身份、性格特点、背景故事
3. 人物设定要符合科幻背景
4. 每个人物描述 100-150 字

请按以下格式输出：

【人物一】李晨
身份：星际舰队指挥官
性格：...
背景：...

【人物二】...

直接输出人物设定，不要其他说明。"""

            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="人物设计",
                temperature=0.8,
                max_tokens=1200,
            )

            content = response.content.strip()
            self.test_results["content"]["characters"] = content

            # Store in memory
            await self.memory.store(
                content=content,
                task_id=f"{self.session_id}_characters",
                task_type="人物设计",
                memory_type=MemoryType.CHARACTER,
                metadata={
                    "session_id": self.session_id,
                    "stage": "character_design",
                },
            )

            logger.info(f"✓ 人物设定完成")
            logger.info(f"内容预览:\n{content[:200]}...")
            logger.info(f"字数: {len(content)}")

            self.test_results["stages"]["characters"] = {
                "status": "success",
                "word_count": len(content),
                "provider": response.provider.value,
                "timestamp": datetime.now().isoformat(),
            }
            return True

        except Exception as e:
            logger.error(f"✗ 人物设定生成失败: {e}")
            self.test_results["errors"].append(f"Character generation error: {str(e)}")
            self.test_results["stages"]["characters"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            return False

    async def generate_chapter(self, chapter_num: int) -> tuple[bool, str]:
        """生成单个章节"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📖 阶段 4.{chapter_num}: 生成第 {chapter_num} 章")
        logger.info("=" * 80)

        try:
            # Retrieve all context
            style_memories = await self.memory.search(
                query="风格",
                memory_type=MemoryType.GENERAL,
                top_k=1,
            )
            outline_memories = await self.memory.search(
                query="大纲",
                memory_type=MemoryType.OUTLINE,
                top_k=1,
            )
            character_memories = await self.memory.search(
                query="人物",
                memory_type=MemoryType.CHARACTER,
                top_k=1,
            )

            style_context = style_memories[0].item.content if style_memories else ""
            outline_context = outline_memories[0].item.content if outline_memories else ""
            character_context = character_memories[0].item.content if character_memories else ""

            # Get previous chapter if exists
            previous_chapter = ""
            if len(self.generated_chapters) > 0:
                previous_chapter = f"\n【上一章内容】\n{self.generated_chapters[-1][:300]}...\n"

            prompt = f"""请创作科幻小说的第 {chapter_num} 章内容：

【风格要求】
{style_context}

【人物设定】
{character_context[:400]}...

【大纲参考】
{outline_context[:500]}...
{previous_chapter}
【创作要求】
1. 严格按照大纲中第 {chapter_num} 章的情节展开
2. 字数：约 {TEST_CONFIG['chapter_word_count']} 字
3. 包含生动的场景描写和人物对话
4. 体现科幻元素和技术细节
5. 确保与前文连贯

请直接输出第 {chapter_num} 章的正文内容，不要包含章节标题和其他说明。"""

            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="章节内容",
                temperature=0.85,
                max_tokens=2000,
            )

            content = response.content.strip()
            word_count = len(content)

            # Evaluate quality
            evaluation = await self.evaluator.evaluate(
                task_type="章节内容",
                content=content,
                context={
                    "chapter_num": chapter_num,
                    "style": style_context[:200],
                    "outline": outline_context[:200],
                },
                criteria={
                    EvaluationCriterion.COHERENCE: 0.25,
                    EvaluationCriterion.CREATIVITY: 0.20,
                    EvaluationCriterion.QUALITY: 0.25,
                    EvaluationCriterion.CONSISTENCY: 0.20,
                    EvaluationCriterion.CHARACTER_VOICE: 0.10,
                },
            )

            logger.info(f"✓ 第 {chapter_num} 章生成完成")
            logger.info(f"字数: {word_count}")
            logger.info(f"质量评分: {evaluation.score:.2f}")
            logger.info(f"内容预览:\n{content[:150]}...")

            # Store in memory
            await self.memory.store(
                content=content,
                task_id=f"{self.session_id}_chapter_{chapter_num}",
                task_type="章节内容",
                memory_type=MemoryType.CHAPTER,
                metadata={
                    "session_id": self.session_id,
                    "chapter_num": chapter_num,
                    "word_count": word_count,
                    "quality_score": evaluation.score,
                },
                chapter_index=chapter_num,
                evaluation=evaluation.to_dict(),
            )

            self.generated_chapters.append(content)
            self.total_word_count += word_count

            self.test_results["stages"][f"chapter_{chapter_num}"] = {
                "status": "success",
                "word_count": word_count,
                "quality_score": evaluation.score,
                "provider": response.provider.value,
                "timestamp": datetime.now().isoformat(),
            }

            self.test_results["quality_scores"][f"chapter_{chapter_num}"] = evaluation.to_dict()

            return True, content

        except Exception as e:
            logger.error(f"✗ 第 {chapter_num} 章生成失败: {e}")
            self.test_results["errors"].append(f"Chapter {chapter_num} error: {str(e)}")
            self.test_results["stages"][f"chapter_{chapter_num}"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            return False, ""

    async def generate_all_chapters(self) -> bool:
        """生成所有章节"""
        logger.info("\n" + "=" * 80)
        logger.info("📚 开始生成所有章节")
        logger.info("=" * 80)

        chapter_num = 1
        while self.total_word_count < TEST_CONFIG["target_words"]:
            success, content = await self.generate_chapter(chapter_num)

            if not success:
                logger.error(f"章节 {chapter_num} 生成失败，终止测试")
                return False

            logger.info(f"当前总字数: {self.total_word_count} / {TEST_CONFIG['target_words']}")

            chapter_num += 1

            # 防止无限循环
            if chapter_num > 10:
                logger.warning("章节数超过 10，终止生成")
                break

            # 短暂延迟，避免 API 限流
            await asyncio.sleep(2)

        logger.info(f"\n✓ 所有章节生成完成，共 {len(self.generated_chapters)} 章")
        logger.info(f"总字数: {self.total_word_count}")

        return True

    async def final_evaluation(self) -> bool:
        """最终质量评估"""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 阶段 5: 最终质量评估")
        logger.info("=" * 80)

        try:
            # Combine all content
            full_novel = "\n\n".join(self.generated_chapters)
            self.test_results["content"]["full_novel"] = full_novel

            # Evaluate complete novel
            style_memories = await self.memory.search(
                query="风格",
                memory_type=MemoryType.GENERAL,
                top_k=1,
            )
            outline_memories = await self.memory.search(
                query="大纲",
                memory_type=MemoryType.OUTLINE,
                top_k=1,
            )

            evaluation = await self.evaluator.evaluate(
                task_type="完整小说",
                content=full_novel,
                context={
                    "genre": "科幻",
                    "target_words": TEST_CONFIG["target_words"],
                    "style": style_memories[0].item.content if style_memories else "",
                    "outline": outline_memories[0].item.content if outline_memories else "",
                },
                criteria={
                    EvaluationCriterion.COHERENCE: 0.25,
                    EvaluationCriterion.CREATIVITY: 0.20,
                    EvaluationCriterion.QUALITY: 0.20,
                    EvaluationCriterion.CONSISTENCY: 0.20,
                    EvaluationCriterion.PLOT_PROGRESSION: 0.15,
                },
            )

            logger.info(f"总字数: {self.total_word_count}")
            logger.info(f"整体质量评分: {evaluation.score:.3f}")

            logger.info("\n维度评分:")
            for dim_name, dim_score in evaluation.dimension_scores.items():
                logger.info(f"  - {dim_name}: {dim_score.score:.3f}")

            # Check acceptance criteria
            passed_criteria = []
            failed_criteria = []

            # 1. Word count check
            if self.total_word_count >= TEST_CONFIG["target_words"]:
                passed_criteria.append(f"✓ 字数达标: {self.total_word_count} ≥ {TEST_CONFIG['target_words']}")
            else:
                failed_criteria.append(f"✗ 字数不足: {self.total_word_count} < {TEST_CONFIG['target_words']}")

            # 2. Overall quality check
            if evaluation.score >= TEST_CONFIG["min_quality_score"]:
                passed_criteria.append(f"✓ 整体质量达标: {evaluation.score:.3f} ≥ {TEST_CONFIG['min_quality_score']}")
            else:
                failed_criteria.append(f"✗ 整体质量不足: {evaluation.score:.3f} < {TEST_CONFIG['min_quality_score']}")

            # 3. Dimension scores check
            all_dimensions_passed = True
            for dim_name, dim_score in evaluation.dimension_scores.items():
                if dim_score.score < TEST_CONFIG["min_dimension_score"]:
                    all_dimensions_passed = False
                    failed_criteria.append(f"✗ {dim_name} 评分不足: {dim_score.score:.3f}")

            if all_dimensions_passed:
                passed_criteria.append(f"✓ 所有维度评分 ≥ {TEST_CONFIG['min_dimension_score']}")

            # Print results
            logger.info("\n" + "=" * 80)
            logger.info("📊 验收标准检查")
            logger.info("=" * 80)

            logger.info("\n✅ 通过的标准:")
            for criterion in passed_criteria:
                logger.info(f"  {criterion}")

            if failed_criteria:
                logger.info("\n❌ 未通过的标准:")
                for criterion in failed_criteria:
                    logger.info(f"  {criterion}")

            passed = len(failed_criteria) == 0
            self.test_results["passed"] = passed
            self.test_results["quality_scores"]["final"] = evaluation.to_dict()
            self.test_results["acceptance_criteria"] = {
                "passed": passed_criteria,
                "failed": failed_criteria,
            }

            return passed

        except Exception as e:
            logger.error(f"✗ 最终评估失败: {e}")
            self.test_results["errors"].append(f"Final evaluation error: {str(e)}")
            return False

    async def save_results(self):
        """保存测试结果"""
        logger.info("\n" + "=" * 80)
        logger.info("💾 保存测试结果")
        logger.info("=" * 80)

        try:
            # Save to file
            output_dir = Path(__file__).parent.parent / "test_results"
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save full novel
            novel_file = output_dir / f"scifi_novel_{timestamp}.txt"
            with open(novel_file, "w", encoding="utf-8") as f:
                f.write(f"科幻小说自动化测试结果\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(f"会话 ID: {self.session_id}\n")
                f.write(f"生成时间: {self.test_results['started_at']}\n")
                f.write(f"总字数: {self.total_word_count}\n")
                f.write(f"章节数: {len(self.generated_chapters)}\n\n")
                f.write(f"{'=' * 80}\n\n")

                # Write style
                if "style" in self.test_results["content"]:
                    f.write("【风格定义】\n\n")
                    f.write(self.test_results["content"]["style"])
                    f.write("\n\n" + "=" * 80 + "\n\n")

                # Write outline
                if "outline" in self.test_results["content"]:
                    f.write("【小说大纲】\n\n")
                    f.write(self.test_results["content"]["outline"])
                    f.write("\n\n" + "=" * 80 + "\n\n")

                # Write characters
                if "characters" in self.test_results["content"]:
                    f.write("【人物设定】\n\n")
                    f.write(self.test_results["content"]["characters"])
                    f.write("\n\n" + "=" * 80 + "\n\n")

                # Write chapters
                for i, chapter in enumerate(self.generated_chapters, 1):
                    f.write(f"第 {i} 章\n\n")
                    f.write(chapter)
                    f.write("\n\n" + "=" * 80 + "\n\n")

            logger.info(f"✓ 小说保存至: {novel_file}")

            # Save test report
            import json
            report_file = output_dir / f"test_report_{timestamp}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                # Convert datetime objects to strings for JSON serialization
                report_data = {
                    "session_id": self.test_results["session_id"],
                    "started_at": self.test_results["started_at"],
                    "completed_at": datetime.now().isoformat(),
                    "config": self.test_results["config"],
                    "total_word_count": self.total_word_count,
                    "chapter_count": len(self.generated_chapters),
                    "passed": self.test_results["passed"],
                    "stages": self.test_results["stages"],
                    "quality_scores": self.test_results["quality_scores"],
                    "acceptance_criteria": self.test_results.get("acceptance_criteria", {}),
                    "errors": self.test_results["errors"],
                }
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✓ 测试报告保存至: {report_file}")

            return True

        except Exception as e:
            logger.error(f"✗ 保存结果失败: {e}")
            return False

    async def run(self):
        """运行完整测试"""
        start_time = time.time()

        try:
            # Initialize
            if not await self.initialize():
                return False

            # Generate style
            if not await self.generate_style():
                return False

            # Generate outline
            if not await self.generate_outline():
                return False

            # Generate characters
            if not await self.generate_characters():
                return False

            # Generate all chapters
            if not await self.generate_all_chapters():
                return False

            # Final evaluation
            passed = await self.final_evaluation()

            # Save results
            await self.save_results()

            # Print summary
            elapsed_time = time.time() - start_time
            logger.info("\n" + "=" * 80)
            logger.info("🏁 测试完成")
            logger.info("=" * 80)
            logger.info(f"总耗时: {elapsed_time:.2f} 秒")
            logger.info(f"总字数: {self.total_word_count}")
            logger.info(f"章节数: {len(self.generated_chapters)}")
            logger.info(f"测试结果: {'✅ 通过' if passed else '❌ 失败'}")
            logger.info("=" * 80)

            return passed

        except Exception as e:
            logger.error(f"测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主函数"""
    # Setup logger
    setup_logger()

    # Run test
    test = SciFiNovelTest()
    success = await test.run()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
