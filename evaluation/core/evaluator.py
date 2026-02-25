"""Main evaluator for D4J fix evaluation system.

This module contains the D4JFixEvaluator class which orchestrates the entire
evaluation process by coordinating all other components.
"""

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from evaluation.core.data_structures import (
    BugEvaluationResult,
    FixAttempt,
    TestResult,
)
from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.input_handler import InputHandler
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_applicator import PatchApplicator
from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.result_generator import ResultGenerator
from evaluation.core.storage_manager import StorageManager
from evaluation.core.test_executor import TestExecutor

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of a single fix attempt.
    
    Attributes:
        success: Whether the fix was successful.
        modeling_type: Type of modeling used ("edit" or "rewrite").
        test_result: Test execution result.
        error: Error message if fix failed.
    """
    
    success: bool
    modeling_type: Optional[str] = None
    test_result: Optional[TestResult] = None
    error: Optional[str] = None


class D4JFixEvaluator:
    """Main evaluator for D4J fix evaluation.
    
    This class orchestrates the entire evaluation process:
    1. Reads fix attempts from result folder
    2. Parses model outputs
    3. Normalizes patches to unified diff format
    4. Applies patches to D4J repositories
    5. Runs tests to verify fixes
    6. Generates and saves evaluation results
    
    Attributes:
        result_folder: Path to the result folder containing fix attempts.
        output_dir: Path to the output directory for evaluation results.
        config: Configuration dictionary.
        input_handler: Handler for reading fix attempts.
        output_parser: Parser for model outputs.
        normalizer: Patch normalizer.
        env_manager: D4J environment manager.
        result_generator: Result generator.
        storage_manager: Storage manager.
    """
    
    def __init__(
        self,
        result_folder: Path,
        output_dir: Path,
        config: Dict
    ):
        """Initialize the evaluator.
        
        Args:
            result_folder: Path to result folder with fix attempts.
            output_dir: Path to output directory.
            config: Configuration dictionary with D4J settings.
        """
        self.result_folder = Path(result_folder)
        self.output_dir = Path(output_dir)
        self.config = config
        
        # Initialize all components
        self.input_handler = InputHandler(self.result_folder)
        self.output_parser = OutputParser()
        self.normalizer = PatchNormalizer()
        
        # Get evaluation config
        eval_config = config.get('evaluation_config', {})
        d4j_path = eval_config.get('d4j_path')
        workspace_dir = eval_config.get('workspace_dir', './workspace')
        
        self.env_manager = EnvironmentManager(
            d4j_path=Path(d4j_path) if d4j_path else None,
            workspace_dir=Path(workspace_dir)
        )
        self.result_generator = ResultGenerator()
        self.storage_manager = StorageManager(self.output_dir)
        
        logger.info(f"Initialized D4JFixEvaluator")
        logger.info(f"  Result folder: {self.result_folder}")
        logger.info(f"  Output dir: {self.output_dir}")
    
    def evaluate(
        self,
        parallel: int = 1,
        verbose: bool = False,
        bug_filter: Optional[List[str]] = None
    ):
        """Execute batch evaluation.
        
        Args:
            parallel: Number of parallel workers (not implemented yet).
            verbose: Whether to show verbose logging.
            bug_filter: List of bug slugs to evaluate (None = all bugs).
            
        Returns:
            BatchEvaluationResult: Batch evaluation result.
            
        Raises:
            ValueError: If result folder structure is invalid.
        """
        start_time = time.time()
        
        # 1. Validate input
        if not self.input_handler.validate_structure():
            raise ValueError(
                f"Invalid result folder structure: {self.result_folder}"
            )
        
        # 2. Get all bugs
        all_bugs = self.input_handler.list_bugs()
        
        # Apply filter if provided
        if bug_filter:
            bugs = [b for b in all_bugs if b in bug_filter]
            logger.info(
                f"Filtered to {len(bugs)} bugs out of {len(all_bugs)}"
            )
        else:
            bugs = all_bugs
        
        logger.info(f"Starting evaluation of {len(bugs)} bugs")
        
        # 3. Process each bug (sequential for now)
        if parallel > 1:
            logger.warning(
                "Parallel processing not yet implemented, using sequential"
            )
            results = self._evaluate_sequential(bugs, verbose)
        else:
            results = self._evaluate_sequential(bugs, verbose)
        
        # 4. Generate batch result
        batch_result = self.result_generator.generate_batch_result()
        
        # 5. Save results
        self.storage_manager.save_batch_result(batch_result)
        statistics = self.result_generator.calculate_statistics()
        self.storage_manager.save_statistics(statistics)
        
        # 6. Log summary
        elapsed_time = time.time() - start_time
        logger.info(f"Evaluation completed in {elapsed_time:.2f} seconds")
        logger.info(f"  Total bugs: {batch_result.total_bugs}")
        logger.info(f"  Fixed bugs: {batch_result.fixed_bugs}")
        logger.info(
            f"  Fix rate: {batch_result.fix_rate:.2f}%"
        )
        
        return batch_result
    
    def evaluate_bug(self, bug_slug: str) -> BugEvaluationResult:
        """Evaluate a single bug.
        
        Args:
            bug_slug: Bug identifier (e.g., "Chart_1").
            
        Returns:
            BugEvaluationResult: Evaluation result for the bug.
        """
        start_time = time.time()
        logger.info(f"Evaluating bug: {bug_slug}")
        
        # 1. Check if bug is deprecated
        if self.env_manager.is_deprecated(bug_slug):
            logger.warning(f"Skipping deprecated bug: {bug_slug}")
            return self._create_skipped_result(bug_slug)
        
        # 2. Checkout bug
        try:
            repo_path = self.env_manager.checkout_bug(bug_slug)
        except Exception as e:
            logger.error(f"Failed to checkout {bug_slug}: {e}")
            return self._create_error_result(
                bug_slug,
                f"Checkout failed: {str(e)}"
            )
        
        try:
            # 3. Get all fix attempts
            attempts = self.input_handler.list_attempts(bug_slug)
            logger.info(f"  Found {len(attempts)} attempts")
            
            failure_reasons = []
            
            # 4. Try each fix attempt
            for attempt_num in attempts:
                logger.info(f"  Trying attempt {attempt_num}")
                
                result = self._try_fix(bug_slug, attempt_num, repo_path)
                
                if result.success:
                    # Fix succeeded!
                    elapsed = time.time() - start_time
                    logger.info(
                        f"  ✓ Bug {bug_slug} fixed with attempt {attempt_num}"
                    )
                    
                    bug_result = BugEvaluationResult(
                        bug_slug=bug_slug,
                        total_attempts=len(attempts),
                        successful_attempt=attempt_num,
                        modeling_type=result.modeling_type,
                        test_result=result.test_result,
                        failure_reasons=[],
                        execution_time=elapsed
                    )
                    self.result_generator.add_bug_result(bug_result)
                    return bug_result
                else:
                    # Fix failed, record reason and continue
                    failure_reasons.append(
                        f"Attempt {attempt_num}: {result.error}"
                    )
                    logger.warning(f"  ✗ Attempt {attempt_num} failed")
            
            # 5. All attempts failed
            elapsed = time.time() - start_time
            logger.error(f"  ✗ All attempts failed for {bug_slug}")
            
            bug_result = BugEvaluationResult(
                bug_slug=bug_slug,
                total_attempts=len(attempts),
                successful_attempt=None,
                modeling_type=None,
                test_result=None,
                failure_reasons=failure_reasons,
                execution_time=elapsed
            )
            self.result_generator.add_bug_result(bug_result)
            return bug_result
            
        finally:
            # 6. Cleanup
            try:
                self.env_manager.cleanup(repo_path)
            except Exception as e:
                logger.warning(f"Cleanup failed for {bug_slug}: {e}")
    
    def _try_fix(
        self,
        bug_slug: str,
        attempt_num: int,
        repo_path: Path
    ) -> FixResult:
        """Try to apply a single fix attempt.
        
        Args:
            bug_slug: Bug identifier.
            attempt_num: Attempt number.
            repo_path: Path to checked out repository.
            
        Returns:
            FixResult: Result of the fix attempt.
        """
        try:
            # 1. Load fix attempt
            attempt = self.input_handler.load_attempt(bug_slug, attempt_num)
            
            # 2. Parse model output
            parsed_patch = self.output_parser.parse(
                model_output=attempt.model_output,
                bug_slug=attempt.bug_slug,
                attempt_num=attempt.attempt_num,
                modeling_type=attempt.modeling_type,
                query=attempt.query
            )
            
            if not parsed_patch.parse_success:
                return FixResult(
                    success=False,
                    error=f"Parse failed: {parsed_patch.parse_error}"
                )
            
            # 3. Locate source file
            source_file = self._locate_source_file(
                repo_path,
                bug_slug,
                parsed_patch
            )
            
            if not source_file or not source_file.exists():
                return FixResult(
                    success=False,
                    error="Source file not found"
                )
            
            # 4. Normalize patch
            try:
                normalized_patch = self.normalizer.normalize(
                    parsed_patch,
                    source_file
                )
            except Exception as e:
                return FixResult(
                    success=False,
                    error=f"Normalization failed: {str(e)}"
                )
            
            # 5. Save normalized patch
            self.storage_manager.save_normalized_patch(normalized_patch)
            
            # 6. Apply patch
            applicator = PatchApplicator(repo_path)
            apply_result = applicator.apply(normalized_patch)
            
            if not apply_result.success:
                return FixResult(
                    success=False,
                    error=f"Apply failed: {apply_result.error_message}"
                )
            
            # 7. Run tests
            executor = TestExecutor(
                repo_path,
                timeout=self.config.get('timeout', 600),
                d4j_path=self.env_manager.d4j_path
            )
            test_result = executor.run_tests(bug_slug)
            
            # 8. Rollback patch
            try:
                applicator.rollback()
            except Exception as e:
                logger.warning(f"Rollback failed: {e}")
            
            # 9. Return result
            return FixResult(
                success=test_result.success,
                modeling_type=attempt.modeling_type,
                test_result=test_result
            )
            
        except Exception as e:
            logger.error(
                f"Error in attempt {attempt_num} for {bug_slug}: {e}",
                exc_info=True
            )
            return FixResult(success=False, error=str(e))
    
    def _evaluate_sequential(
        self,
        bugs: List[str],
        verbose: bool
    ) -> List[BugEvaluationResult]:
        """Evaluate bugs sequentially.
        
        Args:
            bugs: List of bug slugs to evaluate.
            verbose: Whether to show verbose output.
            
        Returns:
            List of bug evaluation results.
        """
        results = []
        
        for i, bug_slug in enumerate(bugs, 1):
            logger.info(f"[{i}/{len(bugs)}] Evaluating {bug_slug}")
            
            try:
                result = self.evaluate_bug(bug_slug)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate {bug_slug}: {e}")
                # Create error result
                error_result = self._create_error_result(
                    bug_slug,
                    str(e)
                )
                results.append(error_result)
        
        return results
    
    def _evaluate_parallel(
        self,
        bugs: List[str],
        workers: int
    ) -> List[BugEvaluationResult]:
        """Evaluate bugs in parallel (not yet implemented).
        
        Args:
            bugs: List of bug slugs to evaluate.
            workers: Number of parallel workers.
            
        Returns:
            List of bug evaluation results.
        """
        # TODO: Implement parallel processing using multiprocessing.Pool
        raise NotImplementedError("Parallel processing not yet implemented")
    
    def _locate_source_file(
        self,
        repo_path: Path,
        bug_slug: str,
        parsed_patch
    ) -> Optional[Path]:
        """Locate the source file to patch.
        
        Args:
            repo_path: Path to repository.
            bug_slug: Bug identifier.
            parsed_patch: Parsed patch object.
            
        Returns:
            Path to source file, or repository root if not found
            (normalizer will search using tree-sitter).
        """
        # Use D4J to get the modified classes for this bug
        try:
            result = subprocess.run(
                [
                    str(self.env_manager.d4j_path / 'framework' / 'bin' / 'defects4j'),
                    'export',
                    '-p', 'classes.modified',
                    '-w', str(repo_path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(
                    f"Failed to get modified classes: {result.stderr}"
                )
                logger.info(
                    "Returning repository root, normalizer will search for file"
                )
                return repo_path
            
            # Parse modified classes (format: org.package.ClassName)
            modified_classes = result.stdout.strip().split('\n')
            
            if not modified_classes or modified_classes == ['']:
                logger.warning("No modified classes found")
                logger.info(
                    "Returning repository root, normalizer will search for file"
                )
                return repo_path
            
            # For now, use the first modified class
            # In a more sophisticated implementation, we would match
            # the class name from the method signature in the patch
            class_name = modified_classes[0].strip()
            
            # Convert class name to file path
            # org.package.ClassName -> org/package/ClassName.java
            file_path = class_name.replace('.', '/') + '.java'
            
            # Search for the file in src directories
            # Note: Gson project has a special structure with gson/ subdirectory
            src_dirs = ['src/main/java', 'src/java', 'src', 'source']
            
            # For Gson project, also check gson/ subdirectory
            project_name = bug_slug.split('_')[0]
            if project_name == 'Gson':
                src_dirs.extend([
                    'gson/src/main/java',
                    'gson/src/java',
                    'gson/src'
                ])
            
            for src_dir in src_dirs:
                full_path = repo_path / src_dir / file_path
                if full_path.exists():
                    logger.info(f"Found source file: {full_path}")
                    return full_path
            
            # If not found in standard locations, search recursively
            logger.warning(
                f"Source file not found in standard locations, "
                f"searching recursively"
            )
            for java_file in repo_path.rglob('*.java'):
                if java_file.name == class_name.split('.')[-1] + '.java':
                    logger.info(f"Found source file: {java_file}")
                    return java_file
            
            logger.warning(f"Source file not found for class: {class_name}")
            logger.info(
                "Returning repository root, normalizer will search for file"
            )
            return repo_path
            
        except subprocess.TimeoutExpired:
            logger.warning("Timeout getting modified classes")
            logger.info(
                "Returning repository root, normalizer will search for file"
            )
            return repo_path
        except Exception as e:
            logger.warning(f"Error locating source file: {e}")
            logger.info(
                "Returning repository root, normalizer will search for file"
            )
            return repo_path
    
    def _create_skipped_result(self, bug_slug: str) -> BugEvaluationResult:
        """Create a result for a skipped bug.
        
        Args:
            bug_slug: Bug identifier.
            
        Returns:
            BugEvaluationResult indicating bug was skipped.
        """
        return BugEvaluationResult(
            bug_slug=bug_slug,
            total_attempts=0,
            successful_attempt=None,
            modeling_type=None,
            test_result=None,
            failure_reasons=["Bug is deprecated"],
            execution_time=0.0
        )
    
    def _create_error_result(
        self,
        bug_slug: str,
        error_message: str
    ) -> BugEvaluationResult:
        """Create a result for a bug that encountered an error.
        
        Args:
            bug_slug: Bug identifier.
            error_message: Error message.
            
        Returns:
            BugEvaluationResult indicating error.
        """
        return BugEvaluationResult(
            bug_slug=bug_slug,
            total_attempts=0,
            successful_attempt=None,
            modeling_type=None,
            test_result=None,
            failure_reasons=[error_message],
            execution_time=0.0
        )
