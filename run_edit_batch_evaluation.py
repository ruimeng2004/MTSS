#!/usr/bin/env python3
"""Run parallel evaluation for edit batch results.

This script evaluates the edit batch from ppl/result/20260106_113852
using parallel workers, similar to the previous evaluation approach.
"""

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.core.data_structures import BugEvaluationResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('edit_batch_evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EditBatchEvaluator:
    """Parallel evaluator for edit batch results."""
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        d4j_path: str,
        base_workspace: str,
        num_workers: int = 4,
        timeout: int = 300
    ):
        """Initialize EditBatchEvaluator.
        
        Args:
            input_dir: Directory containing edit batch results.
            output_dir: Directory for evaluation output.
            d4j_path: Path to Defects4J installation.
            base_workspace: Base directory for workspaces.
            num_workers: Number of parallel workers.
            timeout: Timeout for each bug evaluation in seconds.
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.d4j_path = Path(d4j_path)
        self.base_workspace = Path(base_workspace)
        self.num_workers = num_workers
        self.timeout = timeout
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Initialized EditBatchEvaluator with {num_workers} workers"
        )
    
    def get_all_bugs(self) -> List[str]:
        """Get list of all bugs to evaluate.
        
        Returns:
            List of bug slugs.
        """
        bugs = []
        for bug_dir in sorted(self.input_dir.iterdir()):
            if bug_dir.is_dir():
                bugs.append(bug_dir.name)
        
        logger.info(f"Found {len(bugs)} bugs to evaluate")
        return bugs
    
    def evaluate_bug_worker(
        self,
        bug_slug: str,
        worker_id: int
    ) -> BugEvaluationResult:
        """Evaluate a single bug in a worker thread.
        
        Args:
            bug_slug: Bug identifier.
            worker_id: Worker thread ID.
            
        Returns:
            BugEvaluationResult for the bug.
        """
        # Create worker-specific workspace
        workspace_dir = self.base_workspace / f"worker_{worker_id}"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create evaluator config
        config = {
            'evaluation_config': {
                'd4j_path': str(self.d4j_path),
                'workspace_dir': str(workspace_dir),
                'timeout': self.timeout
            }
        }
        
        # Create evaluator for this worker
        evaluator = D4JFixEvaluator(
            result_folder=self.input_dir,
            output_dir=self.output_dir,
            config=config
        )
        
        try:
            logger.info(
                f"[Worker {worker_id}] Starting evaluation of {bug_slug}"
            )
            result = evaluator.evaluate_bug(bug_slug)
            
            if result.successful_attempt:
                logger.info(
                    f"[Worker {worker_id}] ✓ {bug_slug} fixed "
                    f"(attempt {result.successful_attempt})"
                )
            else:
                logger.info(
                    f"[Worker {worker_id}] ✗ {bug_slug} failed "
                    f"(all {result.total_attempts} attempts)"
                )
            
            return result
            
        except Exception as e:
            logger.error(
                f"[Worker {worker_id}] Error evaluating {bug_slug}: {e}",
                exc_info=True
            )
            # Return error result
            return BugEvaluationResult(
                bug_slug=bug_slug,
                total_attempts=0,
                successful_attempt=None,
                modeling_type=None,
                test_result=None,
                failure_reasons=[f"Evaluation error: {str(e)}"],
                execution_time=0.0
            )
    
    def run_parallel_evaluation(
        self,
        bugs: List[str] = None,
        max_bugs: int = None
    ) -> Dict[str, Any]:
        """Run parallel evaluation on all bugs.
        
        Args:
            bugs: List of specific bugs to evaluate. If None, evaluates all.
            max_bugs: Maximum number of bugs to evaluate (for testing).
            
        Returns:
            Dictionary with evaluation results and statistics.
        """
        start_time = time.time()
        
        # Get bugs to evaluate
        if bugs is None:
            bugs = self.get_all_bugs()
        
        if max_bugs:
            bugs = bugs[:max_bugs]
            logger.info(f"Limiting evaluation to first {max_bugs} bugs")
        
        total_bugs = len(bugs)
        logger.info(f"Starting parallel evaluation of {total_bugs} bugs")
        logger.info(f"Using {self.num_workers} worker threads")
        
        # Track results
        results = []
        completed = 0
        fixed_count = 0
        failed_count = 0
        
        # Run evaluations in parallel
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_bug = {}
            for i, bug_slug in enumerate(bugs):
                worker_id = i % self.num_workers
                future = executor.submit(
                    self.evaluate_bug_worker,
                    bug_slug,
                    worker_id
                )
                future_to_bug[future] = bug_slug
            
            # Process completed tasks
            for future in as_completed(future_to_bug):
                bug_slug = future_to_bug[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update counters
                    if result.successful_attempt:
                        fixed_count += 1
                    else:
                        failed_count += 1
                    
                    # Progress update
                    progress = (completed / total_bugs) * 100
                    logger.info(
                        f"Progress: {completed}/{total_bugs} "
                        f"({progress:.1f}%) - Latest: {bug_slug}"
                    )
                    
                    # Print statistics every 30 bugs
                    if completed % 30 == 0:
                        elapsed = time.time() - start_time
                        success_rate = (fixed_count / completed) * 100
                        avg_time = elapsed / completed
                        remaining = total_bugs - completed
                        eta_seconds = remaining * avg_time
                        eta_minutes = eta_seconds / 60
                        
                        logger.info("\n" + "=" * 70)
                        logger.info(
                            f"📊 PROGRESS REPORT - {completed}/{total_bugs} "
                            f"bugs completed"
                        )
                        logger.info("=" * 70)
                        logger.info(
                            f"✓ Fixed: {fixed_count} | "
                            f"✗ Failed: {failed_count} | "
                            f"Success Rate: {success_rate:.1f}%"
                        )
                        logger.info(
                            f"⏱️  Elapsed: {elapsed/60:.1f} min | "
                            f"Avg: {avg_time:.1f}s/bug | "
                            f"ETA: {eta_minutes:.1f} min"
                        )
                        logger.info("=" * 70 + "\n")
                    
                except Exception as e:
                    logger.error(
                        f"Failed to get result for {bug_slug}: {e}"
                    )
                    failed_count += 1
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        stats = self._calculate_statistics(results, elapsed_time)
        
        # Save results
        output_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'input_batch': str(self.input_dir),
            'total_bugs': total_bugs,
            'num_workers': self.num_workers,
            'statistics': stats,
            'bug_results': [self._result_to_dict(r) for r in results]
        }
        
        output_file = self.output_dir / 'edit_batch_evaluation_results.json'
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        
        return output_data
    
    def _calculate_statistics(
        self,
        results: List[BugEvaluationResult],
        total_time: float
    ) -> Dict[str, Any]:
        """Calculate evaluation statistics.
        
        Args:
            results: List of bug evaluation results.
            total_time: Total evaluation time in seconds.
            
        Returns:
            Dictionary with statistics.
        """
        total_bugs = len(results)
        fixed_bugs = sum(1 for r in results if r.successful_attempt)
        failed_bugs = total_bugs - fixed_bugs
        
        # Modeling type distribution
        edit_success = sum(
            1 for r in results
            if r.successful_attempt and r.modeling_type == 'edit'
        )
        rewrite_success = sum(
            1 for r in results
            if r.successful_attempt and r.modeling_type == 'rewrite'
        )
        
        # Average execution time per bug
        avg_time = (
            sum(r.execution_time for r in results) / total_bugs
            if total_bugs > 0 else 0
        )
        
        # Speedup calculation
        sequential_time = sum(r.execution_time for r in results)
        speedup = sequential_time / total_time if total_time > 0 else 1.0
        
        return {
            'total_bugs': total_bugs,
            'fixed_bugs': fixed_bugs,
            'failed_bugs': failed_bugs,
            'success_rate': fixed_bugs / total_bugs if total_bugs > 0 else 0,
            'edit_success': edit_success,
            'rewrite_success': rewrite_success,
            'average_time_per_bug': avg_time,
            'total_parallel_time': total_time,
            'estimated_sequential_time': sequential_time,
            'speedup': speedup,
            'efficiency': speedup / self.num_workers
        }
    
    def _result_to_dict(self, result: BugEvaluationResult) -> Dict[str, Any]:
        """Convert BugEvaluationResult to dictionary.
        
        Args:
            result: Bug evaluation result.
            
        Returns:
            Dictionary representation.
        """
        return {
            'bug_slug': result.bug_slug,
            'total_attempts': result.total_attempts,
            'successful_attempt': result.successful_attempt,
            'modeling_type': result.modeling_type,
            'execution_time': result.execution_time,
            'failure_reasons': result.failure_reasons[:3]
        }


def main():
    """Main entry point for edit batch evaluation."""
    parser = argparse.ArgumentParser(
        description='Run parallel evaluation for edit batch'
    )
    parser.add_argument(
        '--input-dir',
        default='ppl/result/20260106_113852',
        help='Input directory with edit batch results'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Output directory (default: auto-generated with timestamp)'
    )
    parser.add_argument(
        '--d4j-path',
        default='/Users/mengrui/Desktop/D4J/defects4j',
        help='Path to Defects4J installation'
    )
    parser.add_argument(
        '--workspace',
        default='./parallel_workspace',
        help='Base workspace directory'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=100,
        help='Number of parallel workers'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=240,
        help='Timeout per bug in seconds'
    )
    parser.add_argument(
        '--max-bugs',
        type=int,
        default=None,
        help='Maximum number of bugs to evaluate (for testing)'
    )
    parser.add_argument(
        '--bugs',
        nargs='+',
        default=None,
        help='Specific bugs to evaluate (e.g., Chart_1 Chart_2)'
    )
    
    args = parser.parse_args()
    
    # Generate output directory with timestamp if not specified
    if args.output_dir is None:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        args.output_dir = f'evaluation_output/edit_batch_eval_{timestamp}'
    
    # Create evaluator
    evaluator = EditBatchEvaluator(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        d4j_path=args.d4j_path,
        base_workspace=args.workspace,
        num_workers=args.workers,
        timeout=args.timeout
    )
    
    # Run evaluation
    logger.info("=" * 80)
    logger.info("EDIT BATCH PARALLEL EVALUATION")
    logger.info("=" * 80)
    
    results = evaluator.run_parallel_evaluation(
        bugs=args.bugs,
        max_bugs=args.max_bugs
    )
    
    # Print summary
    stats = results['statistics']
    logger.info("\n" + "=" * 80)
    logger.info("EVALUATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total bugs: {stats['total_bugs']}")
    logger.info(f"Fixed bugs: {stats['fixed_bugs']}")
    logger.info(f"Failed bugs: {stats['failed_bugs']}")
    logger.info(f"Success rate: {stats['success_rate']:.1%}")
    logger.info(f"Edit success: {stats['edit_success']}")
    logger.info(f"Rewrite success: {stats['rewrite_success']}")
    logger.info(f"Average time per bug: {stats['average_time_per_bug']:.1f}s")
    logger.info(f"Total parallel time: {stats['total_parallel_time']:.1f}s")
    logger.info(
        f"Estimated sequential time: "
        f"{stats['estimated_sequential_time']:.1f}s"
    )
    logger.info(f"Speedup: {stats['speedup']:.2f}x")
    logger.info(f"Efficiency: {stats['efficiency']:.1%}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
