"""Configuration validation script for D4J Fix Evaluation System.

This script validates the configuration file and checks that all required
dependencies and paths are correctly set up.
"""

import logging
import sys
from pathlib import Path
from typing import List, Tuple

from evaluation.core.config_loader import load_config
from evaluation.core.environment_manager import EnvironmentManager

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def validate_config_file(config_path: Path) -> Tuple[bool, List[str]]:
    """Validate configuration file.
    
    Args:
        config_path: Path to configuration file.
        
    Returns:
        Tuple of (success, list of issues).
    """
    issues = []
    
    # Check if config file exists
    if not config_path.exists():
        issues.append(f"Configuration file not found: {config_path}")
        return False, issues
    
    # Try to load config
    try:
        config = load_config(config_path)
        logger.info("✓ Configuration file loaded successfully")
    except Exception as e:
        issues.append(f"Failed to load configuration: {e}")
        return False, issues
    
    # Validate evaluation_config section
    if 'evaluation_config' not in config:
        issues.append("Missing 'evaluation_config' section")
        return False, issues
    
    eval_config = config['evaluation_config']
    
    # Check required fields
    required_fields = ['d4j_path', 'workspace_dir', 'output_dir']
    for field in required_fields:
        if field not in eval_config:
            issues.append(f"Missing required field: {field}")
    
    if issues:
        return False, issues
    
    logger.info("✓ Configuration structure is valid")
    
    # Validate field values
    d4j_path = Path(eval_config['d4j_path'])
    if not d4j_path.exists():
        issues.append(
            f"D4J path does not exist: {d4j_path}\n"
            f"  Please update 'd4j_path' in {config_path}"
        )
    else:
        logger.info(f"✓ D4J path exists: {d4j_path}")
    
    # Check timeout
    timeout = eval_config.get('timeout', 600)
    if timeout <= 0:
        issues.append(f"Invalid timeout value: {timeout} (must be > 0)")
    else:
        logger.info(f"✓ Timeout: {timeout} seconds")
    
    # Check parallel_workers
    workers = eval_config.get('parallel_workers', 4)
    if workers < 1:
        issues.append(
            f"Invalid parallel_workers value: {workers} (must be >= 1)"
        )
    else:
        logger.info(f"✓ Parallel workers: {workers}")
    
    # Check deprecated_bugs
    deprecated = eval_config.get('deprecated_bugs', [])
    if not isinstance(deprecated, list):
        issues.append("deprecated_bugs must be a list")
    else:
        logger.info(f"✓ Deprecated bugs: {len(deprecated)} bugs")
    
    return len(issues) == 0, issues


def validate_d4j_installation(config_path: Path) -> Tuple[bool, List[str]]:
    """Validate Defects4J installation.
    
    Args:
        config_path: Path to configuration file.
        
    Returns:
        Tuple of (success, list of issues).
    """
    issues = []
    
    try:
        config = load_config(config_path)
        eval_config = config['evaluation_config']
        
        # Create environment manager
        env_manager = EnvironmentManager(
            d4j_path=eval_config['d4j_path'],
            workspace_dir=eval_config['workspace_dir']
        )
        
        # Verify D4J installation
        if env_manager.verify_installation():
            logger.info("✓ Defects4J installation verified")
            return True, []
        else:
            issues.append("Defects4J installation verification failed")
            return False, issues
            
    except Exception as e:
        issues.append(f"Failed to verify D4J installation: {e}")
        return False, issues


def validate_directories(config_path: Path) -> Tuple[bool, List[str]]:
    """Validate directory paths.
    
    Args:
        config_path: Path to configuration file.
        
    Returns:
        Tuple of (success, list of issues).
    """
    issues = []
    
    try:
        config = load_config(config_path)
        eval_config = config['evaluation_config']
        
        # Check workspace directory
        workspace_dir = Path(eval_config['workspace_dir'])
        if workspace_dir.exists():
            logger.info(f"✓ Workspace directory exists: {workspace_dir}")
        else:
            logger.info(
                f"ℹ Workspace directory will be created: {workspace_dir}"
            )
        
        # Check output directory
        output_dir = Path(eval_config['output_dir'])
        if output_dir.exists():
            logger.info(f"✓ Output directory exists: {output_dir}")
        else:
            logger.info(
                f"ℹ Output directory will be created: {output_dir}"
            )
        
        return True, []
        
    except Exception as e:
        issues.append(f"Failed to validate directories: {e}")
        return False, issues


def main():
    """Main validation function."""
    print("=" * 80)
    print("D4J Fix Evaluation System - Configuration Validation")
    print("=" * 80)
    print()
    
    # Find config file
    config_path = Path('config.yaml')
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.info(
            "Please copy config.example.yaml to config.yaml and update it"
        )
        return 1
    
    logger.info(f"Validating configuration: {config_path}")
    print()
    
    # Validate config file
    print("1. Validating configuration file...")
    success, issues = validate_config_file(config_path)
    if not success:
        logger.error("Configuration validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return 1
    print()
    
    # Validate directories
    print("2. Validating directories...")
    success, issues = validate_directories(config_path)
    if not success:
        logger.error("Directory validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return 1
    print()
    
    # Validate D4J installation
    print("3. Validating Defects4J installation...")
    success, issues = validate_d4j_installation(config_path)
    if not success:
        logger.warning("Defects4J validation failed:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        logger.warning(
            "Please ensure Defects4J is installed and d4j_path is correct"
        )
        print()
        print("=" * 80)
        print("Configuration validation completed with warnings")
        print("=" * 80)
        return 0  # Don't fail on D4J validation
    print()
    
    # Success
    print("=" * 80)
    print("✓ All validations passed!")
    print("=" * 80)
    print()
    print("Your configuration is ready to use.")
    print("Run evaluation with:")
    print("  python -m evaluation --result-folder <path>")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
