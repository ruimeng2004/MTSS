#!/usr/bin/env python3
"""Analyze individual bug balance across all 698 bugs."""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np


def load_ppl_data(model: str) -> Dict[str, Dict[str, float]]:
    """Load PPL data for a model.
    
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
                ppl = obj['value']
                
                if slug not in ppl_data:
                    ppl_data[slug] = {}
                ppl_data[slug][f'{task}_ppl'] = ppl
    
    return ppl_data


def calculate_ppl_gap(edit_ppl: float, gen_ppl: float) -> float:
    """Calculate relative PPL gap.
    
    Args:
        edit_ppl: PPL for edit task.
        gen_ppl: PPL for gen task.
    
    Returns:
        Relative gap as percentage.
    """
    return abs(edit_ppl - gen_ppl) / min(edit_ppl, gen_ppl) * 100


def analyze_bug_balance(
    ppl_data: Dict[str, Dict[str, float]],
    thresholds: List[float]
) -> Dict[float, Dict]:
    """Analyze bug balance for different thresholds.
    
    Args:
        ppl_data: PPL data for all bugs.
        thresholds: List of gap thresholds (as percentages).
    
    Returns:
        Dictionary mapping threshold to analysis results.
    """
    results = {}
    
    # Calculate gaps for all bugs
    bug_gaps = []
    for slug, data in ppl_data.items():
        if 'edit_ppl' in data and 'gen_ppl' in data:
            gap = calculate_ppl_gap(data['edit_ppl'], data['gen_ppl'])
            bug_gaps.append({
                'slug': slug,
                'edit_ppl': data['edit_ppl'],
                'gen_ppl': data['gen_ppl'],
                'gap': gap,
                'preferred': 'edit' if data['edit_ppl'] < data['gen_ppl'] else 'gen'
            })
    
    # Sort by gap
    bug_gaps.sort(key=lambda x: x['gap'])
    
    # Analyze for each threshold
    for threshold in thresholds:
        balanced_bugs = [b for b in bug_gaps if b['gap'] < threshold]
        
        results[threshold] = {
            'threshold': threshold,
            'total_bugs': len(bug_gaps),
            'balanced_bugs': len(balanced_bugs),
            'balanced_percentage': len(balanced_bugs) / len(bug_gaps) * 100,
            'balanced_bug_list': balanced_bugs,
            'gap_statistics': {
                'min': min(b['gap'] for b in bug_gaps),
                'max': max(b['gap'] for b in bug_gaps),
                'mean': np.mean([b['gap'] for b in bug_gaps]),
                'median': np.median([b['gap'] for b in bug_gaps]),
                'std': np.std([b['gap'] for b in bug_gaps]),
                'percentiles': {
                    '10': np.percentile([b['gap'] for b in bug_gaps], 10),
                    '25': np.percentile([b['gap'] for b in bug_gaps], 25),
                    '50': np.percentile([b['gap'] for b in bug_gaps], 50),
                    '75': np.percentile([b['gap'] for b in bug_gaps], 75),
                    '90': np.percentile([b['gap'] for b in bug_gaps], 90),
                }
            }
        }
    
    return results, bug_gaps


def print_summary_table(
    results_coder: Dict[float, Dict],
    results_30b: Dict[float, Dict]
):
    """Print summary comparison table."""
    print("\n" + "=" * 100)
    print("所有 698 个 Bugs 的平衡分析汇总")
    print("=" * 100)
    
    print("\n## 按阈值统计\n")
    print("| Gap 阈值 | qwen3_coder 平衡 Bugs | qwen3_coder % | "
          "qwen3_30b 平衡 Bugs | qwen3_30b % |")
    print("|---------|---------------------|--------------|"
          "-------------------|------------|")
    
    for threshold in sorted(results_coder.keys()):
        coder_count = results_coder[threshold]['balanced_bugs']
        coder_pct = results_coder[threshold]['balanced_percentage']
        b30_count = results_30b[threshold]['balanced_bugs']
        b30_pct = results_30b[threshold]['balanced_percentage']
        
        print(f"| {threshold:.0f}% | {coder_count} | {coder_pct:.1f}% | "
              f"{b30_count} | {b30_pct:.1f}% |")


def print_gap_distribution(
    model: str,
    results: Dict[float, Dict]
):
    """Print gap distribution statistics."""
    print(f"\n## {model} - PPL Gap 分布统计\n")
    
    # Use any threshold to get gap statistics (they're the same)
    stats = results[list(results.keys())[0]]['gap_statistics']
    
    print(f"**基本统计**:")
    print(f"- 最小 gap: {stats['min']:.2f}%")
    print(f"- 最大 gap: {stats['max']:.2f}%")
    print(f"- 平均 gap: {stats['mean']:.2f}%")
    print(f"- 中位数 gap: {stats['median']:.2f}%")
    print(f"- 标准差: {stats['std']:.2f}%")
    
    print(f"\n**百分位数**:")
    print(f"| 百分位 | Gap 值 |")
    print(f"|--------|--------|")
    for percentile, value in stats['percentiles'].items():
        print(f"| {percentile}% | {value:.2f}% |")


def print_detailed_analysis(
    threshold: float,
    results_coder: Dict[float, Dict],
    results_30b: Dict[float, Dict]
):
    """Print detailed analysis for a specific threshold."""
    print(f"\n## 详细分析：Gap < {threshold:.0f}%\n")
    
    for model, results in [('qwen3_coder', results_coder), 
                           ('qwen3_30b', results_30b)]:
        result = results[threshold]
        balanced = result['balanced_bug_list']
        
        print(f"### {model}\n")
        print(f"**平衡 bugs 数量**: {len(balanced)} / {result['total_bugs']} "
              f"({result['balanced_percentage']:.1f}%)\n")
        
        if len(balanced) > 0:
            # Gap distribution
            gaps = [b['gap'] for b in balanced]
            print(f"**Gap 分布**:")
            print(f"- 最小: {min(gaps):.2f}%")
            print(f"- 最大: {max(gaps):.2f}%")
            print(f"- 平均: {np.mean(gaps):.2f}%")
            print(f"- 中位数: {np.median(gaps):.2f}%")
            
            # Preference distribution
            edit_pref = sum(1 for b in balanced if b['preferred'] == 'edit')
            gen_pref = len(balanced) - edit_pref
            print(f"\n**任务偏好分布**:")
            print(f"- 偏好 edit: {edit_pref} ({edit_pref/len(balanced)*100:.1f}%)")
            print(f"- 偏好 gen: {gen_pref} ({gen_pref/len(balanced)*100:.1f}%)")
            
            # Show top 10 most balanced bugs
            print(f"\n**最平衡的 10 个 bugs**:")
            print(f"| Rank | Slug | Gap | Edit PPL | Gen PPL | Preferred |")
            print(f"|------|------|-----|----------|---------|-----------|")
            for i, bug in enumerate(balanced[:10], 1):
                print(f"| {i} | {bug['slug']} | {bug['gap']:.2f}% | "
                      f"{bug['edit_ppl']:.2e} | {bug['gen_ppl']:.2e} | "
                      f"{bug['preferred']} |")
        
        print()


def analyze_cross_model_consistency(
    results_coder: Dict[float, Dict],
    results_30b: Dict[float, Dict],
    threshold: float
):
    """Analyze consistency between models."""
    print(f"\n## 跨模型一致性分析（Gap < {threshold:.0f}%）\n")
    
    coder_balanced = set(b['slug'] 
                        for b in results_coder[threshold]['balanced_bug_list'])
    b30_balanced = set(b['slug'] 
                      for b in results_30b[threshold]['balanced_bug_list'])
    
    both_balanced = coder_balanced & b30_balanced
    only_coder = coder_balanced - b30_balanced
    only_30b = b30_balanced - coder_balanced
    
    print(f"**集合关系**:")
    print(f"- 两个模型都识别为平衡: {len(both_balanced)} bugs")
    print(f"- 仅 qwen3_coder 识别: {len(only_coder)} bugs")
    print(f"- 仅 qwen3_30b 识别: {len(only_30b)} bugs")
    print(f"- 并集: {len(coder_balanced | b30_balanced)} bugs")
    
    if len(coder_balanced) > 0 and len(b30_balanced) > 0:
        jaccard = len(both_balanced) / len(coder_balanced | b30_balanced)
        print(f"\n**Jaccard 相似度**: {jaccard:.3f}")
        
        overlap_coder = len(both_balanced) / len(coder_balanced) * 100
        overlap_30b = len(both_balanced) / len(b30_balanced) * 100
        print(f"**重叠率**:")
        print(f"- qwen3_coder: {overlap_coder:.1f}%")
        print(f"- qwen3_30b: {overlap_30b:.1f}%")


def save_balanced_bug_lists(
    results_coder: Dict[float, Dict],
    results_30b: Dict[float, Dict],
    output_dir: Path
):
    """Save balanced bug lists to files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for threshold in results_coder.keys():
        # Save for each model
        for model, results in [('qwen3_coder', results_coder), 
                               ('qwen3_30b', results_30b)]:
            balanced = results[threshold]['balanced_bug_list']
            
            output_file = output_dir / f"{model}_balanced_bugs_gap{threshold:.0f}.jsonl"
            with open(output_file, 'w') as f:
                for bug in balanced:
                    f.write(json.dumps(bug) + '\n')
            
            print(f"Saved: {output_file}")


