"""Tests for TestExecutor class."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from evaluation.core.test_executor import TestExecutor


class TestTestExecutorInit:
    """Tests for TestExecutor initialization."""
    
    def test_init_valid_repo(self, tmp_path):
        """Test initialization with valid repository path."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        assert executor.repo_path == repo_path
        assert executor.timeout == 600  # Default timeout
    
    def test_init_custom_timeout(self, tmp_path):
        """Test initialization with custom timeout."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path, timeout=300)
        
        assert executor.timeout == 300
    
    def test_init_nonexistent_repo(self, tmp_path):
        """Test initialization with non-existent repository."""
        repo_path = tmp_path / "nonexistent"
        
        with pytest.raises(ValueError, match="does not exist"):
            TestExecutor(repo_path)
    
    def test_init_file_instead_of_directory(self, tmp_path):
        """Test initialization with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        
        with pytest.raises(ValueError, match="not a directory"):
            TestExecutor(file_path)


class TestRunTests:
    """Tests for run_tests method."""
    
    def test_run_tests_all_pass(self, tmp_path):
        """Test running tests when all tests pass."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        mock_output = """Running Chart test suite
Tests run: 10, Failures: 0
All tests passed!
"""
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = executor.run_tests("Chart_1")
            
            assert result.success is True
            assert result.total_tests == 10
            assert result.passed_tests == 10
            assert result.failed_tests == 0
            assert result.timeout is False
            assert result.failed_test_cases == []
            assert result.execution_time > 0
    
    def test_run_tests_some_fail(self, tmp_path):
        """Test running tests when some tests fail."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        mock_output = """Running Chart test suite
Tests run: 10, Failures: 2
Failing tests: 2
  - org.jfree.chart.ChartTest::testMethod1
  - org.jfree.chart.ChartTest::testMethod2
"""
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = mock_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = executor.run_tests("Chart_1")
            
            assert result.success is False
            assert result.total_tests == 10
            assert result.passed_tests == 8
            assert result.failed_tests == 2
            assert result.timeout is False
            assert len(result.failed_test_cases) == 2
            assert "org.jfree.chart.ChartTest::testMethod1" in result.failed_test_cases
    
    def test_run_tests_timeout(self, tmp_path):
        """Test running tests with timeout."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path, timeout=10)
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('defects4j', 10)):
            result = executor.run_tests("Chart_1")
            
            assert result.success is False
            assert result.timeout is True
            assert "timed out" in result.error_message
            assert result.execution_time >= 0
    
    def test_run_tests_command_not_found(self, tmp_path):
        """Test running tests when defects4j command not found."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = executor.run_tests("Chart_1")
            
            assert result.success is False
            assert "not found" in result.error_message
    
    def test_run_tests_unexpected_error(self, tmp_path):
        """Test running tests with unexpected error."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            result = executor.run_tests("Chart_1")
            
            assert result.success is False
            assert "Unexpected error" in result.error_message


class TestParseTestOutput:
    """Tests for parse_test_output method."""
    
    def test_parse_no_failures(self, tmp_path):
        """Test parsing output with no failures."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Running Chart test suite
Tests run: 15, Failures: 0
All tests passed!
"""
        
        result = executor.parse_test_output(output)
        
        assert result['total_tests'] == 15
        assert result['passed_tests'] == 15
        assert result['failed_tests'] == 0
        assert result['failed_test_cases'] == []
    
    def test_parse_with_failures(self, tmp_path):
        """Test parsing output with failures."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Running Chart test suite
Tests run: 20, Failures: 3
Failing tests: 3
  - org.jfree.chart.ChartTest::testMethod1
  - org.jfree.chart.ChartTest::testMethod2
  - org.jfree.chart.PlotTest::testPlot
"""
        
        result = executor.parse_test_output(output)
        
        assert result['total_tests'] == 20
        assert result['passed_tests'] == 17
        assert result['failed_tests'] == 3
        assert len(result['failed_test_cases']) == 3
    
    def test_parse_alternative_format(self, tmp_path):
        """Test parsing output in alternative format."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Running tests...
FAILED: org.jfree.chart.ChartTest::testMethod1
FAILED: org.jfree.chart.ChartTest::testMethod2
"""
        
        result = executor.parse_test_output(output)
        
        assert result['failed_tests'] == 2
        assert len(result['failed_test_cases']) == 2
    
    def test_parse_empty_output(self, tmp_path):
        """Test parsing empty output."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        result = executor.parse_test_output("")
        
        assert result['total_tests'] == 0
        assert result['passed_tests'] == 0
        assert result['failed_tests'] == 0
        assert result['failed_test_cases'] == []
    
    def test_parse_with_asterisk_format(self, tmp_path):
        """Test parsing output with asterisk format."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Running Chart test suite
