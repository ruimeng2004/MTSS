#!/usr/bin/env python3
"""Analyze cluster purity (edit vs gen ratio) across all configurations.

This script analyzes the purity of clusters by calculating the proportion
of edit vs gen tasks in each cluster for all combinations of:
- Base models: qwen3_coder, qwen3_30b
- Views: buggy_code, error, test, report, error_plus_test, 
         buggy_code_mixed, buggy_code_obfuscated
- K values: various cluster counts
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np


def load_ppl_data(model: str) -> Dict[str, str]:
    """Load PPL data and determine task preference for each bug.
    
    Args:
        model: Model name (qwen3_coder or qwen3_30b).
    
    Returns:
        Dictionary mapping slug to preferred task ('edit' or 'gen').
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
                ppl = obj['value']
                
                if slug not in ppl_data:
                    ppl_data[slug] = {}
                ppl_data[slug][f'{task}_ppl'] = ppl
    
    # Determine preferred task
    task_preference = {}
    for slug, data in ppl_data.items():
        if 'edit_ppl' in data and 'gen_ppl' in data:
            task_preference[slug] = 'edit' if data['edit_ppl'] < data['gen_ppl'] else 'gen'
    
    return task_preference


def extract_slug_from_item_id(item_id: str) -> str:
    """Extract bug slug from item_id.
    
    Args:
        item_id: Item identifier (e.g., 'Chart_1__buggy_code').
    
    Returns:
        Bug slug (e.g., 'Chart_1').
    """
    # Remove view suffix
    parts = item_id.split('__')
    return parts[0] if parts else item_id


def analyze_cluster_purity(
    cluster_dir: Path,
    task_preference: Dict[str, str]
) -> Dict[int, Dict]:
    """Analyze purity for all clusters in a directory.
    
    Args:
        cluster_dir: Directory containing cluster assignments.
        task_preference: Mapping from slug to preferred task.
    
    Returns:
        Dictionary mapping cluster_id to purity statistics.
    """
    assignments_file = cluster_dir / "assignments.jsonl"
    if not assignments_file.exists():
        return {}
    
    # Load assignments
    cluster_assignments = defaultdict(list)
    with open(assignments_file, 'r') as f:
        for line in f:
            obj = json.loads(line)
            item_id = obj['item_id']
            cluster_id = obj['cluster_id']
            
            slug = extract_slug_from_item_id(item_id)
            if slug in task_preference:
                cluster_assignments[cluster_id].append(task_preference[slug])
    
    # Calculate purity for each cluster
    cluster_stats = {}
    for cluster_id, tasks in cluster_assignments.items():
        total = len(tasks)
        edit_count = sum(1 for t in tasks if t == 'edit')
        gen_count = total - edit_count
        
        cluster_stats[cluster_id] = {
            'total': total,
            'edit_count': edit_count,
            'gen_count': gen_count,
            'edit_ratio': edit_count / total if total > 0 else 0,
            'gen_ratio': gen_count / total if total > 0 else 0,
            'purity': max(edit_count, gen_count) / total if total > 0 else 0,
            'majority_task': 'edit' if edit_count > gen_count else 'gen'
        }
    
    return cluster_stats


def calculate_overall_metrics(cluster_stats: Dict[int, Dict]) -> Dict:
    """Calculate overall metrics across all clusters.
    
    Args:
        cluster_stats: Statistics for each cluster.
    
    Returns:
        Dictionary of overall metrics.
    """
    if not cluster_stats:
        return {}
    
    purities = [stats['purity'] for stats in cluster_stats.values()]
    edit_ratios = [stats['edit_ratio'] for stats in cluster_stats.values()]
    sizes = [stats['total'] for stats in cluster_stats.values()]
    
    # Weighted purity (by cluster size)
    total_items = sum(sizes)
    weighted_purity = sum(
        stats['purity'] * stats['total'] 
        for stats in cluster_stats.values()
    ) / total_items if total_items > 0 else 0
    
    # Calculate misclassified items (minority in each cluster)
    total_misclassified = sum(
        min(stats['edit_count'], stats['gen_count'])
        for stats in cluster_stats.values()
    )
    misclassification_rate = (
        total_misclassified / total_items if total_items > 0 else 0
    )
    
    return {
        'num_clusters': len(cluster_stats),
        'total_items': total_items,
        'mean_purity': np.mean(purities),
        'median_purity': np.median(purities),
        'min_purity': np.min(purities),
        'max_purity': np.max(purities),
        'std_purity': np.std(purities),
        'weighted_purity': weighted_purity,
        'mean_edit_ratio': np.mean(edit_ratios),
        'mean_cluster_size': np.mean(sizes),
        'median_cluster_size': np.median(sizes),
        'total_misclassified': total_misclassified,
        'misclassification_rate': misclassification_rate,
    }


