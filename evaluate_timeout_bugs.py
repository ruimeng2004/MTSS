#!/usr/bin/env python3
"""Re-evaluate bugs that were marked as timeout but actually checked out successfully."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_gen_batch_evaluation import GenBatchEvaluator


def get_timeout_bugs(log_file: str) -> list:
    """Extract bug slugs that timed out during checkout.
    
    Args:
        log_file: Path to evaluation log file.
        
    Returns:
        List of bug slugs that timed out.
    """
    timeout_bugs = []
    
    with open(log_file, 'r') as f:
        for line in f:
            if 'timed out after 5 minutes' in line or 'timed out after' in line:
                # Extract bug slug from error message
                parts = line.split('checkout ')
                if len(parts) > 1:
                    bug_slug = parts[1].split(':')[0].strip()
                    if bug_slug and bug_slug not in timeout_bugs:
                        timeout_bugs.append(bug_slug)
    
    return timeout_bugs


def verify_checkout_success(bug_slug: str, workspace: Path) -> bool:
    """Check if a bug was actually checked out successfully.
    
    Args:
        bug_slug: Bug identifier.
        workspace: Base workspace directory.
        
    Returns:
        True if checkout was successful (has Java files).
    """
    # Find the bug directory in any worker
    bug_dirs = list(workspace.glob(f"worker_*/{bug_slug}_b"))
    
    if not bug_dirs:
        return False
    
    bug_dir = bug_dirs[0]
    
    # Check if directory has Java files
    java_files = list(bug_dir.rglob("*.java"))
    return len(java_files) > 0


def main():
    """Main function."""
    log_file = "gen_batch_evaluation_output.log"
    workspace = Path("./parallel_workspace")
    
    print("=== 分析超时的bugs ===")
    print()
    
    # Get timeout bugs
    timeout_bugs = get_timeout_bugs(log_file)
    print(f"发现 {len(timeout_bugs)} 个超时的bugs")
    
    # Verify which ones actually succeeded
    actually_succeeded = []
    actually_failed = []
    
    for bug_slug in timeout_bugs:
        if verify_checkout_success(bug_slug, workspace):
            actually_succeeded.append(bug_slug)
        else:
            actually_failed.append(bug_slug)
    
    print(f"  - 实际checkout成功: {len(actually_succeeded)}")
    print(f"  - 实际checkout失败: {len(actually_failed)}")
    print()
    
    # Save list of bugs to re-evaluate
    bugs_to_evaluate = actually_succeeded
    
    output_file = "timeout_bugs_to_reevaluate.json"
    with open(output_file, 'w') as f:
        json.dump({
            'total': len(bugs_to_evaluate),
            'bugs': bugs_to_evaluate
        }, f, indent=2)
    
    print(f"需要重新评测的bugs列表已保存到: {output_file}")
    print()
    print("运行重新评测:")
    print(f"  python run_gen_batch_evaluation.py \\")
    print(f"    --input-dir /Users/mengrui/Desktop/MTSS/ppl/result/20260106_113852 \\")
    print(f"    --workers 20 \\")
    print(f"    --timeout 240 \\")
    print(f"    --bug-list {output_file}")


if __name__ == "__main__":
    main()
