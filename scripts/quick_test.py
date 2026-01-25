"""
Quick test without full dependencies - validates core structure
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")

    try:
        # Test utils
        from creative_autogpt.utils.config import Settings, get_settings
        print("  ✓ config")

        from creative_autogpt.utils.logger import setup_logger, logger
        print("  ✓ logger")

        # Test core
        from creative_autogpt.core.task_planner import TaskPlanner, NovelTaskType
        print("  ✓ task_planner")

        from creative_autogpt.core.evaluator import EvaluationEngine
        print("  ✓ evaluator")

        from creative_autogpt.core.vector_memory import VectorMemoryManager
        print("  ✓ vector_memory")

        # Test modes
        from creative_autogpt.modes.base import Mode
        from creative_autogpt.modes.novel import NovelMode
        print("  ✓ modes")

        # Test plugins
        from creative_autogpt.plugins.base import NovelElementPlugin
        from creative_autogpt.plugins.manager import PluginManager
        print("  ✓ plugins")

        # Test storage
        from creative_autogpt.storage.session import SessionStorage
        from creative_autogpt.storage.vector_store import VectorStore
        from creative_autogpt.storage.file_store import FileStore
        print("  ✓ storage")

        # Test API
        from creative_autogpt.api.main import create_app
        print("  ✓ api")

        print("\n✓ All imports successful!")
        return True

    except ImportError as e:
        print(f"\n✗ Import failed: {e}")
        return False


def test_structure():
    """Test project structure"""
    print("\nTesting project structure...")

    required_dirs = [
        "src/creative_autogpt/core",
        "src/creative_autogpt/modes",
        "src/creative_autogpt/plugins",
        "src/creative_autogpt/prompts",
        "src/creative_autogpt/utils",
        "src/creative_autogpt/storage",
        "src/creative_autogpt/api",
        "prompts/base",
        "prompts/styles",
        "scripts",
    ]

    base_path = Path(__file__).parent.parent

    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if full_path.exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} (missing)")

    required_files = [
        "requirements.txt",
        "pyproject.toml",
        ".env",
        "src/creative_autogpt/__init__.py",
        "src/creative_autogpt/core/loop_engine.py",
        "src/creative_autogpt/utils/llm_client.py",
        "src/creative_autogpt/api/main.py",
        "scripts/init_db.py",
        "scripts/run_server.py",
    ]

    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} (missing)")


def main():
    """Run quick tests"""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║        Creative AutoGPT Quick Structure Test           ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    test_structure()

    print("\n" + "="*50)
    import_success = test_imports()
    print("="*50)

    if import_success:
        print("\n✓ Core structure validated successfully!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Initialize database: python scripts/init_db.py init")
        print("  3. Test LLM: python scripts/test_llm.py --test llm")
        print("  4. Run server: python scripts/run_server.py")
    else:
        print("\n✗ Some imports failed - install dependencies first")


if __name__ == "__main__":
    main()
