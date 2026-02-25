#!/usr/bin/env python3
"""Check why Chart_13 search block is not found."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser

def main():
    """Check Chart_13 search block."""
    
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
    
    print(f"Source file: {source_file}")
    
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
    print(f"\nMethod signature: {sr.method_signature}")
    print(f"\nSEARCH block ({len(sr.search_block)} chars):")
    print("=" * 70)
    print(sr.search_block[:500])
    print("=" * 70)
    
    # 5. Read source file
    with open(source_file, 'r') as f:
        source_content = f.read()
    
    # 6. Check if SEARCH block exists in source
    if sr.search_block in source_content:
        print("\n✓ SEARCH block found in source!")
    else:
        print("\n✗ SEARCH block NOT found in source!")
        
        # Try to find similar content
        search_lines = sr.search_block.split('\n')
        first_line = search_lines[0].strip()
        print(f"\nSearching for first line: '{first_line}'")
        
        if first_line in source_content:
            print("✓ First line found in source")
            # Find context
            idx = source_content.find(first_line)
            context_start = max(0, idx - 200)
            context_end = min(len(source_content), idx + 500)
            print("\nContext around first line:")
            print("=" * 70)
            print(source_content[context_start:context_end])
            print("=" * 70)
        else:
            print("✗ First line NOT found in source")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
