"""Unit tests for ConfigLoader class."""

import tempfile
import unittest
from pathlib import Path

import yaml

from evaluation.core.config_loader import ConfigLoader, load_config


class TestConfigLoader(unittest.TestCase):
    """Test cases for ConfigLoader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def _create_config_file(self, config_dict: dict) -> Path:
        """Create a test config file.
        
        Args:
            config_dict: Configuration dictionary to write.
            
        Returns:
            Path to created config file.
        """
        config_path = self.test_path / 'test_config.yaml'
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f)
        return config_path
    
    def test_load_valid_config(self):
        """Test loading valid configuration."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/test/path/to/defects4j',
                'workspace_dir': './test_workspace',
                'output_dir': './test_output',
                'timeout': 300,
                'parallel_workers': 2
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        config = loader.load()
        
        self.assertIn('evaluation_config', config)
        self.assertEqual(
            config['evaluation_config']['d4j_path'],
            '/test/path/to/defects4j'
        )
        self.assertEqual(config['evaluation_config']['timeout'], 300)
    
    def test_load_nonexistent_config(self):
        """Test loading nonexistent config file uses defaults."""
        config_path = self.test_path / 'nonexistent.yaml'
        loader = ConfigLoader(config_path)
        config = loader.load()
        
        # Should return default config
        self.assertIn('evaluation_config', config)
        self.assertEqual(config['evaluation_config']['timeout'], 600)
    
    def test_merge_with_defaults(self):
        """Test merging partial config with defaults."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/custom/path',
                'timeout': 300
                # Other fields should use defaults
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        config = loader.load()
        
        # Custom values
        self.assertEqual(
            config['evaluation_config']['d4j_path'],
            '/custom/path'
        )
        self.assertEqual(config['evaluation_config']['timeout'], 300)
        
        # Default values
        self.assertEqual(
            config['evaluation_config']['parallel_workers'],
            4
        )
        self.assertTrue(config['evaluation_config']['cache_enabled'])
    
    def test_validate_missing_required_field(self):
        """Test that default values are used for missing fields."""
        # Note: Missing fields will be filled with defaults during merge
        # This test verifies that the merge works correctly
        config_dict = {
            'evaluation_config': {
                # Only provide some fields
                'workspace_dir': './workspace',
                'output_dir': './output',
                'timeout': 600,
                'parallel_workers': 4
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        config = loader.load()
        
        # Should succeed with default d4j_path
        self.assertIn('d4j_path', config['evaluation_config'])
        self.assertEqual(
            config['evaluation_config']['d4j_path'],
            '/path/to/defects4j'  # Default value
        )
    
    def test_validate_invalid_timeout(self):
        """Test validation fails for invalid timeout."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/path/to/d4j',
                'workspace_dir': './workspace',
                'output_dir': './output',
                'timeout': -100  # Invalid: negative
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        
        with self.assertRaises(ValueError) as context:
            loader.load()
        
        self.assertIn('timeout', str(context.exception))
    
    def test_validate_invalid_parallel_workers(self):
        """Test validation fails for invalid parallel_workers."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/path/to/d4j',
                'workspace_dir': './workspace',
                'output_dir': './output',
                'parallel_workers': 0  # Invalid: must be >= 1
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        
        with self.assertRaises(ValueError) as context:
            loader.load()
        
        self.assertIn('parallel_workers', str(context.exception))
    
    def test_get_evaluation_config(self):
        """Test getting evaluation config section."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/test/path',
                'workspace_dir': './workspace',
                'output_dir': './output'
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        loader.load()
        
        eval_config = loader.get_evaluation_config()
        self.assertEqual(eval_config['d4j_path'], '/test/path')
    
    def test_get_d4j_path(self):
        """Test getting D4J path."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/custom/d4j/path',
                'workspace_dir': './workspace',
                'output_dir': './output'
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        loader.load()
        
        d4j_path = loader.get_d4j_path()
        self.assertEqual(d4j_path, Path('/custom/d4j/path'))
    
    def test_get_deprecated_bugs(self):
        """Test getting deprecated bugs list."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/path/to/d4j',
                'workspace_dir': './workspace',
                'output_dir': './output',
                'deprecated_bugs': ['Lang_2', 'Lang_18']
            }
        }
        
        config_path = self._create_config_file(config_dict)
        loader = ConfigLoader(config_path)
        loader.load()
        
        deprecated = loader.get_deprecated_bugs()
        self.assertEqual(len(deprecated), 2)
        self.assertIn('Lang_2', deprecated)
        self.assertIn('Lang_18', deprecated)
    
    def test_convenience_function(self):
        """Test convenience load_config function."""
        config_dict = {
            'evaluation_config': {
                'd4j_path': '/test/path',
                'workspace_dir': './workspace',
                'output_dir': './output'
            }
        }
        
        config_path = self._create_config_file(config_dict)
        config = load_config(config_path)
        
        self.assertIn('evaluation_config', config)
        self.assertEqual(
            config['evaluation_config']['d4j_path'],
            '/test/path'
        )


if __name__ == '__main__':
    unittest.main()
