"""Demo script showing logging system usage.

This script demonstrates various features of the evaluation system's
logging configuration.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evaluation.utils import (
    setup_logging,
    get_logger,
    log_level,
    suppress_logging,
    capture_logs
)


def demo_basic_logging():
    """Demonstrate basic logging setup."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Logging")
    print("=" * 60)
    
    # Setup logging
    setup_logging(level='INFO')
    logger = get_logger(__name__)
    
    # Log messages at different levels
    logger.debug("This is a DEBUG message (won't show at INFO level)")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")


def demo_file_logging():
    """Demonstrate logging to file."""
    print("\n" + "=" * 60)
    print("Demo 2: File Logging")
    print("=" * 60)
    
    # Setup logging with file output
    log_file = Path('demo_logs/evaluation.log')
    setup_logging(level='DEBUG', log_file=log_file)
    logger = get_logger(__name__)
    
    logger.info("This message goes to both console and file")
    logger.debug("Debug information saved to file")
    
    print(f"\nLog file created at: {log_file.absolute()}")


def demo_context_managers():
    """Demonstrate log context managers."""
    print("\n" + "=" * 60)
    print("Demo 3: Context Managers")
    print("=" * 60)
    
    setup_logging(level='INFO')
    logger = get_logger(__name__)
    
    # Normal logging
    logger.info("Normal INFO level")
    logger.debug("This DEBUG won't show")
    
    # Temporarily change to DEBUG level
    print("\n--- Temporarily changing to DEBUG level ---")
    with log_level('DEBUG'):
        logger.debug("Now DEBUG messages show!")
        logger.info("INFO still works")
    
    # Back to INFO level
    print("\n--- Back to INFO level ---")
    logger.debug("DEBUG hidden again")
    logger.info("INFO still visible")
    
    # Suppress logging temporarily
    print("\n--- Suppressing logging ---")
    with suppress_logging():
        logger.info("This won't be shown")
    
    print("--- Logging restored ---")
    logger.info("Logging is back!")


def demo_capture_logs():
    """Demonstrate log capture for testing."""
    print("\n" + "=" * 60)
    print("Demo 4: Capturing Logs")
    print("=" * 60)
    
    setup_logging(level='INFO')
    logger = get_logger(__name__)
    
    # Capture logs
    with capture_logs('INFO') as logs:
        logger.info("Message 1")
        logger.warning("Message 2")
        logger.error("Message 3")
    
    print(f"\nCaptured {len(logs)} log records:")
    for i, record in enumerate(logs, 1):
        print(f"  {i}. [{record.levelname}] {record.message}")


def demo_module_specific():
    """Demonstrate module-specific logging."""
    print("\n" + "=" * 60)
    print("Demo 5: Module-Specific Logging")
    print("=" * 60)
    
    setup_logging(level='WARNING')
    
    # Create loggers for different modules
    core_logger = get_logger('evaluation.core')
    utils_logger = get_logger('evaluation.utils')
    
    print("\n--- Default WARNING level ---")
    core_logger.info("Core INFO (hidden)")
    core_logger.warning("Core WARNING (visible)")
    
    # Change level for specific module
    from evaluation.utils import set_module_level
    set_module_level('evaluation.core', 'DEBUG')
    
    print("\n--- After setting core to DEBUG ---")
    core_logger.debug("Core DEBUG (now visible)")
    core_logger.info("Core INFO (now visible)")
    utils_logger.info("Utils INFO (still hidden)")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("D4J Fix Evaluation System - Logging Demo")
    print("=" * 60)
    
    try:
        demo_basic_logging()
        demo_file_logging()
        demo_context_managers()
        demo_capture_logs()
        demo_module_specific()
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
