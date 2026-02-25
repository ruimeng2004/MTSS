"""Unit tests for logging configuration."""

import logging
import tempfile
import unittest
from pathlib import Path

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


class TestLoggingConfig(unittest.TestCase):
    """Test cases for logging configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear all handlers before each test
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.WARNING)
    
    def tearDown(self):
        """Clean up after tests."""
        # Reset logging to default state
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.WARNING)
    
    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        logger = setup_logging(level='INFO')
        
        self.assertEqual(logger.level, logging.INFO)
        self.assertGreater(len(logger.handlers), 0)
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            
            logger = setup_logging(
                level='DEBUG',
                log_file=log_file
            )
            
            # Log a message
            logger.info("Test message")
            
            # Check file was created
            self.assertTrue(log_file.exists())
            
            # Check message was written
            with open(log_file, 'r') as f:
                content = f.read()
                self.assertIn("Test message", content)
    
    def test_setup_logging_levels(self):
        """Test different logging levels."""
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        for level in levels:
            logger = setup_logging(level=level)
            expected_level = getattr(logging, level)
            self.assertEqual(logger.level, expected_level)
    
    def test_setup_evaluation_logging(self):
        """Test evaluation-specific logging setup."""
        config = {
            'evaluation_config': {
                'logging': {
                    'level': 'DEBUG',
                    'file': 'eval_test.log',
                    'format': '%(levelname)s - %(message)s'
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            import os
            original_dir = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                logger = setup_evaluation_logging(config)
                self.assertEqual(logger.level, logging.DEBUG)
            finally:
                os.chdir(original_dir)
    
    def test_get_logger(self):
        """Test getting module-specific logger."""
        logger = get_logger('test_module')
        
        self.assertEqual(logger.name, 'test_module')
        self.assertIsInstance(logger, logging.Logger)
    
    def test_set_module_level(self):
        """Test setting module-specific log level."""
        setup_logging(level='INFO')
        
        module_logger = get_logger('test_module')
        set_module_level('test_module', 'DEBUG')
        
        self.assertEqual(module_logger.level, logging.DEBUG)
    
    def test_quick_setup(self):
        """Test quick setup convenience function."""
        logger = quick_setup(level='WARNING')
        
        self.assertEqual(logger.level, logging.WARNING)
    
    def test_log_rotation(self):
        """Test log file rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'rotating.log'
            
            # Setup with small max_bytes for testing
            logger = setup_logging(
                level='INFO',
                log_file=log_file,
                max_bytes=100,  # Very small for testing
                backup_count=2
            )
            
            # Write enough to trigger rotation
            for i in range(50):
                logger.info(f"Message {i}" * 10)
            
            # Check that backup files were created
            log_dir = log_file.parent
            log_files = list(log_dir.glob('rotating.log*'))
            
            # Should have main file and possibly backups
            self.assertGreaterEqual(len(log_files), 1)


class TestLogContext(unittest.TestCase):
    """Test cases for log context managers."""
    
    def setUp(self):
        """Set up test fixtures."""
        setup_logging(level='INFO')
    
    def tearDown(self):
        """Clean up after tests."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
    
    def test_log_level_context(self):
        """Test temporary log level change."""
        logger = logging.getLogger()
        original_level = logger.level
        
        with log_level('DEBUG'):
            self.assertEqual(logger.level, logging.DEBUG)
        
        # Should be restored
        self.assertEqual(logger.level, original_level)
    
    def test_suppress_logging_context(self):
        """Test temporary logging suppression."""
        logger = logging.getLogger('test_suppress')
        
        with suppress_logging('test_suppress'):
            self.assertTrue(logger.disabled)
        
        # Should be restored
        self.assertFalse(logger.disabled)
    
    def test_log_to_file_context(self):
        """Test temporary file logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'context.log'
            
            with log_to_file(str(log_file), 'INFO'):
                logger = logging.getLogger()
                logger.info("Context message")
            
            # Check file was created and contains message
            self.assertTrue(log_file.exists())
            with open(log_file, 'r') as f:
                content = f.read()
                self.assertIn("Context message", content)
    
    def test_capture_logs_context(self):
        """Test log capture for testing."""
        with capture_logs('INFO') as logs:
            logger = logging.getLogger()
            logger.info("Captured message")
            logger.debug("Not captured")  # Below threshold
        
        # Should have captured INFO message
        self.assertEqual(len(logs), 1)
        # Check level number instead of name (to avoid color codes)
        self.assertEqual(logs[0].levelno, logging.INFO)
        self.assertIn("Captured message", logs[0].message)


if __name__ == '__main__':
    unittest.main()
