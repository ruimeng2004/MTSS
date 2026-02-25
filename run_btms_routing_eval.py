#!/usr/bin/env python3
"""Run evaluation with BTMS routing decisions.

This script uses the cluster_choices.json from BTMS budget allocation
to route bugs to the appropriate modeling type (edit/gen).
"""

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import random

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.core.data_structures import BugEvaluationResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BTMSRoutingEvaluator:
    """Evaluator using BTMS routing decisions."""
    
    def __init__(
        self,
        cluster_choices_path: str,
        assignments_path: str,
        edit_results_dir: str,
        gen_results_dir: str,
        output_dir: str,
        d4j_path: str,
        base_workspace: str,
        num_workers: int = 32,
        timeout: int = 300,
        force_strategy: Optional[str] = None
    ):
        """Initialize BTMSRoutingEvaluator.
        
        Args:
            cluster_choices_path: Path to cluster_choices.json from BTMS.
            assignments_path: Path to cluster assignments.
            edit_results_dir: Directory containing edit mode results.
            gen_results_dir: Directory containing gen mode results.
            output_dir: Directory for evaluation output.
            d4j_path: Path to Defects4J installation.
            base_workspace: Base directory for workspaces.
            num_workers: Number of parallel workers.
            timeout: Timeout for each bug evaluation in seconds.
            force_strategy: Optional strategy to force ('pure-edit', 'pure-gen', 'random-50-50').
        """
        self.cluster_choices_path = Path(cluster_choices_path)
        self.assignments_path = Path(assignments_path)
        self.edit_results_dir = Path(edit_results_dir)
        self.gen_results_dir = Path(gen_results_dir)
        self.output_dir = Path(output_dir)
        self.d4j_path = Path(d4j_path)
        self.base_workspace = Path(base_workspace)
        self.num_workers = num_workers
        self.timeout = timeout
        self.force_strategy = force_strategy
        
        # Load routing decisions
        self.routing = self._load_routing_decisions()

        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Initialized BTMSRoutingEvaluator with {num_workers} workers"
        )
        logger.info(f"Total bugs with routing: {len(self.routing)}")
    
    def _load_routing_decisions(self) -> Dict[str, Dict[str, Any]]:
        """Load and process routing decisions from cluster choices.
        
        Returns:
            Dictionary mapping bug_slug to routing decision.
        """
        # Load cluster choices
        with open(self.cluster_choices_path, 'r') as f:
            cluster_choices = json.load(f)
        
        # Load assignments
        with open(self.assignments_path, 'r') as f:
            assignments = [json.loads(line) for line in f]
        
        # Create bug-level routing decisions
        routing = {}
        
        # Set random seed for reproducibility (for both forced and mixed strategies)
        random.seed(42)
        logger.info("Set random seed to 42 for reproducible probabilistic routing")
        
        # Log if using forced strategy
        if self.force_strategy == 'random-50-50':
            logger.info("Using forced random 50-50 strategy")
        
        for item in assignments:
            # Support both 'slug' and 'item_id' formats
            slug = item.get('slug')
            if not slug:
                item_id = item.get('item_id', '')
                # Extract bug slug from item_id (e.g., "Chart_1__buggy_code" -> "Chart_1")
                slug = item_id.split('__')[0] if item_id else None
            
            cluster_id = str(item.get('cluster_id'))
            
            # Skip if no slug
            if not slug:
                continue
            
            if self.force_strategy:
                # Bypass cluster logic and force strategy
                if self.force_strategy == 'pure-edit':
                    modeling_type = 'edit'
                    decision = 'force-edit'
                elif self.force_strategy == 'pure-gen':
                    modeling_type = 'gen'
                    decision = 'force-gen'
                elif self.force_strategy == 'random-50-50':
                    modeling_type = random.choice(['edit', 'gen'])
                    decision = 'force-random'
                else:
                    logger.warning(f"Unknown force strategy: {self.force_strategy}, defaulting to edit")
                    modeling_type = 'edit'
                    decision = 'force-unknown'
                    
                routing[slug] = {
                    'slug': slug,
                    'cluster_id': int(cluster_id) if cluster_id else -1,
                    'decision': decision,
                    'ratio': {'edit': 1.0 if modeling_type == 'edit' else 0.0, 
                              'gen': 1.0 if modeling_type == 'gen' else 0.0},
                    'modeling_type': modeling_type,
                    'confidence': 1.0
                }
                continue
            
            if cluster_id in cluster_choices:
                choice = cluster_choices[cluster_id]
                decision = choice.get('decision')
                ratio = choice.get('ratio', {})
                
                # Determine modeling type based on decision
                if decision == 'edit':
                    modeling_type = 'edit'
                elif decision == 'gen':
                    modeling_type = 'gen'
                elif decision == 'mixed':
                    # For mixed, use ratio for probabilistic selection
                    edit_ratio = ratio.get('edit', 0.5)
                    random_val = random.random()
                    modeling_type = 'edit' if random_val < edit_ratio else 'gen'
                else:
                    # Default to edit
                    modeling_type = 'edit'
                
                routing[slug] = {
                    'slug': slug,
                    'cluster_id': int(cluster_id),
                    'decision': decision,
                    'ratio': ratio,
                    'modeling_type': modeling_type,
                    'confidence': choice.get('confidence', 0.0)
                }
        
        logger.info(f"Loaded routing for {len(routing)} bugs")
        
        # Log routing distribution
        modeling_counts = {}
        for r in routing.values():
            mt = r['modeling_type']
            modeling_counts[mt] = modeling_counts.get(mt, 0) + 1
        
        logger.info("Routing distribution:")
        for mt, count in sorted(modeling_counts.items()):
            logger.info(f"  {mt}: {count} ({count/len(routing)*100:.1f}%)")
        
        return routing
    
    def get_result_dir_for_bug(self, bug_slug: str) -> Path:
        """Get the result directory for a bug based on routing.
        
        Args:
            bug_slug: Bug identifier.
            
        Returns:
            Path to the result directory.
        """
        if bug_slug not in self.routing:
            # Default to edit if no routing decision
            logger.warning(f"No routing for {bug_slug}, defaulting to edit")
            return self.edit_results_dir / bug_slug
        
        modeling_type = self.routing[bug_slug]['modeling_type']
        
        if modeling_type == 'edit':
            return self.edit_results_dir / bug_slug
        else:
            return self.gen_results_dir / bug_slug
    
    def get_all_bugs(self) -> List[str]:
        """Get list of all bugs to evaluate.
        
        Returns:
            List of bug slugs.
        """
        return sorted(self.routing.keys())
    
    def evaluate_bug_worker(
        self,
        bug_slug: str,
        worker_id: int
    ) -> Dict[str, Any]:
        """Evaluate a single bug in a worker thread.
        
        Args:
            bug_slug: Bug identifier.
            worker_id: Worker ID for logging.
            
        Returns:
            Evaluation result dictionary.
        """
        start_time = time.time()
        
        try:
            # Determine which result directory to use based on routing
            if bug_slug not in self.routing:
                logger.warning(f"[Worker {worker_id}] No routing for {bug_slug}")
                modeling_type = 'edit'  # Default
            else:
                modeling_type = self.routing[bug_slug]['modeling_type']
            
            # Select the appropriate result directory
            if modeling_type == 'edit':
                result_base_dir = self.edit_results_dir
            else:
                result_base_dir = self.gen_results_dir
            
            # Create worker-specific workspace
            worker_workspace = self.base_workspace / f'worker_{worker_id}'
            worker_workspace.mkdir(parents=True, exist_ok=True)
            
            # Create config for this worker
            config = {
                'evaluation_config': {
                    'd4j_path': str(self.d4j_path),
                    'workspace_dir': str(worker_workspace),
                    'timeout': self.timeout
                }
            }
            
            # Create evaluator for this bug
            # Pass the entire result base directory, evaluator will find bug subdirectory
            evaluator = D4JFixEvaluator(
                result_folder=result_base_dir,
                output_dir=self.output_dir / f'temp_{bug_slug}',
                config=config
            )
            
            # Evaluate the bug
            result = evaluator.evaluate_bug(bug_slug)
            
            execution_time = time.time() - start_time
            
            # Convert to dict
            result_dict = {
                'bug_slug': bug_slug,
                'total_attempts': result.total_attempts,
                'successful_attempt': result.successful_attempt,
                'modeling_type': self.routing.get(bug_slug, {}).get('modeling_type'),
                'execution_time': execution_time,
                'failure_reasons': result.failure_reasons,
                'cluster_id': self.routing.get(bug_slug, {}).get('cluster_id'),
                'decision': self.routing.get(bug_slug, {}).get('decision'),
                'confidence': self.routing.get(bug_slug, {}).get('confidence')
            }
            
            logger.info(
                f"[Worker {worker_id}] {bug_slug}: "
                f"{'✓' if result.successful_attempt else '✗'} "
                f"({execution_time:.1f}s)"
            )
            
            return result_dict
            
        except Exception as e:
            logger.error(
                f"[Worker {worker_id}] Error evaluating {bug_slug}: {e}",
                exc_info=True
            )
            return {
                'bug_slug': bug_slug,
                'total_attempts': 0,
                'successful_attempt': None,
                'modeling_type': self.routing.get(bug_slug, {}).get('modeling_type'),
                'execution_time': time.time() - start_time,
                'failure_reasons': [str(e)]
            }
    
    def run(self) -> Dict[str, Any]:
        """Run parallel evaluation with BTMS routing.
        
        Returns:
            Batch evaluation results.
        """
        start_time = time.time()
        bugs = self.get_all_bugs()
        
        logger.info(f"Starting evaluation of {len(bugs)} bugs")
        logger.info(f"Using {self.num_workers} parallel workers")
        
        # Run parallel evaluation
        results = []
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_bug = {
                executor.submit(
                    self.evaluate_bug_worker,
                    bug_slug,
                    worker_id % self.num_workers
                ): bug_slug
                for worker_id, bug_slug in enumerate(bugs)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_bug):
                bug_slug = future_to_bug[future]
                try:
                    result = future.result(timeout=self.timeout + 60)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to get result for {bug_slug}: {e}")
                    results.append({
                        'bug_slug': bug_slug,
                        'total_attempts': 0,
                        'successful_attempt': None,
                        'modeling_type': None,
                        'execution_time': 0.0,
                        'failure_reasons': [str(e)]
                    })
        
        # Calculate statistics
        total_bugs = len(results)
        fixed_bugs = sum(1 for r in results if r['successful_attempt'] is not None)
        failed_bugs = total_bugs - fixed_bugs
        success_rate = fixed_bugs / total_bugs if total_bugs > 0 else 0.0
        
        # Count by modeling type
        edit_success = sum(
            1 for r in results 
            if r['successful_attempt'] is not None and r['modeling_type'] == 'edit'
        )
        gen_success = sum(
            1 for r in results 
            if r['successful_attempt'] is not None and r['modeling_type'] == 'gen'
        )
        
        total_time = time.time() - start_time
        avg_time = total_time / total_bugs if total_bugs > 0 else 0.0
        
        # Compile batch result
        batch_result = {
            'timestamp': datetime.now().isoformat(),
            'cluster_choices': str(self.cluster_choices_path),
            'total_bugs': total_bugs,
            'fixed_bugs': fixed_bugs,
            'failed_bugs': failed_bugs,
            'success_rate': success_rate,
            'edit_success': edit_success,
            'gen_success': gen_success,
            'total_time': total_time,
            'average_time_per_bug': avg_time,
            'num_workers': self.num_workers,
            'bug_results': results
        }
        
        # Save results
        output_file = self.output_dir / 'btms_routing_results.json'
        with open(output_file, 'w') as f:
            json.dump(batch_result, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BTMS Routing Evaluation Results")
        logger.info(f"{'='*60}")
        logger.info(f"Total bugs:     {total_bugs}")
        logger.info(f"Fixed bugs:     {fixed_bugs}")
        logger.info(f"Failed bugs:    {failed_bugs}")
        logger.info(f"Success rate:   {success_rate*100:.2f}%")
        logger.info(f"Edit success:   {edit_success}")
        logger.info(f"Gen success:    {gen_success}")
        logger.info(f"Total time:     {total_time:.2f}s")
        logger.info(f"Avg time/bug:   {avg_time:.2f}s")
        logger.info(f"\nResults saved to: {output_file}")
        logger.info(f"{'='*60}\n")
        
        return batch_result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run evaluation with BTMS routing decisions'
    )
    parser.add_argument(
        '--cluster-choices',
        type=str,
        required=True,
        help='Path to cluster_choices.json from BTMS experiment'
    )
    parser.add_argument(
        '--assignments',
        type=str,
        required=True,
        help='Path to cluster assignments file'
    )
    parser.add_argument(
        '--edit-results',
        type=str,
        required=True,
        help='Directory containing edit mode results'
    )
    parser.add_argument(
        '--gen-results',
        type=str,
        required=True,
        help='Directory containing gen mode results'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output directory for evaluation results'
    )
    parser.add_argument(
        '--d4j-path',
        type=str,
        default='/home/base/mengrui/defects4j',
        help='Path to Defects4J installation'
    )
    parser.add_argument(
        '--workspace',
        type=str,
        default='btms_routing_workspace',
        help='Base directory for workspaces'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=32,
        help='Number of parallel workers'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Timeout per bug in seconds'
    )
    parser.add_argument(
        '--force-strategy',
        type=str,
        default=None,
        choices=['pure-edit', 'pure-gen', 'random-50-50'],
        help='Force a specific routing strategy (overrides cluster choices)'
    )
    
    args = parser.parse_args()
    
    evaluator = BTMSRoutingEvaluator(
        cluster_choices_path=args.cluster_choices,
        assignments_path=args.assignments,
        edit_results_dir=args.edit_results,
        gen_results_dir=args.gen_results,
        output_dir=args.output,
        d4j_path=args.d4j_path,
        base_workspace=args.workspace,
        num_workers=args.workers,
        timeout=args.timeout,
        force_strategy=args.force_strategy
    )
    
    evaluator.run()


if __name__ == '__main__':
    main()



if __name__ == '__main__':
    sys.exit(main())
