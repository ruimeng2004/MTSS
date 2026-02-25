#!/usr/bin/env python3
"""Analyze routing accuracy: does the representative correctly predict cluster majority?"""

import json
from pathlib import Path
from collections import defaultdict

VIEWS = ["report", "test", "error", "error_plus_test", "buggy_code", "buggy_code_obfuscated", "buggy_code_mixed"]
MODELS = ["qwen3_coder", "qwen3_30b"]
KS = [10, 20, 30, 50, 70, 100, 150, 200, 300]

base_dir = Path("bug_task_model_selection/data")

def load_ppl(path):
    data = {}
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            data[obj["slug"]] = obj["value"]
    return data

def load_assignments(path):
    """Load slug -> cluster_id mapping."""
    data = {}
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            item_id = obj["item_id"]
            slug = item_id.rsplit("__", 1)[0]
            data[slug] = obj["cluster_id"]
    return data

def load_choices(path):
    with open(path) as f:
        data = json.load(f)
        return {int(k): v["chosen"] for k, v in data.items()}

def analyze_routing_accuracy(ppl_edit, ppl_gen, assignments, choices):
    """
    Analyze if representative's choice matches cluster majority.
    
    Returns:
        correct_clusters: number of clusters where rep choice = majority
        total_clusters: total number of clusters
        cluster_details: list of per-cluster stats
    """
    # Group slugs by cluster
    cluster_slugs = defaultdict(list)
    for slug, cid in assignments.items():
        if slug in ppl_edit and slug in ppl_gen:
            cluster_slugs[cid].append(slug)
    
    correct = 0
    total = 0
    details = []
    
    for cid, slugs in cluster_slugs.items():
        if not slugs:
            continue
        
        # Count edit/gen wins in this cluster
        edit_wins = sum(1 for s in slugs if ppl_edit[s] <= ppl_gen[s])
        gen_wins = len(slugs) - edit_wins
        
        # Majority preference
        majority = "edit" if edit_wins > gen_wins else "gen"
        
        # Representative's choice
        chosen = choices.get(cid, "gen")
        
        # Is it correct?
        is_correct = (chosen == majority)
        if is_correct:
            correct += 1
        total += 1
        
        # Agreement rate within cluster
        agreement = max(edit_wins, gen_wins) / len(slugs) if slugs else 0
        
        details.append({
            "cluster_id": cid,
            "size": len(slugs),
            "edit_wins": edit_wins,
            "gen_wins": gen_wins,
            "majority": majority,
            "chosen": chosen,
            "correct": is_correct,
            "agreement": agreement,
        })
    
    return correct, total, details

def main():
    results = []
    
    for model in MODELS:
        ppl_edit = load_ppl(base_dir / "ppl" / f"{model}_edit.jsonl")
        ppl_gen = load_ppl(base_dir / "ppl" / f"{model}_gen.jsonl")
        
        for view in VIEWS:
            for k in KS:
                assignments_path = base_dir / f"clusters_{view}" / "cuts" / f"k={k}" / "assignments.jsonl"
                choices_path = base_dir / f"selection_{view}" / f"k={k}_{model}" / "cluster_choices.json"
                
                if not assignments_path.exists() or not choices_path.exists():
                    continue
                
                assignments = load_assignments(assignments_path)
                choices = load_choices(choices_path)
                
                correct, total, details = analyze_routing_accuracy(ppl_edit, ppl_gen, assignments, choices)
                
                # Calculate average agreement
                avg_agreement = sum(d["agreement"] for d in details) / len(details) if details else 0
                
                results.append({
                    "model": model,
                    "view": view,
                    "k": k,
                    "correct_clusters": correct,
                    "total_clusters": total,
                    "routing_accuracy": correct / total if total > 0 else 0,
                    "avg_cluster_agreement": avg_agreement,
                })
    
    # Print results
    print("=" * 100)
    print("Routing Accuracy Analysis")
    print("(Does representative's choice match cluster majority?)")
    print("=" * 100)
    
    for model in MODELS:
        print(f"\n{model}")
        print("-" * 90)
        
        # Header
        header = f"{'View':<25}"
        for k in KS:
            header += f" k={k:>3}"
        print(header)
        print("-" * 90)
        
        for view in VIEWS:
            row = f"{view:<25}"
            for k in KS:
                r = next((x for x in results if x["model"] == model and x["view"] == view and x["k"] == k), None)
                if r:
                    row += f" {r['routing_accuracy']*100:>5.1f}%"
                else:
                    row += "    N/A"
            print(row)
    
    # Print cluster agreement (how homogeneous are clusters?)
    print("\n" + "=" * 100)
    print("Average Cluster Agreement (how homogeneous are clusters?)")
    print("=" * 100)
    
    for model in MODELS:
        print(f"\n{model}")
        print("-" * 90)
        
        header = f"{'View':<25}"
        for k in KS:
            header += f" k={k:>3}"
        print(header)
        print("-" * 90)
        
        for view in VIEWS:
            row = f"{view:<25}"
            for k in KS:
                r = next((x for x in results if x["model"] == model and x["view"] == view and x["k"] == k), None)
                if r:
                    row += f" {r['avg_cluster_agreement']*100:>5.1f}%"
                else:
                    row += "    N/A"
            print(row)
    
    # Summary: best combinations
    print("\n" + "=" * 100)
    print("Top 10 by Routing Accuracy")
    print("=" * 100)
    sorted_results = sorted(results, key=lambda x: -x["routing_accuracy"])
    for i, r in enumerate(sorted_results[:10], 1):
        print(f"{i:>2}. {r['view']:<25} {r['model']:<15} k={r['k']:<3} "
              f"accuracy={r['routing_accuracy']*100:.1f}% "
              f"agreement={r['avg_cluster_agreement']*100:.1f}%")

if __name__ == "__main__":
    main()