def main():
    """Main analysis function."""
    print("=" * 100)
    print("个体 Bug 平衡分析")
    print("=" * 100)
    
    # Load PPL data
    print("\n加载 PPL 数据...")
    ppl_coder = load_ppl_data('qwen3_coder')
    ppl_30b = load_ppl_data('qwen3_30b')
    
    print(f"qwen3_coder: {len(ppl_coder)} bugs")
    print(f"qwen3_30b: {len(ppl_30b)} bugs")
    
    # Define thresholds
    thresholds = [5, 10, 15, 20, 25, 30, 40, 50]
    
    # Analyze
    print("\n分析中...")
    results_coder, bugs_coder = analyze_bug_balance(ppl_coder, thresholds)
    results_30b, bugs_30b = analyze_bug_balance(ppl_30b, thresholds)
    
    # Print summary
    print_summary_table(results_coder, results_30b)
    
    # Print gap distribution
    print("\n" + "=" * 100)
    print("PPL Gap 分布分析")
    print("=" * 100)
    print_gap_distribution('qwen3_coder', results_coder)
    print_gap_distribution('qwen3_30b', results_30b)
    
    # Detailed analysis for key thresholds
    print("\n" + "=" * 100)
    print("关键阈值详细分析")
    print("=" * 100)
    
    for threshold in [10, 20, 30]:
        print_detailed_analysis(threshold, results_coder, results_30b)
    
    # Cross-model consistency
    print("\n" + "=" * 100)
    print("跨模型一致性")
    print("=" * 100)
    
    for threshold in [10, 20, 30]:
        analyze_cross_model_consistency(results_coder, results_30b, threshold)
    
    # Save results
    print("\n" + "=" * 100)
    print("保存结果")
    print("=" * 100)
    
    output_dir = Path("bug_task_model_selection/data/analysis/balanced_bugs")
    save_balanced_bug_lists(results_coder, results_30b, output_dir)
    
    print("\n" + "=" * 100)
    print("分析完成")
    print("=" * 100)


if __name__ == "__main__":
    main()
