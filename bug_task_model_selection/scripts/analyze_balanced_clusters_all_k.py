#!/usr/bin/env python3
"""Complete analysis of balanced clusters across all K values."""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import numpy as np


def load_ppl_data(model: str) -> Dict[str, Dict[str, float]]:
    """Load aggregated PPL data."""
    ppl_data = {}
    
    for task in ['edit', 'gen']:
        path = Path(f"bug_task_model_selection/data/ppl/{model}_{task}.jsonl")
        if not path.exists():
            continue
        
        with open(path, 'r') as f:
            for line in f:
                obj = json.loads(line)
                slug = obj['slug']
                ppl = obj['value']
                
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


def calculate_ppl_gap(edit_ppl: float, gen_ppl: float) -> float:
    """Calculate relative PPL gap."""
    return abs(edit_ppl - gen_ppl) / min(edit_ppl, gen_ppl) * 100


def analyze_balanced_clusters(
    model: str,
    view: str,
    k: int,
    ppl_data: Dict[str, Dict[str, float]],
    gap_threshold: float,
    proportion_threshold: float
) -> Dict:
    """Analyze balanced clusters for a specific configuration.
    
    Args:
        model: Model name.
        view: View type.
        k: Number of clusters.
        ppl_data: PPL data.
        gap_threshold: PPL gap threshold (percentage).
        proportion_threshold: Minimum proportion of small-gap bugs.
    
    Returns:
        Dictionary with analysis results.
    """
    assignments = load_cluster_assignments(view, k)
    
    if not assignments:
        return None
    
    # Group bugs by cluster
    clusters = defaultdict(list)
    for slug, cluster_id in assignments.items():
        if slug in ppl_data:
            clusters[cluster_id].append(slug)
    
    # Analyze each cluster
    balanced_clusters = []
    all_cluster_stats = []
    
    for cluster_id, members in clusters.items():
        if len(members) == 0:
            continue
        
        # Calculate gaps for all members
        gaps = []
        for slug in members:
            data = ppl_data[slug]
            gap = calculate_ppl_gap(data['edit_ppl'], data['gen_ppl'])
            gaps.append(gap)
        
        # Calculate proportion of small-gap bugs
        small_gap_count = sum(1 for g in gaps if g < gap_threshold)
        small_gap_proportion = small_gap_count / len(members)
        
        cluster_stat = {
            'cluster_id': cluster_id,
            'size': len(members),
            'small_gap_count': small_gap_count,
            'small_gap_proportion': small_gap_proportion,
            'avg_gap': np.mean(gaps),
            'median_gap': np.median(gaps),
            'min_gap': min(gaps),
            'max_gap': max(gaps)
        }
        
        all_cluster_stats.append(cluster_stat)
        
        # Check if balanced
        if small_gap_proportion >= proportion_threshold:
            balanced_clusters.append(cluster_stat)
    
    # Summary statistics
    total_bugs = sum(c['size'] for c in all_cluster_stats)
    balanced_bugs = sum(c['size'] for c in balanced_clusters)
    
    # Distribution of proportions
    proportions = [c['small_gap_proportion'] for c in all_cluster_stats]
    
    return {
        'model': model,
        'view': view,
        'k': k,
        'total_clusters': len(all_cluster_stats),
        'total_bugs': total_bugs,
        'balanced_clusters': len(balanced_clusters),
        'balanced_bugs': balanced_bugs,
        'balanced_cluster_pct': len(balanced_clusters) / len(all_cluster_stats) * 100,
        'balanced_bugs_pct': balanced_bugs / total_bugs * 100,
        'avg_proportion': np.mean(proportions),
        'median_proportion': np.median(proportions),
        'balanced_cluster_details': balanced_clusters,
        'all_cluster_stats': all_cluster_stats
    }


