#!/usr/bin/env python3
"""Analyze preference transition patterns and gap characteristics."""

import json
from pathlib import Path
from typing import Dict, Tuple

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


def compute_preferences_and_gaps(
    edit_ppl: Dict[str, float],
    gen_ppl: Dict[str, float]
) -> Tuple[Dict[str, str], Dict[str, float]]:
    """Compute preferred strategy and gap for each bug."""
    preferences = {}
    gaps = {}
    
    for slug in edit_ppl:
        if slug not in gen_ppl:
            continue
        
        edit_val = edit_ppl[slug]
        gen_val = gen_ppl[slug]
        
        preferences[slug] = 'edit' if edit_val < gen_val else 'gen'
        
        min_val = min(edit_val, gen_val)
        max_val = max(edit_val, gen_val)
        rel_diff = (max_val - min_val) / min_val if min_val > 0 else 0
        gaps[slug] = rel_diff * 100
    
    return preferences, gaps


def main():
    """Main analysis function."""
    print("=" * 100)
    print("偏好转移模式分析 - 深入理解模型偏好差异")
    print("=" * 100)
    
    data_dir = Path("bug_task_model_selection/data/ppl")
    
    # Load all PPL scores
    coder_edit = load_ppl_scores(data_dir / "qwen3_coder_edit.jsonl")
    coder_gen = load_ppl_scores(data_dir / "qwen3_coder_gen.jsonl")
    b30_edit = load_ppl_scores(data_dir / "qwen3_30b_edit.jsonl")
    b30_gen = load_ppl_scores(data_dir / "qwen3_30b_gen.jsonl")
    
    # Compute preferences and gaps
    coder_pref, coder_gaps = compute_preferences_and_gaps(coder_edit, coder_gen)
    b30_pref, b30_gaps = compute_preferences_and_gaps(b30_edit, b30_gen)
    
    common_bugs = set(coder_pref.keys()) & set(b30_pref.keys())
    
    # Categorize bugs by transition pattern
    edit_to_edit = [s for s in common_bugs 
                    if coder_pref[s] == 'edit' and b30_pref[s] == 'edit']
    edit_to_gen = [s for s in common_bugs 
                   if coder_pref[s] == 'edit' and b30_pref[s] == 'gen']
    gen_to_edit = [s for s in common_bugs 
                   if coder_pref[s] == 'gen' and b30_pref[s] == 'edit']
    gen_to_gen = [s for s in common_bugs 
                  if coder_pref[s] == 'gen' and b30_pref[s] == 'gen']
    
    print("\n## 1. 转移模式统计\n")
    print(f"Edit → Edit: {len(edit_to_edit)} (稳定)")
    print(f"Edit → Gen: {len(edit_to_gen)} (转移)")
    print(f"Gen → Edit: {len(gen_to_edit)} (转移)")
    print(f"Gen → Gen: {len(gen_to_gen)} (稳定)")
    
    # Analyze gap characteristics for each transition pattern
    print("\n\n" + "=" * 100)
    print("2. 各转移模式的差距特征分析")
    print("=" * 100)
    
    patterns = [
        ("Edit → Edit (稳定)", edit_to_edit),
        ("Edit → Gen (转移)", edit_to_gen),
        ("Gen → Edit (转移)", gen_to_edit),
        ("Gen → Gen (稳定)", gen_to_gen)
    ]
    
    print("\n### 2.1 差距统计\n")
    print("| 转移模式 | 数量 | Coder 平均差距 | Coder 中位数 | 30b 平均差距 | 30b 中位数 |")
    print("|---------|------|---------------|-------------|-------------|-----------|")
    
    for pattern_name, bugs in patterns:
        if not bugs:
            continue
        
        coder_gaps_list = [coder_gaps[s] for s in bugs]
        b30_gaps_list = [b30_gaps[s] for s in bugs]
        
        print(f"| {pattern_name} | {len(bugs)} | "
              f"{np.mean(coder_gaps_list):.1f}% | "
              f"{np.median(coder_gaps_list):.1f}% | "
              f"{np.mean(b30_gaps_list):.1f}% | "
              f"{np.median(b30_gaps_list):.1f}% |")
    
    # Key insight: Are transition bugs low-gap bugs?
    print("\n\n" + "=" * 100)
    print("3. 关键问题：转移的 bugs 是否差距较小？")
    print("=" * 100)
    
    print("\n### 3.1 Edit → Gen 转移分析\n")
    
    # Categorize by gap size
    edit_to_gen_small = [s for s in edit_to_gen if coder_gaps[s] < 20]
    edit_to_gen_medium = [s for s in edit_to_gen if 20 <= coder_gaps[s] < 100]
    edit_to_gen_large = [s for s in edit_to_gen if coder_gaps[s] >= 100]
    
    print(f"总数: {len(edit_to_gen)}\n")
    print("按 qwen3_coder 差距分类:")
    print(f"  - 差距 < 20% (小): {len(edit_to_gen_small)} ({len(edit_to_gen_small)/len(edit_to_gen):.1%})")
    print(f"  - 差距 20-100% (中): {len(edit_to_gen_medium)} ({len(edit_to_gen_medium)/len(edit_to_gen):.1%})")
    print(f"  - 差距 ≥ 100% (大): {len(edit_to_gen_large)} ({len(edit_to_gen_large)/len(edit_to_gen):.1%})")
    
    print("\n**关键发现**:")
    if len(edit_to_gen_small) / len(edit_to_gen) > 0.5:
        print(f"  ✓ 超过一半 ({len(edit_to_gen_small)/len(edit_to_gen):.1%}) 的转移 bugs 差距很小 (< 20%)")
        print(f"  ✓ 这些 bugs 本来就是'差不多'的情况，转移是合理的")
    else:
        print(f"  ✗ 只有 {len(edit_to_gen_small)/len(edit_to_gen):.1%} 的转移 bugs 差距很小")
        print(f"  ✗ 大部分转移 bugs 差距较大，说明模型依赖性强")
    
    print("\n### 3.2 Gen → Edit 转移分析\n")
    
    gen_to_edit_small = [s for s in gen_to_edit if coder_gaps[s] < 20]
    gen_to_edit_medium = [s for s in gen_to_edit if 20 <= coder_gaps[s] < 100]
    gen_to_edit_large = [s for s in gen_to_edit if coder_gaps[s] >= 100]
    
    print(f"总数: {len(gen_to_edit)}\n")
    print("按 qwen3_coder 差距分类:")
    print(f"  - 差距 < 20% (小): {len(gen_to_edit_small)} ({len(gen_to_edit_small)/len(gen_to_edit):.1%})")
    print(f"  - 差距 20-100% (中): {len(gen_to_edit_medium)} ({len(gen_to_edit_medium)/len(gen_to_edit):.1%})")
    print(f"  - 差距 ≥ 100% (大): {len(gen_to_edit_large)} ({len(gen_to_edit_large)/len(gen_to_edit):.1%})")
    
    print("\n**关键发现**:")
    if len(gen_to_edit_small) / len(gen_to_edit) > 0.5:
        print(f"  ✓ 超过一半 ({len(gen_to_edit_small)/len(gen_to_edit):.1%}) 的转移 bugs 差距很小 (< 20%)")
        print(f"  ✓ 这些 bugs 本来就是'差不多'的情况，转移是合理的")
    else:
        print(f"  ✗ 只有 {len(gen_to_edit_small)/len(gen_to_edit):.1%} 的转移 bugs 差距很小")
        print(f"  ✗ 大部分转移 bugs 差距较大，说明模型依赖性强")
    
    # Compare stable vs transition bugs
    print("\n\n" + "=" * 100)
    print("4. 稳定 vs 转移 bugs 的差距对比")
    print("=" * 100)
    
    stable_bugs = edit_to_edit + gen_to_gen
    transition_bugs = edit_to_gen + gen_to_edit
    
    stable_coder_gaps = [coder_gaps[s] for s in stable_bugs]
    stable_b30_gaps = [b30_gaps[s] for s in stable_bugs]
    transition_coder_gaps = [coder_gaps[s] for s in transition_bugs]
    transition_b30_gaps = [b30_gaps[s] for s in transition_bugs]
    
    print("\n| 类型 | 数量 | Coder 平均差距 | Coder 中位数 | 30b 平均差距 | 30b 中位数 |")
    print("|------|------|---------------|-------------|-------------|-----------|")
    print(f"| 稳定 | {len(stable_bugs)} | "
          f"{np.mean(stable_coder_gaps):.1f}% | "
          f"{np.median(stable_coder_gaps):.1f}% | "
          f"{np.mean(stable_b30_gaps):.1f}% | "
          f"{np.median(stable_b30_gaps):.1f}% |")
    print(f"| 转移 | {len(transition_bugs)} | "
          f"{np.mean(transition_coder_gaps):.1f}% | "
          f"{np.median(transition_coder_gaps):.1f}% | "
          f"{np.mean(transition_b30_gaps):.1f}% | "
          f"{np.median(transition_b30_gaps):.1f}% |")
    
    print("\n**对比**:")
    print(f"  - 稳定 bugs 的 coder 中位数差距: {np.median(stable_coder_gaps):.1f}%")
    print(f"  - 转移 bugs 的 coder 中位数差距: {np.median(transition_coder_gaps):.1f}%")
    print(f"  - 差异: {np.median(stable_coder_gaps) - np.median(transition_coder_gaps):.1f}%")
    
    # Answer the key question
    print("\n\n" + "=" * 100)
    print("5. 回答关键问题")
    print("=" * 100)
    
    print("\n### 问题 1: 'coder 更适合 gen' 这个说法对吗？\n")
    
    print(f"**数据**:")
    print(f"  - qwen3_coder: Gen 偏好 {len([s for s in coder_pref.values() if s == 'gen'])} / {len(coder_pref)} = "
          f"{len([s for s in coder_pref.values() if s == 'gen'])/len(coder_pref):.1%}")
    print(f"  - qwen3_30b: Edit 偏好 {len([s for s in b30_pref.values() if s == 'edit'])} / {len(b30_pref)} = "
          f"{len([s for s in b30_pref.values() if s == 'edit'])/len(b30_pref):.1%}")
    
    print(f"\n**解释**:")
    print(f"  - 'coder 更适合 gen' 是指：在 698 个 bugs 中，有 55.6% 用 gen 更好")
    print(f"  - 这是一个**整体统计**，不是说 coder 模型本身偏向 gen")
    print(f"  - 而是说：对于这个数据集，coder 在 gen 模式下表现更好的 bugs 更多")
    
    print(f"\n### 问题 2: Edit → Gen 转移的 bugs 是否差距很小？\n")
    
    small_ratio = len(edit_to_gen_small) / len(edit_to_gen)
    
    print(f"**数据**:")
    print(f"  - Edit → Gen 转移: {len(edit_to_gen)} 个")
    print(f"  - 其中差距 < 20%: {len(edit_to_gen_small)} ({small_ratio:.1%})")
    print(f"  - 其中差距 ≥ 100%: {len(edit_to_gen_large)} ({len(edit_to_gen_large)/len(edit_to_gen):.1%})")
    
    print(f"\n**结论**:")
    if small_ratio > 0.3:
        print(f"  ✓ 有 {small_ratio:.1%} 的转移 bugs 差距很小 (< 20%)")
        print(f"  ✓ 这部分转移是合理的，因为本来就差不多")
        print(f"  ✓ 但仍有 {1-small_ratio:.1%} 的转移 bugs 差距较大")
        print(f"  ✓ 说明模型依赖性确实存在，但不是全部原因")
    else:
        print(f"  ✗ 只有 {small_ratio:.1%} 的转移 bugs 差距很小")
        print(f"  ✗ 大部分转移 bugs 差距较大 ({1-small_ratio:.1%})")
        print(f"  ✗ 说明模型依赖性很强，不能简单归因于'差不多'")
    
    print(f"\n### 问题 3: 如何理解 37.4% 的 Edit → Gen 转移？\n")
    
    print(f"**分解分析**:")
    print(f"  1. 差距 < 20% 的转移: {len(edit_to_gen_small)} / {len(edit_to_gen)} = {small_ratio:.1%}")
    print(f"     → 这些是'差不多'的情况，转移可以理解")
    print(f"  2. 差距 ≥ 20% 的转移: {len(edit_to_gen_medium) + len(edit_to_gen_large)} / {len(edit_to_gen)} = "
          f"{(len(edit_to_gen_medium) + len(edit_to_gen_large))/len(edit_to_gen):.1%}")
    print(f"     → 这些是真正的模型依赖性，不能简单解释")
    
    print(f"\n**最终答案**:")
    print(f"  - 37.4% 的 Edit → Gen 转移中：")
    print(f"    - 约 {small_ratio:.1%} 可以归因于'差距小，差不多'")
    print(f"    - 约 {1-small_ratio:.1%} 是真正的模型依赖性")
    print(f"  - 所以不能说'coder 更适合 gen'是错的")
    print(f"  - 而是说：任务建模选择确实有模型依赖性")
    print(f"  - 但也有一部分转移是因为差距本来就小")


if __name__ == "__main__":
    main()
