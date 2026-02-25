#!/usr/bin/env python3
"""Ultra-fast parallel evaluation for Gen format.

Optimizations:
- 100 parallel workers (maximum parallelism)
- Reduced timeouts: 300s normal, 900s for Closure
- Early stopping on first success
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

sys.path.insert(0, str(Path(__file__).parent / "evaluation"))

from evaluation.core.evaluator import D4JFixEvaluator

# Aggressive configuration
NUM_WORKERS = 100
TIMEOUT_NORMAL = 300  # 5 minutes
TIMEOUT_CLOSURE = 900  # 15 minutes
INPUT_DIR = Path("ppl/result/20260106_030425")
D4J_PATH = "/Users/mengrui/Desktop/D4J/defects4j"

# Shared state
results_lock = Lock()
completed_bugs = []
failed_bugs = []
start_time = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultra_fast_gen_eval.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def evaluate_single_bug(bug_slug: str, worker_id: int, output_dir: Path) -> dict:
    """Evaluate a single bug in a worker thread.
    
    Args:
        bug_slug: Bug identifier.
        worker_id: Worker thread ID.
        output_dir: Output directory for results.
    
    Returns:
        Dictionary with evaluation result.
    """
    workspace_dir = Path(f"./parallel_workspace/worker_{worker_id}")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine timeout based on project
    timeout = TIMEOUT_CLOSURE if bug_slug.startswith('Closure') else TIMEOUT_NORMAL
    
    config = {
        'evaluation_config': {
            'd4j_path': D4J_PATH,
            'workspace_dir': str(workspace_dir),
            'timeout': timeout
        }
    }
    
    try:
        evaluator = D4JFixEvaluator(
            result_folder=INPUT_DIR,
            output_dir=output_dir,
            config=config
        )
        
        result = evaluator.evaluate_bug(bug_slug)
        
        return {
            'bug_slug': bug_slug,
            'success': result.is_fixed,
            'attempt': result.successful_attempt,
            'reason': result.failure_reason,
            'time': result.evaluation_time
        }
        
    except Exception as e:
        logger.error(f"Worker {worker_id} failed on {bug_slug}: {e}")
        return {
            'bug_slug': bug_slug,
            'success': False,
            'attempt': None,
            'reason': str(e),
            'time': 0
        }


def update_progress(bug_slug: str, success: bool):
    """Update shared progress tracking.
    
    Args:
        bug_slug: Bug identifier.
        success: Whether bug was fixed.
    """
    with results_lock:
        if success:
            completed_bugs.append(bug_slug)
        else:
            failed_bugs.append(bug_slug)
        
        total = len(completed_bugs) + len(failed_bugs)
        elapsed = time.time() - start_time
        rate = total / elapsed if elapsed > 0 else 0
        remaining = (698 - total) / rate if rate > 0 else 0
        
        if total % 10 == 0:  # Log every 10 bugs
            logger.info(
                f"Progress: {total}/698 "
                f"({len(completed_bugs)} fixed, {len(failed_bugs)} failed) "
                f"| Rate: {rate:.2f} bugs/s "
                f"| ETA: {remaining/60:.1f} min"
            )


def get_all_bug_slugs() -> list:
    """Get all bug slugs from input directory.
    
    Returns:
        List of bug slug strings.
    """
    bug_slugs = []
    for project_dir in INPUT_DIR.iterdir():
        if project_dir.is_dir() and not project_dir.name.startswith('.'):
            bug_slugs.append(project_dir.name)
    
    bug_slugs.sort()
    return bug_slugs


def main():
    """Run ultra-fast parallel evaluation."""
    global start_time
    
    if not INPUT_DIR.exists():
        logger.error(f"Input directory not found: {INPUT_DIR}")
        sys.exit(1)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"evaluation_output/ultra_fast_gen_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    bug_slugs = get_all_bug_slugs()
    total_bugs = len(bug_slugs)
    
    logger.info("="*60)
    logger.info("ULTRA-FAST PARALLEL GEN FORMAT EVALUATION")
    logger.info("="*60)
    logger.info(f"Input: {INPUT_DIR}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Total bugs: {total_bugs}")
    logger.info(f"Workers: {NUM_WORKERS}")
    logger.info(f"Timeout: {TIMEOUT_NORMAL}s normal, {TIMEOUT_CLOSURE}s Closure")
    logger.info(f"Target time: <60 minutes")
    logger.info("="*60)
    
    start_time = time.time()
    
    # Create worker pool and submit all tasks
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all bugs to workers
        future_to_bug = {}
        for i, bug_slug in enumerate(bug_slugs):
            worker_id = i % NUM_WORKERS
            future = executor.submit(
                evaluate_single_bug,
                bug_slug,
                worker_id,
                output_dir
            )
            future_to_bug[future] = bug_slug
        
        # Process results as they complete
        for future in as_completed(future_to_bug):
            bug_slug = future_to_bug[future]
            try:
                result = future.result()
                update_progress(result['bug_slug'], result['success'])
                
                # Save individual result
                result_file = output_dir / "bug_results" / f"{bug_slug}.json"
                result_file.parent.mkdir(parents=True, exist_ok=True)
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)
                    
            except Exception as e:
                logger.error(f"Error processing {bug_slug}: {e}")
                update_progress(bug_slug, False)
    
    # Calculate final statistics
    total_time = time.time() - start_time
    success_count = len(completed_bugs)
    fail_count = len(failed_bugs)
    success_rate = success_count / total_bugs * 100 if total_bugs > 0 else 0
    
    stats = {
        'total_bugs': total_bugs,
        'successful': success_count,
        'failed': fail_count,
        'success_rate': f"{success_rate:.1f}%",
        'total_time_seconds': total_time,
        'total_time_minutes': total_time / 60,
        'avg_time_per_bug': total_time / total_bugs if total_bugs > 0 else 0,
        'workers': NUM_WORKERS,
        'timeout_normal': TIMEOUT_NORMAL,
        'timeout_closure': TIMEOUT_CLOSURE,
        'completed_bugs': completed_bugs,
        'failed_bugs': failed_bugs
    }
    
    # Save statistics
    stats_file = output_dir / "statistics.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info("="*60)
    logger.info("EVALUATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total: {total_bugs}")
    logger.info(f"Successful: {success_count} ({success_rate:.1f}%)")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Time: {total_time/60:.1f} minutes")
    logger.info(f"Rate: {total_bugs/total_time:.2f} bugs/second")
    logger.info(f"Output: {output_dir}")
    logger.info("="*60)


if __name__ == "__main__":
    main()
