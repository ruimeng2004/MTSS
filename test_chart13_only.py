#!/usr/bin/env python3
"""Test Chart_13 end-to-end."""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import D4JFixEvaluator

def main():
    """Test Chart_13."""
    
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f'./evaluation_output/chart13_test_{timestamp}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configuration
    config = {
        'evaluation_config': {
            'd4j_path': '/Users/mengrui/Desktop/D4J/defects4j',
            'workspace_dir': './test_workspace'
        },
        'timeout': 600
    }
    
    result_folder = Path("ppl/result/20260105_132306")
    
    print(f"Evaluating Chart_13...")
    print(f"Output directory: {output_dir}\n")
    
    evaluator = D4JFixEvaluator(
        result_folder=result_folder,
        output_dir=output_dir,
        config=config
    )
    
    # Evaluate just Chart_13
    batch_result = evaluator.evaluate(
        parallel=1,
        verbose=True,
        bug_filter=['Chart_13']
    )
    
    print(f"\nResult:")
    print(f"  Total bugs: {batch_result.total_bugs}")
    print(f"  Fixed bugs: {batch_result.fixed_bugs}")
    print(f"  Failed bugs: {batch_result.failed_bugs}")
    print(f"  Fix rate: {batch_result.fix_rate:.2f}%")
    
    if batch_result.fixed_bugs > 0:
        print(f"\n✓ Successfully fixed!")
        for bug_result in batch_result.bug_results:
            if bug_result.successful_attempt:
                print(f"  Attempt: {bug_result.successful_attempt}")
                print(f"  Type: {bug_result.modeling_type}")
    else:
        print(f"\n✗ Fix failed")
        for bug_result in batch_result.bug_results:
            if bug_result.failure_reasons:
                print(f"  Reasons: {bug_result.failure_reasons[:3]}")
    
    print(f"\nResults saved to: {output_dir}")
    
    return 0 if batch_result.fixed_bugs > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
