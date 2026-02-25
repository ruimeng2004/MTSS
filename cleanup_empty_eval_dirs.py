#!/usr/bin/env python3
"""Clean up evaluation output directories without JSON result files.

This script removes directories in evaluation_output that don't contain
any JSON result files, keeping only completed evaluations.
"""

import argparse
import shutil
from pathlib import Path
from typing import List


def has_json_results(directory: Path) -> bool:
    """Check if directory contains any JSON result files.
    
    Args:
        directory: Directory to check.
        
    Returns:
        True if directory contains at least one .json file.
    """
    if not directory.is_dir():
        return False
    
    # Check for any .json files in the directory
    json_files = list(directory.glob("*.json"))
    return len(json_files) > 0


def find_empty_dirs(base_dir: Path) -> List[Path]:
    """Find all subdirectories without JSON result files.
    
    Args:
        base_dir: Base evaluation output directory.
        
    Returns:
        List of directories without JSON files.
    """
    empty_dirs = []
    
    for item in base_dir.iterdir():
        if item.is_dir():
            if not has_json_results(item):
                empty_dirs.append(item)
    
    return empty_dirs


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Clean up evaluation directories without JSON results"
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="/Users/mengrui/Desktop/MTSS/evaluation_output",
        help="Base evaluation output directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    base_dir = Path(args.base_dir)
    
    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        return 1
    
    # Find empty directories
    empty_dirs = find_empty_dirs(base_dir)
    
    if not empty_dirs:
        print("No empty directories found. All directories have JSON results.")
        return 0
    
    print(f"Found {len(empty_dirs)} directories without JSON results:\n")
    
    for dir_path in sorted(empty_dirs):
        print(f"  - {dir_path.name}")
    
    if args.dry_run:
        print(f"\n[DRY RUN] Would delete {len(empty_dirs)} directories")
        return 0
    
    # Confirm deletion
    print(f"\nDelete these {len(empty_dirs)} directories? [y/N]: ", end="")
    response = input().strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return 0
    
    # Delete directories
    deleted_count = 0
    failed_count = 0
    
    for dir_path in empty_dirs:
        try:
            shutil.rmtree(dir_path)
            print(f"✓ Deleted: {dir_path.name}")
            deleted_count += 1
        except Exception as e:
            print(f"✗ Failed to delete {dir_path.name}: {e}")
            failed_count += 1
    
    print(f"\nSummary:")
    print(f"  Deleted: {deleted_count}")
    print(f"  Failed: {failed_count}")
    
    return 0


if __name__ == "__main__":
    exit(main())