def analyze_all_configurations() -> Dict:
    """Analyze cluster purity for all configurations.
    
    Returns:
        Nested dictionary with results for all configurations.
    """
    results = {}
    
    models = ['qwen3_coder', 'qwen3_30b']
    views = [
        'buggy_code', 'error', 'test', 'report', 'error_plus_test',
        'buggy_code_mixed', 'buggy_code_obfuscated'
    ]
    
    for model in models:
        print(f"\n处理模型: {model}")
        task_preference = load_ppl_data(model)
        print(f"  加载了 {len(task_preference)} 个 bugs 的任务偏好")
        
        results[model] = {}
        
        for view in views:
            cluster_base_dir = Path(f"bug_task_model_selection/data/clusters_{view}")
            if not cluster_base_dir.exists():
                print(f"  跳过视图 {view} (目录不存在)")
                continue
            
            print(f"  处理视图: {view}")
            results[model][view] = {}
            
            cuts_dir = cluster_base_dir / "cuts"
            if not cuts_dir.exists():
                print(f"    跳过 (cuts 目录不存在)")
                continue
            
            # Find all k directories
            k_dirs = sorted(cuts_dir.glob("k=*"))
            
            for k_dir in k_dirs:
                k_value = int(k_dir.name.split('=')[1])
                
                cluster_stats = analyze_cluster_purity(k_dir, task_preference)
                if cluster_stats:
                    overall_metrics = calculate_overall_metrics(cluster_stats)
                    
                    results[model][view][k_value] = {
                        'cluster_stats': cluster_stats,
                        'overall_metrics': overall_metrics
                    }
                    
                    print(f"    k={k_value}: "
                          f"{overall_metrics['num_clusters']} 簇, "
                          f"平均纯度={overall_metrics['mean_purity']:.3f}, "
                          f"加权纯度={overall_metrics['weighted_purity']:.3f}")
    
    return results


def print_summary_table(results: Dict):
    """Print summary table of cluster purity across configurations."""
    print("\n" + "=" * 120)
    print("聚类纯度分析汇总表")
    print("=" * 120)
    
    for model in results:
        print(f"\n## 模型: {model}\n")
        
        for view in results[model]:
            print(f"### 视图: {view}\n")
            
            print("| K | 簇数 | 平均纯度 | 中位纯度 | 加权纯度 | "
                  "误分类数 | 误分类率 | 平均Edit比例 | 平均簇大小 |")
            print("|---|------|----------|----------|----------|"
                  "----------|----------|--------------|------------|")
            
            k_values = sorted(results[model][view].keys())
            for k in k_values:
                metrics = results[model][view][k]['overall_metrics']
                print(f"| {k} | {metrics['num_clusters']} | "
                      f"{metrics['mean_purity']:.3f} | "
                      f"{metrics['median_purity']:.3f} | "
                      f"{metrics['weighted_purity']:.3f} | "
                      f"{metrics['total_misclassified']} | "
                      f"{metrics['misclassification_rate']:.3f} | "
                      f"{metrics['mean_edit_ratio']:.3f} | "
                      f"{metrics['mean_cluster_size']:.1f} |")
            
            print()


def print_detailed_cluster_analysis(
    results: Dict,
    model: str,
    view: str,
    k: int,
    top_n: int = 10
):
    """Print detailed analysis for specific configuration.
    
    Args:
        results: Full results dictionary.
        model: Model name.
        view: View name.
        k: Number of clusters.
        top_n: Number of top/bottom clusters to show.
    """
    if model not in results or view not in results[model] or k not in results[model][view]:
        print(f"配置不存在: {model}/{view}/k={k}")
        return
    
    config_data = results[model][view][k]
    cluster_stats = config_data['cluster_stats']
    overall_metrics = config_data['overall_metrics']
    
    print(f"\n## 详细分析: {model} / {view} / k={k}\n")
    
    print(f"**整体指标**:")
    print(f"- 簇数: {overall_metrics['num_clusters']}")
    print(f"- 总样本数: {overall_metrics['total_items']}")
    print(f"- 平均纯度: {overall_metrics['mean_purity']:.3f}")
    print(f"- 加权纯度: {overall_metrics['weighted_purity']:.3f}")
    print(f"- 纯度标准差: {overall_metrics['std_purity']:.3f}")
    print(f"- 平均 Edit 比例: {overall_metrics['mean_edit_ratio']:.3f}")
    
    # Sort clusters by purity
    sorted_clusters = sorted(
        cluster_stats.items(),
        key=lambda x: x[1]['purity'],
        reverse=True
    )
    
    print(f"\n**纯度最高的 {top_n} 个簇**:\n")
    print("| 簇ID | 大小 | Edit数 | Gen数 | Edit比例 | Gen比例 | 纯度 | 主导任务 |")
    print("|------|------|--------|-------|----------|---------|------|----------|")
    
    for cluster_id, stats in sorted_clusters[:top_n]:
        print(f"| {cluster_id} | {stats['total']} | "
              f"{stats['edit_count']} | {stats['gen_count']} | "
              f"{stats['edit_ratio']:.3f} | {stats['gen_ratio']:.3f} | "
              f"{stats['purity']:.3f} | {stats['majority_task']} |")
    
    print(f"\n**纯度最低的 {top_n} 个簇**:\n")
    print("| 簇ID | 大小 | Edit数 | Gen数 | Edit比例 | Gen比例 | 纯度 | 主导任务 |")
    print("|------|------|--------|-------|----------|---------|------|----------|")
    
    for cluster_id, stats in sorted_clusters[-top_n:]:
        print(f"| {cluster_id} | {stats['total']} | "
              f"{stats['edit_count']} | {stats['gen_count']} | "
              f"{stats['edit_ratio']:.3f} | {stats['gen_ratio']:.3f} | "
              f"{stats['purity']:.3f} | {stats['majority_task']} |")
    
    # Purity distribution
    purities = [stats['purity'] for stats in cluster_stats.values()]
    print(f"\n**纯度分布**:")
    print(f"- 纯度 >= 0.9: {sum(1 for p in purities if p >= 0.9)} 簇 "
          f"({sum(1 for p in purities if p >= 0.9)/len(purities)*100:.1f}%)")
    print(f"- 纯度 >= 0.8: {sum(1 for p in purities if p >= 0.8)} 簇 "
          f"({sum(1 for p in purities if p >= 0.8)/len(purities)*100:.1f}%)")
    print(f"- 纯度 >= 0.7: {sum(1 for p in purities if p >= 0.7)} 簇 "
          f"({sum(1 for p in purities if p >= 0.7)/len(purities)*100:.1f}%)")
    print(f"- 纯度 < 0.6: {sum(1 for p in purities if p < 0.6)} 簇 "
          f"({sum(1 for p in purities if p < 0.6)/len(purities)*100:.1f}%)")


