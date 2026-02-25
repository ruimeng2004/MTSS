#!/usr/bin/env python3
"""Analyze reps sensitivity for best configurations."""

import pandas as pd
from pathlib import Path


def load_experiment_data(model: str) -> pd.DataFrame:
    """Load experiment results for a specific model."""
    data_path = Path(f"bug_task_model_selection/data/exp_full_{model}")
    df = pd.read_csv(data_path / "experiment_results.csv")
    return df


def find_best_config_per_k(df: pd.DataFrame) -> pd.DataFrame:
    """Find best configuration for each K value."""
    results = []
    
    for k in sorted(df['k'].unique()):
        k_df = df[df['k'] == k]
        best_idx = k_df['win_rate'].idxmax()
        best_row = k_df.loc[best_idx]
        
        results.append({
            'k': k,
            'view': best_row['view'],
            'algorithm': best_row['clustering_algorithm'],
            'sampling': best_row['sampling_method'],
            'voting': best_row['voting_strategy'],
            'seed': best_row['seed'],
            'best_reps': best_row['reps_per_cluster'],
            'best_win_rate': best_row['win_rate']
        })
    
    return pd.DataFrame(results)


def analyze_reps_for_config(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Analyze all reps values for a specific configuration."""
    mask = (
        (df['k'] == config['k']) &
        (df['view'] == config['view']) &
        (df['clustering_algorithm'] == config['algorithm']) &
        (df['sampling_method'] == config['sampling']) &
        (df['voting_strategy'] == config['voting']) &
        (df['seed'] == config['seed'])
    )
    
    config_df = df[mask].copy()
    config_df = config_df.sort_values('reps_per_cluster')
    
    return config_df[['reps_per_cluster', 'win_rate']]


def main():
    """Main analysis function."""
    print("=" * 100)
    print("最佳配置的 Reps 敏感性分析")
    print("=" * 100)
    
    for model in ['coder', '30b']:
        print(f"\n\n{'=' * 100}")
        print(f"模型: qwen3_{model}")
        print("=" * 100)
        
        df = load_experiment_data(model)
        best_configs = find_best_config_per_k(df)
        
        for _, config in best_configs.iterrows():
            k = config['k']
            avg_cluster_size = 698 / k
            
            print(f"\n\n## K = {k} (平均簇大小: {avg_cluster_size:.1f} bugs)")
            print(f"最佳配置: {config['view']} + {config['algorithm']} + "
                  f"{config['sampling']} + {config['voting']} (seed={config['seed']})")
            print(f"最佳 Reps: {config['best_reps']} (Win Rate: {config['best_win_rate']:.1%})")
            print()
            
            # Get all reps results for this config
            reps_results = analyze_reps_for_config(df, config)
            
            if len(reps_results) > 0:
                print("| Reps | Win Rate | vs 最佳 | 占簇比例 | 推荐 |")
                print("|------|----------|---------|----------|------|")
                
                best_rate = config['best_win_rate']
                
                for _, row in reps_results.iterrows():
                    reps = int(row['reps_per_cluster'])
                    rate = row['win_rate']
                    diff = rate - best_rate
                    ratio = reps / avg_cluster_size * 100
                    
                    # 判断是否推荐
                    recommend = ""
                    if diff >= -0.005:  # 差距小于0.5%
                        if ratio < 80:  # 不会采样过多
                            recommend = "✓ 推荐"
                        elif ratio < 100:
                            recommend = "⚠ 可用"
                        else:
                            recommend = "✗ 过采样"
                    
                    print(f"| {reps} | {rate:.1%} | {diff:+.1%} | {ratio:.0f}% | {recommend} |")
            else:
                print("⚠ 未找到该配置的其他 reps 结果")
    
    # Summary
    print("\n\n" + "=" * 100)
    print("总结与建议")
    print("=" * 100)
    
    print("\n### 关键发现:\n")
    print("1. **K ≤ 50**: 簇较大 (14 bugs)，reps=7 合理 (占50%)")
    print("2. **K = 100**: 簇大小 = 7 bugs，reps=7 会采样全部点 (100%)")
    print("3. **K ≥ 150**: 簇很小 (≤5 bugs)，reps=7 严重过采样 (>150%)")
    print("\n### 推荐策略:\n")
    print("- **K=50**: reps=5~7 (占36~50%)")
    print("- **K=100**: reps=3~5 (占43~71%)")
    print("- **K=150**: reps=3 (占64%)")
    print("- **K=200**: reps=1~3 (占29~86%)")
    print("- **K=300**: reps=1 (占43%)")
    print("- **K=500**: reps=1 (占72%)")


if __name__ == "__main__":
    main()
