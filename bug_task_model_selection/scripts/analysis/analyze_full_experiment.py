#!/usr/bin/env python3
"""Analyze full experiment results and generate plots."""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

VIEWS = ["report", "test", "error", "error_plus_test", "buggy_code", "buggy_code_obfuscated", "buggy_code_mixed"]
MODELS = ["qwen3_coder", "qwen3_30b"]
KS = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200]

base_dir = Path("bug_task_model_selection/data")

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

# Compute baselines for each model
baselines = {}
for model in MODELS:
    ppl_edit = load_ppl(base_dir / "ppl" / f"{model}_edit.jsonl")
    ppl_gen = load_ppl(base_dir / "ppl" / f"{model}_gen.jsonl")
    common = set(ppl_edit.keys()) & set(ppl_gen.keys())
    
    gen_wins = sum(1 for s in common if ppl_gen[s] <= ppl_edit[s])
    edit_wins = sum(1 for s in common if ppl_edit[s] <= ppl_gen[s])
    
    baselines[model] = {
        "always_gen": gen_wins / len(common),
        "always_edit": edit_wins / len(common),
        "best": max(gen_wins, edit_wins) / len(common),
        "best_name": "gen" if gen_wins >= edit_wins else "edit",
    }

print("Baselines:")
for model, b in baselines.items():
    print(f"  {model}: always_gen={b['always_gen']*100:.1f}%, always_edit={b['always_edit']*100:.1f}%, best={b['best_name']} ({b['best']*100:.1f}%)")
print()

# Collect all results
results = []
for view in VIEWS:
    for model in MODELS:
        ppl_edit = load_ppl(base_dir / "ppl" / f"{model}_edit.jsonl")
        ppl_gen = load_ppl(base_dir / "ppl" / f"{model}_gen.jsonl")
        
        for k in KS:
            assignments_path = base_dir / f"clusters_{view}" / "cuts" / f"k={k}" / "assignments.jsonl"
            choices_path = base_dir / f"selection_{view}" / f"k={k}_{model}" / "cluster_choices.json"
            
            if not choices_path.exists():
                continue
            
            assignments = load_assignments(assignments_path)
            choices = load_choices(choices_path)
            win_rate = compute_win_rate(ppl_edit, ppl_gen, assignments, choices)
            
            results.append({
                "view": view,
                "model": model,
                "k": k,
                "win_rate": win_rate,
                "improvement": win_rate - baselines[model]["best"],
            })

# Print summary table
print("=" * 100)
print("Win Rate Summary (improvement over best baseline)")
print("=" * 100)

for model in MODELS:
    print(f"\n{model} (baseline: {baselines[model]['best_name']} = {baselines[model]['best']*100:.1f}%)")
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
            r = next((x for x in results if x["view"] == view and x["model"] == model and x["k"] == k), None)
            if r:
                row += f" {r['improvement']*100:>+5.1f}%"
            else:
                row += "    N/A"
        print(row)

# Find best combinations
print("\n" + "=" * 100)
print("Top 10 Best Combinations (by improvement)")
print("=" * 100)
sorted_results = sorted(results, key=lambda x: -x["improvement"])
for i, r in enumerate(sorted_results[:10], 1):
    print(f"{i:>2}. {r['view']:<25} {r['model']:<15} k={r['k']:<3} win_rate={r['win_rate']*100:.1f}% improvement={r['improvement']*100:+.1f}%")

# Generate plots
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

colors = plt.cm.tab10(np.linspace(0, 1, len(VIEWS)))
view_colors = {v: colors[i] for i, v in enumerate(VIEWS)}

for idx, model in enumerate(MODELS):
    ax = axes[0, idx]
    baseline = baselines[model]["best"]
    
    for view in VIEWS:
        view_results = [r for r in results if r["view"] == view and r["model"] == model]
        if not view_results:
            continue
        view_results.sort(key=lambda x: x["k"])
        ks = [r["k"] for r in view_results]
        win_rates = [r["win_rate"] * 100 for r in view_results]
        ax.plot(ks, win_rates, '-o', color=view_colors[view], label=view, markersize=4)
    
    ax.axhline(y=baseline * 100, color='red', linestyle='--', label=f'best baseline ({baseline*100:.1f}%)')
    ax.set_xlabel('k (number of clusters)')
    ax.set_ylabel('Win Rate (%)')
    ax.set_title(f'{model}')
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='lower right')

# Improvement plots
for idx, model in enumerate(MODELS):
    ax = axes[1, idx]
    
    for view in VIEWS:
        view_results = [r for r in results if r["view"] == view and r["model"] == model]
        if not view_results:
            continue
        view_results.sort(key=lambda x: x["k"])
        ks = [r["k"] for r in view_results]
        improvements = [r["improvement"] * 100 for r in view_results]
        ax.plot(ks, improvements, '-o', color=view_colors[view], label=view, markersize=4)
    
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('k (number of clusters)')
    ax.set_ylabel('Improvement over baseline (%)')
    ax.set_title(f'{model} - Improvement')
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='lower right')

plt.tight_layout()
plt.savefig('bug_task_model_selection/data/full_experiment_analysis.png', dpi=150, bbox_inches='tight')
print(f"\nPlot saved to bug_task_model_selection/data/full_experiment_analysis.png")
