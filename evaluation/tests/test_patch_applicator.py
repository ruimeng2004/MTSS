"""Tests for PatchApplicator class."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from evaluation.core.data_structures import NormalizedPatch
from evaluation.core.patch_applicator import PatchApplicator


class TestPatchApplicatorInit:
    """Tests for PatchApplicator initialization."""
    
    def test_init_valid_repo(self, tmp_path):
        """Test initialization with valid repository path."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        assert applicator.repo_path == repo_path
        assert applicator.backup_dir.exists()
        assert applicator.backup_dir == repo_path / ".patch_backup"
    
    def test_init_nonexistent_repo(self, tmp_path):
        """Test initialization with non-existent repository."""
        repo_path = tmp_path / "nonexistent"
        
        with pytest.raises(ValueError, match="does not exist"):
            PatchApplicator(repo_path)
    
    def test_init_file_instead_of_directory(self, tmp_path):
        """Test initialization with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        
        with pytest.raises(ValueError, match="not a directory"):
            PatchApplicator(file_path)


class TestApplyWithGit:
    """Tests for apply_with_git method."""
    
    def test_apply_with_git_success(self, tmp_path):
        """Test successful patch application with git apply."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        diff_content = """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,3 @@
 line 1
-line 2
+line 2 modified
 line 3
"""
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Checking patch test.txt..."
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = applicator.apply_with_git(diff_content)
            
            assert result.success is True
            assert result.method == 'git_apply'
            assert 'test.txt' in result.applied_files
            assert result.error_message is None
    
    def test_apply_with_git_failure(self, tmp_path):
        """Test failed patch application with git apply."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        diff_content = "invalid diff"
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "error: patch failed"
            mock_run.return_value = mock_result
            
            result = applicator.apply_with_git(diff_content)
            
            assert result.success is False
            assert result.method == 'git_apply'
            assert 'patch failed' in result.error_message
    
    def test_apply_with_git_timeout(self, tmp_path):
        """Test git apply timeout."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('git', 30)):
            result = applicator.apply_with_git("diff content")
            
            assert result.success is False
            assert result.method == 'git_apply'
            assert 'timed out' in result.error_message
    
    def test_apply_with_git_not_found(self, tmp_path):
        """Test git command not found."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = applicator.apply_with_git("diff content")
            
            assert result.success is False
            assert result.method == 'git_apply'
            assert 'not found' in result.error_message


class TestApplyWithPatch:
    """Tests for apply_with_patch method."""
    
    def test_apply_with_patch_success(self, tmp_path):
        """Test successful patch application with patch command."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        diff_content = """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,3 @@
 line 1
-line 2
+line 2 modified
 line 3
"""
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "patching file test.txt"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = applicator.apply_with_patch(diff_content)
            
            assert result.success is True
            assert result.method == 'patch'
            assert 'test.txt' in result.applied_files
            assert result.error_message is None
    
    def test_apply_with_patch_failure(self, tmp_path):
        """Test failed patch application with patch command."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        diff_content = "invalid diff"
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "patch: malformed patch"
            mock_run.return_value = mock_result
            
            result = applicator.apply_with_patch(diff_content)
            
            assert result.success is False
            assert result.method == 'patch'
            assert 'malformed' in result.error_message
    
    def test_apply_with_patch_timeout(self, tmp_path):
        """Test patch command timeout."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('patch', 30)):
            result = applicator.apply_with_patch("diff content")
            
            assert result.success is False
            assert result.method == 'patch'
            assert 'timed out' in result.error_message
    
    def test_apply_with_patch_not_found(self, tmp_path):
        """Test patch command not found."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = applicator.apply_with_patch("diff content")
            
            assert result.success is False
            assert result.method == 'patch'
            assert 'not found' in result.error_message


