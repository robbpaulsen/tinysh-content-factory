"""Logging configuration and utilities."""

import logging
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Generator

from rich.console import Console
from rich.logging import RichHandler

from src.config import settings

console = Console()


def setup_logging(verbose: bool = False, log_to_file: bool = True) -> None:
    """
    Configure logging for the application.

    Args:
        verbose: Enable verbose (DEBUG) logging
        log_to_file: Enable logging to file with rotation

    Logging modes:
        - Simple (default): INFO level, console only with progress bars
        - Verbose: DEBUG level, console + file with detailed traces
    """
    # Determine log level
    log_level = logging.DEBUG if verbose else logging.INFO

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []  # Clear existing handlers

    # Console handler with Rich formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        console=console,
        show_time=verbose,  # Show timestamps in verbose mode
        show_path=verbose,  # Show file paths in verbose mode
        markup=True,
    )
    console_handler.setLevel(log_level)

    # Format: simpler in normal mode, detailed in verbose
    if verbose:
        console_format = "%(message)s"
    else:
        console_format = "%(message)s"

    console_handler.setFormatter(logging.Formatter(console_format))
    root_logger.addHandler(console_handler)

    # File handler with rotation (only if enabled)
    if log_to_file and settings.log_to_file:
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"youtube_shorts_{timestamp}.log"

        # Rotating file handler (max 10MB, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Always DEBUG in file

        # Detailed format for file logs
        file_format = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

        # Log the log file location
        logger = logging.getLogger(__name__)
        logger.info(f"Logging to file: {log_file}")

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Log initial configuration
    logger = logging.getLogger(__name__)
    mode = "VERBOSE" if verbose else "SIMPLE"
    logger.debug(f"Logging initialized - Mode: {mode}, Level: {logging.getLevelName(log_level)}")


@contextmanager
def log_performance(operation: str, logger: logging.Logger | None = None) -> Generator[None, None, None]:
    """
    Context manager to log operation performance.

    Args:
        operation: Name of the operation being measured
        logger: Logger instance (uses root logger if None)

    Usage:
        with log_performance("Generate video", logger):
            # ... do work ...
            pass
    """
    logger = logger or logging.getLogger(__name__)
    start_time = time.time()

    logger.debug(f"[{operation}] Starting...")

    try:
        yield
    finally:
        elapsed = time.time() - start_time
        logger.info(f"[{operation}] Completed in {elapsed:.2f}s")


def log_api_call(
    service: str,
    endpoint: str,
    status: str = "success",
    details: str | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """
    Log API call information.

    Args:
        service: Service name (e.g., "Gemini", "Together.ai", "Media Server")
        endpoint: API endpoint or method called
        status: Call status (success, error, retry)
        details: Additional details
        logger: Logger instance (uses root logger if None)
    """
    logger = logger or logging.getLogger(__name__)

    log_msg = f"[API] {service} | {endpoint} | {status.upper()}"
    if details:
        log_msg += f" | {details}"

    if status == "error":
        logger.error(log_msg)
    elif status == "retry":
        logger.warning(log_msg)
    else:
        logger.debug(log_msg)


def cleanup_old_logs(max_age_days: int = 7) -> None:
    """
    Clean up log files older than max_age_days.

    Args:
        max_age_days: Maximum age of log files to keep
    """
    logger = logging.getLogger(__name__)
    log_dir = Path(settings.log_dir)

    if not log_dir.exists():
        return

    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    deleted_count = 0

    for log_file in log_dir.glob("youtube_shorts_*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            log_file.unlink()
            deleted_count += 1

    if deleted_count > 0:
        logger.debug(f"Cleaned up {deleted_count} old log files (>{max_age_days} days)")
