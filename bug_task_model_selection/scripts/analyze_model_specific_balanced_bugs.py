#!/usr/bin/env python3
"""Analyze bugs that are balanced for one model but not the other."""

import json
from pathlib import Path
from typing import Dict, List, Set
import re
from collections import Counter


def load_balanced_bugs(model: str, threshold: float) -> Set[str]:
    """Load balanced bug list for a model."""
    path = Path(f"bug_task_model_selection/data/analysis/balanced_bugs/"
                f"{model}_balanced_bugs_gap{threshold:.0f}.jsonl")
    
    bugs = set()
    if path.exists():
        with open(path, 'r') as f:
            for line in f:
                obj = json.loads(line)
                bugs.add(obj['slug'])
    
    return bugs


def load_bug_details(model: str, threshold: float) -> Dict[str, Dict]:
    """Load detailed bug information."""
    path = Path(f"bug_task_model_selection/data/analysis/balanced_bugs/"
                f"{model}_balanced_bugs_gap{threshold:.0f}.jsonl")
    
    bugs = {}
    if path.exists():
        with open(path, 'r') as f:
            for line in f:
                obj = json.loads(line)
                bugs[obj['slug']] = obj
    
    return bugs


def load_patches() -> Dict[str, Dict]:
    """Load patch information."""
    path = Path("bug_task_model_selection/data/artifacts/patches.jsonl")
    
    patches = {}
    if path.exists():
        with open(path, 'r') as f:
            for line in f:
                obj = json.loads(line)
                patches[obj['slug']] = obj
    
    return patches


def analyze_patch_characteristics(patch_text: str) -> Dict:
    """Analyze characteristics of a patch.
    
    Args:
        patch_text: The patch diff text.
    
    Returns:
        Dictionary with patch characteristics.
    """
    lines = patch_text.split('\n')
    
    added_lines = [l for l in lines if l.startswith('+') and not l.startswith('+++')]
    removed_lines = [l for l in lines if l.startswith('-') and not l.startswith('---')]
    
    # Count different types of changes
    characteristics = {
        'total_lines': len(lines),
        'added_lines': len(added_lines),
        'removed_lines': len(removed_lines),
        'net_change': len(added_lines) - len(removed_lines),
        'files_changed': len([l for l in lines if l.startswith('diff --git')]),
        
        # Code patterns
        'has_if_statement': any('if ' in l for l in added_lines + removed_lines),
        'has_for_loop': any('for ' in l or 'for(' in l for l in added_lines + removed_lines),
        'has_while_loop': any('while ' in l or 'while(' in l for l in added_lines + removed_lines),
        'has_try_catch': any('try' in l or 'catch' in l for l in added_lines + removed_lines),
        'has_return': any('return' in l for l in added_lines + removed_lines),
        'has_null_check': any('null' in l for l in added_lines + removed_lines),
        'has_method_call': any('(' in l and ')' in l for l in added_lines + removed_lines),
        
        # Change types
        'is_single_line': len(added_lines) + len(removed_lines) == 1,
        'is_small': len(added_lines) + len(removed_lines) <= 5,
        'is_medium': 5 < len(added_lines) + len(removed_lines) <= 20,
        'is_large': len(added_lines) + len(removed_lines) > 20,
        
        # String operations
        'has_string_literal': any('"' in l or "'" in l for l in added_lines + removed_lines),
        'has_concatenation': any('+' in l for l in added_lines + removed_lines),
        
        # Comments
        'has_comment': any('//' in l or '/*' in l or '*/' in l for l in added_lines + removed_lines),
    }
    
    # Calculate complexity score
    complexity = 0
    if characteristics['has_if_statement']:
        complexity += 1
    if characteristics['has_for_loop'] or characteristics['has_while_loop']:
        complexity += 2
    if characteristics['has_try_catch']:
        complexity += 2
    if characteristics['is_large']:
        complexity += 3
    elif characteristics['is_medium']:
        complexity += 1
    
    characteristics['complexity_score'] = complexity
    
    return characteristics


def extract_project_name(slug: str) -> str:
    """Extract project name from slug."""
    return slug.split('_')[0]


