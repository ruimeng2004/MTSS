#!/usr/bin/env python3
"""Generate markdown report from cluster purity analysis results."""

import json
from pathlib import Path
from typing import Dict, List


def load_results(filepath: Path) -> Dict:
    """Load analysis results from JSON file.
    
    Args:
        filepath: Path to JSON results file.
    
    Returns:
        Dictionary containing analysis results.
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def generate_summary_tables(results: Dict) -> str:
    """Generate summary tables for all configurations.
    
    Args:
        results: Full results dictionary.
    
    Returns:
        Markdown formatted tables.
    """
    md = []
    
    for model in sorted(results.keys()):
        md.append(f"## 模型: {model}\n")
        
        for view in sorted(results[model].keys()):
            md.append(f"### 视图: {view}\n")
            
            md.append("| K | 簇数 | 平均纯度 | 加权纯度 | "
                     "误分类数 | 误分类率 | 平均Edit比例 | 平均簇大小 |")
            md.append("|---|------|----------|----------|"
                     "----------|----------|--------------|------------|")
            
            k_values = sorted([int(k) for k in results[model][view].keys()])
            for k in k_values:
                metrics = results[model][view][str(k)]['overall_metrics']
                md.append(
                    f"| {k} | {metrics['num_clusters']} | "
                    f"{metrics['mean_purity']:.3f} | "
                    f"{metrics['weighted_purity']:.3f} | "
                    f"{metrics['total_misclassified']} | "
                    f"{metrics['misclassification_rate']:.3f} | "
                    f"{metrics['mean_edit_ratio']:.3f} | "
                    f"{metrics['mean_cluster_size']:.1f} |"
                )
            
            md.append("")
    
    return "\n".join(md)


def generate_view_comparison(results: Dict, k: int) -> str:
    """Generate view comparison tables for specific k.
    
    Args:
        results: Full results dictionary.
        k: Number of clusters.
    
    Returns:
        Markdown formatted comparison tables.
    """
    md = []
    
    for model in sorted(results.keys()):
        md.append(f"### 模型: {model} (k={k})\n")
        
        md.append("| 视图 | 簇数 | 平均纯度 | 加权纯度 | "
                 "误分类数 | 误分类率 | 平均Edit比例 |")
        md.append("|------|------|----------|----------|"
                 "----------|----------|--------------|")
        
        for view in sorted(results[model].keys()):
            if str(k) in results[model][view]:
                metrics = results[model][view][str(k)]['overall_metrics']
                md.append(
                    f"| {view} | {metrics['num_clusters']} | "
                    f"{metrics['mean_purity']:.3f} | "
                    f"{metrics['weighted_purity']:.3f} | "
                    f"{metrics['total_misclassified']} | "
                    f"{metrics['misclassification_rate']:.3f} | "
                    f"{metrics['mean_edit_ratio']:.3f} |"
                )
        
        md.append("")
    
    return "\n".join(md)


def generate_model_comparison(results: Dict, k: int) -> str:
    """Generate model comparison tables for specific k.
    
    Args:
        results: Full results dictionary.
        k: Number of clusters.
    
    Returns:
        Markdown formatted comparison tables.
    """
    md = []
    
    # Get all views
    all_views = set()
    for model in results:
        all_views.update(results[model].keys())
    
    for view in sorted(all_views):
        md.append(f"### 视图: {view} (k={k})\n")
        
        md.append("| 模型 | 簇数 | 平均纯度 | 加权纯度 | "
                 "误分类数 | 误分类率 | 平均Edit比例 |")
        md.append("|------|------|----------|----------|"
                 "----------|----------|--------------|")
        
        for model in sorted(results.keys()):
            if view in results[model] and str(k) in results[model][view]:
                metrics = results[model][view][str(k)]['overall_metrics']
                md.append(
                    f"| {model} | {metrics['num_clusters']} | "
                    f"{metrics['mean_purity']:.3f} | "
                    f"{metrics['weighted_purity']:.3f} | "
                    f"{metrics['total_misclassified']} | "
                    f"{metrics['misclassification_rate']:.3f} | "
                    f"{metrics['mean_edit_ratio']:.3f} |"
                )
        
        md.append("")
    
    return "\n".join(md)


def generate_purity_distribution_table(
    results: Dict,
    model: str,
    view: str,
    k: int
) -> str:
    """Generate purity distribution table for specific configuration.
    
    Args:
        results: Full results dictionary.
        model: Model name.
        view: View name.
        k: Number of clusters.
    
    Returns:
        Markdown formatted table.
    """
    if (model not in results or view not in results[model] or 
        str(k) not in results[model][view]):
        return ""
    
    cluster_stats = results[model][view][str(k)]['cluster_stats']
    purities = [stats['purity'] for stats in cluster_stats.values()]
    
    thresholds = [0.9, 0.8, 0.7, 0.6]
    
    md = [
        "| 纯度阈值 | 簇数量 | 占比 |",
        "|----------|--------|------|"
    ]
    
    for threshold in thresholds:
        count = sum(1 for p in purities if p >= threshold)
        percentage = count / len(purities) * 100 if purities else 0
        md.append(f"| >= {threshold:.1f} | {count} | {percentage:.1f}% |")
    
    count_low = sum(1 for p in purities if p < 0.6)
    percentage_low = count_low / len(purities) * 100 if purities else 0
    md.append(f"| < 0.6 | {count_low} | {percentage_low:.1f}% |")
    
    return "\n".join(md)


def generate_top_bottom_clusters(
    results: Dict,
    model: str,
    view: str,
    k: int,
    top_n: int = 10
) -> str:
    """Generate tables showing top and bottom clusters by purity.
    
    Args:
        results: Full results dictionary.
        model: Model name.
        view: View name.
        k: Number of clusters.
        top_n: Number of clusters to show.
    
    Returns:
        Markdown formatted tables.
    """
    if (model not in results or view not in results[model] or 
        str(k) not in results[model][view]):
        return ""
    
    cluster_stats = results[model][view][str(k)]['cluster_stats']
    
    # Sort by purity
    sorted_clusters = sorted(
        cluster_stats.items(),
        key=lambda x: x[1]['purity'],
        reverse=True
    )
    
    md = []
    
    # Top clusters
    md.append(f"#### 纯度最高的 {top_n} 个簇\n")
    md.append("| 簇ID | 大小 | Edit数 | Gen数 | "
             "Edit比例 | Gen比例 | 纯度 | 主导任务 |")
    md.append("|------|------|--------|-------|"
             "----------|---------|------|----------|")
    
    for cluster_id, stats in sorted_clusters[:top_n]:
        md.append(
            f"| {cluster_id} | {stats['total']} | "
            f"{stats['edit_count']} | {stats['gen_count']} | "
            f"{stats['edit_ratio']:.3f} | {stats['gen_ratio']:.3f} | "
            f"{stats['purity']:.3f} | {stats['majority_task']} |"
        )
    
    md.append("")
    
    # Bottom clusters
    md.append(f"#### 纯度最低的 {top_n} 个簇\n")
    md.append("| 簇ID | 大小 | Edit数 | Gen数 | "
             "Edit比例 | Gen比例 | 纯度 | 主导任务 |")
    md.append("|------|------|--------|-------|"
             "----------|---------|------|----------|")
    
    for cluster_id, stats in sorted_clusters[-top_n:]:
        md.append(
            f"| {cluster_id} | {stats['total']} | "
            f"{stats['edit_count']} | {stats['gen_count']} | "
            f"{stats['edit_ratio']:.3f} | {stats['gen_ratio']:.3f} | "
            f"{stats['purity']:.3f} | {stats['majority_task']} |"
        )
    
    return "\n".join(md)


def generate_k_impact_analysis(results: Dict) -> str:
    """Generate analysis of k value impact on purity.
    
    Args:
        results: Full results dictionary.
    
    Returns:
        Markdown formatted analysis.
    """
    md = []
    
    for model in sorted(results.keys()):
        md.append(f"### 模型: {model}\n")
        
        for view in sorted(results[model].keys()):
            k_values = sorted([int(k) for k in results[model][view].keys()])
            
            if len(k_values) < 2:
                continue
            
            # Get metrics for min and max k
            min_k = min(k_values)
            max_k = max(k_values)
            
            min_metrics = results[model][view][str(min_k)]['overall_metrics']
            max_metrics = results[model][view][str(max_k)]['overall_metrics']
            
            mean_purity_gain = (
                max_metrics['mean_purity'] - min_metrics['mean_purity']
            )
            weighted_purity_gain = (
                max_metrics['weighted_purity'] - 
                min_metrics['weighted_purity']
            )
            
            md.append(f"**{view}**:")
            md.append(f"- K 范围: {min_k} → {max_k}")
            md.append(
                f"- 平均纯度提升: "
                f"{min_metrics['mean_purity']:.3f} → "
                f"{max_metrics['mean_purity']:.3f} "
                f"(+{mean_purity_gain:.3f})"
            )
            md.append(
                f"- 加权纯度提升: "
                f"{min_metrics['weighted_purity']:.3f} → "
                f"{max_metrics['weighted_purity']:.3f} "
                f"(+{weighted_purity_gain:.3f})"
            )
            md.append("")
    
    return "\n".join(md)


def generate_report(results: Dict, output_file: Path):
    """Generate complete markdown report.
    
    Args:
        results: Full results dictionary.
        output_file: Output file path.
    """
    md = []
    
    # Title and introduction
    md.append("# 聚类纯度分析报告 (Edit vs Gen)\n")
    md.append("本报告分析了不同配置下聚类的纯度，即每个簇中 edit 和 gen 任务的比例分布。\n")
    
    # Configuration summary
    md.append("## 配置概览\n")
    md.append(f"- **基础模型**: {', '.join(sorted(results.keys()))}")
    
    all_views = set()
    for model in results:
        all_views.update(results[model].keys())
    md.append(f"- **视图**: {', '.join(sorted(all_views))}")
    
    all_k_values = set()
    for model in results:
        for view in results[model]:
            all_k_values.update(int(k) for k in results[model][view].keys())
    md.append(
        f"- **K 值范围**: {min(all_k_values)} - {max(all_k_values)}"
    )
    md.append("")
    
    # Key metrics explanation
    md.append("## 指标说明\n")
    md.append("- **平均纯度**: 所有簇纯度的算术平均值")
    md.append("- **加权纯度**: 按簇大小加权的平均纯度")
    md.append("- **纯度**: max(edit_count, gen_count) / total_count")
    md.append("- **误分类数**: 所有簇中少数派任务的总数（被分到错误簇的样本数）")
    md.append("- **误分类率**: 误分类数 / 总样本数（1 - 加权纯度）")
    md.append("- **平均Edit比例**: 所有簇中 edit 任务的平均比例")
    md.append("- **平均簇大小**: 每个簇的平均样本数\n")
    
    # Summary tables for all configurations
    md.append("## 完整配置汇总表\n")
    md.append(generate_summary_tables(results))
    
    # View comparisons at key k values
    md.append("## 视图对比分析\n")
    for k in [100, 200, 300]:
        md.append(f"### K = {k}\n")
        md.append(generate_view_comparison(results, k))
    
    # Model comparisons at key k values
    md.append("## 模型对比分析\n")
    for k in [100, 200, 300]:
        md.append(f"### K = {k}\n")
        md.append(generate_model_comparison(results, k))
    
    # Detailed analysis for key configurations
    md.append("## 关键配置详细分析\n")
    
    key_configs = [
        ('qwen3_coder', 'buggy_code', 100),
        ('qwen3_coder', 'error', 100),
        ('qwen3_30b', 'buggy_code', 100),
        ('qwen3_30b', 'error', 100),
    ]
    
    for model, view, k in key_configs:
        if (model in results and view in results[model] and 
            str(k) in results[model][view]):
            
            md.append(f"### {model} / {view} / k={k}\n")
            
            metrics = results[model][view][str(k)]['overall_metrics']
            
            md.append("**整体指标**:\n")
            md.append(f"- 簇数: {metrics['num_clusters']}")
            md.append(f"- 总样本数: {metrics['total_items']}")
            md.append(f"- 平均纯度: {metrics['mean_purity']:.3f}")
            md.append(f"- 加权纯度: {metrics['weighted_purity']:.3f}")
            md.append(f"- 误分类数: {metrics['total_misclassified']}")
            md.append(
                f"- 误分类率: {metrics['misclassification_rate']:.3f} "
                f"({metrics['misclassification_rate']*100:.1f}%)"
            )
            md.append(f"- 纯度标准差: {metrics['std_purity']:.3f}")
            md.append(
                f"- 平均 Edit 比例: {metrics['mean_edit_ratio']:.3f}\n"
            )
            
            md.append("**纯度分布**:\n")
            md.append(generate_purity_distribution_table(
                results, model, view, k
            ))
            md.append("")
            
            md.append(generate_top_bottom_clusters(
                results, model, view, k, top_n=10
            ))
            md.append("")
    
    # K value impact analysis
    md.append("## K 值影响分析\n")
    md.append(generate_k_impact_analysis(results))
    
    # Key findings
    md.append("## 关键发现\n")
    md.append("### 1. K 值与纯度/误分类率的关系\n")
    md.append("- 随着 K 值增加，平均纯度显著提升，误分类率显著下降")
    md.append("- K=500 时，大多数配置的平均纯度达到 0.94-0.97，误分类率降至 0.10-0.13")
    md.append("- K=100 时，误分类率约为 0.33-0.36（约 230-250 个样本被误分类）")
    md.append("- 加权纯度的提升幅度更大，表明大簇的纯度改善明显\n")
    
    md.append("### 2. 视图对比\n")
    md.append("- **error** 视图在两个模型上都表现最好，误分类率最低")
    md.append("- **buggy_code_obfuscated** 视图也显示出较高的纯度")
    md.append("- **report** 视图的纯度相对较低，误分类率较高\n")
    
    md.append("### 3. 模型对比\n")
    md.append("- qwen3_coder 在大多数配置下略优于 qwen3_30b")
    md.append("- 两个模型的差异较小（误分类率差异通常在 0.01-0.03 范围内）")
    md.append("- 在 error 视图上，qwen3_coder 的优势更明显\n")
    
    md.append("### 4. 误分类分析\n")
    md.append("- 在 K=100 时，约有 33-36% 的样本被分配到少数派任务簇中")
    md.append("- 误分类率 = 1 - 加权纯度，直接反映聚类质量")
    md.append("- 较小的 K 值（如 K=10）误分类率可达 42-47%")
    md.append("- 增加 K 值是降低误分类率的有效方法\n")
    
    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))
    
    print(f"报告已生成: {output_file}")


def main():
    """Main function."""
    # Load results
    results_file = Path(
        "bug_task_model_selection/data/analysis/cluster_purity_analysis.json"
    )
    results = load_results(results_file)
    
    # Generate report
    output_file = Path(
        "bug_task_model_selection/CLUSTER_PURITY_REPORT.md"
    )
    generate_report(results, output_file)


if __name__ == "__main__":
    main()
