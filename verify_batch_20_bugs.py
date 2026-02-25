#!/usr/bin/env python3
"""Verify that we can correctly identify Chart_1 to Chart_20."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.input_handler import InputHandler

def main():
    """Verify bug list."""
    
    result_folder = Path("ppl/result/20260105_132306")
    input_handler = InputHandler(result_folder)
    
    # Get all bugs
    all_bugs = input_handler.list_bugs()
    
    print(f"Total bugs found: {len(all_bugs)}")
    
    # Filter for Chart bugs
    chart_bugs = [bug for bug in all_bugs if bug.startswith('Chart_')]
    chart_bugs = sorted(chart_bugs, key=lambda x: int(x.split('_')[1]))
    
    print(f"\nTotal Chart bugs: {len(chart_bugs)}")
    
    # Get first 20
    test_bugs = chart_bugs[:20]
    
    print(f"\nChart_1 to Chart_20 ({len(test_bugs)} bugs):")
    for i, bug in enumerate(test_bugs, 1):
        # Check how many attempts each bug has
        attempts = input_handler.list_attempts(bug)
        print(f"  {i:2d}. {bug:12s} - {len(attempts)} attempts")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
