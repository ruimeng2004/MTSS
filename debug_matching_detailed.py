#!/usr/bin/env python3
"""Debug matching with detailed output."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.output_parser import OutputParser

def normalize_indentation(text: str) -> str:
    """Normalize by stripping leading whitespace."""
    lines = text.split('\n')
    return '\n'.join(line.lstrip() for line in lines)

def main():
    """Debug Chart_13 matching."""
    
    # 1. Read source file
    source_file = Path("test_workspace/Chart_13_b/source/org/jfree/chart/block/BorderArrangement.java")
    with open(source_file, 'r') as f:
        source_content = f.read()
    
    # 2. Parse model output
    model_output_file = Path("ppl/result/20260105_132306/Chart_13/1/model_output.txt")
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    parser = OutputParser()
    parsed = parser.parse(
        model_output=model_output,
        bug_slug='Chart_13',
        attempt_num=1,
        modeling_type='edit'
    )
    
    sr = parsed.search_replaces[0]
    search_block = sr.search_block
    
    print("SEARCH block (first 3 lines):")
    for i, line in enumerate(search_block.split('\n')[:3]):
        print(f"  {i+1}: '{line}'")
    print()
    
    # Normalize
    search_normalized = normalize_indentation(search_block)
    source_normalized = normalize_indentation(source_content)
    
    print("Normalized SEARCH block (first 3 lines):")
    for i, line in enumerate(search_normalized.split('\n')[:3]):
        print(f"  {i+1}: '{line}'")
    print()
    
    # Try to find in source
    if search_normalized in source_normalized:
        print("✓ Found match in normalized source!")
        idx = source_normalized.find(search_normalized)
        # Count line number
        line_num = source_normalized[:idx].count('\n') + 1
        print(f"  At line: {line_num}")
    else:
        print("✗ Not found in normalized source")
        
        # Try first line
        first_line_norm = search_normalized.split('\n')[0]
        print(f"\nSearching for first normalized line: '{first_line_norm}'")
        
        if first_line_norm in source_normalized:
            print("✓ First line found!")
            
            # Find all occurrences
            count = source_normalized.count(first_line_norm)
            print(f"  Occurrences: {count}")
            
            # Check each occurrence
            source_lines_norm = source_normalized.split('\n')
            search_lines_norm = search_normalized.split('\n')
            
            for i, source_line in enumerate(source_lines_norm):
                if source_line == first_line_norm:
                    print(f"\n  Checking occurrence at line {i+1}:")
                    
                    # Try to match subsequent lines
                    matches = 0
                    for j in range(min(5, len(search_lines_norm))):
                        if i+j < len(source_lines_norm):
                            if search_lines_norm[j] == source_lines_norm[i+j]:
                                matches += 1
                            else:
                                print(f"    Line {j+1}: MISMATCH")
                                print(f"      Search: '{search_lines_norm[j][:60]}'")
                                print(f"      Source: '{source_lines_norm[i+j][:60]}'")
                                break
                    
                    if matches == min(5, len(search_lines_norm)):
                        print(f"    ✓ Matched first {matches} lines!")
        else:
            print("✗ First line not found")

if __name__ == "__main__":
    sys.exit(main())