def analyze_model_specific_bugs(
    only_30b: Set[str],
    only_coder: Set[str],
    both: Set[str],
    bugs_30b: Dict[str, Dict],
    bugs_coder: Dict[str, Dict],
    patches: Dict[str, Dict]
):
    """Analyze bugs specific to each model."""
    
    print("\n" + "=" * 100)
    print("模型特定平衡 Bug 分析")
    print("=" * 100)
    
    # Analyze only_30b bugs
    print("\n## 仅 qwen3_30b 识别的平衡 Bugs\n")
    print(f"**数量**: {len(only_30b)} bugs\n")
    
    # Project distribution
    projects_30b = Counter(extract_project_name(slug) for slug in only_30b)
    print("**项目分布**:")
    print("| 项目 | 数量 | 占比 |")
    print("|------|------|------|")
    for project, count in projects_30b.most_common(10):
        print(f"| {project} | {count} | {count/len(only_30b)*100:.1f}% |")
    
    # Gap comparison
    print("\n**PPL Gap 对比**:")
    gaps_30b_in_30b = [bugs_30b[slug]['gap'] for slug in only_30b if slug in bugs_30b]
    gaps_30b_in_coder = []
    
    # Load coder PPL data to get gaps for these bugs
    from analyze_individual_bug_balance import load_ppl_data, calculate_ppl_gap
    ppl_coder = load_ppl_data('qwen3_coder')
    
    for slug in only_30b:
        if slug in ppl_coder and 'edit_ppl' in ppl_coder[slug] and 'gen_ppl' in ppl_coder[slug]:
            gap = calculate_ppl_gap(ppl_coder[slug]['edit_ppl'], ppl_coder[slug]['gen_ppl'])
            gaps_30b_in_coder.append(gap)
    
    if gaps_30b_in_30b and gaps_30b_in_coder:
        import numpy as np
        print(f"- qwen3_30b gap: 平均 {np.mean(gaps_30b_in_30b):.2f}%, "
              f"中位数 {np.median(gaps_30b_in_30b):.2f}%")
        print(f"- qwen3_coder gap: 平均 {np.mean(gaps_30b_in_coder):.2f}%, "
              f"中位数 {np.median(gaps_30b_in_coder):.2f}%")
        print(f"- Gap 差异: {np.mean(gaps_30b_in_coder) - np.mean(gaps_30b_in_30b):.2f}%")
    
    # Patch characteristics
    print("\n**Patch 特征分析**:")
    
    patch_chars = []
    for slug in only_30b:
        if slug in patches and 'text' in patches[slug]:
            chars = analyze_patch_characteristics(patches[slug]['text'])
            patch_chars.append(chars)
    
    if patch_chars:
        import numpy as np
        
        print(f"\n总共分析了 {len(patch_chars)} 个 patches\n")
        
        # Size statistics
        added = [c['added_lines'] for c in patch_chars]
        removed = [c['removed_lines'] for c in patch_chars]
        
        print("**大小统计**:")
        print(f"- 平均添加行数: {np.mean(added):.1f}")
        print(f"- 平均删除行数: {np.mean(removed):.1f}")
        print(f"- 平均净变化: {np.mean([c['net_change'] for c in patch_chars]):.1f}")
        
        # Size distribution
        single = sum(1 for c in patch_chars if c['is_single_line'])
        small = sum(1 for c in patch_chars if c['is_small'])
        medium = sum(1 for c in patch_chars if c['is_medium'])
        large = sum(1 for c in patch_chars if c['is_large'])
        
        print(f"\n**大小分布**:")
        print(f"- 单行修改: {single} ({single/len(patch_chars)*100:.1f}%)")
        print(f"- 小修改 (≤5行): {small} ({small/len(patch_chars)*100:.1f}%)")
        print(f"- 中等修改 (6-20行): {medium} ({medium/len(patch_chars)*100:.1f}%)")
        print(f"- 大修改 (>20行): {large} ({large/len(patch_chars)*100:.1f}%)")
        
        # Pattern frequency
        print(f"\n**代码模式频率**:")
        patterns = [
            ('if 语句', 'has_if_statement'),
            ('for 循环', 'has_for_loop'),
            ('while 循环', 'has_while_loop'),
            ('try-catch', 'has_try_catch'),
            ('return 语句', 'has_return'),
            ('null 检查', 'has_null_check'),
            ('方法调用', 'has_method_call'),
            ('字符串字面量', 'has_string_literal'),
            ('注释', 'has_comment'),
        ]
        
        for name, key in patterns:
            count = sum(1 for c in patch_chars if c[key])
            print(f"- {name}: {count} ({count/len(patch_chars)*100:.1f}%)")
        
        # Complexity
        complexity = [c['complexity_score'] for c in patch_chars]
        print(f"\n**复杂度**:")
        print(f"- 平均复杂度分数: {np.mean(complexity):.2f}")
        print(f"- 中位数复杂度: {np.median(complexity):.1f}")
        print(f"- 低复杂度 (0-1): {sum(1 for c in complexity if c <= 1)} "
              f"({sum(1 for c in complexity if c <= 1)/len(complexity)*100:.1f}%)")
        print(f"- 中复杂度 (2-3): {sum(1 for c in complexity if 2 <= c <= 3)} "
              f"({sum(1 for c in complexity if 2 <= c <= 3)/len(complexity)*100:.1f}%)")
        print(f"- 高复杂度 (≥4): {sum(1 for c in complexity if c >= 4)} "
              f"({sum(1 for c in complexity if c >= 4)/len(complexity)*100:.1f}%)")
    
    # Show examples
    print("\n**示例 Bugs**:")
    print("\n最平衡的 5 个（qwen3_30b gap 最小）:")
    print("| Slug | 30b Gap | Coder Gap | Gap 差异 | 项目 |")
    print("|------|---------|-----------|---------|------|")
    
    examples = []
    for slug in only_30b:
        if slug in bugs_30b and slug in ppl_coder:
            if 'edit_ppl' in ppl_coder[slug] and 'gen_ppl' in ppl_coder[slug]:
                coder_gap = calculate_ppl_gap(
                    ppl_coder[slug]['edit_ppl'], 
                    ppl_coder[slug]['gen_ppl']
                )
                examples.append({
                    'slug': slug,
                    '30b_gap': bugs_30b[slug]['gap'],
                    'coder_gap': coder_gap,
                    'diff': coder_gap - bugs_30b[slug]['gap'],
                    'project': extract_project_name(slug)
                })
    
    examples.sort(key=lambda x: x['30b_gap'])
    for ex in examples[:5]:
        print(f"| {ex['slug']} | {ex['30b_gap']:.2f}% | {ex['coder_gap']:.2f}% | "
              f"+{ex['diff']:.2f}% | {ex['project']} |")
    
    # Analyze only_coder bugs for comparison
    print("\n\n## 仅 qwen3_coder 识别的平衡 Bugs（对比）\n")
    print(f"**数量**: {len(only_coder)} bugs\n")
    
    projects_coder = Counter(extract_project_name(slug) for slug in only_coder)
    print("**项目分布**:")
    print("| 项目 | 数量 | 占比 |")
    print("|------|------|------|")
    for project, count in projects_coder.most_common(10):
        print(f"| {project} | {count} | {count/len(only_coder)*100:.1f}% |")
    
    # Patch characteristics for coder-only
    patch_chars_coder = []
    for slug in only_coder:
        if slug in patches and 'text' in patches[slug]:
            chars = analyze_patch_characteristics(patches[slug]['text'])
            patch_chars_coder.append(chars)
    
    if patch_chars_coder:
        print(f"\n**Patch 特征对比**:")
        print(f"总共分析了 {len(patch_chars_coder)} 个 patches\n")
        
        added_coder = [c['added_lines'] for c in patch_chars_coder]
        removed_coder = [c['removed_lines'] for c in patch_chars_coder]
        
        print("| 特征 | 仅 qwen3_30b | 仅 qwen3_coder | 差异 |")
        print("|------|-------------|---------------|------|")
        print(f"| 平均添加行数 | {np.mean(added):.1f} | {np.mean(added_coder):.1f} | "
              f"{np.mean(added) - np.mean(added_coder):+.1f} |")
        print(f"| 平均删除行数 | {np.mean(removed):.1f} | {np.mean(removed_coder):.1f} | "
              f"{np.mean(removed) - np.mean(removed_coder):+.1f} |")
        
        complexity_coder = [c['complexity_score'] for c in patch_chars_coder]
        print(f"| 平均复杂度 | {np.mean(complexity):.2f} | {np.mean(complexity_coder):.2f} | "
              f"{np.mean(complexity) - np.mean(complexity_coder):+.2f} |")
        
        # Pattern comparison
        print(f"\n**代码模式对比**:")
        print("| 模式 | 仅 qwen3_30b | 仅 qwen3_coder | 差异 |")
        print("|------|-------------|---------------|------|")
        
        for name, key in patterns:
            count_30b = sum(1 for c in patch_chars if c[key]) / len(patch_chars) * 100
            count_coder = sum(1 for c in patch_chars_coder if c[key]) / len(patch_chars_coder) * 100
            print(f"| {name} | {count_30b:.1f}% | {count_coder:.1f}% | {count_30b - count_coder:+.1f}% |")


