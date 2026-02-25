#!/usr/bin/env python3
"""Exploratory analysis for 'both' strategy in task modeling selection."""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import numpy as np


def load_ppl_data(model: str) -> Dict[str, Dict[str, float]]:
    """Load aggregated PPL data.
    
    Args:
        model: Model name (qwen3_coder or qwen3_30b).
    
    Returns:
        Dictionary mapping slug to {edit_ppl, gen_ppl}.
    """
    ppl_data = {}
    
    for task in ['edit', 'gen']:
        path = Path(f"bug_task_model_selection/data/ppl/{model}_{task}.jsonl")
        if not path.exists():
            print(f"Warning: {path} not found")
            continue
        
        with open(path, 'r') as f:
            for line in f:
                obj = json.loads(line)
                slug = obj['slug']
                ppl = obj['value']  # Field name is 'value' not 'ppl'
                
                if slug not in ppl_data:
                    ppl_data[slug] = {}
                ppl_data[slug][f'{task}_ppl'] = ppl
    
    return ppl_data


def load_cluster_assignments(view: str, k: int) -> Dict[str, int]:
    """Load cluster assignments."""
    path = Path(f"bug_task_model_selection/data/clusters_{view}/cuts/"
                f"k={k}/assignments.jsonl")
    
    if not path.exists():
        return {}
    
    assignments = {}
    with open(path, 'r') as f:
        for line in f:
            obj = json.loads(line)
            item_id = obj['item_id']
            cluster_id = obj['cluster_id']
            slug = item_id.rsplit('__', 1)[0]
            assignments[slug] = cluster_id
    
    return assignments


def calculate_ppl_gap(edit_ppl: float, gen_ppl: float) -> Dict[str, float]:
    """Calculate various PPL gap metrics.
    
    Returns:
        Dictionary with different gap metrics.
    """
    abs_diff = abs(edit_ppl - gen_ppl)
    rel_diff = abs_diff / min(edit_ppl, gen_ppl)
    normalized_gap = abs(edit_ppl - gen_ppl) / (edit_ppl + gen_ppl)
    
    return {
        'abs_diff': abs_diff,
        'rel_diff_pct': rel_diff * 100,
        'normalized_gap': normalized_gap,
        'better': 'edit' if edit_ppl < gen_ppl else 'gen'
    }


def analyze_bug_level_gaps(model: str, thresholds: List[float]):
    """Analyze PPL gaps at bug level.
    
    Args:
        model: Model name.
        thresholds: List of thresholds to test (as percentages).
    """
    print(f"\n{'=' * 100}")
    print(f"问题1: {model} - Bug 级别的 PPL 差距分布")
    print(f"{'=' * 100}\n")
    
    ppl_data = load_ppl_data(model)
    
    gaps = []
    for slug, data in ppl_data.items():
        if 'edit_ppl' in data and 'gen_ppl' in data:
            gap_metrics = calculate_ppl_gap(data['edit_ppl'], data['gen_ppl'])
            gaps.append(gap_metrics)
    
    print(f"总 bugs 数: {len(gaps)}\n")
    
    # Distribution of relative differences
    rel_diffs = [g['rel_diff_pct'] for g in gaps]
    
    print("## 相对差距分布 (百分比)\n")
    print(f"最小值: {min(rel_diffs):.1f}%")
    print(f"最大值: {max(rel_diffs):.1f}%")
    print(f"平均值: {np.mean(rel_diffs):.1f}%")
    print(f"中位数: {np.median(rel_diffs):.1f}%")
    print(f"标准差: {np.std(rel_diffs):.1f}%")
    print()
    
    # Percentiles
    print("## 百分位数\n")
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    for p in percentiles:
        val = np.percentile(rel_diffs, p)
        print(f"P{p}: {val:.1f}%")
    print()
    
    # Count bugs below different thresholds
    print("## 不同阈值下的 'both' 候选 bugs\n")
    print("| 阈值 | Bugs 数量 | 占比 | 说明 |")
    print("|------|----------|------|------|")
    
    for threshold in thresholds:
        count = sum(1 for g in gaps if g['rel_diff_pct'] < threshold)
        pct = count / len(gaps) * 100
        
        if threshold <= 5:
            desc = "极小差距"
        elif threshold <= 10:
            desc = "很小差距"
        elif threshold <= 20:
            desc = "小差距"
        elif threshold <= 30:
            desc = "中等差距"
        else:
            desc = "较大差距"
        
        print(f"| <{threshold}% | {count} | {pct:.1f}% | {desc} |")
    print()
    
    # Normalized gap distribution
    norm_gaps = [g['normalized_gap'] for g in gaps]
    print("## 归一化差距分布\n")
    print(f"平均值: {np.mean(norm_gaps):.3f}")
    print(f"中位数: {np.median(norm_gaps):.3f}")
    print()
    
    return ppl_data, gaps


