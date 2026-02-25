#!/usr/bin/env python3
"""Create a fixed 50-50 baseline for routing evaluation.

This script generates a cluster_choices.json where every cluster is assigned:
- decision: "mixed"
- ratio: {"edit": 0.5, "gen": 0.5}
- confidence: 0.0

This serves as the "Fixed Allocation" baseline to compare dynamic routing strategies against.
"""

import json
import argparse
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser(description='Create fixed 50-50 baseline config')
    parser.add_argument('--assignments', type=str, required=True, help='Path to assignments.jsonl')
    parser.add_argument('--output-dir', type=str, required=True, help='Directory to save cluster_choices.json')
    args = parser.parse_args()

    # Load assignments to find all cluster IDs
    assignments_path = Path(args.assignments)
    output_dir = Path(args.output_dir)
    
    if not assignments_path.exists():
        print(f"Error: Assignments file not found: {assignments_path}")
        sys.exit(1)
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading clusters from {assignments_path}")
    cluster_ids = set()
    with open(assignments_path, 'r') as f:
        for line in f:
            item = json.loads(line)
            if 'cluster_id' in item:
                cluster_ids.add(int(item['cluster_id']))
                
    print(f"Found {len(cluster_ids)} unique clusters")
    
    # Generate fixed choices
    choices = {}
    for cluster_id in sorted(list(cluster_ids)):
        choices[str(cluster_id)] = {
            "cluster_id": cluster_id,
            "decision": "mixed",
            "ratio": {
                "edit": 0.5,
                "gen": 0.5
            },
            "confidence": 0.0,
            "metadata": {
                "metric": "fixed",
                "description": "Fixed 50-50 allocation baseline"
            }
        }
        
    output_file = output_dir / 'cluster_choices.json'
    with open(output_file, 'w') as f:
        json.dump(choices, f, indent=2)
        
    print(f"Saved baseline configuration to {output_file}")
    
if __name__ == '__main__':
    main()
