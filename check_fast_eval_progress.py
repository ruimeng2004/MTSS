#!/usr/bin/env python3
"""Check fast parallel evaluation progress."""

import json
import time
from pathlib import Path
from datetime import datetime

def main():
    """Display current evaluation progress."""
    # Find latest output directory
    output_dirs = sorted(Path("evaluation_output").glob("fast_gen_eval_*"))
    if not output_dirs:
        print("No evaluation output found")
        return
    
    latest_dir = output_dirs[-1]
    bug_results_dir = latest_dir / "bug_results"
    
    print("="*60)
    print("FAST PARALLEL GEN EVALUATION PROGRESS")
    print("="*60)
    print(f"Output: {latest_dir}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Count completed bugs
    if bug_results_dir.exists():
        result_files = list(bug_results_dir.glob("*.json"))
        completed = len(result_files)
        
        # Count successful vs failed
        successful = 0
        failed = 0
        for result_file in result_files:
            try:
                with open(result_file) as f:
                    data = json.load(f)
                    if data.get('success'):
                        successful += 1
                    else:
                        failed += 1
            except:
                pass
        
        print(f"Completed: {completed} / 698 ({completed/698*100:.1f}%)")
        print(f"Successful: {successful} ({successful/completed*100:.1f}% of completed)" if completed > 0 else "Successful: 0")
        print(f"Failed: {failed}")
        print()
        
        # Show recent completions
        if result_files:
            recent = sorted(result_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            print("Recent completions:")
            for rf in recent:
                try:
                    with open(rf) as f:
                        data = json.load(f)
                        status = "✓" if data.get('success') else "✗"
                        print(f"  {status} {data['bug_slug']}")
                except:
                    pass
    else:
        print("No results yet...")
    
    print("="*60)

if __name__ == "__main__":
    main()
