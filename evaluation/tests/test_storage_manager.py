"""Tests for StorageManager class."""

import json
from pathlib import Path

import pytest

from evaluation.core.data_structures import (
    BatchEvaluationResult,
    BugEvaluationResult,
    NormalizedPatch,
    TestResult,
)
from evaluation.core.storage_manager import StorageManager


class TestStorageManagerInit:
    """Tests for StorageManager initialization."""
    
    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates required directories."""
        output_dir = tmp_path / "output"
        
        manager = StorageManager(output_dir)
        
        assert manager.output_dir.exists()
        assert manager.patches_dir.exists()
        assert manager.bug_results_dir.exists()
        assert manager.patches_dir == output_dir / "patches"
        assert manager.bug_results_dir == output_dir / "bug_results"
    
    def test_init_existing_directory(self, tmp_path):
        """Test initialization with existing directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        manager = StorageManager(output_dir)
        
        assert manager.output_dir.exists()


class TestSaveNormalizedPatch:
    """Tests for save_normalized_patch method."""
    
    def test_save_patch_default_filename(self, tmp_path):
        """Test saving patch with default filename."""
        manager = StorageManager(tmp_path)
        
        patch = NormalizedPatch(
            bug_slug="Chart_1",
            attempt_num=2,
            modeling_type="edit",
            diff_content="--- a/test.java\n+++ b/test.java\n@@ -1 +1 @@\n-old\n+new\n",
            target_files=["test.java"],
            metadata={}
        )
        
        saved_path = manager.save_normalized_patch(patch)
        
        assert saved_path.exists()
        assert saved_path.name == "Chart_1_attempt_2.patch"
        assert saved_path.read_text() == patch.diff_content
    
    def test_save_patch_custom_filename(self, tmp_path):
        """Test saving patch with custom filename."""
        manager = StorageManager(tmp_path)
        
        patch = NormalizedPatch(
            bug_slug="Chart_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="diff content",
            target_files=["test.java"],
            metadata={}
        )
        
        saved_path = manager.save_normalized_patch(patch, filename="custom.patch")
        
        assert saved_path.exists()
        assert saved_path.name == "custom.patch"
    
    def test_save_multiple_patches(self, tmp_path):
        """Test saving multiple patches."""
        manager = StorageManager(tmp_path)
        
        for i in range(3):
            patch = NormalizedPatch(
                bug_slug=f"Chart_{i}",
                attempt_num=1,
                modeling_type="edit",
                diff_content=f"diff {i}",
                target_files=["test.java"],
                metadata={}
            )
            manager.save_normalized_patch(patch)
        
        patches = list(manager.patches_dir.glob("*.patch"))
        assert len(patches) == 3


class TestSaveBugResult:
    """Tests for save_bug_result method."""
    
    def test_save_bug_result_basic(self, tmp_path):
        """Test saving basic bug result."""
        manager = StorageManager(tmp_path)
        
        result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=3,
            successful_attempt=2,
            modeling_type="edit"
        )
        
        saved_path = manager.save_bug_result(result)
        
        assert saved_path.exists()
        assert saved_path.name == "Chart_1.json"
        
        # Verify content
        with open(saved_path, 'r') as f:
            data = json.load(f)
        
        assert data['bug_slug'] == "Chart_1"
        assert data['total_attempts'] == 3
        assert data['successful_attempt'] == 2
    
    def test_save_bug_result_with_test_result(self, tmp_path):
        """Test saving bug result with test result."""
        manager = StorageManager(tmp_path)
        
        test_result = TestResult(
            success=True,
            total_tests=10,
            passed_tests=10,
            failed_tests=0
        )
        
        result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=1,
            successful_attempt=1,
            modeling_type="edit",
            test_result=test_result
        )
        
        saved_path = manager.save_bug_result(result)
        
        # Verify test result is saved
        with open(saved_path, 'r') as f:
            data = json.load(f)
        
        assert 'test_result' in data
        assert data['test_result']['total_tests'] == 10
        assert data['test_result']['success'] is True
    
    def test_save_bug_result_with_failures(self, tmp_path):
        """Test saving bug result with failure reasons."""
        manager = StorageManager(tmp_path)
        
        result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=3,
            successful_attempt=None,
            failure_reasons=["patch_failed", "test_failed"]
        )
        
        saved_path = manager.save_bug_result(result)
        
        with open(saved_path, 'r') as f:
            data = json.load(f)
        
        assert data['failure_reasons'] == ["patch_failed", "test_failed"]
        assert data['successful_attempt'] is None


