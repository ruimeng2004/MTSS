#!/usr/bin/env python3
"""Analyze PPL gap between edit and gen to study task modeling sensitivity.

This analysis helps answer: How many bugs have significant PPL differences
between edit and gen? Should we use a 3-class system (edit/gen/default)?
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def load_ppl_scores(path: Path) -> Dict[str, float]:
    """Load PPL scores from JSONL file.
    
    Args:
        path: Path to PPL JSONL file.
    
    Returns:
        Dictionary mapping slug to PPL score.
    """
    scores = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            slug = obj.get('slug')
            value = obj.get('value')
            if slug and value is not None:
                scores[slug] = float(value)
    return scores


def compute_ppl_gap_stats(
    edit_ppl: Dict[str, float],
    gen_ppl: Dict[str, float]
) -> pd.DataFrame:
    """Compute PPL gap statistics for all bugs.
    
    Args:
        edit_ppl: Edit PPL scores.
        gen_ppl: Gen PPL scores.
    
    Returns:
        DataFrame with gap analysis.
    """
    data = []
    
    for slug in edit_ppl:
        if slug not in gen_ppl:
            continue
        
        edit_val = edit_ppl[slug]
        gen_val = gen_ppl[slug]
        
        # Absolute difference
        abs_diff = abs(edit_val - gen_val)
        
        # Relative difference (percentage)
        min_val = min(edit_val, gen_val)
        max_val = max(edit_val, gen_val)
        rel_diff = (max_val - min_val) / min_val if min_val > 0 else 0
        
        # Which is better
        better = 'edit' if edit_val < gen_val else 'gen'
        
        data.append({
            'slug': slug,
            'edit_ppl': edit_val,
            'gen_ppl': gen_val,
            'abs_diff': abs_diff,
            'rel_diff': rel_diff,
            'better': better
        })
    
    return pd.DataFrame(data)


def categorize_bugs(df: pd.DataFrame) -> pd.DataFrame:
    """Categorize bugs based on PPL gap.
    
    Categories:
    - negligible: rel_diff < 5% (差不多，可以用默认)
    - small: 5% <= rel_diff < 20% (有差异但不大)
    - medium: 20% <= rel_diff < 50% (明显差异)
    - large: 50% <= rel_diff < 100% (很大差异)
    - huge: rel_diff >= 100% (巨大差异)
    
    Args:
        df: DataFrame with PPL gap data.
    
    Returns:
        DataFrame with category column added.
    """
    df = df.copy()
    
    def categorize(rel_diff: float) -> str:
        if rel_diff < 0.05:
            return 'negligible'
        elif rel_diff < 0.20:
            return 'small'
        elif rel_diff < 0.50:
            return 'medium'
        elif rel_diff < 1.00:
            return 'large'
        else:
            return 'huge'
    
    df['category'] = df['rel_diff'].apply(categorize)
    
    return df


def main():
    """Main analysis function."""
    print("=" * 100)
    print("PPL 差距分析 - 任务建模敏感性研究")
    print("=" * 100)
    print("\n目标: 分析有多少 bug 对 edit/gen 敏感，是否需要三分类系统\n")
    
    data_dir = Path("bug_task_model_selection/data/ppl")
    
    models = [
        ('qwen3_coder', 'qwen3_coder_edit.jsonl', 'qwen3_coder_gen.jsonl'),
        ('qwen3_30b', 'qwen3_30b_edit.jsonl', 'qwen3_30b_gen.jsonl')
    ]
    
    all_results = {}
    
    for model_name, edit_file, gen_file in models:
        print(f"\n{'=' * 100}")
        print(f"模型: {model_name}")
        print("=" * 100)
        
        # Load PPL scores
        edit_ppl = load_ppl_scores(data_dir / edit_file)
        gen_ppl = load_ppl_scores(data_dir / gen_file)
        
        print(f"\n加载数据: {len(edit_ppl)} edit PPL, {len(gen_ppl)} gen PPL")
        
        # Compute gap statistics
        df = compute_ppl_gap_stats(edit_ppl, gen_ppl)
        df = categorize_bugs(df)
        
        all_results[model_name] = df
        
        print(f"共分析 {len(df)} 个 bugs\n")
        
        # Overall statistics
        print("## 1. 整体统计\n")
        print(f"平均 Edit PPL: {df['edit_ppl'].mean():.4f}")
        print(f"平均 Gen PPL: {df['gen_ppl'].mean():.4f}")
        print(f"平均绝对差距: {df['abs_diff'].mean():.4f}")
        print(f"平均相对差距: {df['rel_diff'].mean():.1%}")
        print(f"中位数相对差距: {df['rel_diff'].median():.1%}")
        
        # Category distribution
        print("\n## 2. 差距分类分布\n")
        print("| 类别 | 相对差距范围 | 数量 | 占比 | 说明 |")
        print("|------|-------------|------|------|------|")
        
        category_order = ['negligible', 'small', 'medium', 'large', 'huge']
        category_labels = {
            'negligible': '< 5%',
            'small': '5-20%',
            'medium': '20-50%',
            'large': '50-100%',
            'huge': '≥ 100%'
        }
        category_desc = {
            'negligible': '几乎无差异，可用默认',
            'small': '有差异但不大',
            'medium': '明显差异',
            'large': '很大差异',
            'huge': '巨大差异'
        }
        
        for cat in category_order:
            count = (df['category'] == cat).sum()
            pct = count / len(df)
            print(f"| {cat} | {category_labels[cat]} | {count} | "
                  f"{pct:.1%} | {category_desc[cat]} |")
        
        # Better strategy distribution
        print("\n## 3. 最优策略分布\n")
        better_counts = df['better'].value_counts()
        print(f"Edit 更好: {better_counts.get('edit', 0)} ({better_counts.get('edit', 0)/len(df):.1%})")
        print(f"Gen 更好: {better_counts.get('gen', 0)} ({better_counts.get('gen', 0)/len(df):.1%})")
        
        # Percentile analysis
        print("\n## 4. 相对差距百分位数\n")
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        print("| 百分位 | 相对差距 | 说明 |")
        print("|--------|----------|------|")
        for p in percentiles:
            val = np.percentile(df['rel_diff'], p)
            print(f"| P{p} | {val:.1%} | {p}% 的 bug 差距小于此值 |")
        
        # Top 10 largest gaps
        print("\n## 5. 差距最大的 10 个 bugs\n")
        print("| Rank | Slug | Edit PPL | Gen PPL | 相对差距 | 更好的策略 |")
        print("|------|------|----------|---------|----------|-----------|")
        top10 = df.nlargest(10, 'rel_diff')
        for i, (_, row) in enumerate(top10.iterrows(), 1):
            print(f"| {i} | {row['slug'][:30]}... | {row['edit_ppl']:.4f} | "
                  f"{row['gen_ppl']:.4f} | {row['rel_diff']:.1%} | {row['better']} |")
        
        # Top 10 smallest gaps
        print("\n## 6. 差距最小的 10 个 bugs\n")
        print("| Rank | Slug | Edit PPL | Gen PPL | 相对差距 | 更好的策略 |")
        print("|------|------|----------|---------|----------|-----------|")
        bottom10 = df.nsmallest(10, 'rel_diff')
        for i, (_, row) in enumerate(bottom10.iterrows(), 1):
            print(f"| {i} | {row['slug'][:30]}... | {row['edit_ppl']:.4f} | "
                  f"{row['gen_ppl']:.4f} | {row['rel_diff']:.1%} | {row['better']} |")
    
    # Cross-model comparison
    print("\n\n" + "=" * 100)
    print("两个模型对比")
    print("=" * 100)
    
    if len(all_results) == 2:
        coder_df = all_results['qwen3_coder']
        b30_df = all_results['qwen3_30b']
        
        print("\n## 差距分类分布对比\n")
        print("| 类别 | qwen3_coder | qwen3_30b | 差异 |")
        print("|------|-------------|-----------|------|")
        
        for cat in category_order:
            coder_pct = (coder_df['category'] == cat).sum() / len(coder_df)
            b30_pct = (b30_df['category'] == cat).sum() / len(b30_df)
            diff = b30_pct - coder_pct
            print(f"| {cat} | {coder_pct:.1%} | {b30_pct:.1%} | {diff:+.1%} |")
    
    # Final recommendations
    print("\n\n" + "=" * 100)
    print("结论与建议")
    print("=" * 100)
    
    for model_name, df in all_results.items():
        print(f"\n## {model_name}:\n")
        
        negligible_pct = (df['category'] == 'negligible').sum() / len(df)
        small_pct = (df['category'] == 'small').sum() / len(df)
        significant_pct = 1 - negligible_pct - small_pct
        
        print(f"1. **差距可忽略 (< 5%)**: {negligible_pct:.1%}")
        print(f"   - 这些 bug 用 edit 或 gen 差不多，可以用默认策略")
        print(f"\n2. **差距较小 (5-20%)**: {small_pct:.1%}")
        print(f"   - 有差异但不大，选择的收益有限")
        print(f"\n3. **差距显著 (≥ 20%)**: {significant_pct:.1%}")
        print(f"   - 这些 bug 对任务建模敏感，选择很重要")
        
        print(f"\n**三分类系统建议**:")
        if negligible_pct > 0.2:
            print(f"- ✓ 建议引入'默认'类别")
            print(f"- {negligible_pct:.1%} 的 bug 可以跳过选择，节省计算成本")
        else:
            print(f"- ✗ 不建议引入'默认'类别")
            print(f"- 只有 {negligible_pct:.1%} 的 bug 差距可忽略，收益有限")
        
        print(f"\n**阈值建议**:")
        p25 = np.percentile(df['rel_diff'], 25)
        print(f"- 如果相对差距 < {p25:.1%}，使用默认策略（覆盖 25% 的 bug）")
        print(f"- 如果相对差距 ≥ {p25:.1%}，进行任务建模选择")


if __name__ == "__main__":
    main()
