"""
Centralized logging configuration for JobSearchAI.

This module provides a unified logging setup with:
- Daily log rotation (at midnight)
- 30-day retention
- Console and file output
- Consistent formatting across all modules

Usage:
    # In entry points (dashboard.py, init_db.py, etc.):
    from utils.logging_config import setup_logging
    setup_logging()

    # In all other modules:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


_logging_initialized = False


def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    log_filename: str = "jobsearchai.log"
) -> None:
    """
    Initialize centralized logging with daily rotation.

    Args:
        log_dir: Directory for log files (relative to project root or absolute)
        log_level: Logging level (default: INFO)
        log_filename: Name of the log file (default: jobsearchai.log)
    """
    global _logging_initialized

    if _logging_initialized:
        return

    # Determine log directory path
    if Path(log_dir).is_absolute():
        log_path = Path(log_dir)
    else:
        # Relative to project root (where dashboard.py is located)
        project_root = Path(__file__).parent.parent
        log_path = project_root / log_dir

    # Create logs directory if it doesn't exist
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / log_filename

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler with daily rotation, keep 30 days
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _logging_initialized = True

    # Log that logging has been initialized
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
