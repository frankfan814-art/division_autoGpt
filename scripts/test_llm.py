"""
Test LLM API connectivity
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from creative_autogpt.utils.llm_client import MultiLLMClient
from creative_autogpt.utils.logger import setup_logger, logger
from creative_autogpt.utils.config import get_settings


async def test_llm():
    """Test LLM connectivity"""
    setup_logger()

    settings = get_settings()

    logger.info("Testing LLM connectivity...")

    # Create client
    client = MultiLLMClient()

    # Test prompt
    test_prompt = "你好，请用一句话介绍你自己。"

    logger.info(f"Test prompt: {test_prompt}")

    # Test each provider
    providers = ["aliyun", "deepseek", "ark"]

    for provider in providers:
        try:
            logger.info(f"Testing {provider}...")

            response = await client.generate(
                prompt=test_prompt,
                llm=provider,
                temperature=0.7,
                max_tokens=200,
            )

            logger.info(f"{provider} response: {response.content[:100]}")
            logger.info(f"Tokens: {response.usage.total_tokens}")

        except Exception as e:
            logger.error(f"{provider} failed: {e}")

    # Test with routing
    logger.info("Testing intelligent routing...")

    try:
        response = await client.generate(
            prompt="请生成一个玄幻小说的大纲框架",
            task_type="大纲",  # Should route to Qwen
            temperature=0.7,
            max_tokens=500,
        )

        logger.info(f"Routed response: {response.content[:200]}")
        logger.info(f"Provider: {response.provider.value}")

    except Exception as e:
        logger.error(f"Routing test failed: {e}")


async def test_embeddings():
    """Test embedding functionality"""
    setup_logger()

    logger.info("Testing embeddings...")

    from creative_autogpt.storage.vector_store import VectorStore

    vector_store = VectorStore()

    # Test adding and searching
    test_texts = [
        "这是一个关于勇敢的骑士的故事",
        "魔法师在森林里发现了秘密",
        "机器人正在思考存在的意义",
    ]

    logger.info("Adding test items...")

    for i, text in enumerate(test_texts):
        await vector_store.add(
            content=text,
            memory_type="general",
            metadata={"test": True, "index": i},
        )

    logger.info("Testing search...")

    results = await vector_store.search(
        query="骑士和冒险",
        top_k=2,
    )

    logger.info(f"Found {len(results)} results")
    for result in results:
        logger.info(f"  Score: {result.score:.3f}, Content: {result.item.content[:50]}...")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="LLM testing")
    parser.add_argument("--test", choices=["llm", "embeddings", "all"], default="all")
    args = parser.parse_args()

    if args.test in ("llm", "all"):
        await test_llm()

    if args.test in ("embeddings", "all"):
        await test_embeddings()


if __name__ == "__main__":
    asyncio.run(main())
