"""Analyze per-case strategy preferences across models and task modeling."""
from __future__ import annotations

import json
import csv
from pathlib import Path
from collections import Counter


def load_ppl(path: Path) -> dict[str, float]:
    out = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line.strip())
            out[obj["slug"]] = obj["value"]
    return out


def analyze():
    ppl_dir = Path("bug_task_model_selection/data/ppl")
    
    # Load all 4 strategies
    data = {
        "qwen3_30b_edit": load_ppl(ppl_dir / "qwen3_30b_edit.jsonl"),
        "qwen3_30b_gen": load_ppl(ppl_dir / "qwen3_30b_gen.jsonl"),
        "qwen3_coder_edit": load_ppl(ppl_dir / "qwen3_coder_edit.jsonl"),
        "qwen3_coder_gen": load_ppl(ppl_dir / "qwen3_coder_gen.jsonl"),
    }
    
    slugs = sorted(data["qwen3_30b_edit"].keys())
    
    # Output CSV
    out_dir = Path("bug_task_model_selection/data/analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    rows = []
    
    for slug in slugs:
        v_30b_edit = data["qwen3_30b_edit"].get(slug)
        v_30b_gen = data["qwen3_30b_gen"].get(slug)
        v_coder_edit = data["qwen3_coder_edit"].get(slug)
        v_coder_gen = data["qwen3_coder_gen"].get(slug)
        
        if None in [v_30b_edit, v_30b_gen, v_coder_edit, v_coder_gen]:
            continue
        
        # Best overall (4选1)
        all_scores = {
            "qwen3_30b_edit": v_30b_edit,
            "qwen3_30b_gen": v_30b_gen,
            "qwen3_coder_edit": v_coder_edit,
            "qwen3_coder_gen": v_coder_gen,
        }
        best_overall = min(all_scores, key=all_scores.get)
        
        # Best within qwen3_30b (2选1)
        best_30b = "edit" if v_30b_edit < v_30b_gen else "gen"
        
        # Best within qwen3_coder (2选1)
        best_coder = "edit" if v_coder_edit < v_coder_gen else "gen"
        
        # Do models agree on task modeling preference?
        models_agree = best_30b == best_coder
        
        rows.append({
            "slug": slug,
            "qwen3_30b_edit": v_30b_edit,
            "qwen3_30b_gen": v_30b_gen,
            "qwen3_coder_edit": v_coder_edit,
            "qwen3_coder_gen": v_coder_gen,
            "best_overall": best_overall,
            "best_30b": best_30b,
            "best_coder": best_coder,
            "models_agree": models_agree,
        })
    
    # Write CSV
    csv_path = out_dir / "case_preferences.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Written {csv_path} with {len(rows)} cases\n")
    
    # Statistics
    print("=" * 60)
    print("STATISTICS")
    print("=" * 60)
    
    # 1. Best overall distribution (4选1)
    best_overall_counts = Counter(r["best_overall"] for r in rows)
    print("\n[1] Best Overall Strategy (4选1):")
    for k, v in sorted(best_overall_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v} ({v/len(rows)*100:.1f}%)")
    
    # 2. Best within each model (2选1)
    best_30b_counts = Counter(r["best_30b"] for r in rows)
    best_coder_counts = Counter(r["best_coder"] for r in rows)
    
    print("\n[2] Best Task Modeling within Model (2选1):")
    print("  qwen3_30b:")
    for k, v in sorted(best_30b_counts.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v} ({v/len(rows)*100:.1f}%)")
    print("  qwen3_coder:")
    for k, v in sorted(best_coder_counts.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v} ({v/len(rows)*100:.1f}%)")
    
    # 3. Model agreement
    agree_count = sum(1 for r in rows if r["models_agree"])
    print(f"\n[3] Models Agree on Task Modeling Preference:")
    print(f"  Agree: {agree_count} ({agree_count/len(rows)*100:.1f}%)")
    print(f"  Disagree: {len(rows)-agree_count} ({(len(rows)-agree_count)/len(rows)*100:.1f}%)")
    
    # 4. Cross analysis: when models disagree, what's the pattern?
    disagree_rows = [r for r in rows if not r["models_agree"]]
    if disagree_rows:
        print(f"\n[4] Disagreement Pattern (n={len(disagree_rows)}):")
        pattern_counts = Counter((r["best_30b"], r["best_coder"]) for r in disagree_rows)
        for (p30b, pcoder), cnt in sorted(pattern_counts.items(), key=lambda x: -x[1]):
            print(f"  30b prefers {p30b}, coder prefers {pcoder}: {cnt}")
    
    # 5. Best model distribution
    print("\n[5] Best Model (ignoring task modeling):")
    best_model_counts = Counter(
        "qwen3_30b" if r["best_overall"].startswith("qwen3_30b") else "qwen3_coder"
        for r in rows
    )
    for k, v in sorted(best_model_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v} ({v/len(rows)*100:.1f}%)")
    
    # 6. Best task modeling distribution (ignoring model)
    print("\n[6] Best Task Modeling (ignoring model):")
    best_task_counts = Counter(
        "edit" if "edit" in r["best_overall"] else "gen"
        for r in rows
    )
    for k, v in sorted(best_task_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v} ({v/len(rows)*100:.1f}%)")


if __name__ == "__main__":
    analyze()
