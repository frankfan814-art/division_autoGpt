"""
Database initialization script
"""
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from creative_autogpt.storage.session import SessionStorage
from creative_autogpt.storage.vector_store import VectorStore
from creative_autogpt.utils.logger import setup_logger, logger


async def init_database():
    """Initialize database tables"""
    setup_logger()

    logger.info("Initializing database...")

    # Initialize session storage
    storage = SessionStorage()
    await storage.initialize()

    logger.info("Database initialized successfully")

    # Test vector store
    logger.info("Testing vector store...")
    vector_store = VectorStore()
    count = vector_store.count()
    logger.info(f"Vector store initialized (current items: {count})")


async def reset_database():
    """Reset database (drop and recreate)"""
    setup_logger()

    logger.warning("Resetting database...")

    storage = SessionStorage()
    # Drop all tables
    async with storage.engine.begin() as conn:
        from creative_autogpt.storage.session import Base
        await conn.run_sync(Base.metadata.drop_all)

    # Recreate
    await storage.initialize()

    logger.info("Database reset complete")


async def clear_vector_store():
    """Clear vector store"""
    setup_logger()

    logger.warning("Clearing vector store...")

    vector_store = VectorStore()
    await vector_store.clear()

    logger.info("Vector store cleared")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Database management")
    parser.add_argument("command", choices=["init", "reset", "clear"], help="Command to run")
    args = parser.parse_args()

    if args.command == "init":
        await init_database()
    elif args.command == "reset":
        await reset_database()
    elif args.command == "clear":
        await clear_vector_store()


if __name__ == "__main__":
    asyncio.run(main())
