"""Result generator for aggregating evaluation results.

This module provides the ResultGenerator class for collecting and aggregating
bug evaluation results into batch statistics.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from evaluation.core.data_structures import (
    BatchEvaluationResult,
    BugEvaluationResult,
)

logger = logging.getLogger(__name__)


class ResultGenerator:
    """Generates batch evaluation results from individual bug results.
    
    This class collects individual bug evaluation results and generates
    comprehensive batch statistics including success rates, modeling type
    breakdown, and failure analysis.
    
    Attributes:
        bug_results: List of individual bug evaluation results.
        result_folder: Path to the result folder being evaluated.
    """
    
    def __init__(self, result_folder: str = ""):
        """Initialize ResultGenerator.
        
        Args:
            result_folder: Path to the result folder being evaluated.
        """
        self.bug_results: List[BugEvaluationResult] = []
        self.result_folder = result_folder
        
        logger.info(f"Initialized ResultGenerator for: {result_folder}")
    
    def add_bug_result(self, bug_result: BugEvaluationResult):
        """Add a single bug evaluation result.
        
        Args:
            bug_result: Bug evaluation result to add.
        """
        self.bug_results.append(bug_result)
        
        logger.debug(
            f"Added result for {bug_result.bug_slug}: "
            f"success={bug_result.successful_attempt is not None}"
        )
    
    def generate_batch_result(self) -> BatchEvaluationResult:
        """Generate batch evaluation result from collected bug results.
        
        Returns:
            BatchEvaluationResult with aggregated statistics.
        """
        logger.info(
            f"Generating batch result for {len(self.bug_results)} bugs"
        )
        
        # Calculate basic statistics
        total_bugs = len(self.bug_results)
        fixed_bugs = sum(
            1 for r in self.bug_results if r.successful_attempt is not None
        )
        failed_bugs = total_bugs - fixed_bugs
        
        # Calculate modeling type breakdown
        rewrite_success = sum(
            1 for r in self.bug_results
            if r.successful_attempt is not None and r.modeling_type == 'rewrite'
        )
        edit_success = sum(
            1 for r in self.bug_results
            if r.successful_attempt is not None and r.modeling_type == 'edit'
        )
        
        # Calculate additional statistics
        statistics = self.calculate_statistics()
        
        # Generate timestamp
        timestamp = datetime.now().isoformat()
        
        batch_result = BatchEvaluationResult(
            result_folder=self.result_folder,
            timestamp=timestamp,
            total_bugs=total_bugs,
            fixed_bugs=fixed_bugs,
            failed_bugs=failed_bugs,
            rewrite_success=rewrite_success,
            edit_success=edit_success,
            bug_results=self.bug_results,
            statistics=statistics
        )
        
        logger.info(
            f"Batch result generated: {fixed_bugs}/{total_bugs} bugs fixed "
            f"({statistics['success_rate']:.1%})"
        )
        
        return batch_result
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate detailed statistics from bug results.
        
        Returns:
            Dictionary with various statistics and metrics.
        """
        total_bugs = len(self.bug_results)
        
        if total_bugs == 0:
            return {
                'success_rate': 0.0,
                'rewrite_success_rate': 0.0,
                'edit_success_rate': 0.0,
                'average_attempts': 0.0,
                'total_attempts': 0,
                'failure_reasons': {},
                'normalization_strategies': {},
                'average_execution_time': 0.0,
                'total_execution_time': 0.0
            }
        
        # Calculate success rates
        fixed_bugs = sum(
            1 for r in self.bug_results if r.successful_attempt is not None
        )
        success_rate = fixed_bugs / total_bugs if total_bugs > 0 else 0.0
        
        # Calculate modeling type success rates
        rewrite_bugs = [
            r for r in self.bug_results if r.modeling_type == 'rewrite'
        ]
        rewrite_success = sum(
            1 for r in rewrite_bugs if r.successful_attempt is not None
        )
        rewrite_success_rate = (
            rewrite_success / len(rewrite_bugs) if rewrite_bugs else 0.0
        )
        
        edit_bugs = [
            r for r in self.bug_results if r.modeling_type == 'edit'
        ]
        edit_success = sum(
            1 for r in edit_bugs if r.successful_attempt is not None
        )
        edit_success_rate = (
            edit_success / len(edit_bugs) if edit_bugs else 0.0
        )
        
        # Calculate attempt statistics
        total_attempts = sum(r.total_attempts for r in self.bug_results)
        average_attempts = total_attempts / total_bugs if total_bugs > 0 else 0.0
        
        # Analyze failure reasons
        failure_reasons: Dict[str, int] = {}
        for result in self.bug_results:
            for reason in result.failure_reasons:
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # Analyze normalization strategies
        normalization_strategies: Dict[str, int] = {}
        for result in self.bug_results:
            if result.normalization_strategy:
                strategy = result.normalization_strategy
                normalization_strategies[strategy] = (
                    normalization_strategies.get(strategy, 0) + 1
                )
        
        # Calculate execution time statistics
        total_execution_time = sum(
            r.execution_time for r in self.bug_results
        )
        average_execution_time = (
            total_execution_time / total_bugs if total_bugs > 0 else 0.0
        )
        
        # Calculate test statistics
        test_results = [
            r.test_result for r in self.bug_results
            if r.test_result is not None
        ]
        
        if test_results:
            total_tests_run = sum(r.total_tests for r in test_results)
            total_tests_passed = sum(r.passed_tests for r in test_results)
            total_tests_failed = sum(r.failed_tests for r in test_results)
            timeouts = sum(1 for r in test_results if r.timeout)
        else:
            total_tests_run = 0
            total_tests_passed = 0
            total_tests_failed = 0
            timeouts = 0
        
        statistics = {
            'success_rate': success_rate,
            'rewrite_success_rate': rewrite_success_rate,
            'edit_success_rate': edit_success_rate,
            'average_attempts': average_attempts,
            'total_attempts': total_attempts,
            'failure_reasons': failure_reasons,
            'normalization_strategies': normalization_strategies,
            'average_execution_time': average_execution_time,
            'total_execution_time': total_execution_time,
            'modeling_type_distribution': {
                'rewrite': len(rewrite_bugs),
                'edit': len(edit_bugs),
                'unknown': total_bugs - len(rewrite_bugs) - len(edit_bugs)
            },
            'test_statistics': {
                'total_tests_run': total_tests_run,
                'total_tests_passed': total_tests_passed,
                'total_tests_failed': total_tests_failed,
                'timeouts': timeouts
            }
        }
        
        logger.debug(f"Calculated statistics: {statistics}")
        
        return statistics
    
    def get_successful_bugs(self) -> List[BugEvaluationResult]:
        """Get list of successfully fixed bugs.
        
        Returns:
            List of bug results where fix was successful.
        """
        return [
            r for r in self.bug_results if r.successful_attempt is not None
        ]
    
    def get_failed_bugs(self) -> List[BugEvaluationResult]:
        """Get list of bugs that failed to be fixed.
        
        Returns:
            List of bug results where fix failed.
        """
        return [
            r for r in self.bug_results if r.successful_attempt is None
        ]
    
    def get_bugs_by_modeling_type(self, modeling_type: str) -> List[BugEvaluationResult]:
        """Get bugs filtered by modeling type.
        
        Args:
            modeling_type: Modeling type to filter by ("edit" or "rewrite").
        
        Returns:
            List of bug results with specified modeling type.
        """
        return [
            r for r in self.bug_results if r.modeling_type == modeling_type
        ]
    
    def get_summary_text(self) -> str:
        """Generate human-readable summary text.
        
        Returns:
            Formatted summary string.
        """
        batch_result = self.generate_batch_result()
        stats = batch_result.statistics
        
        lines = [
            "=" * 80,
            "BATCH EVALUATION SUMMARY",
            "=" * 80,
            f"Result Folder: {batch_result.result_folder}",
            f"Timestamp: {batch_result.timestamp}",
            "",
            "Overall Results:",
            f"  Total Bugs: {batch_result.total_bugs}",
            f"  Fixed Bugs: {batch_result.fixed_bugs}",
            f"  Failed Bugs: {batch_result.failed_bugs}",
            f"  Success Rate: {stats['success_rate']:.1%}",
            "",
            "Modeling Type Breakdown:",
            f"  Rewrite Success: {batch_result.rewrite_success} "
            f"({stats['rewrite_success_rate']:.1%})",
            f"  Edit Success: {batch_result.edit_success} "
            f"({stats['edit_success_rate']:.1%})",
            "",
            "Attempt Statistics:",
            f"  Total Attempts: {stats['total_attempts']}",
            f"  Average Attempts per Bug: {stats['average_attempts']:.2f}",
            "",
            "Execution Time:",
            f"  Total: {stats['total_execution_time']:.2f}s",
            f"  Average per Bug: {stats['average_execution_time']:.2f}s",
            ""
        ]
        
        # Add failure reasons if any
        if stats['failure_reasons']:
            lines.append("Top Failure Reasons:")
            sorted_reasons = sorted(
                stats['failure_reasons'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for reason, count in sorted_reasons[:5]:
                lines.append(f"  {reason}: {count}")
            lines.append("")
        
        # Add test statistics if available
        test_stats = stats.get('test_statistics', {})
        if test_stats.get('total_tests_run', 0) > 0:
            lines.extend([
                "Test Statistics:",
                f"  Total Tests Run: {test_stats['total_tests_run']}",
                f"  Tests Passed: {test_stats['total_tests_passed']}",
                f"  Tests Failed: {test_stats['total_tests_failed']}",
                f"  Timeouts: {test_stats['timeouts']}",
                ""
            ])
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def clear(self):
        """Clear all collected bug results."""
        self.bug_results.clear()
        logger.debug("Cleared all bug results")
