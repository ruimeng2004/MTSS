#!/usr/bin/env python3
"""Test evaluation on a single bug to identify issues."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.utils.logging_config import setup_logging

def main():
    """Test evaluation on Chart_1."""
    setup_logging()
    
    print("=" * 60)
    print("Testing Evaluation on Chart_1")
    print("=" * 60)
    
    # Configuration
    config = {
        'evaluation_config': {
            'd4j_path': '/Users/mengrui/Desktop/D4J/defects4j',
            'workspace_dir': './test_workspace'
        },
        'timeout': 600
    }
    
    result_folder = Path("ppl/result/20260105_132306")
    output_dir = Path("evaluation_output/test_single")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create evaluator
    evaluator = D4JFixEvaluator(
        result_folder=result_folder,
        output_dir=output_dir,
        config=config
    )
    
    # Evaluate single bug
    try:
        print("\nEvaluating Chart_1...")
        result = evaluator.evaluate_bug("Chart_1")
        
        print("\n" + "=" * 60)
        print("Result")
        print("=" * 60)
        print(f"Bug: {result.bug_slug}")
        print(f"Total attempts: {result.total_attempts}")
        print(f"Successful attempt: {result.successful_attempt}")
        print(f"Modeling type: {result.modeling_type}")
        print(f"Execution time: {result.execution_time:.2f}s")
        
        if result.successful_attempt:
            print(f"\n✓ Bug fixed with attempt {result.successful_attempt}")
            if result.test_result:
                print(f"  Tests: {result.test_result.passed_tests}/{result.test_result.total_tests} passed")
        else:
            print(f"\n✗ Bug not fixed")
            print(f"Failure reasons:")
            for reason in result.failure_reasons:
                print(f"  - {reason}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
