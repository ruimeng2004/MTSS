#!/usr/bin/env python3
"""Sample bugs from each project type for evaluation.

This script samples N bugs from each project type to create
a balanced test set.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict


def get_bugs_by_project(input_dir: Path) -> Dict[str, List[str]]:
    """Group bugs by project type.
    
    Args:
        input_dir: Directory containing bug results.
        
    Returns:
        Dictionary mapping project name to list of bug slugs.
    """
    bugs_by_project = defaultdict(list)
    
    for bug_dir in sorted(input_dir.iterdir()):
        if bug_dir.is_dir():
            bug_slug = bug_dir.name
            project = bug_slug.rsplit('_', 1)[0]
            bugs_by_project[project].append(bug_slug)
    
    return dict(bugs_by_project)


def sample_bugs(
    bugs_by_project: Dict[str, List[str]],
    samples_per_project: int
) -> List[str]:
    """Sample N bugs from each project.
    
    Args:
        bugs_by_project: Dictionary mapping project to bug list.
        samples_per_project: Number of bugs to sample per project.
        
    Returns:
        List of sampled bug slugs.
    """
    sampled = []
    
    for project in sorted(bugs_by_project.keys()):
        bugs = bugs_by_project[project]
        # Take first N bugs from each project
        sample = bugs[:samples_per_project]
        sampled.extend(sample)
        print(f"{project}: {len(bugs)} total, sampled {len(sample)}")
    
    return sampled


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Sample bugs from each project type"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing bug results"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of bugs to sample per project"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="sampled_bugs.txt",
        help="Output file for sampled bug list"
    )
    
    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    
    # Get bugs by project
    bugs_by_project = get_bugs_by_project(input_dir)
    
    print(f"Found {len(bugs_by_project)} projects:")
    for project, bugs in sorted(bugs_by_project.items()):
        print(f"  {project}: {len(bugs)} bugs")
    
    print(f"\nSampling {args.samples} bugs per project...")
    sampled = sample_bugs(bugs_by_project, args.samples)
    
    print(f"\nTotal sampled: {len(sampled)} bugs")
    
    # Save to file
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        for bug in sampled:
            f.write(f"{bug}\n")
    
    print(f"Saved to: {output_path}")
    
    # Also save as JSON for easy loading
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w') as f:
        json.dump({
            'total': len(sampled),
            'samples_per_project': args.samples,
            'bugs': sampled
        }, f, indent=2)
    
    print(f"JSON saved to: {json_path}")


if __name__ == "__main__":
    main()