def main():
    """Main analysis function."""
    print("=" * 100)
    print("完整分析：所有最佳配置的平衡簇识别")
    print("=" * 100)
    
    # Best configurations
    best_configs = [
        # qwen3_coder
        {'model': 'qwen3_coder', 'k': 50, 'view': 'buggy_code_mixed'},
        {'model': 'qwen3_coder', 'k': 100, 'view': 'buggy_code_mixed'},
        {'model': 'qwen3_coder', 'k': 150, 'view': 'buggy_code_obfuscated'},
        {'model': 'qwen3_coder', 'k': 200, 'view': 'buggy_code_obfuscated'},
        {'model': 'qwen3_coder', 'k': 300, 'view': 'buggy_code_mixed'},
        {'model': 'qwen3_coder', 'k': 500, 'view': 'buggy_code_obfuscated'},
        # qwen3_30b
        {'model': 'qwen3_30b', 'k': 50, 'view': 'buggy_code_obfuscated'},
        {'model': 'qwen3_30b', 'k': 100, 'view': 'report'},
        {'model': 'qwen3_30b', 'k': 150, 'view': 'buggy_code_obfuscated'},
        {'model': 'qwen3_30b', 'k': 200, 'view': 'buggy_code_mixed'},
        {'model': 'qwen3_30b', 'k': 300, 'view': 'buggy_code_mixed'},
        {'model': 'qwen3_30b', 'k': 500, 'view': 'report'},
    ]
    
    # Test different thresholds
    gap_thresholds = [10, 20, 30]
    proportion_thresholds = [0.5, 0.7]
    
    # Load PPL data once
    ppl_data = {
        'qwen3_coder': load_ppl_data('qwen3_coder'),
        'qwen3_30b': load_ppl_data('qwen3_30b')
    }
    
    for gap_threshold in gap_thresholds:
        for proportion_threshold in proportion_thresholds:
            print(f"\n{'=' * 100}")
            print(f"阈值设置: PPL 差距 <{gap_threshold}%, "
                  f"占比 ≥{proportion_threshold*100:.0f}%")
            print(f"{'=' * 100}\n")
            
            results = []
            
            for config in best_configs:
                model = config['model']
                k = config['k']
                view = config['view']
                
                result = analyze_balanced_clusters(
                    model, view, k,
                    ppl_data[model],
                    gap_threshold,
                    proportion_threshold
                )
                
                if result:
                    results.append(result)
            
            # Print summary table
            print("## 汇总表\n")
            print("| Model | K | View | 总簇数 | 平衡簇数 | 平衡簇% | "
                  "总 Bugs | 平衡 Bugs | 平衡 Bugs% |")
            print("|-------|---|------|--------|---------|---------|"
                  "---------|----------|-----------|")
            
            for r in results:
                model_short = r['model'].split('_')[1]
                view_short = r['view'][:15]
                print(f"| {model_short} | {r['k']} | {view_short} | "
                      f"{r['total_clusters']} | {r['balanced_clusters']} | "
                      f"{r['balanced_cluster_pct']:.1f}% | "
                      f"{r['total_bugs']} | {r['balanced_bugs']} | "
                      f"{r['balanced_bugs_pct']:.1f}% |")
            
            # Statistics by model
            print("\n## 按模型统计\n")
            
            for model_name in ['qwen3_coder', 'qwen3_30b']:
                model_results = [r for r in results if r['model'] == model_name]
                
                if not model_results:
                    continue
                
                print(f"### {model_name}\n")
                
                total_balanced_bugs = sum(r['balanced_bugs'] 
                                         for r in model_results)
                total_bugs = model_results[0]['total_bugs']
                
                print(f"总 bugs: {total_bugs}")
                print(f"被识别为平衡的 bugs 总数: {total_balanced_bugs}")
                print(f"占比: {total_balanced_bugs/total_bugs*100:.1f}%")
                print()
                
                # By K value
                print("按 K 值分布:")
                print("| K | 平衡簇 | 平衡 Bugs | 占比 |")
                print("|---|--------|----------|------|")
                for r in model_results:
                    print(f"| {r['k']} | {r['balanced_clusters']} | "
                          f"{r['balanced_bugs']} | "
                          f"{r['balanced_bugs_pct']:.1f}% |")
                print()
            
            # Detailed analysis for selected configs
            print("\n## 详细分析（K=100 和 K=500）\n")
            
            for config in best_configs:
                if config['k'] not in [100, 500]:
                    continue
                
                model = config['model']
                k = config['k']
                view = config['view']
                
                result = [r for r in results 
                         if r['model'] == model and r['k'] == k][0]
                
                print(f"### {model} K={k}\n")
                
                if result['balanced_clusters'] > 0:
                    # Size distribution of balanced clusters
                    sizes = [c['size'] for c in result['balanced_cluster_details']]
                    print(f"平衡簇大小分布:")
                    print(f"  最小: {min(sizes)}")
                    print(f"  最大: {max(sizes)}")
                    print(f"  平均: {np.mean(sizes):.1f}")
                    print(f"  中位数: {np.median(sizes):.1f}")
                    print()
                    
                    # Count by size
                    size_counts = {}
                    for size in sizes:
                        size_counts[size] = size_counts.get(size, 0) + 1
                    
                    print(f"按大小分类:")
                    print(f"  单点簇 (size=1): {size_counts.get(1, 0)} 个")
                    print(f"  小簇 (size=2-5): "
                          f"{sum(v for k, v in size_counts.items() if 2 <= k <= 5)} 个")
                    print(f"  中簇 (size=6-10): "
                          f"{sum(v for k, v in size_counts.items() if 6 <= k <= 10)} 个")
                    print(f"  大簇 (size>10): "
                          f"{sum(v for k, v in size_counts.items() if k > 10)} 个")
                    print()
                    
                    # Show top 5 largest balanced clusters
                    sorted_clusters = sorted(
                        result['balanced_cluster_details'],
                        key=lambda x: x['size'],
                        reverse=True
                    )[:5]
                    
                    if len(sorted_clusters) > 0:
                        print(f"最大的 {min(5, len(sorted_clusters))} 个平衡簇:")
                        print("| Cluster ID | 大小 | 小差距占比 | 平均差距 |")
                        print("|-----------|------|-----------|---------|")
                        for c in sorted_clusters:
                            print(f"| {c['cluster_id']} | {c['size']} | "
                                  f"{c['small_gap_proportion']:.1%} | "
                                  f"{c['avg_gap']:.1f}% |")
                        print()
                else:
                    print("未识别到平衡簇\n")
    
    print("\n" + "=" * 100)
    print("分析完成")
    print("=" * 100)


if __name__ == "__main__":
    main()
