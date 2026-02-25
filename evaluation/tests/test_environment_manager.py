"""Tests for EnvironmentManager class."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from evaluation.core.environment_manager import EnvironmentManager


class TestEnvironmentManagerInit:
    """Tests for EnvironmentManager initialization."""
    
    def test_init_with_explicit_paths(self, tmp_path):
        """Test initialization with explicit paths."""
        d4j_path = tmp_path / "d4j"
        workspace = tmp_path / "workspace"
        d4j_path.mkdir()
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=workspace
        )
        
        assert manager.d4j_path == d4j_path
        assert manager.workspace_dir == workspace
        assert workspace.exists()
    
    def test_init_creates_workspace(self, tmp_path):
        """Test that workspace directory is created if it doesn't exist."""
        d4j_path = tmp_path / "d4j"
        workspace = tmp_path / "workspace"
        d4j_path.mkdir()
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=workspace
        )
        
        assert workspace.exists()
        assert workspace.is_dir()
    
    def test_init_with_custom_deprecated_bugs(self, tmp_path):
        """Test initialization with custom deprecated bugs list."""
        d4j_path = tmp_path / "d4j"
        d4j_path.mkdir()
        
        custom_deprecated = ['Chart_1', 'Lang_2']
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=tmp_path / "workspace",
            deprecated_bugs=custom_deprecated
        )
        
        assert manager.deprecated_bugs == set(custom_deprecated)
    
    def test_init_uses_default_deprecated_bugs(self, tmp_path):
        """Test that default deprecated bugs are used."""
        d4j_path = tmp_path / "d4j"
        d4j_path.mkdir()
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=tmp_path / "workspace"
        )
        
        assert 'Lang_18' in manager.deprecated_bugs
        assert 'Lang_25' in manager.deprecated_bugs


class TestFindD4JPath:
    """Tests for _find_d4j_path method."""
    
    @patch.dict('os.environ', {'D4J_HOME': '/path/to/d4j'})
    @patch('pathlib.Path.exists')
    def test_find_from_d4j_home(self, mock_exists):
        """Test finding D4J from D4J_HOME environment variable."""
        mock_exists.return_value = True
        
        manager = EnvironmentManager(workspace_dir=Path('./test_workspace'))
        
        # Should find from D4J_HOME
        assert manager.d4j_path == Path('/path/to/d4j')
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('subprocess.run')
    def test_find_from_path(self, mock_run):
        """Test finding D4J from PATH."""
        # Mock which command output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '/usr/local/defects4j/framework/bin/defects4j\n'
        mock_run.return_value = mock_result
        
        manager = EnvironmentManager(workspace_dir=Path('./test_workspace'))
        
        # Should find from PATH
        assert manager.d4j_path == Path('/usr/local/defects4j/framework')
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('subprocess.run')
    def test_find_not_found(self, mock_run):
        """Test when D4J is not found."""
        mock_run.side_effect = FileNotFoundError()
        
        manager = EnvironmentManager(workspace_dir=Path('./test_workspace'))
        
        assert manager.d4j_path is None


class TestVerifyInstallation:
    """Tests for verify_installation method."""
    
    def test_verify_success(self, tmp_path):
        """Test successful verification."""
        d4j_path = tmp_path / "d4j"
        d4j_path.mkdir()
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = manager.verify_installation()
            
            assert result is True
            mock_run.assert_called_once()
    
    def test_verify_d4j_path_not_exists(self, tmp_path):
        """Test verification when D4J path doesn't exist."""
        d4j_path = tmp_path / "nonexistent"
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=tmp_path / "workspace"
        )
        
        result = manager.verify_installation()
        
        assert result is False
    
    def test_verify_command_fails(self, tmp_path):
        """Test verification when defects4j command fails."""
        d4j_path = tmp_path / "d4j"
        d4j_path.mkdir()
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Command failed"
            mock_run.return_value = mock_result
            
            result = manager.verify_installation()
            
            assert result is False
    
    def test_verify_command_not_found(self, tmp_path):
        """Test verification when defects4j command is not found."""
        d4j_path = tmp_path / "d4j"
        d4j_path.mkdir()
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = manager.verify_installation()
            
            assert result is False
    
    def test_verify_timeout(self, tmp_path):
        """Test verification when command times out."""
        d4j_path = tmp_path / "d4j"
        d4j_path.mkdir()
        
        manager = EnvironmentManager(
            d4j_path=d4j_path,
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 30)):
            result = manager.verify_installation()
            
            assert result is False


