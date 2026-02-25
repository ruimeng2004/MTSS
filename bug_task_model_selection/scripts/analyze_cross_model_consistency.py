#!/usr/bin/env python3
"""Analyze cross-model consistency in task modeling preference.

This analysis answers: When we change the base model, does a bug's
preferred task modeling (edit/gen) also change?
"""

import json
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import numpy as np


def load_ppl_scores(path: Path) -> Dict[str, float]:
    """Load PPL scores from JSONL file."""
    scores = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            slug = obj.get('slug')
            value = obj.get('value')
            if slug and value is not None:
                scores[slug] = float(value)
    return scores


def compute_preferences(
    edit_ppl: Dict[str, float],
    gen_ppl: Dict[str, float]
) -> Tuple[Dict[str, str], Dict[str, float]]:
    """Compute preferred strategy and gap for each bug.
    
    Returns:
        Tuple of (preferences, gaps) where:
        - preferences: {slug: 'edit' or 'gen'}
        - gaps: {slug: relative_difference_pct}
    """
    preferences = {}
    gaps = {}
    
    for slug in edit_ppl:
        if slug not in gen_ppl:
            continue
        
        edit_val = edit_ppl[slug]
        gen_val = gen_ppl[slug]
        
        # Preference
        preferences[slug] = 'edit' if edit_val < gen_val else 'gen'
        
        # Gap
        min_val = min(edit_val, gen_val)
        max_val = max(edit_val, gen_val)
        rel_diff = (max_val - min_val) / min_val if min_val > 0 else 0
        gaps[slug] = rel_diff * 100
    
    return preferences, gaps


def categorize_gap(gap_pct: float) -> str:
    """Categorize gap size."""
    if gap_pct < 5:
        return 'negligible'
    elif gap_pct < 20:
        return 'small'
    elif gap_pct < 50:
        return 'medium'
    elif gap_pct < 100:
        return 'large'
    else:
        return 'huge'


