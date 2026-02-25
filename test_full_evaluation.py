#!/usr/bin/env python3
"""Test evaluation on all bugs in the result folder."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.utils.logging_config import setup_logging

def main():
    """Test evaluation on all bugs."""
    setup_logging()
    
    print("=" * 70)
    print("Full Evaluation: Testing All Bugs")
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
    output_dir = Path(f"evaluation_output/full_evaluation_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # Create evaluator
    evaluator = D4JFixEvaluator(
        result_folder=result_folder,
        output_dir=output_dir,
        config=config
    )
    
    # Get all bugs (no filtering)
    all_bugs = evaluator.input_handler.list_bugs()
    
    print(f"\nTesting {len(all_bugs)} bugs from all projects")
    
    # Show bug distribution by project
    from collections import Counter
    projects = Counter([bug.split('_')[0] for bug in all_bugs])
    print(f"\nBug distribution by project:")
    for project, count in sorted(projects.items()):
        print(f"  {project}: {count} bugs")
    
    print(f"\nStarting evaluation...")
    print(f"Output directory: {output_dir}")
    print(f"This will take a long time (estimated: {len(all_bugs) * 2} minutes)")
    print("-" * 70)
    
    # Run evaluation
    try:
        batch_result = evaluator.evaluate(
            parallel=1,
            verbose=True
            # No bug_filter - test all bugs
        )
        
        print("\n" + "=" * 70)
        print("Evaluation Complete!")
        print("=" * 70)
        print(f"\nResults:")
        print(f"  Total bugs: {batch_result.total_bugs}")
        print(f"  Fixed bugs: {batch_result.fixed_bugs}")
        print(f"  Failed bugs: {batch_result.failed_bugs}")
        print(f"  Fix rate: {batch_result.fix_rate:.2f}%")
        
        # Show fixed bugs
        if batch_result.fixed_bugs > 0:
            print(f"\n✓ Successfully fixed bugs:")
            for bug_result in batch_result.bug_results:
                if bug_result.successful_attempt:
                    print(f"  - {bug_result.bug_slug} (attempt {bug_result.successful_attempt}, {bug_result.modeling_type})")
        
        # Show failed bugs (first 10)
        failed_bugs = [br for br in batch_result.bug_results if not br.successful_attempt]
        if failed_bugs:
            print(f"\n✗ Failed bugs (showing first 10):")
            for bug_result in failed_bugs[:10]:
                print(f"  - {bug_result.bug_slug}")
                if bug_result.failure_reasons:
                    reason = bug_result.failure_reasons[0]
                    if len(reason) > 100:
                        print(f"    Reason: {reason[:100]}...")
                    else:
                        print(f"    Reason: {reason}")
        
        print(f"\nDetailed results saved to: {output_dir}")
        print(f"  - batch_evaluation.json")
        print(f"  - statistics.json")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
