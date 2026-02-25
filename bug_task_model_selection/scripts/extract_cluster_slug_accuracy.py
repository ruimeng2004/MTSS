#!/usr/bin/env python3
"""Extract cluster-level and slug-level accuracy from experiment results."""

import pandas as pd
from pathlib import Path


def extract_best_config_accuracy(model: str):
    """Extract accuracy for best configurations.
    
    Args:
        model: Model name (qwen3_coder or qwen3_30b).
    """
    # Load experiment results
    model_suffix = model.replace('qwen3_', '')
    results_path = Path(f"bug_task_model_selection/data/exp_full_{model_suffix}/"
                       f"experiment_results.csv")
    
    if not results_path.exists():
        print(f"Error: {results_path} not found")
        return
    
    df = pd.read_csv(results_path)
    
    # Best configurations
    best_configs = {
        'qwen3_coder': [
            {'k': 50, 'view': 'buggy_code_mixed', 'algorithm': 'hac_complete',
             'sampling': 'kdpp', 'seed': 123},
            {'k': 100, 'view': 'buggy_code_mixed', 
             'algorithm': 'bisecting_kmeans', 'sampling': 'farthest_first',
             'seed': 456},
            {'k': 150, 'view': 'buggy_code_obfuscated',
             'algorithm': 'bisecting_kmeans', 'sampling': 'farthest_first',
             'seed': 123},
            {'k': 200, 'view': 'buggy_code_obfuscated',
             'algorithm': 'bisecting_kmeans', 'sampling': 'farthest_first',
             'seed': 123},
            {'k': 300, 'view': 'buggy_code_mixed', 'algorithm': 'hac_single',
             'sampling': 'farthest_first', 'seed': 42},
            {'k': 500, 'view': 'buggy_code_obfuscated',
             'algorithm': 'hac_single', 'sampling': 'farthest_first',
             'seed': 42},
        ],
        'qwen3_30b': [
            {'k': 50, 'view': 'buggy_code_obfuscated', 'algorithm': 'kmeans',
             'sampling': 'farthest_first', 'seed': 456},
            {'k': 100, 'view': 'report', 'algorithm': 'kmeans',
             'sampling': 'farthest_first', 'seed': 123},
            {'k': 150, 'view': 'buggy_code_obfuscated',
             'algorithm': 'bisecting_kmeans', 'sampling': 'farthest_first',
             'seed': 42},
            {'k': 200, 'view': 'buggy_code_mixed', 'algorithm': 'kmeans',
             'sampling': 'farthest_first', 'seed': 456},
            {'k': 300, 'view': 'buggy_code_mixed',
             'algorithm': 'bisecting_kmeans', 'sampling': 'farthest_first',
             'seed': 42},
            {'k': 500, 'view': 'report', 'algorithm': 'hac_single',
             'sampling': 'farthest_first', 'seed': 42},
        ]
    }
    
    configs = best_configs.get(model, [])
    
    print(f"\n{'=' * 100}")
    print(f"{model} 最佳配置的 Cluster 和 Slug 准确率")
    print(f"{'=' * 100}\n")
    
    for config in configs:
        k = config['k']
        view = config['view']
        algorithm = config['algorithm']
        sampling = config['sampling']
        seed = config['seed']
        
        print(f"K={k} | View={view} | Algorithm={algorithm}")
        print(f"{'=' * 80}\n")
        
        # Filter for this configuration
        mask = (
            (df['k'] == k) &
            (df['view'] == view) &
            (df['clustering_algorithm'] == algorithm) &
            (df['sampling_method'] == sampling) &
            (df['seed'] == seed) &
            (df['voting_strategy'] == 'majority')
        )
        
        config_df = df[mask].copy()
        
        if len(config_df) == 0:
            print("⚠️ 未找到数据\n")
            continue
        
        # Sort by reps
        config_df = config_df.sort_values('reps_per_cluster')
        
        print("| Reps | Cluster 准确率 | Slug 准确率 (Win Rate) | "
              "正确簇数 | 总簇数 |")
        print("|------|---------------|----------------------|---------|--------|")
        
        for _, row in config_df.iterrows():
            reps = row['reps_per_cluster']
            cluster_acc = row['cluster_accuracy']
            win_rate = row['win_rate']
            n_clusters = row['n_clusters']
            
            # Calculate correct clusters
            n_correct = int(cluster_acc * n_clusters)
            
            print(f"| {reps} | {cluster_acc:.1%} | {win_rate:.1%} | "
                  f"{n_correct}/{n_clusters} | {n_clusters} |")
        
        print()


def main():
    """Main function."""
    for model in ['qwen3_coder', 'qwen3_30b']:
        extract_best_config_accuracy(model)


if __name__ == "__main__":
    main()
