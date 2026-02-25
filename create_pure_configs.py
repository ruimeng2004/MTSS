import json
import os
from pathlib import Path

# Paths
base_results_dir = Path("/home/base/mengrui/MTSS/btms_budget_experiments/qwencoder_experiments/results")
pure_edit_dir = base_results_dir / "pure-edit"
pure_gen_dir = base_results_dir / "pure-gen"

pure_edit_dir.mkdir(parents=True, exist_ok=True)
pure_gen_dir.mkdir(parents=True, exist_ok=True)

# Generate Pure Edit (100 clusters)
pure_edit_choices = {}
for i in range(100):
    pure_edit_choices[str(i)] = {
        "cluster_id": i,
        "decision": "edit",
        "ratio": {"edit": 1.0, "gen": 0.0},
        "confidence": 1.0,
        "metadata": {"metric": "manual", "description": "Pure Edit"}
    }
    
with open(pure_edit_dir / "cluster_choices.json", 'w') as f:
    json.dump(pure_edit_choices, f, indent=2)

print(f"Created: {pure_edit_dir / 'cluster_choices.json'}")

# Generate Pure Gen (100 clusters)
pure_gen_choices = {}
for i in range(100):
    pure_gen_choices[str(i)] = {
        "cluster_id": i,
        "decision": "gen",
        "ratio": {"edit": 0.0, "gen": 1.0},
        "confidence": 1.0,
        "metadata": {"metric": "manual", "description": "Pure Gen"}
    }
    
with open(pure_gen_dir / "cluster_choices.json", 'w') as f:
    json.dump(pure_gen_choices, f, indent=2)

print(f"Created: {pure_gen_dir / 'cluster_choices.json'}")