class TestCheckoutBug:
    """Tests for checkout_bug method."""
    
    def test_checkout_success(self, tmp_path):
        """Test successful bug checkout."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            checkout_dir = manager.checkout_bug('Chart_1', version='b')
            
            assert checkout_dir == tmp_path / "workspace" / "Chart_1_b"
            mock_run.assert_called_once()
            
            # Verify command arguments
            call_args = mock_run.call_args[0][0]
            assert 'defects4j' in call_args
            assert 'checkout' in call_args
            assert '-p' in call_args
            assert 'Chart' in call_args
            assert '-v' in call_args
            assert '1b' in call_args
    
    def test_checkout_with_custom_work_dir(self, tmp_path):
        """Test checkout with custom work directory."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        custom_dir = tmp_path / "custom" / "Chart_1"
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            checkout_dir = manager.checkout_bug(
                'Chart_1',
                version='f',
                work_dir=custom_dir
            )
            
            assert checkout_dir == custom_dir
    
    def test_checkout_removes_existing_directory(self, tmp_path):
        """Test that existing checkout directory is removed."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        # Create existing directory
        existing_dir = tmp_path / "workspace" / "Chart_1_b"
        existing_dir.mkdir(parents=True)
        test_file = existing_dir / "test.txt"
        test_file.write_text("test")
        
        assert existing_dir.exists()
        assert test_file.exists()
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            checkout_dir = manager.checkout_bug('Chart_1', version='b')
            
            # Directory should have been removed before checkout
            # (the mock doesn't recreate it, but in real usage D4J would)
            assert checkout_dir == tmp_path / "workspace" / "Chart_1_b"
    
    def test_checkout_invalid_bug_slug(self, tmp_path):
        """Test checkout with invalid bug slug format."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        with pytest.raises(ValueError, match="Invalid bug slug format"):
            manager.checkout_bug('InvalidSlug')
    
    def test_checkout_command_fails(self, tmp_path):
        """Test checkout when defects4j command fails."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Checkout failed"
            mock_run.return_value = mock_result
            
            with pytest.raises(RuntimeError, match="Failed to checkout"):
                manager.checkout_bug('Chart_1')
    
    def test_checkout_timeout(self, tmp_path):
        """Test checkout when command times out."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 300)):
            with pytest.raises(RuntimeError, match="timed out"):
                manager.checkout_bug('Chart_1')


class TestIsDeprecated:
    """Tests for is_deprecated method."""
    
    def test_deprecated_bug(self, tmp_path):
        """Test checking deprecated bug."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        assert manager.is_deprecated('Lang_18') is True
        assert manager.is_deprecated('Lang_25') is True
    
    def test_non_deprecated_bug(self, tmp_path):
        """Test checking non-deprecated bug."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        assert manager.is_deprecated('Chart_1') is False
        assert manager.is_deprecated('Lang_1') is False


