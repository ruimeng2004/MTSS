"""Tests for ResultGenerator class."""

from evaluation.core.data_structures import (
    BugEvaluationResult,
    TestResult,
)
from evaluation.core.result_generator import ResultGenerator


class TestResultGeneratorInit:
    """Tests for ResultGenerator initialization."""
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        generator = ResultGenerator()
        
        assert generator.bug_results == []
        assert generator.result_folder == ""
    
    def test_init_with_folder(self):
        """Test initialization with result folder."""
        generator = ResultGenerator(result_folder="/path/to/results")
        
        assert generator.result_folder == "/path/to/results"
        assert generator.bug_results == []


class TestAddBugResult:
    """Tests for add_bug_result method."""
    
    def test_add_single_result(self):
        """Test adding a single bug result."""
        generator = ResultGenerator()
        
        bug_result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=3,
            successful_attempt=2,
            modeling_type="edit"
        )
        
        generator.add_bug_result(bug_result)
        
        assert len(generator.bug_results) == 1
        assert generator.bug_results[0].bug_slug == "Chart_1"
    
    def test_add_multiple_results(self):
        """Test adding multiple bug results."""
        generator = ResultGenerator()
        
        for i in range(5):
            bug_result = BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=2,
                successful_attempt=1
            )
            generator.add_bug_result(bug_result)
        
        assert len(generator.bug_results) == 5


class TestGenerateBatchResult:
    """Tests for generate_batch_result method."""
    
    def test_generate_empty_batch(self):
        """Test generating batch result with no bugs."""
        generator = ResultGenerator(result_folder="/test/results")
        
        batch_result = generator.generate_batch_result()
        
        assert batch_result.total_bugs == 0
        assert batch_result.fixed_bugs == 0
        assert batch_result.failed_bugs == 0
        assert batch_result.result_folder == "/test/results"
        assert batch_result.timestamp is not None
    
    def test_generate_batch_all_success(self):
        """Test generating batch result with all bugs fixed."""
        generator = ResultGenerator()
        
        for i in range(10):
            bug_result = BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=2,
                successful_attempt=1,
                modeling_type="edit" if i % 2 == 0 else "rewrite"
            )
            generator.add_bug_result(bug_result)
        
        batch_result = generator.generate_batch_result()
        
        assert batch_result.total_bugs == 10
        assert batch_result.fixed_bugs == 10
        assert batch_result.failed_bugs == 0
        assert batch_result.edit_success == 5
        assert batch_result.rewrite_success == 5
    
    def test_generate_batch_mixed_results(self):
        """Test generating batch result with mixed success/failure."""
        generator = ResultGenerator()
        
        # Add 5 successful bugs
        for i in range(5):
            bug_result = BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=2,
                successful_attempt=1,
                modeling_type="edit"
            )
            generator.add_bug_result(bug_result)
        
        # Add 3 failed bugs
        for i in range(5, 8):
            bug_result = BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=3,
                successful_attempt=None,
                failure_reasons=["patch_failed", "test_failed"]
            )
            generator.add_bug_result(bug_result)
        
        batch_result = generator.generate_batch_result()
        
        assert batch_result.total_bugs == 8
        assert batch_result.fixed_bugs == 5
        assert batch_result.failed_bugs == 3
        assert batch_result.edit_success == 5
        assert batch_result.rewrite_success == 0
    
    def test_generate_batch_with_test_results(self):
        """Test generating batch result with test results."""
        generator = ResultGenerator()
        
        test_result = TestResult(
            success=True,
            total_tests=10,
            passed_tests=10,
            failed_tests=0
        )
        
        bug_result = BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=1,
            successful_attempt=1,
            modeling_type="edit",
            test_result=test_result
        )
        
        generator.add_bug_result(bug_result)
        
        batch_result = generator.generate_batch_result()
        
        assert batch_result.fixed_bugs == 1
        assert batch_result.statistics['test_statistics']['total_tests_run'] == 10


