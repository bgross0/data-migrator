"""
Logging configuration for the deterministic field mapper system.
"""
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

# Default log level
DEFAULT_LOG_LEVEL = os.getenv("FIELD_MAPPER_LOG_LEVEL", "INFO")

# Log directory
LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs" / "field_mapper"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.

    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set level
    log_level = getattr(logging, (level or DEFAULT_LOG_LEVEL).upper())
    logger.setLevel(log_level)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (rotating)
    log_file = LOG_DIR / f"{name.replace('.', '_')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


# Create loggers for main components
knowledge_base_logger = setup_logger("field_mapper.knowledge_base")
profiling_logger = setup_logger("field_mapper.profiling")
matching_logger = setup_logger("field_mapper.matching")
validation_logger = setup_logger("field_mapper.validation")
api_logger = setup_logger("field_mapper.api")
performance_logger = setup_logger("field_mapper.performance")
