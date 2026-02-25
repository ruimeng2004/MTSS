#!/usr/bin/env python3
"""
Extract all patches from Defects4J and prepare them for vectorization.
Creates a new 'patch' view in the bug_task_model_selection data directory.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List
from unidiff import PatchSet


# Defects4J projects
PROJECTS = [
    'Chart', 'Cli', 'Closure', 'Codec', 'Collections', 'Compress', 'Csv',
    'Gson', 'JacksonCore', 'JacksonDatabind', 'JacksonXml', 'Jsoup',
    'JxPath', 'Lang', 'Math', 'Mockito', 'Time'
]


def read_active_bugs(project_dir: Path) -> List[int]:
    """Read active bug IDs from active-bugs.csv"""
    bugs_file = project_dir / 'active-bugs.csv'
    if not bugs_file.exists():
        return []
    
    bug_ids = []
    with open(bugs_file, 'r') as f:
        # Skip header
        next(f)
        for line in f:
            parts = line.strip().split(',')
            if parts:
                try:
                    bug_ids.append(int(parts[0]))
                except ValueError:
                    continue
    return bug_ids


def read_patch(patch_file: Path) -> str:
    """Read and return patch content"""
    if not patch_file.exists():
        return ""
    
    with open(patch_file, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def reverse_patch(patch_content: str) -> str:
    """
    Reverse a patch using unidiff library for correct handling.
    
    D4J patches are designed to be applied TO fixed version TO GET buggy version:
      - Lines with '-' are from FIXED version (correct code to remove)
      - Lines with '+' are from BUGGY version (wrong code to add)
    
    For APR research, we want buggy → fixed direction, so we reverse:
      - Lines with '-' become BUGGY version (wrong code to remove)
      - Lines with '+' become FIXED version (correct code to add)
    
    Using unidiff ensures proper line ordering and format compliance.
    """
    if not patch_content:
        return ""
    
    try:
        # Parse the patch
        patchset = PatchSet(patch_content)
        
        # Build reversed patch manually
        reversed_lines = []
        
        for patched_file in patchset:
            # Swap source and target in file headers
            reversed_lines.append(f"diff --git a/{patched_file.path} b/{patched_file.path}")
            
            # Add index line if present
            if patched_file.source_file and patched_file.target_file:
                # Extract index info if available
                for line in patch_content.split('\n'):
                    if line.startswith('index '):
                        reversed_lines.append(line)
                        break
            
            # Swap --- and +++ headers
            reversed_lines.append(f"+++ b/{patched_file.path}")
            reversed_lines.append(f"--- a/{patched_file.path}")
            
            # Process each hunk
            for hunk in patched_file:
                # Swap source and target line numbers in hunk header
                # Original: @@ -source_start,source_length +target_start,target_length @@
                # Reversed: @@ -target_start,target_length +source_start,source_length @@
                reversed_lines.append(
                    f"@@ -{hunk.target_start},{hunk.target_length} "
                    f"+{hunk.source_start},{hunk.source_length} @@"
                )
                
                # Collect all lines first, then output in correct order
                # This ensures deletions come before additions
                context_and_changes = []
                
                for line in hunk:
                    if line.is_context:
                        # Output any pending changes before context
                        if context_and_changes:
                            output_changes(context_and_changes, reversed_lines)
                            context_and_changes = []
                        # Context lines stay as-is
                        reversed_lines.append(' ' + line.value.rstrip('\n\r'))
                    else:
                        # Collect changes (removed or added)
                        context_and_changes.append(line)
                
                # Output any remaining changes
                if context_and_changes:
                    output_changes(context_and_changes, reversed_lines)
        
        return '\n'.join(reversed_lines) + '\n'
    
    except Exception as e:
        # If unidiff fails, return empty (will be caught by caller)
        print(f"Warning: Failed to parse patch with unidiff: {e}")
        return ""


def output_changes(changes, output_lines):
    """
    Output changes in correct order: deletions before additions.
    
    Args:
        changes: List of Line objects from unidiff
        output_lines: List to append output to
    """
    # Separate removed and added lines
    removed = []
    added = []
    
    for line in changes:
        if line.is_removed:
            removed.append(line.value.rstrip('\n\r'))
        elif line.is_added:
            added.append(line.value.rstrip('\n\r'))
    
    # Reverse: original added become removed (output first)
    for line_content in added:
        output_lines.append('-' + line_content)
    
    # Reverse: original removed become added (output second)
    for line_content in removed:
        output_lines.append('+' + line_content)


def extract_patch_info(patch_content: str) -> Dict[str, str]:
    """Extract useful information from patch"""
    lines = patch_content.split('\n')
    
    # Find file path
    file_path = ""
    for line in lines:
        if line.startswith('diff --git'):
            parts = line.split()
            if len(parts) >= 4:
                file_path = parts[2].lstrip('a/')
                break
        elif line.startswith('---'):
            parts = line.split()
            if len(parts) >= 2:
                file_path = parts[1].lstrip('a/')
                break
    
    # Count changes
    additions = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))
    
    return {
        'file_path': file_path,
        'additions': additions,
        'deletions': deletions,
        'total_changes': additions + deletions
    }


def process_project(project: str, d4j_root: Path, output_dir: Path, 
                   reverse: bool = False) -> List[Dict]:
    """Process all bugs for a project"""
    project_dir = d4j_root / 'framework' / 'projects' / project
    patches_dir = project_dir / 'patches'
    
    if not patches_dir.exists():
        print(f"Warning: Patches directory not found for {project}")
        return []
    
    # Get active bugs
    bug_ids = read_active_bugs(project_dir)
    if not bug_ids:
        print(f"Warning: No active bugs found for {project}")
        return []
    
    items = []
    for bug_id in bug_ids:
        slug = f"{project}_{bug_id}"
        
        # Read source patch ONLY (not test patch)
        src_patch_file = patches_dir / f"{bug_id}.src.patch"
        src_patch = read_patch(src_patch_file)
        
        if not src_patch.strip():
            print(f"Warning: Empty patch for {slug}")
            continue
        
        # Reverse patch if requested
        if reverse:
            src_patch = reverse_patch(src_patch)
            if not src_patch:
                print(f"Warning: Failed to reverse patch for {slug}")
                continue
        
        # Extract patch info
        patch_info = extract_patch_info(src_patch)
        
        # Create item
        item = {
            'item_id': f"{slug}__patch",
            'slug': slug,
            'view': 'patch',
            'source_file': f"{bug_id}.src.patch",
            'text': src_patch,
            'metadata': {
                'project': project,
                'bug_id': bug_id,
                'file_path': patch_info['file_path'],
                'additions': patch_info['additions'],
                'deletions': patch_info['deletions'],
                'total_changes': patch_info['total_changes'],
                'reversed': reverse
            }
        }
        
        items.append(item)
        print(f"Processed {slug}: {patch_info['total_changes']} changes in {patch_info['file_path']}")
    
    return items


def main():
    parser = argparse.ArgumentParser(description='Extract patches from Defects4J')
    parser.add_argument('--d4j-root', type=str, 
                       default='/Users/eulerai/代码/lith/work/MTSS-main/d4j/defects4j',
                       help='Path to Defects4J root directory')
    parser.add_argument('--output-dir', type=str,
                       default='bug_task_model_selection/data/artifacts',
                       help='Output directory for patch data')
    parser.add_argument('--reverse', action='store_true',
                       help='Reverse patches to normal direction (buggy->fixed). '
                            'D4J patches are reversed by default (fixed->buggy).')
    parser.add_argument('--projects', nargs='+', default=PROJECTS,
                       help='Projects to process (default: all)')
    
    args = parser.parse_args()
    
    d4j_root = Path(args.d4j_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Output file
    output_file = output_dir / 'patches.jsonl'
    
    print(f"Extracting patches from Defects4J at: {d4j_root}")
    print(f"Output file: {output_file}")
    print(f"Reverse patches: {args.reverse}")
    print(f"Projects: {', '.join(args.projects)}")
    print()
    
    all_items = []
    stats = {
        'total_bugs': 0,
        'total_patches': 0,
        'projects': {}
    }
    
    for project in args.projects:
        print(f"\nProcessing {project}...")
        items = process_project(project, d4j_root, output_dir, args.reverse)
        all_items.extend(items)
        
        stats['projects'][project] = len(items)
        stats['total_patches'] += len(items)
        stats['total_bugs'] += len(items)
    
    # Write all items to JSONL
    print(f"\nWriting {len(all_items)} patches to {output_file}...")
    with open(output_file, 'w') as f:
        for item in all_items:
            f.write(json.dumps(item) + '\n')
    
    # Write statistics
    stats_file = output_dir / 'patches_stats.json'
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\nDone!")
    print(f"Total patches extracted: {stats['total_patches']}")
    print(f"Statistics saved to: {stats_file}")
    print(f"\nPer-project breakdown:")
    for project, count in sorted(stats['projects'].items()):
        print(f"  {project}: {count} patches")


if __name__ == '__main__':
    main()