class TestCalculateStatistics:
    """Tests for calculate_statistics method."""
    
    def test_calculate_empty_statistics(self):
        """Test calculating statistics with no bugs."""
        generator = ResultGenerator()
        
        stats = generator.calculate_statistics()
        
        assert stats['success_rate'] == 0.0
        assert stats['total_attempts'] == 0
        assert stats['average_attempts'] == 0.0
        assert stats['failure_reasons'] == {}
    
    def test_calculate_success_rate(self):
        """Test calculating success rate."""
        generator = ResultGenerator()
        
        # Add 7 successful and 3 failed bugs
        for i in range(7):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=2,
                successful_attempt=1
            ))
        
        for i in range(7, 10):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=3,
                successful_attempt=None
            ))
        
        stats = generator.calculate_statistics()
        
        assert stats['success_rate'] == 0.7
        assert stats['total_attempts'] == 7 * 2 + 3 * 3
        assert stats['average_attempts'] == (7 * 2 + 3 * 3) / 10
    
    def test_calculate_modeling_type_rates(self):
        """Test calculating modeling type success rates."""
        generator = ResultGenerator()
        
        # Add 3 successful edit bugs
        for i in range(3):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=1,
                successful_attempt=1,
                modeling_type="edit"
            ))
        
        # Add 2 failed edit bugs
        for i in range(3, 5):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=2,
                successful_attempt=None,
                modeling_type="edit"
            ))
        
        # Add 4 successful rewrite bugs
        for i in range(5, 9):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Lang_{i}",
                total_attempts=1,
                successful_attempt=1,
                modeling_type="rewrite"
            ))
        
        # Add 1 failed rewrite bug
        generator.add_bug_result(BugEvaluationResult(
            bug_slug="Lang_10",
            total_attempts=3,
            successful_attempt=None,
            modeling_type="rewrite"
        ))
        
        stats = generator.calculate_statistics()
        
        assert stats['edit_success_rate'] == 3 / 5  # 3 success out of 5 edit bugs
        assert stats['rewrite_success_rate'] == 4 / 5  # 4 success out of 5 rewrite bugs
    
    def test_calculate_failure_reasons(self):
        """Test calculating failure reason statistics."""
        generator = ResultGenerator()
        
        generator.add_bug_result(BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=2,
            successful_attempt=None,
            failure_reasons=["patch_failed", "compilation_error"]
        ))
        
        generator.add_bug_result(BugEvaluationResult(
            bug_slug="Chart_2",
            total_attempts=3,
            successful_attempt=None,
            failure_reasons=["patch_failed", "test_failed"]
        ))
        
        generator.add_bug_result(BugEvaluationResult(
            bug_slug="Chart_3",
            total_attempts=1,
            successful_attempt=None,
            failure_reasons=["test_failed"]
        ))
        
        stats = generator.calculate_statistics()
        
        assert stats['failure_reasons']['patch_failed'] == 2
        assert stats['failure_reasons']['test_failed'] == 2
        assert stats['failure_reasons']['compilation_error'] == 1
    
    def test_calculate_execution_time(self):
        """Test calculating execution time statistics."""
        generator = ResultGenerator()
        
        for i in range(5):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=1,
                successful_attempt=1,
                execution_time=10.0 + i
            ))
        
        stats = generator.calculate_statistics()
        
        assert stats['total_execution_time'] == 10 + 11 + 12 + 13 + 14
        assert stats['average_execution_time'] == (10 + 11 + 12 + 13 + 14) / 5
    
    def test_calculate_test_statistics(self):
        """Test calculating test statistics."""
        generator = ResultGenerator()
        
        # Add bug with passing tests
        generator.add_bug_result(BugEvaluationResult(
            bug_slug="Chart_1",
            total_attempts=1,
            successful_attempt=1,
            test_result=TestResult(
                success=True,
                total_tests=10,
                passed_tests=10,
                failed_tests=0
            )
        ))
        
        # Add bug with failing tests
        generator.add_bug_result(BugEvaluationResult(
            bug_slug="Chart_2",
            total_attempts=2,
            successful_attempt=None,
            test_result=TestResult(
                success=False,
                total_tests=15,
                passed_tests=12,
                failed_tests=3
            )
        ))
        
        # Add bug with timeout
        generator.add_bug_result(BugEvaluationResult(
            bug_slug="Chart_3",
            total_attempts=1,
            successful_attempt=None,
            test_result=TestResult(
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                timeout=True
            )
        ))
        
        stats = generator.calculate_statistics()
        
        test_stats = stats['test_statistics']
        assert test_stats['total_tests_run'] == 25
        assert test_stats['total_tests_passed'] == 22
        assert test_stats['total_tests_failed'] == 3
        assert test_stats['timeouts'] == 1


