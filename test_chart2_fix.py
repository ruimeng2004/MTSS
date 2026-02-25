#!/usr/bin/env python3
"""Test that Chart_2 now properly reports SEARCH block not found error."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import Evaluator

def main():
    """Test Chart_2 evaluation with improved error handling."""
    
    config = {
        'input_dir': 'ppl/result/20260105_132306',
        'output_dir': 'evaluation_output/chart2_test',
        'd4j_path': '/Users/mengrui/Desktop/D4J/defects4j',
        'workspace_dir': './test_workspace',
        'timeout': 600
    }
    
    evaluator = Evaluator(config)
    
    print("Testing Chart_2 evaluation...")
    print("=" * 80)
    
    result = evaluator.evaluate_bug("Chart_2", verbose=True)
    
    print("\n" + "=" * 80)
    print("RESULT:")
    print(f"  Bug: {result.bug_slug}")
    print(f"  Total attempts: {result.total_attempts}")
    print(f"  Successful attempt: {result.successful_attempt}")
    print(f"  Failure reasons:")
    for reason in result.failure_reasons:
        print(f"    - {reason}")
    
    # Check that we get proper error messages
    search_not_found_count = sum(
        1 for reason in result.failure_reasons
        if "No SEARCH blocks found" in reason
    )
    
    print(f"\n  Attempts with 'SEARCH not found' error: {search_not_found_count}")
    
    if search_not_found_count > 0:
        print("\n✓ SUCCESS: System properly reports SEARCH block mismatch")
    else:
        print("\n✗ ISSUE: Expected 'SEARCH not found' errors but got other errors")

if __name__ == "__main__":
    main()
