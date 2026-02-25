"""Context managers for temporary logging configuration changes.

This module provides context managers that allow temporary changes to
logging configuration within a specific scope.
"""

import logging
from contextlib import contextmanager
from typing import Optional


@contextmanager
def log_level(level: str, logger: Optional[logging.Logger] = None):
    """Temporarily change logging level.
    
    Args:
        level: Temporary logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        logger: Logger to modify. If None, modifies root logger.
        
    Example:
        >>> with log_level('DEBUG'):
        ...     # Code here will have DEBUG logging
        ...     logger.debug("This will be logged")
        >>> # Back to original level
    """
    if logger is None:
        logger = logging.getLogger()
    
    original_level = logger.level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    try:
        logger.setLevel(numeric_level)
        yield logger
    finally:
        logger.setLevel(original_level)


@contextmanager
def suppress_logging(logger_name: Optional[str] = None):
    """Temporarily suppress logging for a module.
    
    Args:
        logger_name: Name of logger to suppress. If None, suppresses root logger.
        
    Example:
        >>> with suppress_logging('evaluation.core'):
        ...     # No logs from evaluation.core will be shown
        ...     pass
    """
    if logger_name is None:
        logger = logging.getLogger()
    else:
        logger = logging.getLogger(logger_name)
    
    original_disabled = logger.disabled
    
    try:
        logger.disabled = True
        yield logger
    finally:
        logger.disabled = original_disabled


@contextmanager
def log_to_file(filepath: str, level: str = 'INFO'):
    """Temporarily add file handler to logger.
    
    Args:
        filepath: Path to log file.
        level: Logging level for file handler.
        
    Example:
        >>> with log_to_file('debug.log', 'DEBUG'):
        ...     # Logs will be written to debug.log
        ...     logger.debug("Debug info")
    """
    from pathlib import Path
    
    logger = logging.getLogger()
    
    # Create file handler
    log_file = Path(filepath)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    file_handler.setLevel(numeric_level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    try:
        logger.addHandler(file_handler)
        yield logger
    finally:
        logger.removeHandler(file_handler)
        file_handler.close()


@contextmanager
def capture_logs(level: str = 'INFO'):
    """Capture logs to a list for testing or analysis.
    
    Args:
        level: Minimum logging level to capture.
        
    Returns:
        List of log records.
        
    Example:
        >>> with capture_logs('INFO') as logs:
        ...     logger.info("Test message")
        >>> print(logs[0].message)
        Test message
    """
    from logging.handlers import MemoryHandler
    
    logger = logging.getLogger()
    
    # Create memory handler
    records = []
    
    class ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)
    
    handler = ListHandler()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler.setLevel(numeric_level)
    
    try:
        logger.addHandler(handler)
        yield records
    finally:
        logger.removeHandler(handler)