def analyze_cluster_level_gaps(
    model: str, 
    view: str, 
    k: int,
    ppl_data: Dict[str, Dict[str, float]],
    thresholds: List[float]
):
    """Analyze PPL gaps at cluster level.
    
    Args:
        model: Model name.
        view: View type.
        k: Number of clusters.
        ppl_data: PPL data for all bugs.
        thresholds: List of thresholds to test.
    """
    print(f"\n{'=' * 100}")
    print(f"问题2: {model} K={k} - Cluster 级别的 PPL 差距分布")
    print(f"{'=' * 100}\n")
    
    assignments = load_cluster_assignments(view, k)
    
    if not assignments:
        print("⚠️ 未找到聚类数据\n")
        return
    
    # Group bugs by cluster
    clusters = defaultdict(list)
    for slug, cluster_id in assignments.items():
        if slug in ppl_data:
            clusters[cluster_id].append(slug)
    
    # Calculate metrics per cluster
    cluster_stats = []
    
    for cluster_id, members in clusters.items():
        if len(members) == 0:
            continue
        
        # Calculate gaps for all members
        member_gaps = []
        edit_votes = 0
        gen_votes = 0
        
        for slug in members:
            data = ppl_data[slug]
            gap_metrics = calculate_ppl_gap(
                data['edit_ppl'], data['gen_ppl']
            )
            member_gaps.append(gap_metrics)
            
            if gap_metrics['better'] == 'edit':
                edit_votes += 1
            else:
                gen_votes += 1
        
        # Cluster-level metrics
        avg_rel_diff = np.mean([g['rel_diff_pct'] for g in member_gaps])
        vote_ratio = edit_votes / (edit_votes + gen_votes)
        
        # NEW: Calculate proportion of small-gap bugs for different thresholds
        small_gap_proportions = {}
        for threshold in thresholds:
            count = sum(1 for g in member_gaps if g['rel_diff_pct'] < threshold)
            small_gap_proportions[threshold] = count / len(members)
        
        cluster_stats.append({
            'cluster_id': cluster_id,
            'size': len(members),
            'avg_rel_diff': avg_rel_diff,
            'vote_ratio': vote_ratio,
            'edit_votes': edit_votes,
            'gen_votes': gen_votes,
            'small_gap_proportions': small_gap_proportions,
            'member_gaps': [g['rel_diff_pct'] for g in member_gaps]
        })
    
    print(f"总 clusters 数: {len(cluster_stats)}\n")
    
    # Distribution of cluster average gaps
    avg_rel_diffs = [c['avg_rel_diff'] for c in cluster_stats]
    
    print("## 方法1: Cluster 平均相对差距分布\n")
    print(f"最小值: {min(avg_rel_diffs):.1f}%")
    print(f"最大值: {max(avg_rel_diffs):.1f}%")
    print(f"平均值: {np.mean(avg_rel_diffs):.1f}%")
    print(f"中位数: {np.median(avg_rel_diffs):.1f}%")
    print()
    
    # NEW: Analyze proportion-based metric
    print("## 方法2: 差距小的 bugs 占比分析\n")
    
    for threshold in [10, 20, 30]:
        print(f"### 阈值 = {threshold}%\n")
        
        # Distribution of proportions across clusters
        proportions = [c['small_gap_proportions'][threshold] 
                      for c in cluster_stats]
        
        print(f"簇内小差距 bugs 占比的分布:")
        print(f"  最小值: {min(proportions):.1%}")
        print(f"  最大值: {max(proportions):.1%}")
        print(f"  平均值: {np.mean(proportions):.1%}")
        print(f"  中位数: {np.median(proportions):.1%}")
        print()
        
        # Count clusters by proportion ranges
        print("簇的分类（按小差距 bugs 占比）:")
        print("| 占比范围 | Clusters 数量 | 占比 | 包含 bugs |")
        print("|---------|--------------|------|----------|")
        
        ranges = [
            (0.0, 0.1, "0-10%"),
            (0.1, 0.3, "10-30%"),
            (0.3, 0.5, "30-50%"),
            (0.5, 0.7, "50-70%"),
            (0.7, 0.9, "70-90%"),
            (0.9, 1.01, "90-100%")
        ]
        
        for low, high, label in ranges:
            matching = [c for c in cluster_stats 
                       if low <= c['small_gap_proportions'][threshold] < high]
            count = len(matching)
            pct = count / len(cluster_stats) * 100
            total_bugs = sum(c['size'] for c in matching)
            print(f"| {label} | {count} | {pct:.1f}% | {total_bugs} |")
        print()
        
        # High-proportion clusters (>= 70%)
        high_prop_clusters = [
            c for c in cluster_stats 
            if c['small_gap_proportions'][threshold] >= 0.7
        ]
        
        if high_prop_clusters:
            print(f"**高占比簇（≥70% 成员差距 <{threshold}%）: "
                  f"{len(high_prop_clusters)} 个**")
            print(f"  包含 bugs: {sum(c['size'] for c in high_prop_clusters)}")
            print(f"  平均簇大小: {np.mean([c['size'] for c in high_prop_clusters]):.1f}")
            print()
    
    # Compare two methods
    print("## 两种方法的对比\n")
    
    for threshold in [10, 20]:
        print(f"### 阈值 = {threshold}%\n")
        
        # Method 1: Average gap < threshold
        method1_clusters = [c for c in cluster_stats 
                           if c['avg_rel_diff'] < threshold]
        method1_bugs = sum(c['size'] for c in method1_clusters)
        
        # Method 2: Proportion >= 70%
        method2_clusters = [c for c in cluster_stats 
                           if c['small_gap_proportions'][threshold] >= 0.7]
        method2_bugs = sum(c['size'] for c in method2_clusters)
        
        # Method 3: Proportion >= 50%
        method3_clusters = [c for c in cluster_stats 
                           if c['small_gap_proportions'][threshold] >= 0.5]
        method3_bugs = sum(c['size'] for c in method3_clusters)
        
        print("| 方法 | Clusters | Bugs | 说明 |")
        print("|------|---------|------|------|")
        print(f"| 平均差距 <{threshold}% | {len(method1_clusters)} | "
              f"{method1_bugs} | 传统方法 |")
        print(f"| ≥70% 成员差距 <{threshold}% | {len(method2_clusters)} | "
              f"{method2_bugs} | 严格标准 |")
        print(f"| ≥50% 成员差距 <{threshold}% | {len(method3_clusters)} | "
              f"{method3_bugs} | 宽松标准 |")
        print()
        
        # Overlap analysis
        method1_ids = set(c['cluster_id'] for c in method1_clusters)
        method2_ids = set(c['cluster_id'] for c in method2_clusters)
        overlap = len(method1_ids & method2_ids)
        
        print(f"方法1 和 方法2 的重叠: {overlap} 个簇")
        print()
    
    return cluster_stats


