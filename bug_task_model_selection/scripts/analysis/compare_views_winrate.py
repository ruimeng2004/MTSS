#!/usr/bin/env python3
"""Compare routing effectiveness across different views using win rate."""

import json
from pathlib import Path
from collections import defaultdict

def load_ppl_data(ppl_path: Path) -> dict[str, float]:
    """Load PPL data as slug -> value mapping."""
    data = {}
    with open(ppl_path) as f:
        for line in f:
            obj = json.loads(line)
            slug = obj["slug"]
            data[slug] = obj["value"]
    return data

def load_cluster_choices(choices_path: Path) -> dict[int, str]:
    """Load cluster -> strategy choices."""
    with open(choices_path) as f:
        data = json.load(f)
        # Format: {"0": {"cluster_id": 0, "chosen": "gen", ...}, ...}
        return {int(k): v["chosen"] for k, v in data.items()}

def load_assignments(assignments_path: Path) -> dict[str, int]:
    """Load slug -> cluster_id mapping."""
    data = {}
    with open(assignments_path) as f:
        for line in f:
            obj = json.loads(line)
            # item_id format: "slug__view", we need slug
            item_id = obj["item_id"]
            # Split by "__" and take all but last part (in case slug contains "__")
            parts = item_id.rsplit("__", 1)
            slug = parts[0]
            data[slug] = obj["cluster_id"]
    return data

def compute_win_rate(
    ppl_edit: dict[str, float],
    ppl_gen: dict[str, float],
    assignments: dict[str, int],
    choices: dict[int, str],
) -> dict[str, dict]:
    """Compute win rate for each strategy."""
    results = {
        "routed": {"wins": 0, "total": 0},
        "always_edit": {"wins": 0, "total": 0},
        "always_gen": {"wins": 0, "total": 0},
        "oracle": {"wins": 0, "total": 0},
    }
    
    # Get common slugs
    common_slugs = set(ppl_edit.keys()) & set(ppl_gen.keys()) & set(assignments.keys())
    
    for slug in common_slugs:
        edit_ppl = ppl_edit[slug]
        gen_ppl = ppl_gen[slug]
        cluster_id = assignments[slug]
        
        # Determine best strategy for this slug (oracle)
        best = "edit" if edit_ppl <= gen_ppl else "gen"
        
        # Routed strategy
        routed_choice = choices.get(cluster_id, "gen")  # default to gen
        routed_ppl = edit_ppl if routed_choice == "edit" else gen_ppl
        
        # Count wins (lower PPL is better)
        # Win = routed/strategy PPL <= other strategy's PPL
        
        # Routed wins if it picks the better or equal option
        if routed_choice == best:
            results["routed"]["wins"] += 1
        results["routed"]["total"] += 1
        
        # always_edit wins if edit <= gen
        if edit_ppl <= gen_ppl:
            results["always_edit"]["wins"] += 1
        results["always_edit"]["total"] += 1
        
        # always_gen wins if gen <= edit
        if gen_ppl <= edit_ppl:
            results["always_gen"]["wins"] += 1
        results["always_gen"]["total"] += 1
        
        # oracle always wins
        results["oracle"]["wins"] += 1
        results["oracle"]["total"] += 1
    
    # Compute win rates
    for strategy in results:
        total = results[strategy]["total"]
        wins = results[strategy]["wins"]
        results[strategy]["win_rate"] = wins / total if total > 0 else 0
    
    return results

def run_for_model(model_name: str, base_dir: Path, ppl_dir: Path, views: list[str]) -> list[dict]:
    """Run win rate analysis for a specific model."""
    ppl_edit = load_ppl_data(ppl_dir / f"{model_name}_edit.jsonl")
    ppl_gen = load_ppl_data(ppl_dir / f"{model_name}_gen.jsonl")
    
    view_results = []
    
    for view in views:
        choices_path = base_dir / f"selection_{view}" / f"k=20_{model_name}" / "cluster_choices.json"
        assignments_path = base_dir / f"clusters_{view}" / "cuts" / "k=20" / "assignments.jsonl"
        
        if not choices_path.exists() or not assignments_path.exists():
            continue
        
        choices = load_cluster_choices(choices_path)
        assignments = load_assignments(assignments_path)
        
        results = compute_win_rate(ppl_edit, ppl_gen, assignments, choices)
        
        # Determine best baseline
        best_baseline = "gen" if results["always_gen"]["win_rate"] >= results["always_edit"]["win_rate"] else "edit"
        best_baseline_rate = max(results["always_gen"]["win_rate"], results["always_edit"]["win_rate"])
        
        view_results.append({
            "view": view,
            "routed_win_rate": results["routed"]["win_rate"],
            "always_edit_win_rate": results["always_edit"]["win_rate"],
            "always_gen_win_rate": results["always_gen"]["win_rate"],
            "best_baseline": best_baseline,
            "best_baseline_rate": best_baseline_rate,
            "improvement": results["routed"]["win_rate"] - best_baseline_rate,
        })
    
    return view_results


def main():
    views = ["report", "test", "error", "error_plus_test", "buggy_code", "buggy_code_obfuscated", "buggy_code_mixed"]
    base_dir = Path("bug_task_model_selection/data")
    ppl_dir = base_dir / "ppl"
    
    models = ["qwen3_coder", "qwen3_30b"]
    all_results = {}
    
    for model in models:
        print("=" * 80)
        print(f"Per-View Routing Effectiveness (Win Rate) - {model} edit vs gen")
        print("=" * 80)
        
        view_results = run_for_model(model, base_dir, ppl_dir, views)
        all_results[model] = view_results
        
        print(f"{'View':<25} {'Routed':>10} {'edit':>8} {'gen':>8} {'vs best':>10}")
        print("-" * 65)
        
        for r in sorted(view_results, key=lambda x: -x["routed_win_rate"]):
            print(f"{r['view']:<25} {r['routed_win_rate']*100:>9.1f}% {r['always_edit_win_rate']*100:>7.1f}% {r['always_gen_win_rate']*100:>7.1f}% {r['improvement']*100:>+9.1f}%")
        print()
    
    # Combined summary
    print("=" * 80)
    print("Combined Summary - Improvement over best baseline")
    print("=" * 80)
    print(f"{'View':<25} {'qwen3_coder':>15} {'qwen3_30b':>15}")
    print("-" * 60)
    
    for view in views:
        coder_r = next((r for r in all_results["qwen3_coder"] if r["view"] == view), None)
        b30_r = next((r for r in all_results["qwen3_30b"] if r["view"] == view), None)
        
        coder_imp = f"{coder_r['improvement']*100:+.1f}%" if coder_r else "N/A"
        b30_imp = f"{b30_r['improvement']*100:+.1f}%" if b30_r else "N/A"
        
        print(f"{view:<25} {coder_imp:>15} {b30_imp:>15}")

if __name__ == "__main__":
    main()
