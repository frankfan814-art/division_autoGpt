"""Logging configuration for Creative AutoGPT"""

import sys
from pathlib import Path
from loguru import logger as _logger
from typing import Optional

from creative_autogpt.utils.config import get_settings


def setup_logger(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    rotation: Optional[str] = None,
    retention: Optional[str] = None,
) -> None:
    """
    Configure loguru logger for the application

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        rotation: Log rotation configuration
        retention: Log retention configuration
    """
    settings = get_settings()

    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file
    rotation = rotation or settings.log_rotation
    retention = retention or settings.log_retention

    # Remove default handler
    _logger.remove()

    # Console handler with colors
    _logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        _logger.add(
            log_file,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

    _logger.info(f"Logger initialized with level: {log_level}")


def get_logger(name: str = None):
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    if name:
        return _logger.bind(name=name)
    return _logger


# Re-export for convenience
logger = _logger
