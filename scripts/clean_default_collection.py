"""
清理被污染的默认 creative_autogpt collection

这个脚本会删除名为 'creative_autogpt' 的默认 collection，
该 collection 可能包含来自不同会话的混合数据。
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger


def clean_default_collection(persist_directory: str = "./data/chroma"):
    """
    删除默认的 creative_autogpt collection

    Args:
        persist_directory: ChromaDB 持久化目录
    """
    # 初始化 ChromaDB 客户端
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )

    # 获取所有 collections
    collections = client.list_collections()

    logger.info(f"当前共有 {len(collections)} 个 collections:")

    for coll in collections:
        count = coll.count()
        logger.info(f"  - {coll.name}: {count} 条数据")

    # 查找并删除默认 collection
    default_collection_name = "creative_autogpt"

    try:
        # 尝试获取默认 collection
        default_collection = client.get_collection(name=default_collection_name)

        count = default_collection.count()
        logger.warning(f"⚠️ 发现默认 collection '{default_collection_name}'，包含 {count} 条数据")
        logger.warning("这些数据可能是由于 session_id 未正确传递而导致的跨会话污染")

        # 删除 collection
        client.delete_collection(name=default_collection_name)
        logger.success(f"✅ 已成功删除默认 collection '{default_collection_name}'")

    except Exception as e:
        logger.info(f"✓ 默认 collection 不存在或已被删除: {e}")

    # 验证删除结果
    collections_after = client.list_collections()
    logger.info(f"\n清理后剩余 {len(collections_after)} 个 collections:")

    for coll in collections_after:
        count = coll.count()
        logger.info(f"  - {coll.name}: {count} 条数据")


if __name__ == "__main__":
    logger.info("=== 清理默认 ChromaDB Collection ===\n")
    clean_default_collection()
    logger.info("\n=== 清理完成 ===")
