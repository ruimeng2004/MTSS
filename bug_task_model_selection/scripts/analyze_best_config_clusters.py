#!/usr/bin/env python3
"""Analyze cluster size distribution for best configurations."""

import json
from pathlib import Path
from collections import Counter
from typing import Dict, List

import numpy as np


def load_assignments(path: Path) -> Dict[str, int]:
    """Load cluster assignments from JSONL file.
    
    Returns:
        Dictionary mapping item_id to cluster_id.
    """
    assignments = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            item_id = obj.get('item_id')
            cluster_id = obj.get('cluster_id')
            if item_id and cluster_id is not None:
                assignments[item_id] = int(cluster_id)
    return assignments


def analyze_cluster_sizes(assignments: Dict[str, int]) -> Dict:
    """Analyze cluster size distribution.
    
    Args:
        assignments: Dictionary mapping slug to cluster_id.
    
    Returns:
        Dictionary with cluster size statistics.
    """
    # Count bugs per cluster
    cluster_counts = Counter(assignments.values())
    sizes = list(cluster_counts.values())
    
    if not sizes:
        return {}
    
    return {
        'n_clusters': len(cluster_counts),
        'total_bugs': len(assignments),
        'min_size': min(sizes),
        'max_size': max(sizes),
        'mean_size': np.mean(sizes),
        'median_size': np.median(sizes),
        'std_size': np.std(sizes),
        'size_distribution': dict(Counter(sizes)),
        'cluster_sizes': dict(cluster_counts)
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("最佳配置的聚类簇大小分析")
    print("=" * 100)
    
    # Best configurations from the report
    best_configs = [
        # qwen3_coder
        {
            'model': 'qwen3_coder',
            'k': 50,
            'view': 'buggy_code_mixed',
            'algorithm': 'hac_complete',
            'win_rate': 0.635
        },
        {
            'model': 'qwen3_coder',
            'k': 100,
            'view': 'buggy_code_mixed',
            'algorithm': 'bisecting_kmeans',
            'win_rate': 0.683
        },
        {
            'model': 'qwen3_coder',
            'k': 150,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'bisecting_kmeans',
            'win_rate': 0.716
        },
        {
            'model': 'qwen3_coder',
            'k': 200,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'bisecting_kmeans',
            'win_rate': 0.749
        },
        {
            'model': 'qwen3_coder',
            'k': 300,
            'view': 'buggy_code_mixed',
            'algorithm': 'hac_single',
            'win_rate': 0.798
        },
        {
            'model': 'qwen3_coder',
            'k': 500,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'hac_single',
            'win_rate': 0.911
        },
        # qwen3_30b
        {
            'model': 'qwen3_30b',
            'k': 50,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'kmeans',
            'win_rate': 0.626
        },
        {
            'model': 'qwen3_30b',
            'k': 100,
            'view': 'report',
            'algorithm': 'kmeans',
            'win_rate': 0.686
        },
        {
            'model': 'qwen3_30b',
            'k': 150,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'bisecting_kmeans',
            'win_rate': 0.722
        },
        {
            'model': 'qwen3_30b',
            'k': 200,
            'view': 'buggy_code_mixed',
            'algorithm': 'kmeans',
            'win_rate': 0.742
        },
        {
            'model': 'qwen3_30b',
            'k': 300,
            'view': 'buggy_code_mixed',
            'algorithm': 'bisecting_kmeans',
            'win_rate': 0.801
        },
        {
            'model': 'qwen3_30b',
            'k': 500,
            'view': 'report',
            'algorithm': 'hac_single',
            'win_rate': 0.901
        }
    ]
    
    base_dir = Path("bug_task_model_selection/data")
    
    for config in best_configs:
        model = config['model']
        k = config['k']
        view = config['view']
        algorithm = config['algorithm']
        win_rate = config['win_rate']
        
        print(f"\n\n{'=' * 100}")
        print(f"配置: {model} | K={k} | View={view} | Algorithm={algorithm}")
        print(f"Win Rate: {win_rate:.1%}")
        print("=" * 100)
        
        # Find assignments file
        assignments_path = base_dir / f"clusters_{view}" / "cuts" / f"k={k}" / "assignments.jsonl"
        
        if not assignments_path.exists():
            print(f"⚠ 未找到聚类数据: {assignments_path}")
            continue
        
        # Load and analyze
        assignments = load_assignments(assignments_path)
        stats = analyze_cluster_sizes(assignments)
        
        if not stats:
            print("⚠ 无法分析聚类数据")
            continue
        
        # Print statistics
        print(f"\n## 基本统计\n")
        print(f"簇数量: {stats['n_clusters']}")
        print(f"总 bugs: {stats['total_bugs']}")
        print(f"最小簇大小: {stats['min_size']}")
        print(f"最大簇大小: {stats['max_size']}")
        print(f"平均簇大小: {stats['mean_size']:.2f}")
        print(f"中位数簇大小: {stats['median_size']:.1f}")
        print(f"标准差: {stats['std_size']:.2f}")
        
        # Size distribution
        print(f"\n## 簇大小分布\n")
        size_dist = sorted(stats['size_distribution'].items())
        print("| 簇大小 | 数量 | 占比 |")
        print("|--------|------|------|")
        for size, count in size_dist[:20]:  # Top 20
            pct = count / stats['n_clusters']
            print(f"| {size} | {count} | {pct:.1%} |")
        
        if len(size_dist) > 20:
            print(f"| ... | ... | ... |")
            print(f"(共 {len(size_dist)} 种不同的簇大小)")
        
        # Percentiles
        sizes = list(stats['cluster_sizes'].values())
        print(f"\n## 簇大小百分位数\n")
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        print("| 百分位 | 簇大小 |")
        print("|--------|--------|")
        for p in percentiles:
            val = np.percentile(sizes, p)
            print(f"| P{p} | {val:.1f} |")
        
        # Cluster balance analysis
        print(f"\n## 簇平衡性分析\n")
        cv = stats['std_size'] / stats['mean_size']  # Coefficient of variation
        print(f"变异系数 (CV): {cv:.3f}")
        if cv < 0.3:
            balance = "非常均衡"
        elif cv < 0.5:
            balance = "较均衡"
        elif cv < 1.0:
            balance = "中等不均衡"
        else:
            balance = "严重不均衡"
        print(f"平衡性评价: {balance}")
        
        # Largest and smallest clusters
        cluster_sizes_sorted = sorted(stats['cluster_sizes'].items(), 
                                     key=lambda x: x[1], reverse=True)
        
        print(f"\n## 最大的 5 个簇\n")
        print("| Cluster ID | 大小 |")
        print("|------------|------|")
        for cid, size in cluster_sizes_sorted[:5]:
            print(f"| {cid} | {size} |")
        
        print(f"\n## 最小的 5 个簇\n")
        print("| Cluster ID | 大小 |")
        print("|------------|------|")
        for cid, size in cluster_sizes_sorted[-5:]:
            print(f"| {cid} | {size} |")
    
    # Summary comparison
    print("\n\n" + "=" * 100)
    print("所有最佳配置的簇大小对比")
    print("=" * 100)
    
    print("\n| Model | K | View | Algorithm | Win Rate | 平均簇大小 | 中位数 | 最小 | 最大 | CV |")
    print("|-------|---|------|-----------|----------|-----------|--------|------|------|----|")
    
    for config in best_configs:
        model = config['model']
        k = config['k']
        view = config['view']
        algorithm = config['algorithm']
        win_rate = config['win_rate']
        
        assignments_path = base_dir / f"clusters_{view}" / "cuts" / f"k={k}" / "assignments.jsonl"
        
        if not assignments_path.exists():
            continue
        
        assignments = load_assignments(assignments_path)
        stats = analyze_cluster_sizes(assignments)
        
        if not stats:
            continue
        
        cv = stats['std_size'] / stats['mean_size']
        
        print(f"| {model.split('_')[1]} | {k} | {view[:15]}... | "
              f"{algorithm[:10]}... | {win_rate:.1%} | "
              f"{stats['mean_size']:.2f} | {stats['median_size']:.1f} | "
              f"{stats['min_size']} | {stats['max_size']} | {cv:.3f} |")


if __name__ == "__main__":
    main()