def main():
    """Main analysis function."""
    print("=" * 100)
    print("模型特定平衡 Bug 深度分析")
    print("=" * 100)
    
    threshold = 10  # Use 10% threshold for clearer differences
    
    # Load balanced bugs
    print(f"\n加载平衡 bug 列表（阈值 {threshold}%）...")
    bugs_30b_set = load_balanced_bugs('qwen3_30b', threshold)
    bugs_coder_set = load_balanced_bugs('qwen3_coder', threshold)
    
    # Find model-specific bugs
    only_30b = bugs_30b_set - bugs_coder_set
    only_coder = bugs_coder_set - bugs_30b_set
    both = bugs_30b_set & bugs_coder_set
    
    print(f"qwen3_30b: {len(bugs_30b_set)} bugs")
    print(f"qwen3_coder: {len(bugs_coder_set)} bugs")
    print(f"仅 qwen3_30b: {len(only_30b)} bugs")
    print(f"仅 qwen3_coder: {len(only_coder)} bugs")
    print(f"两者都识别: {len(both)} bugs")
    
    # Load detailed information
    print("\n加载详细信息...")
    bugs_30b = load_bug_details('qwen3_30b', threshold)
    bugs_coder = load_bug_details('qwen3_coder', threshold)
    patches = load_patches()
    
    print(f"加载了 {len(patches)} 个 patches")
    
    # Analyze
    analyze_model_specific_bugs(
        only_30b, only_coder, both,
        bugs_30b, bugs_coder, patches
    )
    
    print("\n" + "=" * 100)
    print("分析完成")
    print("=" * 100)


if __name__ == "__main__":
    main()
