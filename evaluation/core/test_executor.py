"""Test executor for running Defects4J tests.

This module provides the TestExecutor class for running D4J test suites
and parsing test results.
"""

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from evaluation.core.data_structures import TestResult

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes Defects4J test suites and collects results.
    
    This class handles running D4J tests with timeout control and parsing
    test output to extract pass/fail information.
    
    Attributes:
        repo_path: Path to the checked out repository.
        timeout: Maximum time in seconds to wait for tests to complete.
        d4j_path: Path to Defects4J installation.
    """
    
    def __init__(
        self,
        repo_path: Path,
        timeout: int = 600,
        d4j_path: Optional[Path] = None
    ):
        """Initialize TestExecutor.
        
        Args:
            repo_path: Path to the checked out repository where tests will
                be executed.
            timeout: Maximum time in seconds to wait for tests (default: 600).
            d4j_path: Path to Defects4J installation. If None, uses command
                from PATH.
        
        Raises:
            ValueError: If repo_path doesn't exist or is not a directory.
        """
        self.repo_path = Path(repo_path)
        self.timeout = timeout
        self.d4j_path = Path(d4j_path) if d4j_path else None
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        if not self.repo_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repo_path}")
        
        logger.info(
            f"Initialized TestExecutor for: {self.repo_path} "
            f"(timeout={timeout}s)"
        )
    
    def _get_d4j_command(self) -> str:
        """Get the defects4j command path.
        
        Returns:
            Path to defects4j command.
        """
        if self.d4j_path:
            return str(self.d4j_path / 'framework' / 'bin' / 'defects4j')
        return 'defects4j'
    
    def run_tests(self, bug_slug: str) -> TestResult:
        """Run Defects4J test suite.
        
        Executes 'defects4j test' command and parses the output to extract
        test results.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1") for logging purposes.
        
        Returns:
            TestResult with test execution details.
        """
        logger.info(f"Running tests for {bug_slug}")
        
        start_time = time.time()
        
        # Closure project tests are very slow, use longer timeout
        # Use 2x timeout for Closure instead of 1800s to avoid excessive delays
        timeout = self.timeout * 2 if bug_slug.startswith('Closure_') else self.timeout
        if timeout != self.timeout:
            logger.info(
                f"Using extended timeout for Closure project: {timeout}s"
            )
        
        try:
            # Run defects4j test command
            d4j_cmd = self._get_d4j_command()
            result = subprocess.run(
                [d4j_cmd, 'test'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse test output
            parsed_results = self.parse_test_output(result.stdout)
            
            # Determine success based on failed tests
            success = parsed_results['failed_tests'] == 0
            
            test_result = TestResult(
                success=success,
                total_tests=parsed_results['total_tests'],
                passed_tests=parsed_results['passed_tests'],
                failed_tests=parsed_results['failed_tests'],
                timeout=False,
                error_message=None if success else "Some tests failed",
                failed_test_cases=parsed_results['failed_test_cases'],
                execution_time=execution_time,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
            if success:
                logger.info(
                    f"All tests passed for {bug_slug} "
                    f"({parsed_results['total_tests']} tests, "
                    f"{execution_time:.2f}s)"
                )
            else:
                logger.warning(
                    f"Tests failed for {bug_slug}: "
                    f"{parsed_results['failed_tests']}/{parsed_results['total_tests']} "
                    f"failed"
                )
            
            return test_result
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error(
                f"Test execution timed out for {bug_slug} "
                f"after {timeout}s"
            )
            
            return TestResult(
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                timeout=True,
                error_message=f"Test execution timed out after {timeout}s",
                failed_test_cases=[],
                execution_time=execution_time
            )
            
        except FileNotFoundError:
            execution_time = time.time() - start_time
            logger.error("defects4j command not found")
            
            return TestResult(
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                timeout=False,
                error_message="defects4j command not found",
                failed_test_cases=[],
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error running tests for {bug_slug}: {e}")
            
            return TestResult(
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                timeout=False,
                error_message=f"Unexpected error: {str(e)}",
                failed_test_cases=[],
                execution_time=execution_time
            )
    
    def parse_test_output(self, output: str) -> Dict[str, any]:
        """Parse Defects4J test output.
        
        Extracts test statistics and failed test cases from D4J test output.
        
        Expected output format:
            Running <project> test suite
            ...
            Failing tests: <count>
              - <test_class>::<test_method>
              - ...
            
        Args:
            output: stdout from 'defects4j test' command.
        
        Returns:
            Dictionary with keys:
                - total_tests: int
                - passed_tests: int
                - failed_tests: int
                - failed_test_cases: List[str]
        """
        failed_tests = 0
        failed_test_cases = []
        
        # Parse output line by line
        lines = output.split('\n')
        
        for i, line in enumerate(lines):
            # Look for "Failing tests: <count>"
            match = re.search(r'Failing tests:\s*(\d+)', line)
            if match:
                failed_tests = int(match.group(1))
                
                # Extract failed test cases from following lines
                # They start with "  - " or "  * "
                j = i + 1
                while j < len(lines):
                    test_line = lines[j].strip()
                    if test_line.startswith('- ') or test_line.startswith('* '):
                        # Remove leading "- " or "* "
                        test_case = test_line[2:].strip()
                        if test_case:
                            failed_test_cases.append(test_case)
                        j += 1
                    elif test_line == '':
                        # Empty line, continue
                        j += 1
                    else:
                        # Non-test line, stop parsing
                        break
                
                break
        
        # Try alternative format: look for individual test failures
        if failed_tests == 0 and not failed_test_cases:
            # Look for lines like "FAILED: TestClass::testMethod"
            for line in lines:
                if 'FAILED:' in line or 'FAIL:' in line:
                    # Extract test case name
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        test_case = parts[1].strip()
                        if test_case and test_case not in failed_test_cases:
                            failed_test_cases.append(test_case)
            
            failed_tests = len(failed_test_cases)
        
        # Calculate total and passed tests
        # D4J doesn't always report total tests, so we estimate
        # If we have failed tests but no total, we can't determine passed
        total_tests = failed_tests  # Minimum estimate
        passed_tests = 0
        
        # Try to find total tests from output
        for line in lines:
            # Look for patterns like "Tests run: 10, Failures: 2"
            match = re.search(r'Tests run:\s*(\d+)', line)
            if match:
                total_tests = int(match.group(1))
                passed_tests = total_tests - failed_tests
                break
        
        # If no explicit total found, assume passed = 0 if there are failures
        if total_tests == failed_tests and failed_tests > 0:
            passed_tests = 0
        
        logger.debug(
            f"Parsed test results: total={total_tests}, "
            f"passed={passed_tests}, failed={failed_tests}"
        )
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'failed_test_cases': failed_test_cases
        }
    
    def run_specific_tests(
        self,
        bug_slug: str,
        test_cases: List[str]
    ) -> TestResult:
        """Run specific test cases.
        
        Args:
            bug_slug: Bug identifier for logging.
            test_cases: List of test case names to run.
        
        Returns:
            TestResult with test execution details.
        """
        logger.info(
            f"Running {len(test_cases)} specific tests for {bug_slug}"
        )
        
        start_time = time.time()
        
        try:
            # Run defects4j test with specific test cases
            # Format: defects4j test -t TestClass::testMethod
            test_args = []
            for test_case in test_cases:
                test_args.extend(['-t', test_case])
            
            d4j_cmd = self._get_d4j_command()
            result = subprocess.run(
                [d4j_cmd, 'test'] + test_args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse test output
            parsed_results = self.parse_test_output(result.stdout)
            
            # Determine success
            success = parsed_results['failed_tests'] == 0
            
            return TestResult(
                success=success,
                total_tests=len(test_cases),
                passed_tests=len(test_cases) - parsed_results['failed_tests'],
                failed_tests=parsed_results['failed_tests'],
                timeout=False,
                error_message=None if success else "Some tests failed",
                failed_test_cases=parsed_results['failed_test_cases'],
                execution_time=execution_time,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error(f"Test execution timed out after {self.timeout}s")
            
            return TestResult(
                success=False,
                total_tests=len(test_cases),
                passed_tests=0,
                failed_tests=len(test_cases),
                timeout=True,
                error_message=f"Test execution timed out after {self.timeout}s",
                failed_test_cases=test_cases,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error running specific tests: {e}")
            
            return TestResult(
                success=False,
                total_tests=len(test_cases),
                passed_tests=0,
                failed_tests=len(test_cases),
                timeout=False,
                error_message=f"Unexpected error: {str(e)}",
                failed_test_cases=test_cases,
                execution_time=execution_time
            )
