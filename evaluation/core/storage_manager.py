"""Storage manager for saving evaluation results and intermediate data.

This module provides the StorageManager class for organizing and saving
evaluation results, patches, and logs to disk.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from evaluation.core.data_structures import (
    BatchEvaluationResult,
    BugEvaluationResult,
    NormalizedPatch,
)

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages storage of evaluation results and intermediate data.
    
    This class handles saving normalized patches, bug results, batch results,
    and statistics to a structured output directory.
    
    Attributes:
        output_dir: Base output directory for all results.
        patches_dir: Directory for normalized patches.
        bug_results_dir: Directory for individual bug results.
        log_file: Path to evaluation log file.
    """
    
    def __init__(self, output_dir: Path):
        """Initialize StorageManager.
        
        Args:
            output_dir: Base directory for storing all evaluation outputs.
        """
        self.output_dir = Path(output_dir)
        
        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.patches_dir = self.output_dir / "patches"
        self.patches_dir.mkdir(exist_ok=True)
        
        self.bug_results_dir = self.output_dir / "bug_results"
        self.bug_results_dir.mkdir(exist_ok=True)
        
        # Log file path
        self.log_file = self.output_dir / "evaluation.log"
        
        logger.info(f"Initialized StorageManager: {self.output_dir}")
    
    def save_normalized_patch(
        self,
        patch: NormalizedPatch,
        filename: str = None
    ) -> Path:
        """Save a normalized patch to disk.
        
        Args:
            patch: Normalized patch to save.
            filename: Optional custom filename. If None, generates filename
                from bug_slug and attempt_num.
        
        Returns:
            Path to the saved patch file.
        """
        if filename is None:
            filename = f"{patch.bug_slug}_attempt_{patch.attempt_num}.patch"
        
        patch_path = self.patches_dir / filename
        
        try:
            patch_path.write_text(patch.diff_content)
            logger.debug(f"Saved patch: {patch_path}")
            return patch_path
        except Exception as e:
            logger.error(f"Failed to save patch {filename}: {e}")
            raise
    
    def save_bug_result(
        self,
        result: BugEvaluationResult,
        filename: str = None
    ) -> Path:
        """Save a bug evaluation result to disk.
        
        Args:
            result: Bug evaluation result to save.
            filename: Optional custom filename. If None, generates filename
                from bug_slug.
        
        Returns:
            Path to the saved result file.
        """
        if filename is None:
            filename = f"{result.bug_slug}.json"
        
        result_path = self.bug_results_dir / filename
        
        try:
            # Convert result to dictionary
            result_dict = {
                'bug_slug': result.bug_slug,
                'total_attempts': result.total_attempts,
                'successful_attempt': result.successful_attempt,
                'modeling_type': result.modeling_type,
                'failure_reasons': result.failure_reasons,
                'normalization_strategy': result.normalization_strategy,
                'execution_time': result.execution_time
            }
            
            # Add test result if available
            if result.test_result:
                result_dict['test_result'] = {
                    'success': result.test_result.success,
                    'total_tests': result.test_result.total_tests,
                    'passed_tests': result.test_result.passed_tests,
                    'failed_tests': result.test_result.failed_tests,
                    'timeout': result.test_result.timeout,
                    'error_message': result.test_result.error_message,
                    'failed_test_cases': result.test_result.failed_test_cases,
                    'execution_time': result.test_result.execution_time
                }
            
            # Write to file
            with open(result_path, 'w') as f:
                json.dump(result_dict, f, indent=2)
            
            logger.debug(f"Saved bug result: {result_path}")
            return result_path
        except Exception as e:
            logger.error(f"Failed to save bug result {filename}: {e}")
            raise
    
    def save_batch_result(
        self,
        result: BatchEvaluationResult,
        filename: str = "batch_evaluation.json"
    ) -> Path:
        """Save batch evaluation result to disk.
        
        Args:
            result: Batch evaluation result to save.
            filename: Filename for the batch result.
        
        Returns:
            Path to the saved batch result file.
        """
        result_path = self.output_dir / filename
        
        try:
            # Convert result to dictionary
            result_dict = {
                'result_folder': result.result_folder,
                'timestamp': result.timestamp,
                'total_bugs': result.total_bugs,
                'fixed_bugs': result.fixed_bugs,
                'failed_bugs': result.failed_bugs,
                'rewrite_success': result.rewrite_success,
                'edit_success': result.edit_success,
                'statistics': result.statistics,
                'bug_results': [
                    {
                        'bug_slug': r.bug_slug,
                        'total_attempts': r.total_attempts,
                        'successful_attempt': r.successful_attempt,
                        'modeling_type': r.modeling_type,
                        'failure_reasons': r.failure_reasons
                    }
                    for r in result.bug_results
                ]
            }
            
            # Write to file
            with open(result_path, 'w') as f:
                json.dump(result_dict, f, indent=2)
            
            logger.info(f"Saved batch result: {result_path}")
            return result_path
        except Exception as e:
            logger.error(f"Failed to save batch result: {e}")
            raise
    
    def save_statistics(
        self,
        stats: Dict[str, Any],
        filename: str = "statistics.json"
    ) -> Path:
        """Save statistics to disk.
        
        Args:
            stats: Statistics dictionary to save.
            filename: Filename for the statistics file.
        
        Returns:
            Path to the saved statistics file.
        """
        stats_path = self.output_dir / filename
        
        try:
            with open(stats_path, 'w') as f:
                json.dump(stats, f, indent=2)
            
            logger.debug(f"Saved statistics: {stats_path}")
            return stats_path
        except Exception as e:
            logger.error(f"Failed to save statistics: {e}")
            raise
    
    def log(self, message: str, level: str = "INFO"):
        """Write a log message to the evaluation log file.
        
        Args:
            message: Log message to write.
            level: Log level (INFO, WARNING, ERROR, DEBUG).
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
    
    def save_summary_text(
        self,
        summary: str,
        filename: str = "summary.txt"
    ) -> Path:
        """Save a text summary to disk.
        
        Args:
            summary: Summary text to save.
            filename: Filename for the summary file.
        
        Returns:
            Path to the saved summary file.
        """
        summary_path = self.output_dir / filename
        
        try:
            summary_path.write_text(summary)
            logger.debug(f"Saved summary: {summary_path}")
            return summary_path
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            raise
    
    def load_bug_result(self, bug_slug: str) -> Dict[str, Any]:
        """Load a bug evaluation result from disk.
        
        Args:
            bug_slug: Bug identifier.
        
        Returns:
            Dictionary with bug evaluation result.
        
        Raises:
            FileNotFoundError: If result file doesn't exist.
        """
        result_path = self.bug_results_dir / f"{bug_slug}.json"
        
        if not result_path.exists():
            raise FileNotFoundError(f"Bug result not found: {bug_slug}")
        
        try:
            with open(result_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load bug result {bug_slug}: {e}")
            raise
    
    def load_batch_result(
        self,
        filename: str = "batch_evaluation.json"
    ) -> Dict[str, Any]:
        """Load batch evaluation result from disk.
        
        Args:
            filename: Filename of the batch result.
        
        Returns:
            Dictionary with batch evaluation result.
        
        Raises:
            FileNotFoundError: If result file doesn't exist.
        """
        result_path = self.output_dir / filename
        
        if not result_path.exists():
            raise FileNotFoundError(f"Batch result not found: {filename}")
        
        try:
            with open(result_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load batch result: {e}")
            raise
    
    def list_bug_results(self) -> list:
        """List all saved bug results.
        
        Returns:
            List of bug slugs that have saved results.
        """
        bug_slugs = []
        
        for result_file in self.bug_results_dir.glob("*.json"):
            bug_slug = result_file.stem
            bug_slugs.append(bug_slug)
        
        return sorted(bug_slugs)
    
    def list_patches(self) -> list:
        """List all saved patches.
        
        Returns:
            List of patch filenames.
        """
        patches = []
        
        for patch_file in self.patches_dir.glob("*.patch"):
            patches.append(patch_file.name)
        
        return sorted(patches)
    
    def get_output_summary(self) -> Dict[str, Any]:
        """Get summary of saved outputs.
        
        Returns:
            Dictionary with counts of saved items.
        """
        return {
            'output_dir': str(self.output_dir),
            'total_patches': len(list(self.patches_dir.glob("*.patch"))),
            'total_bug_results': len(list(self.bug_results_dir.glob("*.json"))),
            'has_batch_result': (self.output_dir / "batch_evaluation.json").exists(),
            'has_statistics': (self.output_dir / "statistics.json").exists(),
            'log_file_size': self.log_file.stat().st_size if self.log_file.exists() else 0
        }
    
    def clear_output(self):
        """Clear all output files (use with caution!).
        
        Warning: This removes all saved results, patches, and logs.
        """
        import shutil
        
        logger.warning(f"Clearing all output in: {self.output_dir}")
        
        # Remove all files in subdirectories
        for patch_file in self.patches_dir.glob("*"):
            patch_file.unlink()
        
        for result_file in self.bug_results_dir.glob("*"):
            result_file.unlink()
        
        # Remove files in output directory
        for file in self.output_dir.glob("*.json"):
            file.unlink()
        
        for file in self.output_dir.glob("*.txt"):
            file.unlink()
        
        if self.log_file.exists():
            self.log_file.unlink()
        
        logger.info("Output cleared")
