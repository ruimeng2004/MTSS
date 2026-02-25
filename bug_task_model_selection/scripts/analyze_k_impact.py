#!/usr/bin/env python3
"""Analyze K value impact under different control variable combinations."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple


def load_experiment_data(model: str) -> pd.DataFrame:
    """Load experiment results for a specific model.
    
    Args:
        model: Model name (coder or 30b).
    
    Returns:
        DataFrame with experiment results.
    """
    data_path = Path(f"bug_task_model_selection/data/exp_full_{model}")
    df = pd.read_csv(data_path / "experiment_results.csv")
    return df


def analyze_k_by_single_variable(
    df: pd.DataFrame, 
    control_var: str
) -> pd.DataFrame:
    """Analyze K impact for each value of a control variable.
    
    Args:
        df: Experiment results DataFrame.
        control_var: Variable to analyze (e.g., 'view', 'clustering_algorithm').
    
    Returns:
        DataFrame with K impact for each control variable value.
    """
    results = []
    
    for var_value in sorted(df[control_var].unique()):
        subset = df[df[control_var] == var_value]
        k_stats = subset.groupby('k')['win_rate'].agg(['mean', 'std', 'count'])
        
        for k in k_stats.index:
            results.append({
                'control_variable': control_var,
                'control_value': var_value,
                'k': k,
                'win_rate_mean': k_stats.loc[k, 'mean'],
                'win_rate_std': k_stats.loc[k, 'std'],
                'n_experiments': k_stats.loc[k, 'count']
            })
    
    return pd.DataFrame(results)


def analyze_k_by_combination(
    df: pd.DataFrame,
    control_vars: List[str]
) -> pd.DataFrame:
    """Analyze K impact for specific combinations of control variables.
    
    Args:
        df: Experiment results DataFrame.
        control_vars: List of control variables to combine.
    
    Returns:
        DataFrame with K impact for each combination.
    """
    results = []
    
    grouped = df.groupby(control_vars + ['k'])
    
    for group_keys, group_df in grouped:
        *control_values, k = group_keys
        
        results.append({
            **{f'{var}': val for var, val in zip(control_vars, control_values)},
            'k': k,
            'win_rate_mean': group_df['win_rate'].mean(),
            'win_rate_std': group_df['win_rate'].std(),
            'n_experiments': len(group_df)
        })
    
    return pd.DataFrame(results)


def find_best_worst_configs(
    df: pd.DataFrame,
    control_vars: List[str],
    k_value: int
) -> Tuple[pd.Series, pd.Series]:
    """Find best and worst configurations for a specific K value.
    
    Args:
        df: Experiment results DataFrame.
        control_vars: Control variables to consider.
        k_value: K value to analyze.
    
    Returns:
        Tuple of (best_config, worst_config) Series.
    """
    k_df = df[df['k'] == k_value]
    grouped = k_df.groupby(control_vars)['win_rate'].mean()
    
    best_idx = grouped.idxmax()
    worst_idx = grouped.idxmin()
    
    return grouped[best_idx], grouped[worst_idx]


def main():
    """Main analysis function."""
    print("=" * 80)
    print("K 值影响详细分析")
    print("=" * 80)
    
    for model in ['coder', '30b']:
        print(f"\n\n{'=' * 80}")
        print(f"模型: qwen3_{model}")
        print("=" * 80)
        
        df = load_experiment_data(model)
        
        # 1. 按单个控制变量分析
        print("\n\n## 1. K 值在不同控制变量下的影响\n")
        
        control_variables = [
            'view', 
            'clustering_algorithm', 
            'sampling_method',
            'reps_per_cluster',
            'voting_strategy'
        ]
        
        for control_var in control_variables:
            print(f"\n### 控制变量: {control_var}\n")
            
            k_analysis = analyze_k_by_single_variable(df, control_var)
            
            # 计算每个控制变量值的 k 影响范围
            for var_value in k_analysis['control_value'].unique():
                subset = k_analysis[k_analysis['control_value'] == var_value]
                k50 = subset[subset['k'] == 50]['win_rate_mean'].values[0]
                k500 = subset[subset['k'] == 500]['win_rate_mean'].values[0]
                improvement = k500 - k50
                
                print(f"{str(var_value):30s}: k=50: {k50:.1%}, "
                      f"k=500: {k500:.1%}, 提升: {improvement:+.1%}")
        
        # 2. 找出 k 影响最大和最小的配置
        print("\n\n## 2. K 值影响的极端情况\n")
        
        # 分析所有组合（除了 k 和 seed）
        combo_vars = ['view', 'clustering_algorithm', 'sampling_method', 
                      'reps_per_cluster', 'voting_strategy']
        
        combo_df = analyze_k_by_combination(df, combo_vars)
        
        # 计算每个组合的 k50 到 k500 的提升
        improvements = []
        for combo_keys, combo_group in combo_df.groupby(combo_vars):
            k50_rate = combo_group[combo_group['k'] == 50]['win_rate_mean']
            k500_rate = combo_group[combo_group['k'] == 500]['win_rate_mean']
            
            if len(k50_rate) > 0 and len(k500_rate) > 0:
                improvement = k500_rate.values[0] - k50_rate.values[0]
                improvements.append({
                    **{var: val for var, val in zip(combo_vars, combo_keys)},
                    'k50_win_rate': k50_rate.values[0],
                    'k500_win_rate': k500_rate.values[0],
                    'improvement': improvement
                })
        
        imp_df = pd.DataFrame(improvements)
        
        print("\n### K 值影响最大的 5 个配置（k=50 → k=500）:\n")
        top5 = imp_df.nlargest(5, 'improvement')
        for idx, row in top5.iterrows():
            print(f"提升 {row['improvement']:+.1%}:")
            print(f"  - View: {row['view']}")
            print(f"  - Algorithm: {row['clustering_algorithm']}")
            print(f"  - Sampling: {row['sampling_method']}")
            print(f"  - Reps: {row['reps_per_cluster']}")
            print(f"  - Voting: {row['voting_strategy']}")
            print(f"  - k=50: {row['k50_win_rate']:.1%}, "
                  f"k=500: {row['k500_win_rate']:.1%}\n")
        
        print("\n### K 值影响最小的 5 个配置（k=50 → k=500）:\n")
        bottom5 = imp_df.nsmallest(5, 'improvement')
        for idx, row in bottom5.iterrows():
            print(f"提升 {row['improvement']:+.1%}:")
            print(f"  - View: {row['view']}")
            print(f"  - Algorithm: {row['clustering_algorithm']}")
            print(f"  - Sampling: {row['sampling_method']}")
            print(f"  - Reps: {row['reps_per_cluster']}")
            print(f"  - Voting: {row['voting_strategy']}")
            print(f"  - k=50: {row['k50_win_rate']:.1%}, "
                  f"k=500: {row['k500_win_rate']:.1%}\n")
        
        # 3. 每个 k 值的最佳和最差配置
        print("\n\n## 3. 每个 K 值的最佳和最差配置\n")
        
        for k in sorted(df['k'].unique()):
            k_df = df[df['k'] == k]
            grouped = k_df.groupby(combo_vars)['win_rate'].mean()
            
            best_config = grouped.idxmax()
            worst_config = grouped.idxmin()
            best_rate = grouped.max()
            worst_rate = grouped.min()
            
            print(f"\n### K = {k}:\n")
            print(f"最佳配置 ({best_rate:.1%}):")
            for var, val in zip(combo_vars, best_config):
                print(f"  - {var}: {val}")
            
            print(f"\n最差配置 ({worst_rate:.1%}):")
            for var, val in zip(combo_vars, worst_config):
                print(f"  - {var}: {val}")
            
            print(f"\n配置差异: {best_rate - worst_rate:.1%}")


if __name__ == "__main__":
    main()