class TestSaveBatchResult:
    """Tests for save_batch_result method."""
    
    def test_save_batch_result(self, tmp_path):
        """Test saving batch result."""
        manager = StorageManager(tmp_path)
        
        bug_results = [
            BugEvaluationResult(
                bug_slug="Chart_1",
                total_attempts=2,
                successful_attempt=1,
                modeling_type="edit"
            ),
            BugEvaluationResult(
                bug_slug="Chart_2",
                total_attempts=3,
                successful_attempt=None
            )
        ]
        
        batch_result = BatchEvaluationResult(
            result_folder="/test/results",
            timestamp="2024-01-01T00:00:00",
            total_bugs=2,
            fixed_bugs=1,
            failed_bugs=1,
            rewrite_success=0,
            edit_success=1,
            bug_results=bug_results,
            statistics={'success_rate': 0.5}
        )
        
        saved_path = manager.save_batch_result(batch_result)
        
        assert saved_path.exists()
        assert saved_path.name == "batch_evaluation.json"
        
        # Verify content
        with open(saved_path, 'r') as f:
            data = json.load(f)
        
        assert data['total_bugs'] == 2
        assert data['fixed_bugs'] == 1
        assert len(data['bug_results']) == 2
    
    def test_save_batch_result_custom_filename(self, tmp_path):
        """Test saving batch result with custom filename."""
        manager = StorageManager(tmp_path)
        
        batch_result = BatchEvaluationResult(
            result_folder="/test",
            timestamp="2024-01-01T00:00:00",
            total_bugs=0,
            fixed_bugs=0,
            failed_bugs=0,
            rewrite_success=0,
            edit_success=0,
            bug_results=[],
            statistics={}
        )
        
        saved_path = manager.save_batch_result(batch_result, filename="custom.json")
        
        assert saved_path.name == "custom.json"


class TestSaveStatistics:
    """Tests for save_statistics method."""
    
    def test_save_statistics(self, tmp_path):
        """Test saving statistics."""
        manager = StorageManager(tmp_path)
        
        stats = {
            'success_rate': 0.75,
            'total_attempts': 100,
            'average_attempts': 2.5
        }
        
        saved_path = manager.save_statistics(stats)
        
        assert saved_path.exists()
        assert saved_path.name == "statistics.json"
        
        # Verify content
        with open(saved_path, 'r') as f:
            data = json.load(f)
        
        assert data['success_rate'] == 0.75
        assert data['total_attempts'] == 100


class TestLog:
    """Tests for log method."""
    
    def test_log_message(self, tmp_path):
        """Test logging a message."""
        manager = StorageManager(tmp_path)
        
        manager.log("Test message", level="INFO")
        
        assert manager.log_file.exists()
        
        content = manager.log_file.read_text()
        assert "Test message" in content
        assert "INFO" in content
    
    def test_log_multiple_messages(self, tmp_path):
        """Test logging multiple messages."""
        manager = StorageManager(tmp_path)
        
        manager.log("Message 1", level="INFO")
        manager.log("Message 2", level="WARNING")
        manager.log("Message 3", level="ERROR")
        
        content = manager.log_file.read_text()
        assert "Message 1" in content
        assert "Message 2" in content
        assert "Message 3" in content


class TestSaveSummaryText:
    """Tests for save_summary_text method."""
    
    def test_save_summary(self, tmp_path):
        """Test saving summary text."""
        manager = StorageManager(tmp_path)
        
        summary = "This is a test summary\nWith multiple lines"
        
        saved_path = manager.save_summary_text(summary)
        
        assert saved_path.exists()
        assert saved_path.name == "summary.txt"
        assert saved_path.read_text() == summary


