"""Configuration loader for the D4J Fix Evaluation System.

This module provides utilities for loading and validating configuration
from YAML files.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates configuration from YAML files."""
    
    DEFAULT_CONFIG = {
        'evaluation_config': {
            'd4j_path': '/path/to/defects4j',
            'workspace_dir': './workspace',
            'output_dir': './evaluation_output',
            'timeout': 600,
            'parallel_workers': 4,
            'cache_enabled': True,
            'deprecated_bugs': [],
            'normalization': {
                'context_lines': 3,
                'max_retries': 3
            },
            'logging': {
                'level': 'INFO',
                'file': 'evaluation.log',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ConfigLoader.
        
        Args:
            config_path: Path to config.yaml file. If None, uses default
                        config.yaml in project root.
        """
        if config_path is None:
            config_path = Path('config.yaml')
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Returns:
            Configuration dictionary.
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
            yaml.YAMLError: If config file is invalid YAML.
        """
        if not self.config_path.exists():
            logger.warning(
                f"Config file not found: {self.config_path}. "
                f"Using default configuration."
            )
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from: {self.config_path}")
            
            # Validate loaded config before merging
            if 'evaluation_config' in loaded_config:
                self._validate_loaded_config(loaded_config['evaluation_config'])
            
            # Merge with defaults for missing keys
            self.config = self._merge_with_defaults(loaded_config)
            
            # Validate final merged configuration
            self._validate()
            
            return self.config
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def _validate_loaded_config(self, eval_config: Dict[str, Any]) -> None:
        """Validate loaded config before merging with defaults.
        
        This checks that explicitly provided values are valid.
        
        Args:
            eval_config: Loaded evaluation_config section.
            
        Raises:
            ValueError: If any provided value is invalid.
        """
        # Validate numeric fields if provided
        if 'timeout' in eval_config:
            timeout = eval_config['timeout']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError(
                    f"Invalid timeout value: {timeout}. Must be positive number."
                )
        
        if 'parallel_workers' in eval_config:
            workers = eval_config['parallel_workers']
            if not isinstance(workers, int) or workers < 1:
                raise ValueError(
                    f"Invalid parallel_workers value: {workers}. "
                    f"Must be positive integer."
                )
        
        # Validate deprecated_bugs is a list if provided
        if 'deprecated_bugs' in eval_config:
            if not isinstance(eval_config['deprecated_bugs'], list):
                raise ValueError(
                    "deprecated_bugs must be a list of bug slugs"
                )
    
    def _merge_with_defaults(
        self, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge loaded config with default values for missing keys.
        
        Args:
            config: Loaded configuration.
            
        Returns:
            Merged configuration.
        """
        import copy
        merged = copy.deepcopy(self.DEFAULT_CONFIG)
        
        if 'evaluation_config' in config:
            eval_config = config['evaluation_config']
            
            # Merge top-level keys
            for key, value in eval_config.items():
                if isinstance(value, dict) and key in merged['evaluation_config']:
                    # Merge nested dicts - update defaults with provided values
                    if isinstance(merged['evaluation_config'][key], dict):
                        merged['evaluation_config'][key].update(value)
                    else:
                        merged['evaluation_config'][key] = value
                else:
                    merged['evaluation_config'][key] = value
        
        # Keep other config sections (model_config, test_config, etc.)
        for key, value in config.items():
            if key != 'evaluation_config':
                merged[key] = value
        
        return merged
    
    def _validate(self) -> None:
        """Validate final merged configuration values.
        
        Raises:
            ValueError: If configuration is invalid.
        """
        if 'evaluation_config' not in self.config:
            raise ValueError("Missing 'evaluation_config' section in config")
        
        eval_config = self.config['evaluation_config']
        
        # Validate required fields exist in final config
        required_fields = ['d4j_path', 'workspace_dir', 'output_dir']
        for field in required_fields:
            if field not in eval_config:
                raise ValueError(
                    f"Missing required field in evaluation_config: {field}"
                )
        
        logger.info("Configuration validation passed")
    
    def get_evaluation_config(self) -> Dict[str, Any]:
        """Get evaluation configuration section.
        
        Returns:
            Evaluation configuration dictionary.
        """
        if not self.config:
            self.load()
        
        return self.config.get('evaluation_config', {})
    
    def get_d4j_path(self) -> Path:
        """Get Defects4J installation path.
        
        Returns:
            Path to D4J installation.
        """
        eval_config = self.get_evaluation_config()
        return Path(eval_config['d4j_path'])
    
    def get_workspace_dir(self) -> Path:
        """Get workspace directory path.
        
        Returns:
            Path to workspace directory.
        """
        eval_config = self.get_evaluation_config()
        return Path(eval_config['workspace_dir'])
    
    def get_output_dir(self) -> Path:
        """Get output directory path.
        
        Returns:
            Path to output directory.
        """
        eval_config = self.get_evaluation_config()
        return Path(eval_config['output_dir'])
    
    def get_timeout(self) -> int:
        """Get test execution timeout.
        
        Returns:
            Timeout in seconds.
        """
        eval_config = self.get_evaluation_config()
        return eval_config.get('timeout', 600)
    
    def get_parallel_workers(self) -> int:
        """Get number of parallel workers.
        
        Returns:
            Number of parallel workers.
        """
        eval_config = self.get_evaluation_config()
        return eval_config.get('parallel_workers', 4)
    
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled.
        
        Returns:
            True if caching is enabled, False otherwise.
        """
        eval_config = self.get_evaluation_config()
        return eval_config.get('cache_enabled', True)
    
    def get_deprecated_bugs(self) -> List[str]:
        """Get list of deprecated bugs.
        
        Returns:
            List of deprecated bug slugs.
        """
        eval_config = self.get_evaluation_config()
        return eval_config.get('deprecated_bugs', [])
    
    def get_context_lines(self) -> int:
        """Get number of context lines for unified diff.
        
        Returns:
            Number of context lines.
        """
        eval_config = self.get_evaluation_config()
        normalization = eval_config.get('normalization', {})
        return normalization.get('context_lines', 3)
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration.
        
        Returns:
            Logging configuration dictionary.
        """
        eval_config = self.get_evaluation_config()
        return eval_config.get('logging', {
            'level': 'INFO',
            'file': 'evaluation.log',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        })


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Convenience function to load configuration.
    
    Args:
        config_path: Path to config.yaml file.
        
    Returns:
        Configuration dictionary.
    """
    loader = ConfigLoader(config_path)
    return loader.load()
