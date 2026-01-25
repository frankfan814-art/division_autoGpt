"""
Server startup script
"""
import sys
import uvicorn
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from creative_autogpt.utils.config import get_settings
from creative_autogpt.utils.logger import setup_logger


def main():
    """Start the server"""
    settings = get_settings()
    setup_logger()

    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║           Creative AutoGPT API Server                  ║
    ╠═══════════════════════════════════════════════════════╣
    ║  Environment: {settings.app_env:<41} ║
    ║  Host:        {settings.app_host + ':' + str(settings.app_port):<41} ║
    ║  Docs:        http://{settings.app_host}:{settings.app_port}/docs{'':42} ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "creative_autogpt.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
