"""Verification script for D4J Fix Evaluation System setup.

This script checks that all required dependencies and tools are installed
and properly configured.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def check_python_version() -> bool:
    """Check Python version is 3.7 or higher.
    
    Returns:
        True if version is sufficient, False otherwise.
    """
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        logger.info(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        logger.error(
            f"✗ Python version {version.major}.{version.minor} is too old. "
            f"Requires Python 3.7+"
        )
        return False


def check_package(package_name: str) -> bool:
    """Check if a Python package is installed.
    
    Args:
        package_name: Name of the package to check.
        
    Returns:
        True if package is installed, False otherwise.
    """
    try:
        __import__(package_name.replace('-', '_'))
        logger.info(f"✓ {package_name} is installed")
        return True
    except ImportError:
        logger.error(f"✗ {package_name} is not installed")
        return False


def check_command(command: str, args: List[str] = None) -> bool:
    """Check if a command-line tool is available.
    
    Args:
        command: Command to check.
        args: Arguments to pass to command (default: ['--version']).
        
    Returns:
        True if command is available, False otherwise.
    """
    if args is None:
        args = ['--version']
    
    try:
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info(f"✓ {command} is available")
            return True
        else:
            logger.error(f"✗ {command} returned error code {result.returncode}")
            return False
    except FileNotFoundError:
        logger.error(f"✗ {command} is not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"✗ {command} timed out")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking {command}: {e}")
        return False


def check_d4j_installation(d4j_path: str = None) -> bool:
    """Check if Defects4J is installed and accessible.
    
    Args:
        d4j_path: Path to D4J installation (optional).
        
    Returns:
        True if D4J is installed, False otherwise.
    """
    # Try to run defects4j command
    if check_command('defects4j', ['info', '-p', 'Chart']):
        return True
    
    # If d4j_path is provided, check that location
    if d4j_path:
        d4j_bin = Path(d4j_path) / 'framework' / 'bin' / 'defects4j'
        if d4j_bin.exists():
            logger.info(f"✓ Defects4J found at: {d4j_path}")
            logger.warning(
                f"  Note: Add {d4j_bin.parent} to your PATH to use 'defects4j' command"
            )
            return True
        else:
            logger.error(f"✗ Defects4J not found at: {d4j_path}")
            return False
    
    logger.error(
        "✗ Defects4J is not installed or not in PATH. "
        "Please install from: https://github.com/rjust/defects4j"
    )
    return False


def check_config_file() -> Tuple[bool, dict]:
    """Check if config.yaml exists and is valid.
    
    Returns:
        Tuple of (is_valid, config_dict).
    """
    config_path = Path('config.yaml')
    
    if not config_path.exists():
        logger.warning("⚠ config.yaml not found in project root")
        return False, {}
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'evaluation_config' in config:
            logger.info("✓ config.yaml exists and contains evaluation_config")
            return True, config
        else:
            logger.warning(
                "⚠ config.yaml exists but missing 'evaluation_config' section"
            )
            return False, config
    except Exception as e:
        logger.error(f"✗ Error reading config.yaml: {e}")
        return False, {}


def main():
    """Run all verification checks."""
    logger.info("=" * 60)
    logger.info("D4J Fix Evaluation System - Setup Verification")
    logger.info("=" * 60)
    
    checks = []
    
    # Check Python version
    logger.info("\n1. Checking Python version...")
    checks.append(check_python_version())
    
    # Check required Python packages
    logger.info("\n2. Checking Python packages...")
    required_packages = [
        'yaml',
        'git',
        'tqdm',
        'pytest',
        'tree_sitter',
    ]
    
    for package in required_packages:
        checks.append(check_package(package))
    
    # Check command-line tools
    logger.info("\n3. Checking command-line tools...")
    required_commands = [
        ('git', ['--version']),
        ('java', ['-version']),
    ]
    
    for command, args in required_commands:
        checks.append(check_command(command, args))
    
    # Check Defects4J
    logger.info("\n4. Checking Defects4J installation...")
    config_valid, config = check_config_file()
    
    d4j_path = None
    if config_valid and 'evaluation_config' in config:
        d4j_path = config['evaluation_config'].get('d4j_path')
    
    checks.append(check_d4j_installation(d4j_path))
    
    # Check config file
    logger.info("\n5. Checking configuration file...")
    checks.append(config_valid)
    
    # Summary
    logger.info("\n" + "=" * 60)
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        logger.info(f"✓ All checks passed ({passed}/{total})")
        logger.info("\nYour environment is ready for D4J Fix Evaluation!")
        return 0
    else:
        logger.error(f"✗ Some checks failed ({passed}/{total} passed)")
        logger.error("\nPlease fix the issues above before running evaluation.")
        
        # Print installation instructions
        logger.info("\n" + "=" * 60)
        logger.info("Installation Instructions:")
        logger.info("=" * 60)
        logger.info("\n1. Install Python packages:")
        logger.info("   pip install -r requirements.txt")
        logger.info("\n2. Install Defects4J:")
        logger.info("   git clone https://github.com/rjust/defects4j.git")
        logger.info("   cd defects4j")
        logger.info("   cpanm --installdeps .")
        logger.info("   ./init.sh")
        logger.info("\n3. Update config.yaml with your D4J path")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
