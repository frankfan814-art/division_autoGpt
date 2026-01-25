"""
System integration test
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.core.vector_memory import VectorMemoryManager, MemoryType
from creative_autogpt.core.task_planner import TaskPlanner, NovelTaskType
from creative_autogpt.core.evaluator import EvaluationEngine
from creative_autogpt.core.loop_engine import LoopEngine
from creative_autogpt.modes.novel import NovelMode
from creative_autogpt.plugins.manager import PluginManager
from creative_autogpt.storage.vector_store import VectorStore
from creative_autogpt.utils.logger import setup_logger, logger
from creative_autogpt.utils.config import get_settings


async def test_basic_generation():
    """Test basic LLM generation"""
    logger.info("=== Testing Basic Generation ===")

    client = MultiLLMClient()

    response = await client.generate(
        prompt="请用100字左右介绍什么是玄幻小说。",
        task_type="大纲",  # Should route to Qwen
        temperature=0.7,
        max_tokens=300,
    )

    logger.info(f"Provider: {response.provider.value}")
    logger.info(f"Content: {response.content}")
    logger.info(f"Tokens: {response.usage.total_tokens}")
    logger.info("✓ Basic generation test passed")


async def test_vector_memory():
    """Test vector memory"""
    logger.info("=== Testing Vector Memory ===")

    vector_store = VectorStore()
    memory = VectorMemoryManager(vector_store=vector_store)

    # Add test data
    await memory.store(
        content="主角林动从小天赋异禀，却因家族变故而失去灵力",
        task_id="test_1",
        task_type="人物设计",
        memory_type=MemoryType.CHARACTER,
        metadata={"character": "林动", "role": "protagonist"},
    )

    await memory.store(
        content="主角在深山中发现一枚神秘的石符，里面蕴含着强大的能量",
        task_id="test_2",
        task_type="事件",
        memory_type=MemoryType.PLOT,
        metadata={"importance": "high"},
    )

    # Test search
    context = await memory.get_context(
        task_id="test_3",
        task_type="章节内容",
        query="主角",
    )

    logger.info(f"Recent results: {len(context.recent_results)}")
    logger.info(f"Relevant memories: {len(context.relevant_memories)}")

    for mem in context.relevant_memories:
        logger.info(f"  - {mem['memory_type']}: {mem['content'][:50]}... (score: {mem['score']:.3f})")

    logger.info("✓ Vector memory test passed")


async def test_task_planner():
    """Test task planner"""
    logger.info("=== Testing Task Planner ===")

    planner = TaskPlanner()

    goal = {
        "title": "测试小说",
        "genre": "玄幻",
        "theme": "成长与复仇",
        "style": "热血",
        "length": "100万字",
    }

    tasks = await planner.plan(goal=goal, chapter_count=3)

    logger.info(f"Generated {len(tasks)} tasks")

    # Show first few tasks
    for task in list(tasks)[:5]:
        logger.info(f"  - {task.task_type.value}: {task.description}")

    logger.info("✓ Task planner test passed")


async def test_evaluator():
    """Test evaluator"""
    logger.info("=== Testing Evaluator ===")

    llm_client = MultiLLMClient()
    evaluator = EvaluationEngine(llm_client=llm_client)

    test_content = """
    天元大陆，武道为尊。

    林动站在家族演武场上，手中紧握着那枚从山中捡到的神秘石符。石符散发着淡淡的温热，仿佛在呼吸一般。他回想起三个月前，自己还是林家公认的天才，一身灵力已达淬体境九重。

    "哼，曾经的林天才，现在也不过是个废物罢了。"
    """

    result = await evaluator.evaluate(
        task_type="章节内容",
        content=test_content,
        goal={"genre": "玄幻"},
    )

    logger.info(f"Score: {result.score:.3f}")
    logger.info(f"Passed: {result.passed}")
    logger.info(f"Reasons: {result.reasons}")

    logger.info("✓ Evaluator test passed")


async def test_mode():
    """Test novel mode"""
    logger.info("=== Testing Novel Mode ===")

    mode = NovelMode(config={"genre": "玄幻"})

    from creative_autogpt.core.vector_memory import MemoryContext

    context = MemoryContext(
        task_id="test",
        task_type="风格元素",
        recent_results=[],
        relevant_memories=[],
        chapter_context=[],
        task_memories=[],
    )

    prompt = await mode.build_prompt(
        task_type="风格元素",
        context=context,
        metadata={"genre": "玄幻"},
    )

    logger.info(f"Generated prompt length: {len(prompt)} chars")
    logger.info(f"Prompt preview: {prompt[:200]}...")

    logger.info("✓ Novel mode test passed")


async def test_full_pipeline():
    """Test the full pipeline (mini version)"""
    logger.info("=== Testing Full Pipeline ===")

    # Initialize components
    llm_client = MultiLLMClient()
    vector_store = VectorStore()
    memory = VectorMemoryManager(vector_store=vector_store)
    evaluator = EvaluationEngine(llm_client=llm_client)
    mode = NovelMode(config={"genre": "玄幻"})

    # Create goal
    goal = {
        "title": "星辰变",
        "genre": "玄幻",
        "theme": "修仙问道",
        "style": "热血",
        "length": "50万字",
    }

    # Generate tasks (just 1 chapter for testing)
    planner = TaskPlanner()

    logger.info("Planning tasks...")
    tasks = await planner.plan(goal=goal, chapter_count=1)

    logger.info(f"Generated {len(tasks)} tasks")

    # Execute first task
    task = tasks[0]
    logger.info(f"Executing first task: {task.task_type.value}")

    # Get context
    context = await memory.get_context(
        task_id=task.task_id,
        task_type=task.task_type.value,
    )

    # Build prompt
    prompt = await mode.build_prompt(
        task_type=task.task_type.value,
        context=context,
        metadata=goal,
    )

    # Generate
    logger.info("Generating with LLM...")
    response = await llm_client.generate(
        prompt=prompt,
        task_type=task.task_type.value,
        temperature=0.7,
        max_tokens=500,
    )

    logger.info(f"Generated content: {response.content[:200]}...")

    # Store
    await memory.store(
        content=response.content,
        task_id=task.task_id,
        task_type=task.task_type.value,
        memory_type=MemoryType.CHARACTER,
        metadata={"chapter": 0},
    )

    logger.info("✓ Full pipeline test passed")


async def main():
    """Run all tests"""
    setup_logger()

    settings = get_settings()

    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║        Creative AutoGPT System Integration Test        ║
    ╠═══════════════════════════════════════════════════════╣
    ║  Environment: {settings.app_env:<41} ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    try:
        await test_basic_generation()
        await test_vector_memory()
        await test_task_planner()
        await test_evaluator()
        await test_mode()
        await test_full_pipeline()

        print("\n" + "="*50)
        print("✓ All tests passed successfully!")
        print("="*50)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print("\n" + "="*50)
        print(f"✗ Test failed: {e}")
        print("="*50)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
