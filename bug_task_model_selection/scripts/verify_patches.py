#!/usr/bin/env python3
"""
Verify the extracted patches and generate a summary report.
"""

import json
import statistics
from pathlib import Path
from collections import defaultdict


def load_patches(jsonl_file):
    """Load patches from JSONL file"""
    patches = []
    with open(jsonl_file, 'r') as f:
        for line in f:
            patches.append(json.loads(line))
    return patches


def analyze_patches(patches):
    """Analyze patches and generate statistics"""
    
    # Basic stats
    total = len(patches)
    
    # By project
    by_project = defaultdict(list)
    for p in patches:
        by_project[p['metadata']['project']].append(p)
    
    # Patch sizes
    sizes = [p['metadata']['total_changes'] for p in patches]
    
    # Test patches
    with_tests = sum(1 for p in patches if p['metadata']['has_test_patch'])
    
    # File types
    file_extensions = defaultdict(int)
    for p in patches:
        file_path = p['metadata']['file_path']
        if file_path:
            ext = Path(file_path).suffix
            file_extensions[ext] += 1
    
    return {
        'total': total,
        'by_project': {k: len(v) for k, v in by_project.items()},
        'sizes': {
            'min': min(sizes),
            'max': max(sizes),
            'mean': statistics.mean(sizes),
            'median': statistics.median(sizes),
            'stdev': statistics.stdev(sizes) if len(sizes) > 1 else 0
        },
        'with_tests': with_tests,
        'without_tests': total - with_tests,
        'file_extensions': dict(file_extensions)
    }


def find_interesting_patches(patches):
    """Find interesting patches for manual inspection"""
    
    # Smallest patch
    smallest = min(patches, key=lambda p: p['metadata']['total_changes'])
    
    # Largest patch
    largest = max(patches, key=lambda p: p['metadata']['total_changes'])
    
    # Patches with only additions
    only_additions = [p for p in patches 
                     if p['metadata']['additions'] > 0 and p['metadata']['deletions'] == 0]
    
    # Patches with only deletions
    only_deletions = [p for p in patches 
                     if p['metadata']['deletions'] > 0 and p['metadata']['additions'] == 0]
    
    # Balanced patches (similar additions and deletions)
    balanced = [p for p in patches 
               if abs(p['metadata']['additions'] - p['metadata']['deletions']) <= 2
               and p['metadata']['total_changes'] > 4]
    
    return {
        'smallest': smallest,
        'largest': largest,
        'only_additions': len(only_additions),
        'only_deletions': len(only_deletions),
        'balanced': len(balanced)
    }


def print_report(stats, interesting):
    """Print a formatted report"""
    
    print("=" * 80)
    print("DEFECTS4J PATCHES VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    print(f"Total patches: {stats['total']}")
    print(f"Patches with test changes: {stats['with_tests']} ({stats['with_tests']/stats['total']*100:.1f}%)")
    print(f"Patches without test changes: {stats['without_tests']} ({stats['without_tests']/stats['total']*100:.1f}%)")
    print()
    
    print("Patch Size Statistics:")
    print(f"  Min:    {stats['sizes']['min']} lines")
    print(f"  Max:    {stats['sizes']['max']} lines")
    print(f"  Mean:   {stats['sizes']['mean']:.2f} lines")
    print(f"  Median: {stats['sizes']['median']} lines")
    print(f"  StdDev: {stats['sizes']['stdev']:.2f} lines")
    print()
    
    print("Patches by Project:")
    for project, count in sorted(stats['by_project'].items(), key=lambda x: -x[1]):
        print(f"  {project:20s}: {count:3d} patches")
    print()
    
    print("File Extensions:")
    for ext, count in sorted(stats['file_extensions'].items(), key=lambda x: -x[1]):
        ext_display = ext if ext else "(no extension)"
        print(f"  {ext_display:20s}: {count:3d} files")
    print()
    
    print("Interesting Patches:")
    print(f"  Smallest patch: {interesting['smallest']['slug']} "
          f"({interesting['smallest']['metadata']['total_changes']} lines)")
    print(f"  Largest patch:  {interesting['largest']['slug']} "
          f"({interesting['largest']['metadata']['total_changes']} lines)")
    print(f"  Only additions: {interesting['only_additions']} patches")
    print(f"  Only deletions: {interesting['only_deletions']} patches")
    print(f"  Balanced:       {interesting['balanced']} patches")
    print()
    
    print("=" * 80)
    print("Sample Patch (smallest):")
    print("=" * 80)
    print(f"Bug: {interesting['smallest']['slug']}")
    print(f"File: {interesting['smallest']['metadata']['file_path']}")
    print(f"Changes: +{interesting['smallest']['metadata']['additions']} "
          f"-{interesting['smallest']['metadata']['deletions']}")
    print()
    print(interesting['smallest']['text'][:500])
    if len(interesting['smallest']['text']) > 500:
        print("... (truncated)")
    print()


def main():
    patches_file = Path('bug_task_model_selection/data/artifacts/patches.jsonl')
    
    if not patches_file.exists():
        print(f"Error: {patches_file} not found!")
        print("Please run extract_patches.py first.")
        return
    
    print("Loading patches...")
    patches = load_patches(patches_file)
    
    print("Analyzing patches...")
    stats = analyze_patches(patches)
    interesting = find_interesting_patches(patches)
    
    print_report(stats, interesting)
    
    print("Verification complete!")


if __name__ == '__main__':
    main()