class TestLoadMethods:
    """Tests for load methods."""
    
    def test_load_bug_result(self, tmp_path):
        """Test loading bug result."""
        manager = StorageManager(tmp_path)
        
        # Save a result first
        result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=2,
            successful_attempt=1,
            modeling_type="edit"
        )
        manager.save_bug_result(result)
        
        # Load it back
        loaded = manager.load_bug_result("Chart_1")
        
        assert loaded['bug_slug'] == "Chart_1"
        assert loaded['total_attempts'] == 2
    
    def test_load_bug_result_not_found(self, tmp_path):
        """Test loading non-existent bug result."""
        manager = StorageManager(tmp_path)
        
        with pytest.raises(FileNotFoundError):
            manager.load_bug_result("NonExistent")
    
    def test_load_batch_result(self, tmp_path):
        """Test loading batch result."""
        manager = StorageManager(tmp_path)
        
        # Save a batch result first
        batch_result = BatchEvaluationResult(
            result_folder="/test",
            timestamp="2024-01-01T00:00:00",
            total_bugs=5,
            fixed_bugs=3,
            failed_bugs=2,
            rewrite_success=1,
            edit_success=2,
            bug_results=[],
            statistics={}
        )
        manager.save_batch_result(batch_result)
        
        # Load it back
        loaded = manager.load_batch_result()
        
        assert loaded['total_bugs'] == 5
        assert loaded['fixed_bugs'] == 3
    
    def test_load_batch_result_not_found(self, tmp_path):
        """Test loading non-existent batch result."""
        manager = StorageManager(tmp_path)
        
        with pytest.raises(FileNotFoundError):
            manager.load_batch_result()


class TestListMethods:
    """Tests for list methods."""
    
    def test_list_bug_results(self, tmp_path):
        """Test listing bug results."""
        manager = StorageManager(tmp_path)
        
        # Save some results
        for i in range(3):
            result = BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=1,
                successful_attempt=1
            )
            manager.save_bug_result(result)
        
        bug_slugs = manager.list_bug_results()
        
        assert len(bug_slugs) == 3
        assert "Chart_0" in bug_slugs
        assert "Chart_1" in bug_slugs
        assert "Chart_2" in bug_slugs
    
    def test_list_bug_results_empty(self, tmp_path):
        """Test listing bug results when none exist."""
        manager = StorageManager(tmp_path)
        
        bug_slugs = manager.list_bug_results()
        
        assert bug_slugs == []
    
    def test_list_patches(self, tmp_path):
        """Test listing patches."""
        manager = StorageManager(tmp_path)
        
        # Save some patches
        for i in range(3):
            patch = NormalizedPatch(
                bug_slug=f"Chart_{i}",
                attempt_num=1,
                modeling_type="edit",
                diff_content="diff",
                target_files=["test.java"],
                metadata={}
            )
            manager.save_normalized_patch(patch)
        
        patches = manager.list_patches()
        
        assert len(patches) == 3


class TestGetOutputSummary:
    """Tests for get_output_summary method."""
    
    def test_get_output_summary(self, tmp_path):
        """Test getting output summary."""
        manager = StorageManager(tmp_path)
        
        # Save some data
        patch = NormalizedPatch(
            bug_slug="Chart_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="diff",
            target_files=["test.java"],
            metadata={}
        )
        manager.save_normalized_patch(patch)
        
        result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=1,
            successful_attempt=1
        )
        manager.save_bug_result(result)
        
        manager.log("Test message")
        
        summary = manager.get_output_summary()
        
        assert summary['total_patches'] == 1
        assert summary['total_bug_results'] == 1
        assert summary['log_file_size'] > 0


class TestClearOutput:
    """Tests for clear_output method."""
    
    def test_clear_output(self, tmp_path):
        """Test clearing all output."""
        manager = StorageManager(tmp_path)
        
        # Save some data
        patch = NormalizedPatch(
            bug_slug="Chart_1",
            attempt_num=1,
            modeling_type="edit",
            diff_content="diff",
            target_files=["test.java"],
            metadata={}
        )
        manager.save_normalized_patch(patch)
        
        result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=1,
            successful_attempt=1
        )
        manager.save_bug_result(result)
        
        manager.log("Test message")
        
        # Clear everything
        manager.clear_output()
        
        # Verify everything is cleared
        assert len(list(manager.patches_dir.glob("*"))) == 0
        assert len(list(manager.bug_results_dir.glob("*"))) == 0
        assert not manager.log_file.exists()
