#!/usr/bin/env python3
"""Test Chart_11 and Chart_12 only to verify the fix."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.utils.logging_config import setup_logging

def main():
    """Test Chart_11 and Chart_12."""
    setup_logging()
    
    print("=" * 70)
    print("Testing Chart_11 and Chart_12")
    print("=" * 70)
    
    # Configuration
    config = {
        'evaluation_config': {
            'd4j_path': '/Users/mengrui/Desktop/D4J/defects4j',
            'workspace_dir': './test_workspace'
        },
        'timeout': 600
    }
    
    result_folder = Path("ppl/result/20260105_132306")
    
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"evaluation_output/chart11_12_test_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # Create evaluator
    evaluator = D4JFixEvaluator(
        result_folder=result_folder,
        output_dir=output_dir,
        config=config
    )
    
    # Test only Chart_11 and Chart_12
    test_bugs = ['Chart_11', 'Chart_12']
    
    print(f"\nTesting {len(test_bugs)} bugs:")
    for i, bug in enumerate(test_bugs, 1):
        print(f"  {i}. {bug}")
    
    print(f"\nStarting evaluation...")
    print("-" * 70)
    
    # Run evaluation
    try:
        batch_result = evaluator.evaluate(
            parallel=1,
            verbose=True,
            bug_filter=test_bugs
        )
        
        print("\n" + "=" * 70)
        print("Evaluation Complete!")
        print("=" * 70)
        print(f"\nResults:")
        print(f"  Total bugs: {batch_result.total_bugs}")
        print(f"  Fixed bugs: {batch_result.fixed_bugs}")
        print(f"  Failed bugs: {batch_result.failed_bugs}")
        print(f"  Fix rate: {batch_result.fix_rate:.2f}%")
        
        # Show results
        for bug_result in batch_result.bug_results:
            if bug_result.successful_attempt:
                print(f"\n✓ {bug_result.bug_slug}: Fixed (attempt {bug_result.successful_attempt})")
            else:
                print(f"\n✗ {bug_result.bug_slug}: Failed")
                if bug_result.failure_reasons:
                    for reason in bug_result.failure_reasons[:3]:
                        print(f"    - {reason}")
        
        print(f"\nDetailed results saved to: {output_dir}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
