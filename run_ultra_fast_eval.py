#!/usr/bin/env python
"""Ultra-fast evaluation with aggressive optimizations for 2-hour target."""

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultra_fast_evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UltraFastEvaluator:
    """Ultra-fast evaluator optimized for 2-hour completion."""
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        d4j_path: str,
        base_workspace: str,
        num_workers: int = 200,
        timeout: int = 60,
        early_stop_after: int = 3
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.d4j_path = Path(d4j_path)
        self.base_workspace = Path(base_workspace)
        self.num_workers = num_workers
        self.timeout = timeout
        self.early_stop_after = early_stop_after
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Initialized UltraFastEvaluator with {num_workers} workers"
        )
        logger.info(
            f"Timeout: {timeout}s, Early stop after: {early_stop_after} attempts"
        )
    
    def get_all_bugs(self) -> List[str]:
        """Get list of all bugs to evaluate."""
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
        """Evaluate a single bug with aggressive optimizations."""
        workspace_dir = self.base_workspace / f"worker_{worker_id}"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        config = {
            'evaluation_config': {
                'd4j_path': str(self.d4j_path),
                'workspace_dir': str(workspace_dir),
                'timeout': self.timeout
            }
        }
        
        evaluator = D4JFixEvaluator(
            result_folder=self.input_dir,
            output_dir=self.output_dir,
            config=config
        )
        
        try:
            start_time = time.time()
            
            # Check if deprecated
            if evaluator.env_manager.is_deprecated(bug_slug):
                logger.info(f"[Worker {worker_id}] Skipping deprecated: {bug_slug}")
                return BugEvaluationResult(
                    bug_slug=bug_slug,
                    total_attempts=0,
                    successful_attempt=None,
                    modeling_type=None,
                    test_result=None,
                    failure_reasons=["Deprecated"],
                    execution_time=0.0
                )
            
            # Checkout
            try:
                repo_path = evaluator.env_manager.checkout_bug(bug_slug)
            except Exception as e:
                logger.warning(f"[Worker {worker_id}] Checkout failed: {bug_slug}")
                return BugEvaluationResult(
                    bug_slug=bug_slug,
                    total_attempts=0,
                    successful_attempt=None,
                    modeling_type=None,
                    test_result=None,
                    failure_reasons=[f"Checkout failed: {str(e)}"],
                    execution_time=time.time() - start_time
                )
            
            try:
                # Get attempts
                attempts = evaluator.input_handler.list_attempts(bug_slug)
                
                # Early stopping: only try first N attempts
                attempts_to_try = attempts[:self.early_stop_after]
                
                failure_count = 0
                for attempt_num in attempts_to_try:
                    result = evaluator._try_fix(bug_slug, attempt_num, repo_path)
                    
                    if result.success:
                        elapsed = time.time() - start_time
                        logger.info(
                            f"[Worker {worker_id}] ✓ {bug_slug} fixed "
                            f"(attempt {attempt_num}, {elapsed:.1f}s)"
                        )
                        
                        return BugEvaluationResult(
                            bug_slug=bug_slug,
                            total_attempts=len(attempts),
                            successful_attempt=attempt_num,
                            modeling_type=result.modeling_type,
                            test_result=result.test_result,
                            failure_reasons=[],
                            execution_time=elapsed
                        )
                    else:
                        failure_count += 1
                        # Early stop if first 2 attempts fail
                        if failure_count >= 2:
                            logger.info(
                                f"[Worker {worker_id}] Early stopping {bug_slug} "
                                f"after {failure_count} failures"
                            )
                            break
                
                # All attempts failed
                elapsed = time.time() - start_time
                logger.info(
                    f"[Worker {worker_id}] ✗ {bug_slug} failed "
                    f"(tried {failure_count} attempts, {elapsed:.1f}s)"
                )
                
                return BugEvaluationResult(
                    bug_slug=bug_slug,
                    total_attempts=len(attempts),
                    successful_attempt=None,
                    modeling_type=None,
                    test_result=None,
                    failure_reasons=[f"Failed after {failure_count} attempts"],
                    execution_time=elapsed
                )
                
            finally:
                try:
                    evaluator.env_manager.cleanup(repo_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(
                f"[Worker {worker_id}] Error evaluating {bug_slug}: {e}"
            )
            return BugEvaluationResult(
                bug_slug=bug_slug,
                total_attempts=0,
                successful_attempt=None,
                modeling_type=None,
                test_result=None,
                failure_reasons=[f"Error: {str(e)}"],
                execution_time=0.0
            )
    
    def run_parallel_evaluation(
        self,
        bugs: List[str] = None,
        max_bugs: int = None
    ) -> Dict[str, Any]:
        """Run ultra-fast parallel evaluation."""
        start_time = time.time()
        
        if bugs is None:
            bugs = self.get_all_bugs()
        
        if max_bugs:
            bugs = bugs[:max_bugs]
        
        total_bugs = len(bugs)
        logger.info(f"Starting ultra-fast evaluation of {total_bugs} bugs")
        logger.info(f"Using {self.num_workers} workers")
        logger.info(f"Target: 2 hours ({total_bugs/120:.1f} bugs/min needed)")
        
        results = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_bug = {}
            for i, bug_slug in enumerate(bugs):
                worker_id = i % self.num_workers
                future = executor.submit(
                    self.evaluate_bug_worker,
                    bug_slug,
                    worker_id
                )
                future_to_bug[future] = bug_slug
            
            for future in as_completed(future_to_bug):
                bug_slug = future_to_bug[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    progress = (completed / total_bugs) * 100
                    elapsed = time.time() - start_time
                    rate = completed / (elapsed / 60) if elapsed > 0 else 0
                    eta_min = (total_bugs - completed) / rate if rate > 0 else 0
                    
                    logger.info(
                        f"Progress: {completed}/{total_bugs} ({progress:.1f}%) "
                        f"- Rate: {rate:.1f} bugs/min - ETA: {eta_min:.0f}min "
                        f"- Latest: {bug_slug}"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to get result for {bug_slug}: {e}")
        
        elapsed_time = time.time() - start_time
        stats = self._calculate_statistics(results, elapsed_time)
        
        output_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'input_batch': str(self.input_dir),
            'total_bugs': total_bugs,
            'num_workers': self.num_workers,
            'timeout': self.timeout,
            'early_stop_after': self.early_stop_after,
            'statistics': stats,
            'bug_results': [self._result_to_dict(r) for r in results]
        }
        
        output_file = self.output_dir / 'ultra_fast_results.json'
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        
        return output_data
    
    def _calculate_statistics(
        self,
        results: List[BugEvaluationResult],
        total_time: float
    ) -> Dict[str, Any]:
        """Calculate statistics."""
        total_bugs = len(results)
        fixed_bugs = sum(1 for r in results if r.successful_attempt)
        
        return {
            'total_bugs': total_bugs,
            'fixed_bugs': fixed_bugs,
            'failed_bugs': total_bugs - fixed_bugs,
            'success_rate': fixed_bugs / total_bugs if total_bugs > 0 else 0,
            'total_time_hours': total_time / 3600,
            'bugs_per_minute': total_bugs / (total_time / 60) if total_time > 0 else 0
        }
    
    def _result_to_dict(self, result: BugEvaluationResult) -> Dict[str, Any]:
        """Convert result to dict."""
        return {
            'bug_slug': result.bug_slug,
            'successful_attempt': result.successful_attempt,
            'modeling_type': result.modeling_type,
            'execution_time': result.execution_time
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ultra-fast evaluation (2-hour target)'
    )
    parser.add_argument('--input-dir', default='ppl/result/20260106_113852')
    parser.add_argument('--output-dir', default=None)
    parser.add_argument('--d4j-path', default='/Users/mengrui/Desktop/D4J/defects4j')
    parser.add_argument('--workspace', default='./parallel_workspace')
    parser.add_argument('--workers', type=int, default=200)
    parser.add_argument('--timeout', type=int, default=240)
    parser.add_argument('--early-stop', type=int, default=3)
    
    args = parser.parse_args()
    
    if args.output_dir is None:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        args.output_dir = f'evaluation_output/ultra_fast_{timestamp}'
    
    evaluator = UltraFastEvaluator(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        d4j_path=args.d4j_path,
        base_workspace=args.workspace,
        num_workers=args.workers,
        timeout=args.timeout,
        early_stop_after=args.early_stop
    )
    
    logger.info("=" * 80)
    logger.info("ULTRA-FAST EVALUATION (2-HOUR TARGET)")
    logger.info("=" * 80)
    
    results = evaluator.run_parallel_evaluation()
    
    stats = results['statistics']
    logger.info("\n" + "=" * 80)
    logger.info("EVALUATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total bugs: {stats['total_bugs']}")
    logger.info(f"Fixed bugs: {stats['fixed_bugs']}")
    logger.info(f"Success rate: {stats['success_rate']:.1%}")
    logger.info(f"Total time: {stats['total_time_hours']:.2f} hours")
    logger.info(f"Speed: {stats['bugs_per_minute']:.1f} bugs/min")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