class TestGetMethods:
    """Tests for getter methods."""
    
    def test_get_successful_bugs(self):
        """Test getting successful bugs."""
        generator = ResultGenerator()
        
        # Add 3 successful bugs
        for i in range(3):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=1,
                successful_attempt=1
            ))
        
        # Add 2 failed bugs
        for i in range(3, 5):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=2,
                successful_attempt=None
            ))
        
        successful = generator.get_successful_bugs()
        
        assert len(successful) == 3
        assert all(r.successful_attempt is not None for r in successful)
    
    def test_get_failed_bugs(self):
        """Test getting failed bugs."""
        generator = ResultGenerator()
        
        # Add 2 successful bugs
        for i in range(2):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=1,
                successful_attempt=1
            ))
        
        # Add 4 failed bugs
        for i in range(2, 6):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=3,
                successful_attempt=None
            ))
        
        failed = generator.get_failed_bugs()
        
        assert len(failed) == 4
        assert all(r.successful_attempt is None for r in failed)
    
    def test_get_bugs_by_modeling_type(self):
        """Test getting bugs by modeling type."""
        generator = ResultGenerator()
        
        # Add edit bugs
        for i in range(3):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=1,
                successful_attempt=1,
                modeling_type="edit"
            ))
        
        # Add rewrite bugs
        for i in range(3, 7):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Lang_{i}",
                total_attempts=1,
                successful_attempt=1,
                modeling_type="rewrite"
            ))
        
        edit_bugs = generator.get_bugs_by_modeling_type("edit")
        rewrite_bugs = generator.get_bugs_by_modeling_type("rewrite")
        
        assert len(edit_bugs) == 3
        assert len(rewrite_bugs) == 4
        assert all(r.modeling_type == "edit" for r in edit_bugs)
        assert all(r.modeling_type == "rewrite" for r in rewrite_bugs)


class TestGetSummaryText:
    """Tests for get_summary_text method."""
    
    def test_get_summary_text_empty(self):
        """Test getting summary text with no bugs."""
        generator = ResultGenerator(result_folder="/test/results")
        
        summary = generator.get_summary_text()
        
        assert "BATCH EVALUATION SUMMARY" in summary
        assert "/test/results" in summary
        assert "Total Bugs: 0" in summary
    
    def test_get_summary_text_with_results(self):
        """Test getting summary text with results."""
        generator = ResultGenerator(result_folder="/test/results")
        
        # Add some bugs
        for i in range(5):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=2,
                successful_attempt=1,
                modeling_type="edit",
                execution_time=10.0
            ))
        
        for i in range(5, 8):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=3,
                successful_attempt=None,
                failure_reasons=["test_failed"]
            ))
        
        summary = generator.get_summary_text()
        
        assert "Total Bugs: 8" in summary
        assert "Fixed Bugs: 5" in summary
        assert "Failed Bugs: 3" in summary
        assert "test_failed" in summary


class TestClear:
    """Tests for clear method."""
    
    def test_clear(self):
        """Test clearing bug results."""
        generator = ResultGenerator()
        
        # Add some bugs
        for i in range(5):
            generator.add_bug_result(BugEvaluationResult(
                bug_slug=f"Chart_{i}",
                total_attempts=1,
                successful_attempt=1
            ))
        
        assert len(generator.bug_results) == 5
        
        generator.clear()
        
        assert len(generator.bug_results) == 0
