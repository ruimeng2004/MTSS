#!/usr/bin/env python3
"""
计算混合指标预算分配实验的评估指标

评估指标：
1. 修复成功率：在给定 budget 下的成功率
2. 资源利用效率：相比固定策略的提升
3. 鲁棒性：在不同簇大小下的稳定性
4. 置信度校准：置信度与实际成功率的相关性
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import statistics


def load_cluster_choices(path: Path) -> Dict[str, Any]:
    """加载cluster_choices.json"""
    with open(path) as f:
        return json.load(f)


def load_selection_stats(path: Path) -> Dict[str, Any]:
    """加载selection_statistics.json"""
    with open(path) as f:
        return json.load(f)


def load_cluster_data(data_dir: Path) -> Tuple[Dict, Dict]:
    """加载聚类数据和分配"""
    # 加载bug分配（包含cluster_id和size信息）
    assignments_path = data_dir / "assignments.jsonl"
    assignments = {}
    cluster_sizes = defaultdict(int)
    
    if assignments_path.exists():
        with open(assignments_path) as f:
            for line in f:
                bug = json.loads(line)
                item_id = bug.get('item_id', bug.get('bug_slug', ''))
                cluster_id = bug['cluster_id']
                
                # 从item_id提取bug_slug (格式: "Chart_1__buggy_code")
                if '__buggy_code' in item_id:
                    bug_slug = item_id.replace('__buggy_code', '')
                else:
                    bug_slug = item_id
                
                assignments[bug_slug] = bug
                cluster_sizes[cluster_id] += 1
    
    # 创建clusters字典（从assignments推导）
    clusters = {}
    for cluster_id, size in cluster_sizes.items():
        clusters[str(cluster_id)] = {
            'cluster_id': cluster_id,
            'size': size
        }
    
    return clusters, assignments


def calculate_robustness_by_cluster_size(
    cluster_choices: Dict[str, Any],
    clusters: Dict[str, Any]
) -> Dict[str, Any]:
    """计算不同簇大小下的鲁棒性（Edit比例稳定性）"""
    
    # 按簇大小分组
    size_groups = defaultdict(list)
    
    for cluster_id, choice in cluster_choices.items():
        if cluster_id in clusters:
            size = clusters[cluster_id]['size']
            edit_ratio = choice.get('ratio', {}).get('edit', choice.get('edit_ratio', 0.5))
            confidence = choice.get('confidence', 0.0)
            
            # 分组：小簇(1-5), 中簇(6-15), 大簇(16+)
            if size <= 5:
                group = 'small'
            elif size <= 15:
                group = 'medium'
            else:
                group = 'large'
            
            size_groups[group].append({
                'size': size,
                'edit_ratio': edit_ratio,
                'confidence': confidence
            })
    
    # 计算每组的统计数据
    robustness = {}
    for group, data in size_groups.items():
        if data:
            edit_ratios = [d['edit_ratio'] for d in data]
            confidences = [d['confidence'] for d in data]
            
            robustness[group] = {
                'count': len(data),
                'edit_ratio': {
                    'mean': statistics.mean(edit_ratios),
                    'std': statistics.stdev(edit_ratios) if len(edit_ratios) > 1 else 0.0,
                    'min': min(edit_ratios),
                    'max': max(edit_ratios),
                    'range': max(edit_ratios) - min(edit_ratios)
                },
                'confidence': {
                    'mean': statistics.mean(confidences),
                    'std': statistics.stdev(confidences) if len(confidences) > 1 else 0.0
                }
            }
    
    return robustness


def calculate_confidence_calibration(
    cluster_choices: Dict[str, Any],
    clusters: Dict[str, Any]
) -> Dict[str, Any]:
    """计算置信度校准指标"""
    
    # 按置信度区间分组
    confidence_bins = {
        'very_low': (0.0, 0.1),
        'low': (0.1, 0.3),
        'medium': (0.3, 0.5),
        'high': (0.5, 0.7),
        'very_high': (0.7, 1.0)
    }
    
    binned_data = defaultdict(list)
    
    for cluster_id, choice in cluster_choices.items():
        confidence = choice.get('confidence', 0.0)
        edit_ratio = choice.get('ratio', {}).get('edit', choice.get('edit_ratio', 0.5))
        
        # 确定置信度区间
        for bin_name, (low, high) in confidence_bins.items():
            if low <= confidence < high or (bin_name == 'very_high' and confidence >= high):
                binned_data[bin_name].append({
                    'confidence': confidence,
                    'edit_ratio': edit_ratio,
                    'deviation': abs(edit_ratio - 0.5)  # 偏离中性的程度
                })
                break
    
    # 计算每个区间的统计
    calibration = {}
    for bin_name, data in binned_data.items():
        if data:
            calibration[bin_name] = {
                'count': len(data),
                'avg_confidence': statistics.mean(d['confidence'] for d in data),
                'avg_edit_ratio': statistics.mean(d['edit_ratio'] for d in data),
                'avg_deviation': statistics.mean(d['deviation'] for d in data),
                'edit_ratio_range': {
                    'min': min(d['edit_ratio'] for d in data),
                    'max': max(d['edit_ratio'] for d in data)
                }
            }
    
    return calibration


def calculate_resource_efficiency_potential(
    cluster_choices: Dict[str, Any],
    clusters: Dict[str, Any]
) -> Dict[str, Any]:
    """计算资源利用潜力（相比固定50-50策略）"""
    
    total_bugs = sum(clusters[cid]['size'] for cid in cluster_choices.keys() 
                     if cid in clusters)
    
    # 策略1: 固定50-50分配
    fixed_edit_count = total_bugs * 0.5
    fixed_gen_count = total_bugs * 0.5
    
    # 策略2: 动态分配（基于cluster_choices）
    dynamic_edit_count = 0
    dynamic_gen_count = 0
    
    # 追踪不同置信度下的分配决策
    allocation_by_confidence = defaultdict(lambda: {'edit': 0, 'gen': 0, 'total': 0})
    
    for cluster_id, choice in cluster_choices.items():
        if cluster_id not in clusters:
            continue
        
        cluster_size = clusters[cluster_id]['size']
        edit_ratio = choice.get('ratio', {}).get('edit', choice.get('edit_ratio', 0.5))
        confidence = choice.get('confidence', 0.0)
        
        # 计算edit和gen的数量
        edit_count = cluster_size * edit_ratio
        gen_count = cluster_size * (1 - edit_ratio)
        
        dynamic_edit_count += edit_count
        dynamic_gen_count += gen_count
        
        # 按置信度区间统计
        if confidence < 0.3:
            conf_level = 'low'
        elif confidence < 0.6:
            conf_level = 'medium'
        else:
            conf_level = 'high'
        
        allocation_by_confidence[conf_level]['edit'] += edit_count
        allocation_by_confidence[conf_level]['gen'] += gen_count
        allocation_by_confidence[conf_level]['total'] += cluster_size
    
    # 计算分配差异
    edit_difference = abs(dynamic_edit_count - fixed_edit_count)
    gen_difference = abs(dynamic_gen_count - fixed_gen_count)
    
    # 计算分配决策的方差（反映策略多样性）
    edit_ratios = [choice.get('ratio', {}).get('edit', choice.get('edit_ratio', 0.5)) 
                   for choice in cluster_choices.values()]
    allocation_variance = statistics.variance(edit_ratios) if len(edit_ratios) > 1 else 0.0
    
    return {
        'total_bugs': total_bugs,
        'fixed_strategy': {
            'edit': fixed_edit_count,
            'gen': fixed_gen_count
        },
        'dynamic_strategy': {
            'edit': dynamic_edit_count,
            'gen': dynamic_gen_count
        },
        'allocation_difference': {
            'edit': edit_difference,
            'gen': gen_difference,
            'total': edit_difference + gen_difference
        },
        'allocation_variance': allocation_variance,
        'allocation_by_confidence': dict(allocation_by_confidence),
        'potential_improvement': {
            'description': '动态分配相比固定50-50的潜在提升',
            'variance': allocation_variance,
            'note': '需要实际修复结果来验证实际提升'
        }
    }


def analyze_experiment(experiment_dir: Path, data_dir: Path) -> Dict[str, Any]:
    """分析单个实验的完整评估指标"""
    
    # 加载数据
    cluster_choices = load_cluster_choices(experiment_dir / "cluster_choices.json")
    selection_stats = load_selection_stats(experiment_dir / "selection_statistics.json")
    clusters, assignments = load_cluster_data(data_dir)
    
    # 计算各项指标
    metrics = {
        'experiment_name': experiment_dir.name,
        'basic_stats': selection_stats,
        'robustness': calculate_robustness_by_cluster_size(cluster_choices, clusters),
        'confidence_calibration': calculate_confidence_calibration(cluster_choices, clusters),
        'resource_efficiency': calculate_resource_efficiency_potential(cluster_choices, clusters)
    }
    
    return metrics


def compare_experiments(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """对比多个实验的结果"""
    
    comparison = {
        'experiments': [],
        'rankings': {
            'by_confidence': [],
            'by_robustness': [],
            'by_allocation_diversity': []
        }
    }
    
    for result in results:
        exp_name = result['experiment_name']
        avg_conf = result['basic_stats']['average_confidence']
        
        # 计算鲁棒性得分（范围越小越好）
        robustness_score = 0
        if 'small' in result['robustness']:
            robustness_score += result['robustness']['small']['edit_ratio']['range']
        if 'medium' in result['robustness']:
            robustness_score += result['robustness']['medium']['edit_ratio']['range']
        if 'large' in result['robustness']:
            robustness_score += result['robustness']['large']['edit_ratio']['range']
        
        allocation_diversity = result['resource_efficiency']['allocation_variance']
        
        comparison['experiments'].append({
            'name': exp_name,
            'avg_confidence': avg_conf,
            'robustness_score': robustness_score,
            'allocation_diversity': allocation_diversity
        })
    
    # 排序
    comparison['rankings']['by_confidence'] = sorted(
        comparison['experiments'], 
        key=lambda x: x['avg_confidence'], 
        reverse=True
    )
    
    comparison['rankings']['by_robustness'] = sorted(
        comparison['experiments'], 
        key=lambda x: x['robustness_score']
    )
    
    comparison['rankings']['by_allocation_diversity'] = sorted(
        comparison['experiments'], 
        key=lambda x: x['allocation_diversity'], 
        reverse=True
    )
    
    return comparison


def main():
    parser = argparse.ArgumentParser(
        description="计算BTMS预算分配实验的评估指标"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        required=True,
        help="实验结果目录（包含多个实验子目录）"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="数据目录（包含clusters和assignments）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_metrics.json",
        help="输出文件路径"
    )
    
    args = parser.parse_args()
    
    results_dir = Path(args.results_dir)
    data_dir = Path(args.data_dir)
    output_path = Path(args.output)
    
    # 分析所有实验
    all_results = []
    for exp_dir in sorted(results_dir.iterdir()):
        if exp_dir.is_dir() and (exp_dir / "cluster_choices.json").exists():
            print(f"\n分析实验: {exp_dir.name}")
            result = analyze_experiment(exp_dir, data_dir)
            all_results.append(result)
            
            # 打印基本信息
            print(f"  平均置信度: {result['basic_stats']['average_confidence']:.4f}")
            print(f"  Edit比例: {result['basic_stats']['edit_ratio']['mean']:.4f}")
            print(f"  分配方差: {result['resource_efficiency']['allocation_variance']:.6f}")
    
    # 对比分析
    if len(all_results) > 1:
        print("\n\n=== 实验对比 ===")
        comparison = compare_experiments(all_results)
        
        print("\n置信度排名:")
        for i, exp in enumerate(comparison['rankings']['by_confidence'], 1):
            print(f"  {i}. {exp['name']}: {exp['avg_confidence']:.4f}")
        
        print("\n鲁棒性排名（得分越低越好）:")
        for i, exp in enumerate(comparison['rankings']['by_robustness'], 1):
            print(f"  {i}. {exp['name']}: {exp['robustness_score']:.4f}")
        
        print("\n分配多样性排名:")
        for i, exp in enumerate(comparison['rankings']['by_allocation_diversity'], 1):
            print(f"  {i}. {exp['name']}: {exp['allocation_diversity']:.6f}")
    
    # 保存完整结果
    output = {
        'individual_experiments': all_results,
        'comparison': comparison if len(all_results) > 1 else None
    }
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\n完整结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
