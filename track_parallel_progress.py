#!/usr/bin/env python3
"""Track parallel evaluation progress with detailed statistics."""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

def parse_log_file(log_path: str):
    """Parse parallel evaluation log file.
    
    Args:
        log_path: Path to log file.
        
    Returns:
        Dictionary with statistics.
    """
    stats = {
        'total_completed': 0,
        'total_fixed': 0,
        'total_failed': 0,
        'edit_fixed': 0,
        'rewrite_fixed': 0,
        'edit_failed': 0,
        'rewrite_failed': 0,
        'fixed_bugs': [],
        'failed_bugs': [],
        'by_project': defaultdict(lambda: {'fixed': 0, 'failed': 0})
    }
    
    if not Path(log_path).exists():
        return stats
    
    with open(log_path, 'r') as f:
        for line in f:
            # Match fixed bugs: [Worker X] ✓ BugName fixed (attempt Y)
            fixed_match = re.search(
                r'\[Worker \d+\] ✓ (\w+_\d+) fixed \(attempt \d+\)',
                line
            )
            if fixed_match:
                bug_slug = fixed_match.group(1)
                stats['total_fixed'] += 1
                stats['fixed_bugs'].append(bug_slug)
                
                # Extract project name
                project = bug_slug.split('_')[0]
                stats['by_project'][project]['fixed'] += 1
            
            # Match failed bugs: [Worker X] ✗ BugName failed (all Y attempts)
            failed_match = re.search(
                r'\[Worker \d+\] ✗ (\w+_\d+) failed \(all \d+ attempts\)',
                line
            )
            if failed_match:
                bug_slug = failed_match.group(1)
                stats['total_failed'] += 1
                stats['failed_bugs'].append(bug_slug)
                
                # Extract project name
                project = bug_slug.split('_')[0]
                stats['by_project'][project]['failed'] += 1
    
    stats['total_completed'] = stats['total_fixed'] + stats['total_failed']
    
    return stats

def get_modeling_types_from_results(results_file: str):
    """Get modeling type breakdown from results JSON.
    
    Args:
        results_file: Path to results JSON file.
        
    Returns:
        Dictionary with edit/rewrite breakdown.
    """
    breakdown = {
        'edit_fixed': 0,
        'rewrite_fixed': 0,
        'edit_total': 0,
        'rewrite_total': 0
    }
    
    if not Path(results_file).exists():
        return breakdown
    
    try:
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        for bug_result in data.get('bug_results', []):
            modeling_type = bug_result.get('modeling_type')
            successful = bug_result.get('successful_attempt') is not None
            
            if modeling_type == 'edit':
                breakdown['edit_total'] += 1
                if successful:
                    breakdown['edit_fixed'] += 1
            elif modeling_type == 'rewrite':
                breakdown['rewrite_total'] += 1
                if successful:
                    breakdown['rewrite_fixed'] += 1
        
        return breakdown
    except Exception as e:
        print(f"Error reading results file: {e}", file=sys.stderr)
        return breakdown

def print_progress():
    """Print current progress with detailed statistics."""
    log_path = 'parallel_evaluation.log'
    results_path = 'evaluation_output/parallel_eval_20260204_193202/parallel_evaluation_results.json'
    
    # Parse log file
    stats = parse_log_file(log_path)
    
    # Get modeling type breakdown from results if available
    breakdown = get_modeling_types_from_results(results_path)
    
    print("=" * 70)
    print("100线程并行评估进度追踪")
    print("=" * 70)
    print()
    
    # Overall progress
    total_bugs = 698
    completed = stats['total_completed']
    progress_pct = (completed / total_bugs * 100) if total_bugs > 0 else 0
    
    print(f"总体进度: {completed}/{total_bugs} ({progress_pct:.1f}%)")
    print(f"  ✓ 成功修复: {stats['total_fixed']}")
    print(f"  ✗ 修复失败: {stats['total_failed']}")
    
    if completed > 0:
        success_rate = stats['total_fixed'] / completed * 100
        print(f"  成功率: {success_rate:.1f}%")
    
    print()
    
    # Modeling type breakdown
    if breakdown['edit_total'] > 0 or breakdown['rewrite_total'] > 0:
        print("按建模类型统计:")
        print("-" * 70)
        
        # Edit format
        if breakdown['edit_total'] > 0:
            edit_rate = (breakdown['edit_fixed'] / breakdown['edit_total'] * 100)
            print(f"  Edit (SEARCH/REPLACE):")
            print(f"    成功: {breakdown['edit_fixed']}/{breakdown['edit_total']} ({edit_rate:.1f}%)")
        
        # Rewrite format
        if breakdown['rewrite_total'] > 0:
            rewrite_rate = (breakdown['rewrite_fixed'] / breakdown['rewrite_total'] * 100)
            print(f"  Rewrite (完整方法):")
            print(f"    成功: {breakdown['rewrite_fixed']}/{breakdown['rewrite_total']} ({rewrite_rate:.1f}%)")
        
        print()
    
    # Top projects
    if stats['by_project']:
        print("各项目统计 (前10):")
        print("-" * 70)
        
        # Sort by total bugs
        sorted_projects = sorted(
            stats['by_project'].items(),
            key=lambda x: x[1]['fixed'] + x[1]['failed'],
            reverse=True
        )[:10]
        
        for project, counts in sorted_projects:
            total = counts['fixed'] + counts['failed']
            rate = (counts['fixed'] / total * 100) if total > 0 else 0
            print(f"  {project:15s}: {counts['fixed']:3d}/{total:3d} ({rate:5.1f}%)")
        
        print()
    
    # Recent activity
    print("最近修复的bug (最后10个):")
    print("-" * 70)
    for bug in stats['fixed_bugs'][-10:]:
        print(f"  ✓ {bug}")
    
    print()
    print("=" * 70)
    print("提示: 运行 'watch -n 10 python3 track_parallel_progress.py' 持续监控")
    print("=" * 70)

if __name__ == '__main__':
    print_progress()