Failing tests: 2
  * org.jfree.chart.ChartTest::testMethod1
  * org.jfree.chart.ChartTest::testMethod2
"""
        
        result = executor.parse_test_output(output)
        
        assert result['failed_tests'] == 2
        assert len(result['failed_test_cases']) == 2
    
    def test_parse_only_failing_count(self, tmp_path):
        """Test parsing output with only failing count."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Running Chart test suite
Failing tests: 5
"""
        
        result = executor.parse_test_output(output)
        
        assert result['failed_tests'] == 5
        assert result['total_tests'] == 5  # Minimum estimate
        assert result['passed_tests'] == 0


class TestRunSpecificTests:
    """Tests for run_specific_tests method."""
    
    def test_run_specific_tests_success(self, tmp_path):
        """Test running specific tests successfully."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        test_cases = [
            "org.jfree.chart.ChartTest::testMethod1",
            "org.jfree.chart.ChartTest::testMethod2"
        ]
        
        mock_output = """Running specific tests
Tests run: 2, Failures: 0
All tests passed!
"""
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = executor.run_specific_tests("Chart_1", test_cases)
            
            assert result.success is True
            assert result.total_tests == 2
            assert result.passed_tests == 2
            assert result.failed_tests == 0
            
            # Verify command was called with correct arguments
            call_args = mock_run.call_args[0][0]
            assert 'defects4j' in call_args
            assert 'test' in call_args
            assert '-t' in call_args
    
    def test_run_specific_tests_some_fail(self, tmp_path):
        """Test running specific tests with some failures."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        test_cases = [
            "org.jfree.chart.ChartTest::testMethod1",
            "org.jfree.chart.ChartTest::testMethod2",
            "org.jfree.chart.ChartTest::testMethod3"
        ]
        
        mock_output = """Running specific tests
Failing tests: 1
  - org.jfree.chart.ChartTest::testMethod2
"""
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = mock_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = executor.run_specific_tests("Chart_1", test_cases)
            
            assert result.success is False
            assert result.total_tests == 3
            assert result.passed_tests == 2
            assert result.failed_tests == 1
    
    def test_run_specific_tests_timeout(self, tmp_path):
        """Test running specific tests with timeout."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path, timeout=10)
        
        test_cases = ["org.jfree.chart.ChartTest::testMethod1"]
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('defects4j', 10)):
            result = executor.run_specific_tests("Chart_1", test_cases)
            
            assert result.success is False
            assert result.timeout is True
            assert result.total_tests == 1
            assert result.failed_tests == 1
    
    def test_run_specific_tests_empty_list(self, tmp_path):
        """Test running specific tests with empty list."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        mock_output = "No tests to run"
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            result = executor.run_specific_tests("Chart_1", [])
            
            assert result.total_tests == 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_parse_malformed_output(self, tmp_path):
        """Test parsing malformed output."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Some random output
that doesn't match
any expected format
"""
        
        result = executor.parse_test_output(output)
        
        # Should return default values without crashing
        assert result['total_tests'] >= 0
        assert result['passed_tests'] >= 0
        assert result['failed_tests'] >= 0
    
    def test_parse_with_unicode(self, tmp_path):
        """Test parsing output with unicode characters."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Running Chart test suite
Tests run: 5, Failures: 1
Failing tests: 1
  - org.jfree.chart.ChartTest::testMethod™
"""
        
        result = executor.parse_test_output(output)
        
        assert result['failed_tests'] == 1
        assert len(result['failed_test_cases']) == 1
    
    def test_multiple_test_run_lines(self, tmp_path):
        """Test parsing output with multiple 'Tests run' lines."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        
        executor = TestExecutor(repo_path)
        
        output = """Running Chart test suite
Tests run: 5, Failures: 0
Tests run: 10, Failures: 2
Failing tests: 2
  - org.jfree.chart.ChartTest::testMethod1
  - org.jfree.chart.ChartTest::testMethod2
"""
        
        result = executor.parse_test_output(output)
        
        # Should use the first match
        assert result['total_tests'] == 5
        assert result['failed_tests'] == 2