def compare_strategies(
    model: str,
    view: str,
    k: int,
    ppl_data: Dict[str, Dict[str, float]],
    threshold: float
):
    """Compare different strategies for 'both' classification.
    
    Args:
        model: Model name.
        view: View type.
        k: Number of clusters.
        ppl_data: PPL data.
        threshold: Threshold for 'both' classification (percentage).
    """
    print(f"\n{'=' * 100}")
    print(f"问题3: {model} K={k} - 不同策略对比 (阈值={threshold}%)")
    print(f"{'=' * 100}\n")
    
    assignments = load_cluster_assignments(view, k)
    
    if not assignments:
        print("⚠️ 未找到聚类数据\n")
        return
    
    # Group bugs by cluster
    clusters = defaultdict(list)
    for slug, cluster_id in assignments.items():
        if slug in ppl_data:
            clusters[cluster_id].append(slug)
    
    # Ground truth: bugs with gap < threshold
    ground_truth_both = set()
    for slug, data in ppl_data.items():
        gap = calculate_ppl_gap(data['edit_ppl'], data['gen_ppl'])
        if gap['rel_diff_pct'] < threshold:
            ground_truth_both.add(slug)
    
    print(f"Ground Truth: {len(ground_truth_both)} bugs 应该选 'both' "
          f"({len(ground_truth_both)/len(ppl_data)*100:.1f}%)\n")
    
    # Strategy 1: Cluster average gap
    strategy1_both_bugs = set()
    for cluster_id, members in clusters.items():
        gaps = [
            calculate_ppl_gap(
                ppl_data[slug]['edit_ppl'], 
                ppl_data[slug]['gen_ppl']
            )['rel_diff_pct']
            for slug in members
        ]
        avg_gap = np.mean(gaps)
        
        if avg_gap < threshold:
            strategy1_both_bugs.update(members)
    
    # Strategy 2: Vote ratio + average gap
    strategy2_both_bugs = set()
    for cluster_id, members in clusters.items():
        edit_votes = 0
        gen_votes = 0
        gaps = []
        
        for slug in members:
            gap = calculate_ppl_gap(
                ppl_data[slug]['edit_ppl'],
                ppl_data[slug]['gen_ppl']
            )
            gaps.append(gap['rel_diff_pct'])
            
            if gap['better'] == 'edit':
                edit_votes += 1
            else:
                gen_votes += 1
        
        vote_ratio = edit_votes / (edit_votes + gen_votes)
        avg_gap = np.mean(gaps)
        
        # Two-stage decision
        if 0.4 <= vote_ratio <= 0.6:  # Balanced votes
            if avg_gap < threshold:  # Small gap
                strategy2_both_bugs.update(members)
    
    # Evaluate strategies
    print("## 策略1: 仅基于 Cluster 平均差距\n")
    s1_correct = len(strategy1_both_bugs & ground_truth_both)
    s1_precision = (s1_correct / len(strategy1_both_bugs) 
                   if strategy1_both_bugs else 0)
    s1_recall = s1_correct / len(ground_truth_both)
    s1_f1 = (2 * s1_precision * s1_recall / (s1_precision + s1_recall)
            if (s1_precision + s1_recall) > 0 else 0)
    
    print(f"预测为 'both': {len(strategy1_both_bugs)} bugs")
    print(f"正确预测: {s1_correct} bugs")
    print(f"Precision: {s1_precision:.1%}")
    print(f"Recall: {s1_recall:.1%}")
    print(f"F1 Score: {s1_f1:.1%}")
    print()
    
    print("## 策略2: 投票比例 + 平均差距 (两阶段)\n")
    s2_correct = len(strategy2_both_bugs & ground_truth_both)
    s2_precision = (s2_correct / len(strategy2_both_bugs)
                   if strategy2_both_bugs else 0)
    s2_recall = s2_correct / len(ground_truth_both)
    s2_f1 = (2 * s2_precision * s2_recall / (s2_precision + s2_recall)
            if (s2_precision + s2_recall) > 0 else 0)
    
    print(f"预测为 'both': {len(strategy2_both_bugs)} bugs")
    print(f"正确预测: {s2_correct} bugs")
    print(f"Precision: {s2_precision:.1%}")
    print(f"Recall: {s2_recall:.1%}")
    print(f"F1 Score: {s2_f1:.1%}")
    print()
    
    print("## 策略对比\n")
    print("| 策略 | Precision | Recall | F1 | 预测数量 |")
    print("|------|-----------|--------|-----|---------|")
    print(f"| 策略1 (平均差距) | {s1_precision:.1%} | {s1_recall:.1%} | "
          f"{s1_f1:.1%} | {len(strategy1_both_bugs)} |")
    print(f"| 策略2 (两阶段) | {s2_precision:.1%} | {s2_recall:.1%} | "
          f"{s2_f1:.1%} | {len(strategy2_both_bugs)} |")
    print()


