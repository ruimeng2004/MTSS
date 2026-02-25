#!/usr/bin/env python3
"""Analyze timeout bugs to determine if they actually checked out successfully."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def extract_timeout_bugs(log_file: str) -> List[str]:
    """Extract bug slugs that timed out during checkout.
    
    Args:
        log_file: Path to evaluation log file.
        
    Returns:
        List of bug slugs that timed out.
    """
    timeout_bugs = []
    
    with open(log_file, 'r') as f:
        for line in f:
            if 'timed out' in line and 'Checkout of' in line:
                # Extract bug slug from error message
                # Format: "Failed to checkout Bug_X: Checkout of Bug_X timed out..."
                parts = line.split('Checkout of ')
                if len(parts) > 1:
                    bug_slug = parts[1].split(' timed out')[0].strip()
                    if bug_slug and bug_slug not in timeout_bugs:
                        timeout_bugs.append(bug_slug)
    
    return timeout_bugs


def verify_checkout_success(bug_slug: str, workspace: Path) -> Tuple[bool, int]:
    """Check if a bug was actually checked out successfully.
    
    Args:
        bug_slug: Bug identifier.
        workspace: Base workspace directory.
        
    Returns:
        Tuple of (success: bool, java_file_count: int).
    """
    # Find the bug directory in any worker
    bug_dirs = list(workspace.glob(f"worker_*/{bug_slug}_b"))
    
    if not bug_dirs:
        return False, 0
    
    bug_dir = bug_dirs[0]
    
    # Check if directory has Java files
    java_files = list(bug_dir.rglob("*.java"))
    return len(java_files) > 0, len(java_files)


def analyze_timeout_bugs(log_file: str, workspace: Path) -> Dict:
    """Analyze all timeout bugs.
    
    Args:
        log_file: Path to evaluation log file.
        workspace: Base workspace directory.
        
    Returns:
        Dictionary with analysis results.
    """
    print("=" * 70)
    print("Timeout Bugs Analysis")
    print("=" * 70)
    print()
    
    # Get timeout bugs
    timeout_bugs = extract_timeout_bugs(log_file)
    print(f"Found {len(timeout_bugs)} bugs marked as timeout")
    print()
    
    # Verify which ones actually succeeded
    actually_succeeded = []
    actually_failed = []
    
    for bug_slug in timeout_bugs:
        success, java_count = verify_checkout_success(bug_slug, workspace)
        if success:
            actually_succeeded.append({
                'bug_slug': bug_slug,
                'java_files': java_count
            })
        else:
            actually_failed.append(bug_slug)
    
    # Print results
    print(f"✓ Actually checked out successfully: {len(actually_succeeded)}")
    print(f"✗ Actually failed to checkout: {len(actually_failed)}")
    print()
    
    # Show breakdown by project
    if actually_succeeded:
        print("Successfully checked out bugs by project:")
        project_counts = {}
        for bug in actually_succeeded:
            project = bug['bug_slug'].split('_')[0]
            project_counts[project] = project_counts.get(project, 0) + 1
        
        for project, count in sorted(project_counts.items()):
            print(f"  {project}: {count}")
        print()
    
    if actually_failed:
        print("Actually failed bugs:")
        for bug_slug in actually_failed:
            print(f"  - {bug_slug}")
        print()
    
    # Calculate statistics
    success_rate = len(actually_succeeded) / len(timeout_bugs) * 100 if timeout_bugs else 0
    
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print(f"Total timeout bugs: {len(timeout_bugs)}")
    print(f"False positives (actually succeeded): {len(actually_succeeded)} ({success_rate:.1f}%)")
    print(f"True failures: {len(actually_failed)}")
    print()
    
    # Save results
    results = {
        'total_timeout': len(timeout_bugs),
        'actually_succeeded': len(actually_succeeded),
        'actually_failed': len(actually_failed),
        'success_rate': success_rate,
        'succeeded_bugs': actually_succeeded,
        'failed_bugs': actually_failed
    }
    
    output_file = 'timeout_bugs_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Detailed results saved to: {output_file}")
    print()
    
    # Recommendation
    if len(actually_succeeded) > 0:
        print("💡 Recommendation:")
        print(f"   {len(actually_succeeded)} bugs were marked as timeout but actually")
        print("   checked out successfully. These should be re-evaluated.")
        print()
        print("   To re-evaluate these bugs, you can:")
        print("   1. Extract the bug list from timeout_bugs_analysis.json")
        print("   2. Run evaluation again with only these bugs")
        print("   3. Use fewer workers (e.g., 20) to avoid timeout issues")
    
    return results


def main():
    """Main function."""
    log_file = "gen_batch_evaluation_restart.log"
    workspace = Path("./parallel_workspace")
    
    if not Path(log_file).exists():
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)
    
    if not workspace.exists():
        print(f"Error: Workspace directory not found: {workspace}")
        sys.exit(1)
    
    analyze_timeout_bugs(log_file, workspace)


if __name__ == "__main__":
    main()
