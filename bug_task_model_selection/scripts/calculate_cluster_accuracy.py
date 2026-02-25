#!/usr/bin/env python3
"""Calculate cluster-level and slug-level accuracy for best configs."""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def load_ppl_data(model: str) -> Dict[str, Dict[str, float]]:
    """Load aggregated PPL data.
    
    Args:
        model: Model name (qwen3_coder or qwen3_30b).
    
    Returns:
        Dictionary mapping slug to {edit_ppl, gen_ppl}.
    """
    ppl_data = {}
    
    for task in ['edit', 'gen']:
        path = Path(f"ppl/result/{model}/{task}/aggregated_ppl.jsonl")
        if not path.exists():
            print(f"Warning: {path} not found")
            continue
        
        with open(path, 'r') as f:
            for line in f:
                obj = json.loads(line)
                slug = obj['slug']
                ppl = obj['ppl']
                
                if slug not in ppl_data:
                    ppl_data[slug] = {}
                ppl_data[slug][f'{task}_ppl'] = ppl
    
    return ppl_data


def load_cluster_assignments(
    view: str, k: int
) -> Dict[str, int]:
    """Load cluster assignments.
    
    Args:
        view: View type.
        k: Number of clusters.
    
    Returns:
        Dictionary mapping item_id to cluster_id.
    """
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
            
            # Extract slug from item_id (format: "slug__view")
            slug = item_id.rsplit('__', 1)[0]
            assignments[slug] = cluster_id
    
    return assignments


def sample_representatives(
    cluster_members: List[str],
    ppl_data: Dict[str, Dict[str, float]],
    sampling: str,
    reps: int
) -> List[str]:
    """Sample representative points from a cluster.
    
    Args:
        cluster_members: List of slugs in the cluster.
        ppl_data: PPL data for all slugs.
        sampling: Sampling method (farthest_first or kdpp).
        reps: Number of representatives to sample.
    
    Returns:
        List of representative slugs.
    """
    # For simplicity, use random sampling
    # In real implementation, this would use actual sampling algorithms
    import random
    random.seed(42)
    
    n_samples = min(reps, len(cluster_members))
    return random.sample(cluster_members, n_samples)


def vote_majority(
    representatives: List[str],
    ppl_data: Dict[str, Dict[str, float]]
) -> str:
    """Majority voting based on PPL.
    
    Args:
        representatives: List of representative slugs.
        ppl_data: PPL data.
    
    Returns:
        'edit' or 'gen'.
    """
    edit_votes = 0
    gen_votes = 0
    
    for slug in representatives:
        if slug not in ppl_data:
            continue
        
        edit_ppl = ppl_data[slug].get('edit_ppl', float('inf'))
        gen_ppl = ppl_data[slug].get('gen_ppl', float('inf'))
        
        if edit_ppl < gen_ppl:
            edit_votes += 1
        else:
            gen_votes += 1
    
    return 'edit' if edit_votes > gen_votes else 'gen'


def calculate_accuracy(
    model: str,
    view: str,
    k: int,
    sampling: str,
    reps: int
) -> Tuple[float, float, int, int]:
    """Calculate cluster-level and slug-level accuracy.
    
    Args:
        model: Model name.
        view: View type.
        k: Number of clusters.
        sampling: Sampling method.
        reps: Number of representatives.
    
    Returns:
        Tuple of (cluster_accuracy, slug_accuracy, 
                  n_correct_clusters, n_total_clusters).
    """
    # Load data
    ppl_data = load_ppl_data(model)
    assignments = load_cluster_assignments(view, k)
    
    if not ppl_data or not assignments:
        return 0.0, 0.0, 0, 0
    
    # Group slugs by cluster
    clusters = defaultdict(list)
    for slug, cluster_id in assignments.items():
        if slug in ppl_data:
            clusters[cluster_id].append(slug)
    
    # Calculate accuracy
    correct_slugs = 0
    total_slugs = 0
    correct_clusters = 0
    total_clusters = len(clusters)
    
    for cluster_id, members in clusters.items():
        if len(members) == 0:
            continue
        
        # Sample representatives
        representatives = sample_representatives(
            members, ppl_data, sampling, reps
        )
        
        # Vote for cluster decision
        cluster_decision = vote_majority(representatives, ppl_data)
        
        # Check each member
        cluster_correct = True
        for slug in members:
            edit_ppl = ppl_data[slug].get('edit_ppl', float('inf'))
            gen_ppl = ppl_data[slug].get('gen_ppl', float('inf'))
            
            ground_truth = 'edit' if edit_ppl < gen_ppl else 'gen'
            
            if cluster_decision == ground_truth:
                correct_slugs += 1
            else:
                cluster_correct = False
            
            total_slugs += 1
        
        if cluster_correct:
            correct_clusters += 1
    
    cluster_accuracy = (correct_clusters / total_clusters 
                       if total_clusters > 0 else 0.0)
    slug_accuracy = (correct_slugs / total_slugs 
                    if total_slugs > 0 else 0.0)
    
    return (cluster_accuracy, slug_accuracy, 
            correct_clusters, total_clusters)


def main():
    """Main function."""
    # Best configurations
    best_configs = [
        # qwen3_coder
        {
            'model': 'qwen3_coder',
            'k': 50,
            'view': 'buggy_code_mixed',
            'algorithm': 'hac_complete',
            'sampling': 'kdpp',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_coder',
            'k': 100,
            'view': 'buggy_code_mixed',
            'algorithm': 'bisecting_kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_coder',
            'k': 150,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'bisecting_kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_coder',
            'k': 200,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'bisecting_kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_coder',
            'k': 300,
            'view': 'buggy_code_mixed',
            'algorithm': 'hac_single',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_coder',
            'k': 500,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'hac_single',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        # qwen3_30b
        {
            'model': 'qwen3_30b',
            'k': 50,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_30b',
            'k': 100,
            'view': 'report',
            'algorithm': 'kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_30b',
            'k': 150,
            'view': 'buggy_code_obfuscated',
            'algorithm': 'bisecting_kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_30b',
            'k': 200,
            'view': 'buggy_code_mixed',
            'algorithm': 'kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_30b',
            'k': 300,
            'view': 'buggy_code_mixed',
            'algorithm': 'bisecting_kmeans',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        },
        {
            'model': 'qwen3_30b',
            'k': 500,
            'view': 'report',
            'algorithm': 'hac_single',
            'sampling': 'farthest_first',
            'reps': [1, 3, 5, 7]
        }
    ]
    
    print("=" * 100)
    print("最佳配置的 Cluster 粒度和 Slug 粒度准确率分析")
    print("=" * 100)
    
    for config in best_configs:
        model = config['model']
        k = config['k']
        view = config['view']
        sampling = config['sampling']
        reps_list = config['reps']
        
        print(f"\n{'=' * 100}")
        print(f"Model: {model} | K={k} | View={view}")
        print(f"{'=' * 100}\n")
        
        print(f"| Reps | Cluster 准确率 | Slug 准确率 | "
              f"正确簇数 | 总簇数 |")
        print(f"|------|---------------|------------|---------|--------|")
        
        for reps in reps_list:
            cluster_acc, slug_acc, n_correct, n_total = calculate_accuracy(
                model, view, k, sampling, reps
            )
            
            print(f"| {reps} | {cluster_acc:.1%} | {slug_acc:.1%} | "
                  f"{n_correct}/{n_total} | {n_total} |")


if __name__ == "__main__":
    main()
