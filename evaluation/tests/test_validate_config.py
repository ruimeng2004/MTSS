"""Tests for configuration validation script."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from evaluation.validate_config import (
    validate_config_file,
    validate_d4j_installation,
    validate_directories,
)


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_config():
    """Create valid configuration dictionary."""
    return {
        'evaluation_config': {
            'd4j_path': '/path/to/defects4j',
            'workspace_dir': './workspace',
            'output_dir': './output',
            'timeout': 600,
            'parallel_workers': 4,
            'deprecated_bugs': ['Lang_2', 'Lang_18']
        }
    }


class TestValidateConfigFile:
    """Tests for validate_config_file function."""
    
    def test_validate_nonexistent_file(self, temp_config_dir):
        """Test validation of nonexistent config file."""
        config_path = temp_config_dir / 'nonexistent.yaml'
        
        success, issues = validate_config_file(config_path)
        
        assert not success
        assert len(issues) > 0
        assert 'not found' in issues[0].lower()
    
    def test_validate_valid_config(self, temp_config_dir, valid_config):
        """Test validation of valid config file."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Create D4J path
        d4j_path = temp_config_dir / 'defects4j'
        d4j_path.mkdir()
        valid_config['evaluation_config']['d4j_path'] = str(d4j_path)
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        success, issues = validate_config_file(config_path)
        
        assert success
        assert len(issues) == 0
    
    def test_validate_missing_section(self, temp_config_dir):
        """Test validation with missing evaluation_config section."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Write config without evaluation_config
        with open(config_path, 'w') as f:
            yaml.dump({'other_config': {}}, f)
        
        success, issues = validate_config_file(config_path)
        
        # Should succeed with default config, but D4J path won't exist
        assert not success
        assert any('does not exist' in issue for issue in issues)
    
    def test_validate_missing_required_field(
        self,
        temp_config_dir,
        valid_config
    ):
        """Test validation with missing required field."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Remove required field
        del valid_config['evaluation_config']['d4j_path']
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        success, issues = validate_config_file(config_path)
        
        assert not success
        assert any('d4j_path' in issue for issue in issues)
    
    def test_validate_nonexistent_d4j_path(
        self,
        temp_config_dir,
        valid_config
    ):
        """Test validation with nonexistent D4J path."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Set nonexistent D4J path
        valid_config['evaluation_config']['d4j_path'] = '/nonexistent/path'
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        success, issues = validate_config_file(config_path)
        
        assert not success
        assert any('does not exist' in issue for issue in issues)
    
    def test_validate_invalid_timeout(self, temp_config_dir, valid_config):
        """Test validation with invalid timeout."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Create D4J path
        d4j_path = temp_config_dir / 'defects4j'
        d4j_path.mkdir()
        valid_config['evaluation_config']['d4j_path'] = str(d4j_path)
        
        # Set invalid timeout
        valid_config['evaluation_config']['timeout'] = -100
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        success, issues = validate_config_file(config_path)
        
        assert not success
        assert any('timeout' in issue.lower() for issue in issues)
    
    def test_validate_invalid_workers(self, temp_config_dir, valid_config):
        """Test validation with invalid parallel_workers."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Create D4J path
        d4j_path = temp_config_dir / 'defects4j'
        d4j_path.mkdir()
        valid_config['evaluation_config']['d4j_path'] = str(d4j_path)
        
        # Set invalid workers
        valid_config['evaluation_config']['parallel_workers'] = 0
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        success, issues = validate_config_file(config_path)
        
        assert not success
        assert any('parallel_workers' in issue for issue in issues)


class TestValidateD4JInstallation:
    """Tests for validate_d4j_installation function."""
    
    @patch('evaluation.validate_config.EnvironmentManager')
    def test_validate_d4j_success(
        self,
        mock_env_manager_class,
        temp_config_dir,
        valid_config
    ):
        """Test successful D4J validation."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        # Mock environment manager
        mock_env = Mock()
        mock_env.verify_installation.return_value = True
        mock_env_manager_class.return_value = mock_env
        
        success, issues = validate_d4j_installation(config_path)
        
        assert success
        assert len(issues) == 0
    
    @patch('evaluation.validate_config.EnvironmentManager')
    def test_validate_d4j_failure(
        self,
        mock_env_manager_class,
        temp_config_dir,
        valid_config
    ):
        """Test failed D4J validation."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        # Mock environment manager
        mock_env = Mock()
        mock_env.verify_installation.return_value = False
        mock_env_manager_class.return_value = mock_env
        
        success, issues = validate_d4j_installation(config_path)
        
        assert not success
        assert len(issues) > 0


class TestValidateDirectories:
    """Tests for validate_directories function."""
    
    def test_validate_existing_directories(
        self,
        temp_config_dir,
        valid_config
    ):
        """Test validation with existing directories."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Create directories
        workspace_dir = temp_config_dir / 'workspace'
        workspace_dir.mkdir()
        output_dir = temp_config_dir / 'output'
        output_dir.mkdir()
        
        valid_config['evaluation_config']['workspace_dir'] = str(workspace_dir)
        valid_config['evaluation_config']['output_dir'] = str(output_dir)
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        success, issues = validate_directories(config_path)
        
        assert success
        assert len(issues) == 0
    
    def test_validate_nonexistent_directories(
        self,
        temp_config_dir,
        valid_config
    ):
        """Test validation with nonexistent directories."""
        config_path = temp_config_dir / 'config.yaml'
        
        # Set nonexistent directories
        valid_config['evaluation_config']['workspace_dir'] = './nonexistent1'
        valid_config['evaluation_config']['output_dir'] = './nonexistent2'
        
        # Write config
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        success, issues = validate_directories(config_path)
        
        # Should succeed (directories will be created)
        assert success
        assert len(issues) == 0
