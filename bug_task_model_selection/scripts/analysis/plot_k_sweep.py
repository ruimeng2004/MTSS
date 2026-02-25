#!/usr/bin/env python3
"""Analyze and plot win rate vs k."""

import json
from pathlib import Path
import matplotlib.pyplot as plt

def load_ppl(path):
    data = {}
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            data[obj["slug"]] = obj["value"]
    return data

def load_assignments(path):
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

def compute_win_rate(ppl_edit, ppl_gen, assignments, choices):
    wins = 0
    total = 0
    common_slugs = set(ppl_edit.keys()) & set(ppl_gen.keys()) & set(assignments.keys())
    
    for slug in common_slugs:
        edit = ppl_edit[slug]
        gen = ppl_gen[slug]
        cluster_id = assignments[slug]
        
        best = "edit" if edit <= gen else "gen"
        routed = choices.get(cluster_id, "gen")
        
        if routed == best:
            wins += 1
        total += 1
    
    return wins / total if total > 0 else 0

# Config
KS = [10, 20, 30, 50, 70, 100, 150, 200, 300]
VIEW = "buggy_code_mixed"
MODEL = "qwen3_coder"
base_dir = Path("bug_task_model_selection/data")

# Load PPL
ppl_edit = load_ppl(base_dir / "ppl" / f"{MODEL}_edit.jsonl")
ppl_gen = load_ppl(base_dir / "ppl" / f"{MODEL}_gen.jsonl")

# Compute baseline
common = set(ppl_edit.keys()) & set(ppl_gen.keys())
always_gen_wins = sum(1 for s in common if ppl_gen[s] <= ppl_edit[s])
always_edit_wins = sum(1 for s in common if ppl_edit[s] <= ppl_gen[s])
always_gen_rate = always_gen_wins / len(common)
always_edit_rate = always_edit_wins / len(common)

print(f"Baseline: always_gen = {always_gen_rate*100:.1f}%, always_edit = {always_edit_rate*100:.1f}%")
print()

# Compute win rate for each k
results = []
for k in KS:
    assignments_path = base_dir / f"clusters_{VIEW}" / "cuts" / f"k={k}" / "assignments.jsonl"
    choices_path = base_dir / f"selection_{VIEW}" / f"k={k}_{MODEL}" / "cluster_choices.json"
    
    assignments = load_assignments(assignments_path)
    choices = load_choices(choices_path)
    
    win_rate = compute_win_rate(ppl_edit, ppl_gen, assignments, choices)
    improvement = win_rate - always_gen_rate
    
    results.append({
        "k": k,
        "win_rate": win_rate,
        "improvement": improvement,
        "avg_cluster_size": len(common) / k,
    })
    
    print(f"k={k:>3}: win_rate={win_rate*100:.1f}%, improvement={improvement*100:+.1f}%, avg_size={len(common)/k:.1f}")

# Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

ks = [r["k"] for r in results]
win_rates = [r["win_rate"] * 100 for r in results]
improvements = [r["improvement"] * 100 for r in results]

# Plot 1: Win rate vs k
ax1.plot(ks, win_rates, 'b-o', linewidth=2, markersize=8, label='Routed')
ax1.axhline(y=always_gen_rate * 100, color='r', linestyle='--', label=f'always_gen ({always_gen_rate*100:.1f}%)')
ax1.axhline(y=100, color='g', linestyle=':', alpha=0.5, label='Oracle (100%)')
ax1.set_xlabel('k (number of clusters)', fontsize=12)
ax1.set_ylabel('Win Rate (%)', fontsize=12)
ax1.set_title('Win Rate vs Number of Clusters', fontsize=14)
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.set_xscale('log')

# Plot 2: Improvement vs k
ax2.plot(ks, improvements, 'g-o', linewidth=2, markersize=8)
ax2.axhline(y=0, color='r', linestyle='--', alpha=0.5)
ax2.set_xlabel('k (number of clusters)', fontsize=12)
ax2.set_ylabel('Improvement over always_gen (%)', fontsize=12)
ax2.set_title('Routing Improvement vs Number of Clusters', fontsize=14)
ax2.grid(True, alpha=0.3)
ax2.set_xscale('log')

plt.tight_layout()
plt.savefig('bug_task_model_selection/data/k_sweep_analysis.png', dpi=150, bbox_inches='tight')
print(f"\nPlot saved to bug_task_model_selection/data/k_sweep_analysis.png")