def main():
    """Main analysis function."""
    print("=" * 100)
    print("跨模型一致性分析 - 任务建模偏好的模型依赖性")
    print("=" * 100)
    print("\n目标: 分析基础模型改变时，bug 的任务建模偏好是否也改变\n")
    
    data_dir = Path("bug_task_model_selection/data/ppl")
    
    # Load all PPL scores
    coder_edit = load_ppl_scores(data_dir / "qwen3_coder_edit.jsonl")
    coder_gen = load_ppl_scores(data_dir / "qwen3_coder_gen.jsonl")
    b30_edit = load_ppl_scores(data_dir / "qwen3_30b_edit.jsonl")
    b30_gen = load_ppl_scores(data_dir / "qwen3_30b_gen.jsonl")
    
    # Compute preferences
    coder_pref, coder_gaps = compute_preferences(coder_edit, coder_gen)
    b30_pref, b30_gaps = compute_preferences(b30_edit, b30_gen)
    
    # Find common bugs
    common_bugs = set(coder_pref.keys()) & set(b30_pref.keys())
    print(f"共同的 bugs: {len(common_bugs)}\n")
    
    # 1. Overall consistency
    print("=" * 100)
    print("1. 整体一致性分析")
    print("=" * 100)
    
    consistent = 0
    inconsistent = 0
    
    for slug in common_bugs:
        if coder_pref[slug] == b30_pref[slug]:
            consistent += 1
        else:
            inconsistent += 1
    
    consistency_rate = consistent / len(common_bugs)
    
    print(f"\n一致的 bugs: {consistent} ({consistency_rate:.1%})")
    print(f"不一致的 bugs: {inconsistent} ({1-consistency_rate:.1%})")
    
    # 2. Consistency by gap size
    print("\n\n" + "=" * 100)
    print("2. 按差距大小分析一致性")
    print("=" * 100)
    
    print("\n### 2.1 按 qwen3_coder 的差距分类\n")
    print("| 差距类别 | 一致数 | 不一致数 | 总数 | 一致率 | 说明 |")
    print("|---------|--------|----------|------|--------|------|")
    
    categories = ['negligible', 'small', 'medium', 'large', 'huge']
    category_labels = {
        'negligible': '< 5%',
        'small': '5-20%',
        'medium': '20-50%',
        'large': '50-100%',
        'huge': '≥ 100%'
    }
    
    for cat in categories:
        bugs_in_cat = [s for s in common_bugs 
                       if categorize_gap(coder_gaps[s]) == cat]
        
        if not bugs_in_cat:
            continue
        
        consistent_in_cat = sum(1 for s in bugs_in_cat 
                               if coder_pref[s] == b30_pref[s])
        inconsistent_in_cat = len(bugs_in_cat) - consistent_in_cat
        consistency_in_cat = consistent_in_cat / len(bugs_in_cat)
        
        explanation = ""
        if cat == 'negligible':
            explanation = "差距小，容易受模型影响"
        elif cat == 'huge':
            explanation = "差距大，偏好稳定"
        
        print(f"| {cat} ({category_labels[cat]}) | {consistent_in_cat} | "
              f"{inconsistent_in_cat} | {len(bugs_in_cat)} | "
              f"{consistency_in_cat:.1%} | {explanation} |")
    
    # 3. Preference distribution
    print("\n\n" + "=" * 100)
    print("3. 偏好分布对比")
    print("=" * 100)
    
    print("\n| 模型 | Edit 偏好 | Gen 偏好 |")
    print("|------|-----------|----------|")
    
    coder_edit_count = sum(1 for p in coder_pref.values() if p == 'edit')
    coder_gen_count = sum(1 for p in coder_pref.values() if p == 'gen')
    b30_edit_count = sum(1 for p in b30_pref.values() if p == 'edit')
    b30_gen_count = sum(1 for p in b30_pref.values() if p == 'gen')
    
    print(f"| qwen3_coder | {coder_edit_count} ({coder_edit_count/len(coder_pref):.1%}) | "
          f"{coder_gen_count} ({coder_gen_count/len(coder_pref):.1%}) |")
    print(f"| qwen3_30b | {b30_edit_count} ({b30_edit_count/len(b30_pref):.1%}) | "
          f"{b30_gen_count} ({b30_gen_count/len(b30_pref):.1%}) |")
    
    # 4. Preference transition matrix
    print("\n\n" + "=" * 100)
    print("4. 偏好转移矩阵")
    print("=" * 100)
    
    print("\n从 qwen3_coder 到 qwen3_30b 的偏好变化:\n")
    
    edit_to_edit = sum(1 for s in common_bugs 
                       if coder_pref[s] == 'edit' and b30_pref[s] == 'edit')
    edit_to_gen = sum(1 for s in common_bugs 
                      if coder_pref[s] == 'edit' and b30_pref[s] == 'gen')
    gen_to_edit = sum(1 for s in common_bugs 
                      if coder_pref[s] == 'gen' and b30_pref[s] == 'edit')
    gen_to_gen = sum(1 for s in common_bugs 
                     if coder_pref[s] == 'gen' and b30_pref[s] == 'gen')
    
    print("| coder \\ 30b | Edit | Gen | 总计 |")
    print("|-------------|------|-----|------|")
    print(f"| **Edit** | {edit_to_edit} ({edit_to_edit/(edit_to_edit+edit_to_gen):.1%}) | "
          f"{edit_to_gen} ({edit_to_gen/(edit_to_edit+edit_to_gen):.1%}) | "
          f"{edit_to_edit+edit_to_gen} |")
    print(f"| **Gen** | {gen_to_edit} ({gen_to_edit/(gen_to_edit+gen_to_gen):.1%}) | "
          f"{gen_to_gen} ({gen_to_gen/(gen_to_edit+gen_to_gen):.1%}) | "
          f"{gen_to_edit+gen_to_gen} |")
    print(f"| **总计** | {edit_to_edit+gen_to_edit} | {edit_to_gen+gen_to_gen} | "
          f"{len(common_bugs)} |")
    
    print(f"\n**稳定性**:")
    print(f"- Edit 保持 Edit: {edit_to_edit} / {edit_to_edit+edit_to_gen} = "
          f"{edit_to_edit/(edit_to_edit+edit_to_gen):.1%}")
    print(f"- Gen 保持 Gen: {gen_to_gen} / {gen_to_edit+gen_to_gen} = "
          f"{gen_to_gen/(gen_to_edit+gen_to_gen):.1%}")
    
    # 5. Inconsistent bugs analysis
    print("\n\n" + "=" * 100)
    print("5. 不一致 bugs 的特征分析")
    print("=" * 100)
    
    inconsistent_bugs = [s for s in common_bugs 
                        if coder_pref[s] != b30_pref[s]]
    
    print(f"\n共 {len(inconsistent_bugs)} 个不一致的 bugs\n")
    
    # Gap distribution of inconsistent bugs
    print("### 5.1 不一致 bugs 的差距分布\n")
    print("| 模型 | 平均差距 | 中位数差距 | 最小差距 | 最大差距 |")
    print("|------|----------|-----------|----------|----------|")
    
    coder_gaps_incon = [coder_gaps[s] for s in inconsistent_bugs]
    b30_gaps_incon = [b30_gaps[s] for s in inconsistent_bugs]
    
    print(f"| qwen3_coder | {np.mean(coder_gaps_incon):.1f}% | "
          f"{np.median(coder_gaps_incon):.1f}% | "
          f"{np.min(coder_gaps_incon):.1f}% | "
          f"{np.max(coder_gaps_incon):.1f}% |")
    print(f"| qwen3_30b | {np.mean(b30_gaps_incon):.1f}% | "
          f"{np.median(b30_gaps_incon):.1f}% | "
          f"{np.min(b30_gaps_incon):.1f}% | "
          f"{np.max(b30_gaps_incon):.1f}% |")
    
    # Top 20 inconsistent bugs
    print("\n### 5.2 差距最大的 20 个不一致 bugs\n")
    print("| Rank | Slug | Coder Pref | Coder Gap | 30b Pref | 30b Gap |")
    print("|------|------|------------|-----------|----------|---------|")
    
    # Sort by average gap
    inconsistent_with_gaps = [(s, (coder_gaps[s] + b30_gaps[s]) / 2) 
                              for s in inconsistent_bugs]
    inconsistent_with_gaps.sort(key=lambda x: x[1], reverse=True)
    
    for i, (slug, _) in enumerate(inconsistent_with_gaps[:20], 1):
        print(f"| {i} | {slug[:30]} | {coder_pref[slug]} | "
              f"{coder_gaps[slug]:.1f}% | {b30_pref[slug]} | "
              f"{b30_gaps[slug]:.1f}% |")
    
    # 6. Highly sensitive bugs (both models have large gaps)
    print("\n\n" + "=" * 100)
    print("6. 高敏感 bugs 分析（两个模型差距都很大）")
    print("=" * 100)
    
    highly_sensitive = [s for s in common_bugs 
                       if coder_gaps[s] >= 100 and b30_gaps[s] >= 100]
    
    print(f"\n共 {len(highly_sensitive)} 个高敏感 bugs（两个模型差距都 ≥ 100%）\n")
    
    consistent_hs = sum(1 for s in highly_sensitive 
                       if coder_pref[s] == b30_pref[s])
    inconsistent_hs = len(highly_sensitive) - consistent_hs
    
    print(f"一致: {consistent_hs} ({consistent_hs/len(highly_sensitive):.1%})")
    print(f"不一致: {inconsistent_hs} ({inconsistent_hs/len(highly_sensitive):.1%})")
    
    print("\n**结论**: 即使两个模型都认为差距很大，仍有 "
          f"{inconsistent_hs/len(highly_sensitive):.1%} 的 bugs 偏好不一致")
    
    # 7. Final conclusions
    print("\n\n" + "=" * 100)
    print("总结与结论")
    print("=" * 100)
    
    print(f"\n1. **整体一致性**: {consistency_rate:.1%}")
    print(f"   - {consistent} 个 bugs 在两个模型上偏好相同")
    print(f"   - {inconsistent} 个 bugs 在两个模型上偏好不同")
    
    print(f"\n2. **差距大的 bugs 更一致**:")
    huge_bugs = [s for s in common_bugs if categorize_gap(coder_gaps[s]) == 'huge']
    huge_consistent = sum(1 for s in huge_bugs if coder_pref[s] == b30_pref[s])
    print(f"   - 差距 ≥ 100% 的 bugs 一致率: {huge_consistent/len(huge_bugs):.1%}")
    
    negligible_bugs = [s for s in common_bugs 
                      if categorize_gap(coder_gaps[s]) == 'negligible']
    if negligible_bugs:
        neg_consistent = sum(1 for s in negligible_bugs 
                            if coder_pref[s] == b30_pref[s])
        print(f"   - 差距 < 5% 的 bugs 一致率: {neg_consistent/len(negligible_bugs):.1%}")
    
    print(f"\n3. **模型偏好差异**:")
    print(f"   - qwen3_coder 更偏好 Gen ({coder_gen_count/len(coder_pref):.1%})")
    print(f"   - qwen3_30b 更偏好 Edit ({b30_edit_count/len(b30_pref):.1%})")
    
    print(f"\n4. **实际影响**:")
    print(f"   - 如果基于 qwen3_coder 选择任务建模，在 qwen3_30b 上会有 "
          f"{inconsistent/len(common_bugs):.1%} 的 bugs 选择错误")
    print(f"   - 任务建模选择具有一定的模型依赖性")
    
    print(f"\n5. **建议**:")
    if consistency_rate > 0.8:
        print(f"   - 一致性较高（{consistency_rate:.1%}），任务建模选择相对稳定")
        print(f"   - 可以使用一个模型的选择结果应用到另一个模型")
    else:
        print(f"   - 一致性较低（{consistency_rate:.1%}），任务建模选择模型依赖性强")
        print(f"   - 建议为每个模型单独进行任务建模选择")


if __name__ == "__main__":
    main()
