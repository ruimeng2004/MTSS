#!/usr/bin/env python3
"""Analyze modeling types (edit vs rewrite) from input data and results."""

import json
import sys
from pathlib import Path
from collections import defaultdict

def get_modeling_type(bug_slug: str, attempt_num: int, input_dir: Path) -> str:
    """Get modeling type for a specific bug attempt.
    
    Args:
        bug_slug: Bug identifier.
        attempt_num: Attempt number.
        input_dir: Input directory with model outputs.
        
    Returns:
        'edit', 'rewrite', or 'unknown'.
    """
    result_file = input_dir / bug_slug / str(attempt_num) / 'result.json'
    
    if not result_file.exists():
        return 'unknown'
    
    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
        
        # Check task field
        task = data.get('task', '')
        if 'edit' in task.lower():
            return 'edit'
        elif 'rewrite' in task.lower():
            return 'rewrite'
        
        # Fallback: check model_output.txt for format indicators
        output_file = input_dir / bug_slug / str(attempt_num) / 'model_output.txt'
        if output_file.exists():
            with open(output_file, 'r') as f:
                content = f.read()
            
            # Check for SEARCH/REPLACE blocks (edit format)
            if '<<<<<<< SEARCH' in content and '>>>>>>> REPLACE' in content:
                return 'edit'
            # Check for full method rewrite (rewrite format)
            elif '<<<<<<< COMPLETE' in content or 'FIXED_CODE' in content:
                return 'rewrite'
        
        return 'unknown'
    except Exception:
        return 'unknown'

def analyze_from_log(log_path: str, input_dir: str):
    """Analyze modeling types from log file.
    
    Args:
        log_path: Path to parallel evaluation log.
        input_dir: Input directory with model outputs.
    """
    input_path = Path(input_dir)
    
    stats = {
        'edit': {'fixed': [], 'failed': []},
        'rewrite': {'fixed': [], 'failed': []},
        'unknown': {'fixed': [], 'failed': []}
    }
    
    if not Path(log_path).exists():
        print(f"日志文件不存在: {log_path}")
        return
    
    # Parse log file for fixed bugs
    with open(log_path, 'r') as f:
        for line in f:
            # Match: [Worker X] ✓ BugName fixed (attempt Y)
            if '✓' in line and 'fixed (attempt' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == '✓':
                        bug_slug = parts[i + 1]
                        # Find attempt number
                        for j, p in enumerate(parts):
                            if p == '(attempt':
                                attempt_str = parts[j + 1].rstrip(')')
                                attempt_num = int(attempt_str)
                                
                                # Get modeling type
                                modeling_type = get_modeling_type(
                                    bug_slug, attempt_num, input_path
                                )
                                stats[modeling_type]['fixed'].append(
                                    (bug_slug, attempt_num)
                                )
                                break
                        break
            
            # Match: [Worker X] ✗ BugName failed (all Y attempts)
            elif '✗' in line and 'failed (all' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == '✗':
                        bug_slug = parts[i + 1]
                        # For failed bugs, check first attempt
                        modeling_type = get_modeling_type(
                            bug_slug, 1, input_path
                        )
                        stats[modeling_type]['failed'].append(bug_slug)
                        break
    
    # Print statistics
    print("=" * 70)
    print("建模类型统计分析")
    print("=" * 70)
    print()
    
    total_fixed = sum(len(stats[t]['fixed']) for t in stats)
    total_failed = sum(len(stats[t]['failed']) for t in stats)
    total = total_fixed + total_failed
    
    print(f"总计: {total} 个bug")
    print(f"  成功修复: {total_fixed}")
    print(f"  修复失败: {total_failed}")
    print()
    
    # Edit format
    edit_fixed = len(stats['edit']['fixed'])
    edit_failed = len(stats['edit']['failed'])
    edit_total = edit_fixed + edit_failed
    
    print(f"Edit格式 (SEARCH/REPLACE blocks):")
    if edit_total > 0:
        edit_rate = edit_fixed / edit_total * 100
        print(f"  总数: {edit_total}")
        print(f"  成功: {edit_fixed} ({edit_rate:.1f}%)")
        print(f"  失败: {edit_failed}")
    else:
        print(f"  总数: 0 (暂无数据)")
    print()
    
    # Rewrite format
    rewrite_fixed = len(stats['rewrite']['fixed'])
    rewrite_failed = len(stats['rewrite']['failed'])
    rewrite_total = rewrite_fixed + rewrite_failed
    
    print(f"Rewrite格式 (完整方法重写):")
    if rewrite_total > 0:
        rewrite_rate = rewrite_fixed / rewrite_total * 100
        print(f"  总数: {rewrite_total}")
        print(f"  成功: {rewrite_fixed} ({rewrite_rate:.1f}%)")
        print(f"  失败: {rewrite_failed}")
    else:
        print(f"  总数: 0 (暂无数据)")
    print()
    
    # Unknown
    unknown_fixed = len(stats['unknown']['fixed'])
    unknown_failed = len(stats['unknown']['failed'])
    unknown_total = unknown_fixed + unknown_failed
    
    if unknown_total > 0:
        print(f"未知格式:")
        print(f"  总数: {unknown_total}")
        print(f"  成功: {unknown_fixed}")
        print(f"  失败: {unknown_failed}")
        print()
    
    # Show some examples
    if edit_fixed > 0:
        print("Edit格式成功案例 (前10个):")
        for bug, attempt in stats['edit']['fixed'][:10]:
            print(f"  ✓ {bug} (attempt {attempt})")
        print()
    
    if rewrite_fixed > 0:
        print("Rewrite格式成功案例 (前10个):")
        for bug, attempt in stats['rewrite']['fixed'][:10]:
            print(f"  ✓ {bug} (attempt {attempt})")
        print()
    
    print("=" * 70)

if __name__ == '__main__':
    log_path = 'parallel_evaluation.log'
    input_dir = 'ppl/result/20260105_132306'
    
    analyze_from_log(log_path, input_dir)
