#!/usr/bin/env python3
"""Compare cluster balance across different algorithms."""

import json
from pathlib import Path
from collections import Counter
import numpy as np


def analyze_cluster_balance(view: str, k: int, algorithm: str):
    """Analyze cluster balance for a specific configuration.
    
    Args:
        view: View type.
        k: Number of clusters.
        algorithm: Clustering algorithm.
    
    Returns:
        Dictionary with balance metrics.
    """
    # For bisecting_kmeans and other algorithms, clustering is done per view
    # The algorithm parameter doesn't affect the clustering itself in this setup
    path = Path(f"bug_task_model_selection/data/clusters_{view}/cuts/"
                f"k={k}/assignments.jsonl")
    
    if not path.exists():
        return None
    
    assignments = {}
    with open(path, 'r') as f:
        for line in f:
            obj = json.loads(line)
            item_id = obj['item_id']
            cluster_id = obj['cluster_id']
            slug = item_id.rsplit('__', 1)[0]
            assignments[slug] = cluster_id
    
    # Count bugs per cluster
    cluster_counts = Counter(assignments.values())
    sizes = list(cluster_counts.values())
    
    if not sizes:
        return None
    
    return {
        'n_clusters': len(cluster_counts),
        'total_bugs': len(assignments),
        'min_size': min(sizes),
        'max_size': max(sizes),
        'mean_size': np.mean(sizes),
        'median_size': np.median(sizes),
        'std_size': np.std(sizes),
        'cv': np.std(sizes) / np.mean(sizes),
        'size_distribution': dict(Counter(sizes)),
        'single_point_clusters': sum(1 for s in sizes if s == 1),
        'single_point_pct': sum(1 for s in sizes if s == 1) / len(sizes)
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("Bisecting KMeans vs 其他算法的簇平衡性对比")
    print("=" * 100)
    
    # Best configs using bisecting_kmeans
    bisecting_configs = [
        {'model': 'qwen3_coder', 'k': 100, 'view': 'buggy_code_mixed'},
        {'model': 'qwen3_coder', 'k': 150, 'view': 'buggy_code_obfuscated'},
        {'model': 'qwen3_coder', 'k': 200, 'view': 'buggy_code_obfuscated'},
        {'model': 'qwen3_30b', 'k': 150, 'view': 'buggy_code_obfuscated'},
        {'model': 'qwen3_30b', 'k': 300, 'view': 'buggy_code_mixed'},
    ]
    
    # Compare with other algorithms at same K
    other_configs = [
        {'model': 'qwen3_coder', 'k': 50, 'view': 'buggy_code_mixed', 
         'algorithm': 'hac_complete'},
        {'model': 'qwen3_coder', 'k': 300, 'view': 'buggy_code_mixed',
         'algorithm': 'hac_single'},
        {'model': 'qwen3_coder', 'k': 500, 'view': 'buggy_code_obfuscated',
         'algorithm': 'hac_single'},
        {'model': 'qwen3_30b', 'k': 50, 'view': 'buggy_code_obfuscated',
         'algorithm': 'kmeans'},
        {'model': 'qwen3_30b', 'k': 100, 'view': 'report',
         'algorithm': 'kmeans'},
        {'model': 'qwen3_30b', 'k': 200, 'view': 'buggy_code_mixed',
         'algorithm': 'kmeans'},
        {'model': 'qwen3_30b', 'k': 500, 'view': 'report',
         'algorithm': 'hac_single'},
    ]
    
    print("\n## Bisecting KMeans 配置的簇平衡性\n")
    print("| Model | K | View | CV | 单点簇% | 最小 | 最大 | 平均 | 中位数 |")
    print("|-------|---|------|-----|---------|------|------|------|--------|")
    
    bisecting_stats = []
    for config in bisecting_configs:
        stats = analyze_cluster_balance(
            config['view'], config['k'], 'bisecting_kmeans'
        )
        if stats:
            bisecting_stats.append({**config, **stats})
            print(f"| {config['model'].split('_')[1]} | {config['k']} | "
                  f"{config['view'][:15]}... | {stats['cv']:.3f} | "
                  f"{stats['single_point_pct']:.1%} | {stats['min_size']} | "
                  f"{stats['max_size']} | {stats['mean_size']:.1f} | "
                  f"{stats['median_size']:.1f} |")
    
    print("\n## 其他算法配置的簇平衡性\n")
    print("| Model | K | View | Algorithm | CV | 单点簇% | 最小 | 最大 | "
          "平均 | 中位数 |")
    print("|-------|---|------|-----------|-----|---------|------|------|------|"
          "--------|")
    
    other_stats = []
    for config in other_configs:
        stats = analyze_cluster_balance(
            config['view'], config['k'], config['algorithm']
        )
        if stats:
            other_stats.append({**config, **stats})
            print(f"| {config['model'].split('_')[1]} | {config['k']} | "
                  f"{config['view'][:10]}... | {config['algorithm'][:8]}... | "
                  f"{stats['cv']:.3f} | {stats['single_point_pct']:.1%} | "
                  f"{stats['min_size']} | {stats['max_size']} | "
                  f"{stats['mean_size']:.1f} | {stats['median_size']:.1f} |")
    
    # Statistical comparison
    print("\n## 统计对比\n")
    
    bisecting_cvs = [s['cv'] for s in bisecting_stats]
    other_cvs = [s['cv'] for s in other_stats]
    
    bisecting_single_pcts = [s['single_point_pct'] for s in bisecting_stats]
    other_single_pcts = [s['single_point_pct'] for s in other_stats]
    
    bisecting_max_sizes = [s['max_size'] for s in bisecting_stats]
    other_max_sizes = [s['max_size'] for s in other_stats]
    
    print(f"**变异系数 (CV):**")
    print(f"- Bisecting KMeans 平均: {np.mean(bisecting_cvs):.3f}")
    print(f"- 其他算法平均: {np.mean(other_cvs):.3f}")
    print(f"- 差异: {np.mean(bisecting_cvs) - np.mean(other_cvs):.3f}")
    print()
    
    print(f"**单点簇占比:**")
    print(f"- Bisecting KMeans 平均: {np.mean(bisecting_single_pcts):.1%}")
    print(f"- 其他算法平均: {np.mean(other_single_pcts):.1%}")
    print(f"- 差异: {np.mean(bisecting_single_pcts) - np.mean(other_single_pcts):.1%}")
    print()
    
    print(f"**最大簇大小:**")
    print(f"- Bisecting KMeans 平均: {np.mean(bisecting_max_sizes):.1f}")
    print(f"- 其他算法平均: {np.mean(other_max_sizes):.1f}")
    print(f"- 差异: {np.mean(bisecting_max_sizes) - np.mean(other_max_sizes):.1f}")
    print()
    
    # Detailed analysis by K
    print("\n## 按 K 值分组对比\n")
    
    k_values = sorted(set([s['k'] for s in bisecting_stats + other_stats]))
    
    for k in k_values:
        bisecting_k = [s for s in bisecting_stats if s['k'] == k]
        other_k = [s for s in other_stats if s['k'] == k]
        
        if not bisecting_k or not other_k:
            continue
        
        print(f"### K={k}")
        print(f"- Bisecting KMeans: CV={np.mean([s['cv'] for s in bisecting_k]):.3f}, "
              f"单点簇={np.mean([s['single_point_pct'] for s in bisecting_k]):.1%}, "
              f"最大簇={np.mean([s['max_size'] for s in bisecting_k]):.1f}")
        print(f"- 其他算法: CV={np.mean([s['cv'] for s in other_k]):.3f}, "
              f"单点簇={np.mean([s['single_point_pct'] for s in other_k]):.1%}, "
              f"最大簇={np.mean([s['max_size'] for s in other_k]):.1f}")
        print()
    
    # Conclusion
    print("\n## 结论\n")
    
    if np.mean(bisecting_cvs) < np.mean(other_cvs):
        print("✓ Bisecting KMeans 的簇平衡性**更好**（CV 更低）")
    else:
        print("✗ Bisecting KMeans 的簇平衡性**更差**（CV 更高）")
    
    if np.mean(bisecting_single_pcts) < np.mean(other_single_pcts):
        print("✓ Bisecting KMeans 产生**更少**的单点簇")
    else:
        print("✗ Bisecting KMeans 产生**更多**的单点簇")
    
    if np.mean(bisecting_max_sizes) < np.mean(other_max_sizes):
        print("✓ Bisecting KMeans 的最大簇**更小**（更均衡）")
    else:
        print("✗ Bisecting KMeans 的最大簇**更大**（更不均衡）")


if __name__ == "__main__":
    main()