def main():
    """Main analysis function."""
    print("=" * 100)
    print("'Both' 策略探索性分析")
    print("=" * 100)
    
    models = ['qwen3_coder', 'qwen3_30b']
    thresholds = [5, 10, 15, 20, 30, 50]
    
    # Best configs for detailed analysis
    best_configs = {
        'qwen3_coder': [
            {'k': 100, 'view': 'buggy_code_mixed'},
            {'k': 500, 'view': 'buggy_code_obfuscated'},
        ],
        'qwen3_30b': [
            {'k': 100, 'view': 'report'},
            {'k': 500, 'view': 'report'},
        ]
    }
    
    for model in models:
        # Question 1: Bug-level gaps
        ppl_data, gaps = analyze_bug_level_gaps(model, thresholds)
        
        # Question 2 & 3: Cluster-level analysis
        for config in best_configs[model]:
            k = config['k']
            view = config['view']
            
            cluster_gaps = analyze_cluster_level_gaps(
                model, view, k, ppl_data, thresholds
            )
            
            # Compare strategies with different thresholds
            for threshold in [10, 20]:
                compare_strategies(model, view, k, ppl_data, threshold)
    
    print("\n" + "=" * 100)
    print("分析完成")
    print("=" * 100)


if __name__ == "__main__":
    main()
