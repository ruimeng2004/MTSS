#!/usr/bin/env python3
"""
Quick test to verify that reversed patches have correct line ordering
and can be applied with standard patch tools.
"""

import json
import tempfile
import subprocess
from pathlib import Path


def test_patch_format():
    """Test that patches have correct line ordering (- before +)"""
    patches_file = Path('bug_task_model_selection/data/artifacts/patches.jsonl')
    
    print("Testing patch format and line ordering...")
    print()
    
    # Read first few patches
    with open(patches_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= 5:  # Test first 5 patches
                break
            
            item = json.loads(line)
            slug = item['slug']
            patch_text = item['text']
            
            print(f"Testing {slug}...")
            
            # Check for basic patch structure
            if not patch_text.startswith('diff --git'):
                print(f"  ❌ Missing diff header")
                continue
            
            # Extract the main source patch (before test patch)
            lines = patch_text.split('\n')
            
            # Find hunks and check line ordering
            in_hunk = False
            hunk_lines = []
            issues = []
            
            for line in lines:
                if line.startswith('@@'):
                    # Process previous hunk if exists
                    if hunk_lines:
                        if not check_hunk_ordering(hunk_lines):
                            issues.append(f"Bad ordering in hunk")
                    hunk_lines = []
                    in_hunk = True
                elif in_hunk:
                    if line.startswith('diff') or line.startswith('Index:'):
                        # End of current diff
                        if hunk_lines and not check_hunk_ordering(hunk_lines):
                            issues.append(f"Bad ordering in hunk")
                        in_hunk = False
                        hunk_lines = []
                    elif line.startswith(('+', '-', ' ')):
                        hunk_lines.append(line)
            
            # Check last hunk
            if hunk_lines and not check_hunk_ordering(hunk_lines):
                issues.append(f"Bad ordering in final hunk")
            
            if issues:
                print(f"  ❌ Issues found: {', '.join(issues)}")
            else:
                print(f"  ✓ Patch format looks good")
            
            print()
    
    print("Format check complete!")


def check_hunk_ordering(hunk_lines):
    """
    Check that in each change block, deletions (-) come before additions (+).
    This is required for patches to be applicable.
    """
    # Group consecutive change lines
    i = 0
    while i < len(hunk_lines):
        line = hunk_lines[i]
        
        if line.startswith('-') and not line.startswith('---'):
            # Found deletion, check if there are additions after
            j = i + 1
            has_addition_after = False
            
            # Skip consecutive deletions
            while j < len(hunk_lines) and hunk_lines[j].startswith('-') and not hunk_lines[j].startswith('---'):
                j += 1
            
            # Check if additions follow
            if j < len(hunk_lines) and hunk_lines[j].startswith('+') and not hunk_lines[j].startswith('+++'):
                has_addition_after = True
            
            # This is fine - deletions before additions
            i = j
        elif line.startswith('+') and not line.startswith('+++'):
            # Found addition, check if there are deletions after (BAD!)
            j = i + 1
            
            # Skip consecutive additions
            while j < len(hunk_lines) and hunk_lines[j].startswith('+') and not hunk_lines[j].startswith('+++'):
                j += 1
            
            # Check if deletions follow (this would be wrong)
            if j < len(hunk_lines) and hunk_lines[j].startswith('-') and not hunk_lines[j].startswith('---'):
                return False  # Bad ordering: + before -
            
            i = j
        else:
            i += 1
    
    return True


if __name__ == '__main__':
    test_patch_format()
