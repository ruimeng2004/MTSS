#!/usr/bin/env python3
"""Analyze why SEARCH blocks don't match source code."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for comparison."""
    lines = text.split('\n')
    normalized = []
    for line in lines:
        # Strip trailing whitespace but preserve leading indentation
        normalized.append(line.rstrip())
    return '\n'.join(normalized)

def main():
    """Analyze Chart_13 search block mismatch."""
    
    # 1. Checkout Chart_13
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    repo_path = env_manager.checkout_bug('Chart_13')
    print(f"Checked out to: {repo_path}")
    
    # 2. Find source file
    source_file = repo_path / 'source/org/jfree/chart/block/BorderArrangement.java'
    if not source_file.exists():
        print(f"Source file not found: {source_file}")
        return 1
    
    # 3. Read model output
    model_output_file = Path("ppl/result/20260105_132306/Chart_13/1/model_output.txt")
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    # 4. Parse to get SEARCH block
    parser = OutputParser()
    parsed = parser.parse(
        model_output=model_output,
        bug_slug='Chart_13',
        attempt_num=1,
        modeling_type='edit'
    )
    
    if not parsed.search_replaces:
        print("No search/replace blocks found!")
        return 1
    
    sr = parsed.search_replaces[0]
    search_block = sr.search_block
    
    print(f"\nMethod signature: {sr.method_signature}")
    print(f"\nSEARCH block length: {len(search_block)} chars")
    print(f"SEARCH block lines: {len(search_block.splitlines())}")
    
    # 5. Read source file
    with open(source_file, 'r') as f:
        source_content = f.read()
    
    # 6. Try different normalization strategies
    print("\n" + "=" * 70)
    print("TESTING DIFFERENT MATCHING STRATEGIES")
    print("=" * 70)
    
    # Strategy 1: Exact match
    print("\n1. EXACT MATCH:")
    if search_block in source_content:
        print("   ✓ Found exact match")
    else:
        print("   ✗ No exact match")
    
    # Strategy 2: Normalize newlines
    print("\n2. NORMALIZE NEWLINES:")
    search_normalized = search_block.replace('\r\n', '\n').replace('\r', '\n')
    source_normalized = source_content.replace('\r\n', '\n').replace('\r', '\n')
    if search_normalized in source_normalized:
        print("   ✓ Found match after normalizing newlines")
    else:
        print("   ✗ No match after normalizing newlines")
    
    # Strategy 3: Normalize trailing whitespace
    print("\n3. NORMALIZE TRAILING WHITESPACE:")
    search_ws_norm = normalize_whitespace(search_block)
    source_ws_norm = normalize_whitespace(source_content)
    if search_ws_norm in source_ws_norm:
        print("   ✓ Found match after normalizing whitespace")
    else:
        print("   ✗ No match after normalizing whitespace")
    
    # Strategy 4: Line-by-line fuzzy match
    print("\n4. LINE-BY-LINE ANALYSIS:")
    search_lines = search_block.split('\n')
    print(f"   Searching for {len(search_lines)} lines...")
    
    # Find first line
    first_line = search_lines[0].strip()
    if first_line in source_content:
        print(f"   ✓ First line found: '{first_line}'")
        
        # Try to match subsequent lines
        idx = source_content.find(first_line)
        source_from_first = source_content[idx:]
        source_lines_from_first = source_from_first.split('\n')
        
        print(f"\n   Comparing lines:")
        matches = 0
        for i, search_line in enumerate(search_lines[:10]):  # Check first 10 lines
            search_stripped = search_line.strip()
            if i < len(source_lines_from_first):
                source_stripped = source_lines_from_first[i].strip()
                match = search_stripped == source_stripped
                matches += 1 if match else 0
                status = "✓" if match else "✗"
                print(f"   Line {i+1}: {status}")
                if not match:
                    print(f"      Expected: '{search_stripped[:60]}'")
                    print(f"      Got:      '{source_stripped[:60]}'")
        
        print(f"\n   Matched {matches}/{min(10, len(search_lines))} lines")
    else:
        print(f"   ✗ First line not found: '{first_line}'")
    
    # Strategy 5: Check if this is the wrong version
    print("\n5. VERSION CHECK:")
    print("   The model may have been trained on a different version of the code.")
    print("   Let's check what the actual buggy code looks like...")
    
    # Find the method in source
    method_name = "arrangeFF"
    if method_name in source_content:
        idx = source_content.find(method_name)
        method_start = source_content.rfind('\n', max(0, idx-500), idx)
        method_end = source_content.find('\n    }\n', idx) + 6
        method_code = source_content[method_start:method_end]
        
        print(f"\n   Found method '{method_name}' in source:")
        print("   " + "=" * 66)
        # Show first 1000 chars of method
        print("   " + method_code[:1000].replace('\n', '\n   '))
        print("   " + "=" * 66)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
