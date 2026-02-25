#!/usr/bin/env python3
"""Run parallel evaluation for gen batch results.

This script evaluates the gen batch results using parallel workers,
similar to the edit batch evaluation approach.
"""

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
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
        logging.FileHandler('gen_batch_evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GenBatchEvaluator:
    """Parallel evaluator for gen batch results."""
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        d4j_path: str,
        base_workspace: str,
        num_workers: int = 4,
        timeout: int = 300,
        bug_limit: int = None
    ):
        """Initialize GenBatchEvaluator.
        
        Args:
            input_dir: Directory containing gen batch results.
            output_dir: Directory for evaluation output.
            d4j_path: Path to Defects4J installation.
            base_workspace: Base directory for workspaces.
            num_workers: Number of parallel workers.
            timeout: Timeout for each bug evaluation in seconds.
            bug_limit: Maximum number of bugs to evaluate (None = all).
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.d4j_path = Path(d4j_path)
        self.base_workspace = Path(base_workspace)
        self.num_workers = num_workers
        self.timeout = timeout
        self.bug_limit = bug_limit
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Initialized GenBatchEvaluator with {num_workers} workers"
        )
        if bug_limit:
            logger.info(f"Bug limit: {bug_limit}")
    
    def get_all_bugs(self) -> List[str]:
        """Get list of all bugs to evaluate.
        
        Returns:
            List of bug slugs.
        """
        bugs = []
        for bug_dir in sorted(self.input_dir.iterdir()):
            if bug_dir.is_dir():
                bugs.append(bug_dir.name)
        
        # Apply bug limit if specified
        if self.bug_limit:
            bugs = bugs[:self.bug_limit]
        
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
    
    def evaluate_parallel(self) -> Dict[str, Any]:
        """Run parallel evaluation of all bugs.
        
        Returns:
            Dictionary with evaluation results and statistics.
        """
        bugs = self.get_all_bugs()
        total_bugs = len(bugs)
        
        results = {}
        completed = 0
        fixed_count = 0
        failed_count = 0
        
        start_time = time.time()
        
        logger.info(f"Starting parallel evaluation with {self.num_workers} workers")
        logger.info(f"Total bugs to evaluate: {total_bugs}")
        
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
                
                try:
                    result = future.result()
                    results[bug_slug] = result
                    
                    completed += 1
                    if result.successful_attempt:
                        fixed_count += 1
                    else:
                        failed_count += 1
                    
                    # Progress update
                    logger.info(
                        f"Progress: {completed}/{total_bugs} "
                        f"({completed/total_bugs*100:.1f}%) - "
                        f"Latest: {bug_slug}"
                    )
                    
                    # Report every 30 bugs
                    if completed % 30 == 0:
                        elapsed = time.time() - start_time
                        avg_time = elapsed / completed
                        remaining = (total_bugs - completed) * avg_time
                        success_rate = (fixed_count / completed * 100) if completed > 0 else 0
                        
                        logger.info("=" * 70)
                        logger.info(
                            f"📊 PROGRESS REPORT - {completed}/{total_bugs} bugs completed"
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
                            f"ETA: {remaining/60:.1f} min"
                        )
                        logger.info("=" * 70)
                
                except Exception as e:
                    logger.error(f"Error processing {bug_slug}: {e}")
                    completed += 1
                    failed_count += 1
        
        elapsed_time = time.time() - start_time
        
        # Final statistics
        logger.info("=" * 70)
        logger.info("EVALUATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total bugs: {total_bugs}")
        logger.info(f"Fixed bugs: {fixed_count}")
        logger.info(f"Failed bugs: {failed_count}")
        logger.info(f"Success rate: {fixed_count/total_bugs*100:.1f}%")
        
        # Count by modeling type
        edit_success = sum(
            1 for r in results.values()
            if r.successful_attempt and r.modeling_type == 'edit'
        )
        rewrite_success = sum(
            1 for r in results.values()
            if r.successful_attempt and r.modeling_type == 'rewrite'
        )
        
        logger.info(f"Edit success: {edit_success}")
        logger.info(f"Rewrite success: {rewrite_success}")
        logger.info(f"Average time per bug: {elapsed_time/total_bugs:.1f}s")
        logger.info(f"Total parallel time: {elapsed_time:.1f}s")
        
        # Calculate speedup
        total_sequential_time = sum(
            r.execution_time for r in results.values()
        )
        speedup = total_sequential_time / elapsed_time if elapsed_time > 0 else 0
        efficiency = speedup / self.num_workers * 100 if self.num_workers > 0 else 0
        
        logger.info(f"Estimated sequential time: {total_sequential_time:.1f}s")
        logger.info(f"Speedup: {speedup:.2f}x")
        logger.info(f"Efficiency: {efficiency:.1f}%")
        logger.info("=" * 70)
        
        # Save results
        output_data = {
            'total_bugs': total_bugs,
            'fixed_bugs': fixed_count,
            'failed_bugs': failed_count,
            'success_rate': fixed_count / total_bugs if total_bugs > 0 else 0,
            'edit_success': edit_success,
            'rewrite_success': rewrite_success,
            'elapsed_time': elapsed_time,
            'avg_time_per_bug': elapsed_time / total_bugs if total_bugs > 0 else 0,
            'speedup': speedup,
            'efficiency': efficiency,
            'results': {
                bug: {
                    'bug_slug': r.bug_slug,
                    'total_attempts': r.total_attempts,
                    'successful_attempt': r.successful_attempt,
                    'modeling_type': r.modeling_type,
                    'execution_time': r.execution_time,
                    'failure_reasons': r.failure_reasons
                }
                for bug, r in results.items()
            }
        }
        
        output_file = self.output_dir / 'gen_batch_evaluation_results.json'
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        
        return output_data


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run parallel evaluation for gen batch results"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing gen batch results"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: auto-generated)"
    )
    parser.add_argument(
        "--d4j-path",
        type=str,
        default="/Users/mengrui/Desktop/D4J/defects4j",
        help="Path to Defects4J installation"
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default="./parallel_workspace",
        help="Base workspace directory"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=100,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
        help="Timeout per bug in seconds"
    )
    parser.add_argument(
        "--bug-limit",
        type=int,
        default=None,
        help="Maximum number of bugs to evaluate (default: all)"
    )
    
    args = parser.parse_args()
    
    # Generate output directory name if not specified
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = f"evaluation_output/gen_batch_eval_{timestamp}"
    
    # Create evaluator
    evaluator = GenBatchEvaluator(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        d4j_path=args.d4j_path,
        base_workspace=args.workspace,
        num_workers=args.workers,
        timeout=args.timeout,
        bug_limit=args.bug_limit
    )
    
    # Run evaluation
    evaluator.evaluate_parallel()


if __name__ == "__main__":
    main()
