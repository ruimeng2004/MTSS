"""Utility modules for the D4J Fix Evaluation System.

This package contains utility functions and helpers:
- Logging: Unified logging configuration
- Log context managers: Temporary logging configuration changes
- Cache: Performance optimization through caching
- Error handling: Retry mechanisms and checkpoint management
"""

from evaluation.utils.logging_config import (
    setup_logging,
    setup_evaluation_logging,
    get_logger,
    set_module_level,
    quick_setup
)
from evaluation.utils.log_context import (
    log_level,
    suppress_logging,
    log_to_file,
    capture_logs
)
from evaluation.utils.cache_manager import (
    CacheManager,
    FileCache,
    get_cache,
    get_file_cache,
    init_cache,
)
from evaluation.utils.error_handler import (
    RetryableError,
    FatalError,
    retry,
    CheckpointManager,
    ErrorContext,
    safe_execute,
    ErrorCollector,
)

__all__ = [
    # Logging configuration
    'setup_logging',
    'setup_evaluation_logging',
    'get_logger',
    'set_module_level',
    'quick_setup',
    # Log context managers
    'log_level',
    'suppress_logging',
    'log_to_file',
    'capture_logs',
    # Cache management
    'CacheManager',
    'FileCache',
    'get_cache',
    'get_file_cache',
    'init_cache',
    # Error handling
    'RetryableError',
    'FatalError',
    'retry',
    'CheckpointManager',
    'ErrorContext',
    'safe_execute',
    'ErrorCollector',
]
