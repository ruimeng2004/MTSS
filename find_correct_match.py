#!/usr/bin/env python3
"""Find the correct location of SEARCH block in source."""

import sys
from pathlib import Path

def main():
    """Find Chart_13 search block location."""
    
    # Read source file
    source_file = Path("test_workspace/Chart_13_b/source/org/jfree/chart/block/BorderArrangement.java")
    with open(source_file, 'r') as f:
        source_content = f.read()
    
    # The SEARCH block from model
    search_block = """        h[1] = size.height;
        h[2] = constraint.getHeight() - h[1] - h[0];
        if (this.leftBlock != null) {
            RectangleConstraint c3 = new RectangleConstraint(0.0,
                    new Range(0.0, constraint.getWidth()),
                    LengthConstraintType.RANGE, h[2], null,
                    LengthConstraintType.FIXED);
            Size2D size = this.leftBlock.arrange(g2, c3);
            w[2] = size.width;
        }
        h[3] = h[2];
        if (this.rightBlock != null) {
            RectangleConstraint c4 = new RectangleConstraint(0.0,
                    new Range(0.0, constraint.getWidth() - w[2]),
                    LengthConstraintType.RANGE, h[2], null,
                    LengthConstraintType.FIXED);
            Size2D size = this.rightBlock.arrange(g2, c4);
            w[3] = size.width;
        }
        h[4] = h[2];
        w[4] = constraint.getWidth() - w[3] - w[2];"""
    
    print("SEARCH block:")
    print("=" * 70)
    print(search_block[:300])
    print("=" * 70)
    print()
    
    # Try exact match
    if search_block in source_content:
        print("✓ EXACT MATCH FOUND!")
        idx = source_content.find(search_block)
        # Count line number
        line_num = source_content[:idx].count('\n') + 1
        print(f"  Location: Line {line_num}")
        print(f"  Character index: {idx}")
        return 0
    else:
        print("✗ Exact match not found")
        print()
        
        # Try to find why it doesn't match
        search_lines = search_block.split('\n')
        source_lines = source_content.split('\n')
        
        print(f"Searching for sequence of {len(search_lines)} lines...")
        print()
        
        # Find first line
        first_line = search_lines[0]
        print(f"First line: '{first_line}'")
        
        # Find all occurrences of first line
        occurrences = []
        for i, line in enumerate(source_lines):
            if line == first_line:
                occurrences.append(i)
        
        print(f"Found {len(occurrences)} occurrence(s) of first line at lines: {[i+1 for i in occurrences]}")
        print()
        
        # Check each occurrence
        for occ_idx in occurrences:
            print(f"Checking occurrence at line {occ_idx + 1}:")
            matches = 0
            mismatches = []
            
            for j, search_line in enumerate(search_lines):
                if occ_idx + j < len(source_lines):
                    source_line = source_lines[occ_idx + j]
                    if search_line == source_line:
                        matches += 1
                    else:
                        mismatches.append({
                            'line_num': occ_idx + j + 1,
                            'search': search_line,
                            'source': source_line
                        })
                else:
                    mismatches.append({
                        'line_num': occ_idx + j + 1,
                        'search': search_line,
                        'source': '<EOF>'
                    })
            
            print(f"  Matched: {matches}/{len(search_lines)} lines")
            
            if mismatches:
                print(f"  Mismatches: {len(mismatches)}")
                for mm in mismatches[:3]:  # Show first 3 mismatches
                    print(f"    Line {mm['line_num']}:")
                    print(f"      Search: '{mm['search'][:60]}'")
                    print(f"      Source: '{mm['source'][:60]}'")
            print()
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