class TestApply:
    """Tests for apply method."""
    
    def test_apply_success_with_git(self, tmp_path):
        """Test successful patch application using git apply."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        # Create test file
        test_file = repo_path / "test.txt"
        test_file.write_text("line 1\nline 2\nline 3\n")
        
        applicator = PatchApplicator(repo_path)
        
        normalized_patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="--- a/test.txt\n+++ b/test.txt\n@@ -1,3 +1,3 @@\n line 1\n-line 2\n+line 2 modified\n line 3\n",
            target_files=["test.txt"],
            metadata={}
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Checking patch test.txt..."
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = applicator.apply(normalized_patch)
            
            assert result.success is True
            assert result.method == 'git_apply'
    
    def test_apply_fallback_to_patch(self, tmp_path):
        """Test fallback to patch command when git apply fails."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        # Create test file
        test_file = repo_path / "test.txt"
        test_file.write_text("line 1\nline 2\nline 3\n")
        
        applicator = PatchApplicator(repo_path)
        
        normalized_patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="--- a/test.txt\n+++ b/test.txt\n@@ -1,3 +1,3 @@\n line 1\n-line 2\n+line 2 modified\n line 3\n",
            target_files=["test.txt"],
            metadata={}
        )
        
        with patch('subprocess.run') as mock_run:
            # First call (git apply) fails
            # Second call (patch) succeeds
            mock_run.side_effect = [
                Mock(returncode=1, stdout="", stderr="git apply failed"),
                Mock(returncode=0, stdout="patching file test.txt", stderr="")
            ]
            
            result = applicator.apply(normalized_patch)
            
            assert result.success is True
            assert result.method == 'patch'
    
    def test_apply_all_methods_fail(self, tmp_path):
        """Test when all patch application methods fail."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        normalized_patch = NormalizedPatch(
            bug_slug="Test_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="invalid diff",
            target_files=["test.txt"],
            metadata={}
        )
        
        with patch('subprocess.run') as mock_run:
            # Both git apply and patch fail
            mock_run.side_effect = [
                Mock(returncode=1, stdout="", stderr="git apply failed"),
                Mock(returncode=1, stdout="", stderr="patch failed")
            ]
            
            result = applicator.apply(normalized_patch)
            
            assert result.success is False


class TestBackupAndRollback:
    """Tests for backup and rollback functionality."""
    
    def test_backup_files(self, tmp_path):
        """Test backing up files before applying patch."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        # Create test files
        test_file1 = repo_path / "test1.txt"
        test_file1.write_text("original content 1")
        test_file2 = repo_path / "test2.txt"
        test_file2.write_text("original content 2")
        
        applicator = PatchApplicator(repo_path)
        
        # Backup files
        applicator._backup_files(["test1.txt", "test2.txt"])
        
        # Check backups exist
        assert (applicator.backup_dir / "test1.txt.backup").exists()
        assert (applicator.backup_dir / "test2.txt.backup").exists()
        
        # Verify backup content
        backup1 = (applicator.backup_dir / "test1.txt.backup").read_text()
        assert backup1 == "original content 1"
    
    def test_backup_nonexistent_file(self, tmp_path):
        """Test backing up non-existent file."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        # Should not raise error
        applicator._backup_files(["nonexistent.txt"])
        
        # No backup should be created
        assert not (applicator.backup_dir / "nonexistent.txt.backup").exists()
    
    def test_rollback(self, tmp_path):
        """Test rolling back to original state."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        # Create test file
        test_file = repo_path / "test.txt"
        test_file.write_text("original content")
        
        applicator = PatchApplicator(repo_path)
        
        # Backup file
        applicator._backup_files(["test.txt"])
        
        # Modify file
        test_file.write_text("modified content")
        assert test_file.read_text() == "modified content"
        
        # Rollback
        applicator.rollback()
        
        # File should be restored
        assert test_file.read_text() == "original content"
    
    def test_rollback_no_backup(self, tmp_path):
        """Test rollback when no backup exists."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        # Remove backup directory
        shutil.rmtree(applicator.backup_dir)
        
        # Should not raise error
        applicator.rollback()


class TestExtractAppliedFiles:
    """Tests for extracting applied files from command output."""
    
    def test_extract_from_git_output(self, tmp_path):
        """Test extracting files from git apply output."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        output = """Checking patch src/main/java/Test.java...
Checking patch src/test/java/TestTest.java...
Applied patch src/main/java/Test.java cleanly.
Applied patch src/test/java/TestTest.java cleanly.
"""
        
        files = applicator._extract_applied_files_from_git(output)
        
        assert len(files) == 2
        assert "src/main/java/Test.java" in files
        assert "src/test/java/TestTest.java" in files
    
    def test_extract_from_patch_output(self, tmp_path):
        """Test extracting files from patch command output."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        output = """patching file src/main/java/Test.java
patching file src/test/java/TestTest.java
"""
        
        files = applicator._extract_applied_files_from_patch(output)
        
        assert len(files) == 2
        assert "src/main/java/Test.java" in files
        assert "src/test/java/TestTest.java" in files
    
    def test_extract_from_empty_output(self, tmp_path):
        """Test extracting files from empty output."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        files = applicator._extract_applied_files_from_git("")
        assert files == []
        
        files = applicator._extract_applied_files_from_patch("")
        assert files == []


class TestCleanup:
    """Tests for cleanup functionality."""
    
    def test_cleanup(self, tmp_path):
        """Test cleaning up backup directory."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        # Create some backup files
        (applicator.backup_dir / "test1.txt.backup").write_text("backup 1")
        (applicator.backup_dir / "test2.txt.backup").write_text("backup 2")
        
        assert applicator.backup_dir.exists()
        
        # Cleanup
        applicator.cleanup()
        
        # Backup directory should be removed
        assert not applicator.backup_dir.exists()
    
    def test_cleanup_no_backup_dir(self, tmp_path):
        """Test cleanup when backup directory doesn't exist."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        # Remove backup directory
        shutil.rmtree(applicator.backup_dir)
        
        # Should not raise error
        applicator.cleanup()


class TestFindOriginalPath:
    """Tests for finding original file paths."""
    
    def test_find_original_path_exists(self, tmp_path):
        """Test finding original path when file exists."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        # Create test file in subdirectory
        subdir = repo_path / "src" / "main"
        subdir.mkdir(parents=True)
        test_file = subdir / "Test.java"
        test_file.write_text("test content")
        
        applicator = PatchApplicator(repo_path)
        
        # Find original path
        found_path = applicator._find_original_path("Test.java")
        
        assert found_path is not None
        assert found_path == test_file
    
    def test_find_original_path_not_exists(self, tmp_path):
        """Test finding original path when file doesn't exist."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        # Find non-existent file
        found_path = applicator._find_original_path("nonexistent.txt")
        
        assert found_path is None
    
    def test_find_original_path_excludes_backup(self, tmp_path):
        """Test that backup directory is excluded from search."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        applicator = PatchApplicator(repo_path)
        
        # Create file only in backup directory
        (applicator.backup_dir / "test.txt").write_text("backup")
        
        # Should not find it
        found_path = applicator._find_original_path("test.txt")
        
        assert found_path is None