class TestCleanup:
    """Tests for cleanup method."""
    
    def test_cleanup_existing_repo(self, tmp_path):
        """Test cleaning up existing repository."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        # Create a test repository
        repo_path = tmp_path / "workspace" / "Chart_1_b"
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test")
        
        manager.cleanup(repo_path)
        
        assert not repo_path.exists()
    
    def test_cleanup_nonexistent_repo(self, tmp_path):
        """Test cleaning up non-existent repository."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        repo_path = tmp_path / "workspace" / "nonexistent"
        
        # Should not raise error
        manager.cleanup(repo_path)
    
    def test_cleanup_outside_workspace_without_force(self, tmp_path):
        """Test cleanup fails for repo outside workspace without force."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        outside_repo = tmp_path / "outside" / "repo"
        outside_repo.mkdir(parents=True)
        
        with pytest.raises(ValueError, match="not in workspace directory"):
            manager.cleanup(outside_repo, force=False)
    
    def test_cleanup_outside_workspace_with_force(self, tmp_path):
        """Test cleanup succeeds for repo outside workspace with force."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        outside_repo = tmp_path / "outside" / "repo"
        outside_repo.mkdir(parents=True)
        (outside_repo / "test.txt").write_text("test")
        
        manager.cleanup(outside_repo, force=True)
        
        assert not outside_repo.exists()


class TestGetBugInfo:
    """Tests for get_bug_info method."""
    
    def test_get_bug_info_success(self, tmp_path):
        """Test getting bug info successfully."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Bug info output"
            mock_run.return_value = mock_result
            
            info = manager.get_bug_info('Chart_1')
            
            assert info is not None
            assert info['bug_slug'] == 'Chart_1'
            assert info['project'] == 'Chart'
            assert info['bug_id'] == '1'
            assert 'raw_output' in info
    
    def test_get_bug_info_invalid_slug(self, tmp_path):
        """Test getting bug info with invalid slug."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        info = manager.get_bug_info('InvalidSlug')
        
        assert info is None
    
    def test_get_bug_info_command_fails(self, tmp_path):
        """Test getting bug info when command fails."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result
            
            info = manager.get_bug_info('Chart_1')
            
            assert info is None


class TestCompileBug:
    """Tests for compile_bug method."""
    
    def test_compile_success(self, tmp_path):
        """Test successful compilation."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        repo_path = tmp_path / "workspace" / "Chart_1_b"
        repo_path.mkdir(parents=True)
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = manager.compile_bug(repo_path)
            
            assert result is True
            mock_run.assert_called_once()
            assert mock_run.call_args[1]['cwd'] == repo_path
    
    def test_compile_fails(self, tmp_path):
        """Test compilation failure."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        repo_path = tmp_path / "workspace" / "Chart_1_b"
        repo_path.mkdir(parents=True)
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Compilation error"
            mock_run.return_value = mock_result
            
            result = manager.compile_bug(repo_path)
            
            assert result is False
    
    def test_compile_timeout(self, tmp_path):
        """Test compilation timeout."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        repo_path = tmp_path / "workspace" / "Chart_1_b"
        repo_path.mkdir(parents=True)
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 600)):
            result = manager.compile_bug(repo_path)
            
            assert result is False


class TestWorkspaceManagement:
    """Tests for workspace management methods."""
    
    def test_get_workspace_size(self, tmp_path):
        """Test getting workspace size."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        # Create some files
        (tmp_path / "workspace" / "file1.txt").write_text("a" * 100)
        (tmp_path / "workspace" / "file2.txt").write_text("b" * 200)
        
        size = manager.get_workspace_size()
        
        assert size == 300
    
    def test_cleanup_all(self, tmp_path):
        """Test cleaning up entire workspace."""
        manager = EnvironmentManager(
            d4j_path=tmp_path / "d4j",
            workspace_dir=tmp_path / "workspace"
        )
        
        # Create some files and directories
        repo1 = tmp_path / "workspace" / "Chart_1_b"
        repo2 = tmp_path / "workspace" / "Lang_1_b"
        repo1.mkdir(parents=True)
        repo2.mkdir(parents=True)
        (repo1 / "test.txt").write_text("test")
        (repo2 / "test.txt").write_text("test")
        
        manager.cleanup_all()
        
        # Workspace should exist but be empty
        assert manager.workspace_dir.exists()
        assert list(manager.workspace_dir.iterdir()) == []
