"""Unified logging configuration for the D4J Fix Evaluation System.

This module provides centralized logging setup with support for:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- File and console output
- Log rotation
- Colored console output (optional)
- Per-module logging configuration
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# ANSI color codes for console output
COLORS = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[35m',   # Magenta
    'RESET': '\033[0m'        # Reset
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""
    
    def __init__(self, fmt: str, use_colors: bool = True):
        """Initialize ColoredFormatter.
        
        Args:
            fmt: Log format string.
            use_colors: Whether to use colors in output.
        """
        super().__init__(fmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.
        
        Args:
            record: Log record to format.
            
        Returns:
            Formatted log string with colors.
        """
        if self.use_colors and record.levelname in COLORS:
            # Add color to level name
            levelname_color = (
                f"{COLORS[record.levelname]}{record.levelname}{COLORS['RESET']}"
            )
            record.levelname = levelname_color
        
        return super().format(record)


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
    use_colors: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """Setup unified logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, only console output.
        log_format: Custom log format string. If None, uses default.
        use_colors: Whether to use colored console output.
        max_bytes: Maximum size of log file before rotation (bytes).
        backup_count: Number of backup log files to keep.
        
    Returns:
        Configured root logger.
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Default format
    if log_format is None:
        log_format = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(filename)s:%(lineno)d - %(message)s'
        )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = ColoredFormatter(log_format, use_colors=use_colors)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (if log_file specified)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        root_logger.info(f"Logging to file: {log_file}")
    
    root_logger.info(f"Logging level set to: {level}")
    
    return root_logger


def setup_evaluation_logging(config: dict = None) -> logging.Logger:
    """Setup logging for evaluation system using config.
    
    Args:
        config: Configuration dictionary. If None, uses defaults.
        
    Returns:
        Configured logger.
    """
    if config is None:
        config = {}
    
    # Get logging config from evaluation_config
    eval_config = config.get('evaluation_config', {})
    logging_config = eval_config.get('logging', {})
    
    level = logging_config.get('level', 'INFO')
    log_file = logging_config.get('file', 'evaluation.log')
    log_format = logging_config.get(
        'format',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup logging
    logger = setup_logging(
        level=level,
        log_file=Path(log_file),
        log_format=log_format,
        use_colors=True
    )
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def set_module_level(module_name: str, level: str) -> None:
    """Set logging level for a specific module.
    
    Args:
        module_name: Name of the module (e.g., 'evaluation.core').
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logger = logging.getLogger(module_name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logging.info(f"Set {module_name} logging level to {level}")


def disable_module(module_name: str) -> None:
    """Disable logging for a specific module.
    
    Args:
        module_name: Name of the module to disable.
    """
    logger = logging.getLogger(module_name)
    logger.disabled = True
    logging.info(f"Disabled logging for {module_name}")


def enable_module(module_name: str) -> None:
    """Enable logging for a specific module.
    
    Args:
        module_name: Name of the module to enable.
    """
    logger = logging.getLogger(module_name)
    logger.disabled = False
    logging.info(f"Enabled logging for {module_name}")


# Convenience function for quick setup
def quick_setup(level: str = 'INFO', log_file: str = None) -> logging.Logger:
    """Quick logging setup with minimal configuration.
    
    Args:
        level: Logging level.
        log_file: Optional log file path.
        
    Returns:
        Configured logger.
    """
    return setup_logging(
        level=level,
        log_file=Path(log_file) if log_file else None
    )