def compare_views(results: Dict, model: str, k: int):
    """Compare purity across views for a specific model and k.
    
    Args:
        results: Full results dictionary.
        model: Model name.
        k: Number of clusters.
    """
    print(f"\n## 视图对比: {model} / k={k}\n")
    
    print("| 视图 | 簇数 | 平均纯度 | 加权纯度 | 平均Edit比例 | 纯度标准差 |")
    print("|------|------|----------|----------|--------------|------------|")
    
    if model not in results:
        print("模型不存在")
        return
    
    for view in results[model]:
        if k in results[model][view]:
            metrics = results[model][view][k]['overall_metrics']
            print(f"| {view} | {metrics['num_clusters']} | "
                  f"{metrics['mean_purity']:.3f} | "
                  f"{metrics['weighted_purity']:.3f} | "
                  f"{metrics['mean_edit_ratio']:.3f} | "
                  f"{metrics['std_purity']:.3f} |")


def compare_models(results: Dict, view: str, k: int):
    """Compare purity across models for a specific view and k.
    
    Args:
        results: Full results dictionary.
        view: View name.
        k: Number of clusters.
    """
    print(f"\n## 模型对比: {view} / k={k}\n")
    
    print("| 模型 | 簇数 | 平均纯度 | 加权纯度 | 平均Edit比例 | 纯度标准差 |")
    print("|------|------|----------|----------|--------------|------------|")
    
    for model in results:
        if view in results[model] and k in results[model][view]:
            metrics = results[model][view][k]['overall_metrics']
            print(f"| {model} | {metrics['num_clusters']} | "
                  f"{metrics['mean_purity']:.3f} | "
                  f"{metrics['weighted_purity']:.3f} | "
                  f"{metrics['mean_edit_ratio']:.3f} | "
                  f"{metrics['std_purity']:.3f} |")


def save_results(results: Dict, output_file: Path):
    """Save results to JSON file.
    
    Args:
        results: Full results dictionary.
        output_file: Output file path.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n结果已保存到: {output_file}")


def main():
    """Main analysis function."""
    print("=" * 120)
    print("聚类纯度分析 (Edit vs Gen)")
    print("=" * 120)
    
    # Analyze all configurations
    results = analyze_all_configurations()
    
    # Print summary table
    print_summary_table(results)
    
    # Detailed analysis for key configurations
    print("\n" + "=" * 120)
    print("关键配置详细分析")
    print("=" * 120)
    
    # Example detailed analyses
    key_configs = [
        ('qwen3_coder', 'buggy_code', 100),
        ('qwen3_coder', 'error', 100),
        ('qwen3_30b', 'buggy_code', 100),
        ('qwen3_30b', 'error', 100),
    ]
    
    for model, view, k in key_configs:
        if (model in results and view in results[model] and 
            k in results[model][view]):
            print_detailed_cluster_analysis(results, model, view, k)
    
    # View comparisons
    print("\n" + "=" * 120)
    print("视图对比分析")
    print("=" * 120)
    
    for model in results:
        compare_views(results, model, 100)
    
    # Model comparisons
    print("\n" + "=" * 120)
    print("模型对比分析")
    print("=" * 120)
    
    common_views = ['buggy_code', 'error', 'test', 'report']
    for view in common_views:
        compare_models(results, view, 100)
    
    # Save results
    output_file = Path("bug_task_model_selection/data/analysis/cluster_purity_analysis.json")
    save_results(results, output_file)
    
    print("\n" + "=" * 120)
    print("分析完成")
    print("=" * 120)


if __name__ == "__main__":
    main()
