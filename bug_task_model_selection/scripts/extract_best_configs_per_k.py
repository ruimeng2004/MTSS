#!/usr/bin/env python3
"""Extract best configurations for each K value."""

import pandas as pd
from pathlib import Path


def load_experiment_data(model: str) -> pd.DataFrame:
    """Load experiment results for a specific model."""
    data_path = Path(f"bug_task_model_selection/data/exp_full_{model}")
    df = pd.read_csv(data_path / "experiment_results.csv")
    return df


def find_best_config_per_k(df: pd.DataFrame, model: str) -> pd.DataFrame:
    """Find best configuration for each K value."""
    results = []
    
    for k in sorted(df['k'].unique()):
        k_df = df[df['k'] == k]
        
        # Find best configuration
        best_idx = k_df['win_rate'].idxmax()
        best_row = k_df.loc[best_idx]
        
        results.append({
            'model': model,
            'k': k,
            'win_rate': best_row['win_rate'],
            'view': best_row['view'],
            'algorithm': best_row['clustering_algorithm'],
            'sampling': best_row['sampling_method'],
            'reps': best_row['reps_per_cluster'],
            'voting': best_row['voting_strategy'],
            'seed': best_row['seed']
        })
    
    return pd.DataFrame(results)


def main():
    """Main function."""
    print("=" * 100)
    print("每个 K 值的最佳实验配置")
    print("=" * 100)
    
    all_results = []
    
    for model in ['coder', '30b']:
        print(f"\n\n## 模型: qwen3_{model}\n")
        
        df = load_experiment_data(model)
        best_configs = find_best_config_per_k(df, model)
        
        # Print as markdown table
        print("| K | Win Rate | View | Algorithm | Sampling | Reps | Voting | Seed |")
        print("|---|----------|------|-----------|----------|------|--------|------|")
        
        for _, row in best_configs.iterrows():
            print(f"| {row['k']} | {row['win_rate']:.1%} | "
                  f"{row['view']} | {row['algorithm']} | "
                  f"{row['sampling']} | {row['reps']} | "
                  f"{row['voting']} | {row['seed']} |")
        
        all_results.append(best_configs)
    
    # Combined comparison
    print("\n\n## 两个模型对比\n")
    print("| K | qwen3_coder | qwen3_30b | 最佳配置 (coder) | 最佳配置 (30b) |")
    print("|---|-------------|-----------|------------------|----------------|")
    
    coder_df = all_results[0]
    b30_df = all_results[1]
    
    for k in sorted(coder_df['k'].unique()):
        coder_row = coder_df[coder_df['k'] == k].iloc[0]
        b30_row = b30_df[b30_df['k'] == k].iloc[0]
        
        coder_config = f"{coder_row['view'][:15]}... + {coder_row['algorithm']} + reps={coder_row['reps']}"
        b30_config = f"{b30_row['view'][:15]}... + {b30_row['algorithm']} + reps={b30_row['reps']}"
        
        print(f"| {k} | {coder_row['win_rate']:.1%} | "
              f"{b30_row['win_rate']:.1%} | {coder_config} | {b30_config} |")
    
    # Analysis: configuration patterns
    print("\n\n## 配置模式分析\n")
    
    for model_name, best_df in [('qwen3_coder', all_results[0]), 
                                  ('qwen3_30b', all_results[1])]:
        print(f"\n### {model_name}:\n")
        
        print("**View 分布:**")
        view_counts = best_df['view'].value_counts()
        for view, count in view_counts.items():
            print(f"  - {view}: {count} 次")
        
        print("\n**Algorithm 分布:**")
        algo_counts = best_df['algorithm'].value_counts()
        for algo, count in algo_counts.items():
            print(f"  - {algo}: {count} 次")
        
        print("\n**Sampling 分布:**")
        sampling_counts = best_df['sampling'].value_counts()
        for sampling, count in sampling_counts.items():
            print(f"  - {sampling}: {count} 次")
        
        print("\n**Reps 分布:**")
        reps_counts = best_df['reps'].value_counts()
        for reps, count in reps_counts.items():
            print(f"  - {reps}: {count} 次")
        
        print("\n**Voting 分布:**")
        voting_counts = best_df['voting'].value_counts()
        for voting, count in voting_counts.items():
            print(f"  - {voting}: {count} 次")


if __name__ == "__main__":
    main()
