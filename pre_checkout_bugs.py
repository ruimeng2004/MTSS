#!/usr/bin/env python3
"""Pre-checkout all bugs to avoid repeated checkout during evaluation.

This script checks out all bugs from the input directory to worker directories
before evaluation starts, significantly reducing evaluation time.
"""

import argparse
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_all_bugs(input_dir: Path) -> list[str]:
    """Get list of all bugs from input directory.
    
    Args:
        input_dir: Directory containing bug results.
        
    Returns:
        List of bug slugs.
    """
    bugs = []
    for bug_dir in sorted(input_dir.iterdir()):
        if bug_dir.is_dir():
            bugs.append(bug_dir.name)
    return bugs


def checkout_bug(
    bug_slug: str,
    worker_id: int,
    workspace_dir: Path,
    d4j_path: Path
) -> tuple[str, bool, str]:
    """Checkout a single bug to worker directory.
    
    Args:
        bug_slug: Bug identifier (e.g., Chart_1).
        worker_id: Worker ID for directory naming.
        workspace_dir: Base workspace directory.
        d4j_path: Path to Defects4J installation.
        
    Returns:
        Tuple of (bug_slug, success, message).
    """
    project, bug_id = bug_slug.rsplit('_', 1)
    checkout_dir = workspace_dir / f"worker_{worker_id}" / f"{bug_slug}_b"
    
    # Create worker directory
    checkout_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing checkout if present
    if checkout_dir.exists():
        try:
            subprocess.run(
                ['rm', '-rf', str(checkout_dir)],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            return (bug_slug, False, f"Failed to remove existing: {e}")
    
    # Checkout bug
    try:
        cmd = [
            str(d4j_path / 'framework' / 'bin' / 'defects4j'),
            'checkout',
            '-p', project,
            '-v', f"{bug_id}b",
            '-w', str(checkout_dir)
        ]
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return (bug_slug, True, f"Checked out to worker_{worker_id}")
        
    except subprocess.TimeoutExpired:
        return (bug_slug, False, "Checkout timeout")
    except subprocess.CalledProcessError as e:
        return (bug_slug, False, f"Checkout failed: {e.stderr[:100]}")
    except Exception as e:
        return (bug_slug, False, f"Error: {str(e)}")


def main():
    """Main entry point for pre-checkout script."""
    parser = argparse.ArgumentParser(
        description='Pre-checkout all bugs for evaluation'
    )
    parser.add_argument(
        '--input-dir',
        default='ppl/result/20260106_113852',
        help='Input directory with bug results'
    )
    parser.add_argument(
        '--workspace',
        default='./parallel_workspace',
        help='Base workspace directory'
    )
    parser.add_argument(
        '--d4j-path',
        default='/Users/mengrui/Desktop/D4J/defects4j',
        help='Path to Defects4J installation'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=100,
        help='Number of worker directories'
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    workspace_dir = Path(args.workspace)
    d4j_path = Path(args.d4j_path)
    
    # Get all bugs
    bugs = get_all_bugs(input_dir)
    total_bugs = len(bugs)
    
    logger.info(f"Found {total_bugs} bugs to checkout")
    logger.info(f"Using {args.workers} workers")
    logger.info(f"Workspace: {workspace_dir}")
    
    # Checkout bugs in parallel
    success_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all checkout tasks
        future_to_bug = {}
        for i, bug_slug in enumerate(bugs):
            worker_id = i % args.workers
            future = executor.submit(
                checkout_bug,
                bug_slug,
                worker_id,
                workspace_dir,
                d4j_path
            )
            future_to_bug[future] = bug_slug
        
        # Process results
        completed = 0
        for future in as_completed(future_to_bug):
            bug_slug, success, message = future.result()
            completed += 1
            
            if success:
                success_count += 1
                logger.info(
                    f"[{completed}/{total_bugs}] ✓ {bug_slug}: {message}"
                )
            else:
                failed_count += 1
                logger.error(
                    f"[{completed}/{total_bugs}] ✗ {bug_slug}: {message}"
                )
            
            # Progress update every 50 bugs
            if completed % 50 == 0:
                logger.info(
                    f"Progress: {completed}/{total_bugs} "
                    f"(Success: {success_count}, Failed: {failed_count})"
                )
    
    # Final summary
    logger.info("=" * 70)
    logger.info("PRE-CHECKOUT COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total bugs: {total_bugs}")
    logger.info(f"Successfully checked out: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Success rate: {success_count/total_bugs*100:.1f}%")
    logger.info("=" * 70)
    
    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
