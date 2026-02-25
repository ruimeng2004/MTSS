#!/usr/bin/env python3
"""Debug SEARCH block matching for Chart_11 and Chart_12."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer

def debug_matching(bug_slug: str, attempt_num: int = 1):
    """Debug SEARCH block matching."""
    
    print(f"\n{'='*70}")
    print(f"Debugging {bug_slug} - SEARCH block matching")
    print(f"{'='*70}\n")
    
    # 1. Load and parse
    model_output_file = Path(f"ppl/result/20260105_132306/{bug_slug}/{attempt_num}/model_output.txt")
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    parser = OutputParser()
    parsed = parser.parse(model_output, bug_slug, attempt_num, modeling_type='edit')
    
    sr = parsed.search_replaces[0]
    
    # 2. Checkout and find file
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    repo_path = env_manager.checkout_bug(bug_slug)
    
    normalizer = PatchNormalizer()
    found_file = normalizer.find_source_file_for_method(
        repo_path=repo_path,
        method_signature=sr.method_signature
    )
    
    if not found_file:
        print(f"✗ Could not find source file")
        return
    
    print(f"Found file: {found_file.name}")
    
    # 3. Read source file and locate method
    with open(found_file, 'r', encoding='utf-8') as f:
        source_content = f.read()
    
    method_node = normalizer._locate_method_with_treesitter(
        source_content=source_content,
        method_signature=sr.method_signature
    )
    
    if not method_node:
        print(f"✗ Could not locate method in source")
        return
    
    print(f"Method found at lines {method_node['start_line']}-{method_node['end_line']}")
    print(f"Method text length: {len(method_node['text'])} chars")
    
    # 4. Show method content
    print(f"\nMethod content:")
    print("---")
    print(method_node['text'][:1000])
    if len(method_node['text']) > 1000:
        print(f"... (truncated, total {len(method_node['text'])} chars)")
    print("---")
    
    # 5. Try to match SEARCH block
    print(f"\nSEARCH block to find:")
    print("---")
    print(sr.search_block)
    print("---")
    
    # 6. Call locate_search_block_with_method_context
    match_result = normalizer.locate_search_block_with_method_context(
        source_content=source_content,
        method_signature=sr.method_signature,
        search_text=sr.search_block
    )
    
    print(f"\nMatch result:")
    print(f"  Found: {match_result.found}")
    print(f"  Quality: {match_result.quality.value}")
    print(f"  Match count: {match_result.match_count}")
    
    if match_result.found:
        print(f"\n✓ Match found!")
        for i, match in enumerate(match_result.matches, 1):
            print(f"  Match {i}: lines {match['start_line']}-{match['end_line']}")
    else:
        print(f"\n✗ No match found")
        print(f"  Metadata: {match_result.metadata}")
        
        # Try to understand why
        print(f"\nDiagnostics:")
        
        # Normalize and compare
        search_normalized = normalizer._normalize_indentation(sr.search_block)
        method_normalized = normalizer._normalize_indentation(method_node['text'])
        
        print(f"  SEARCH block (normalized, first 200 chars):")
        print(f"    {repr(search_normalized[:200])}")
        
        print(f"\n  Method text (normalized, first 500 chars):")
        print(f"    {repr(method_normalized[:500])}")
        
        # Check if search text appears anywhere in method
        if search_normalized in method_normalized:
            print(f"\n  ✓ Normalized SEARCH block DOES appear in normalized method")
        else:
            print(f"\n  ✗ Normalized SEARCH block does NOT appear in normalized method")
            
            # Try line-by-line comparison
            search_lines = search_normalized.split('\n')
            method_lines = method_normalized.split('\n')
            
            print(f"\n  Line-by-line check:")
            print(f"    SEARCH has {len(search_lines)} lines")
            print(f"    Method has {len(method_lines)} lines")
            
            # Check if first search line appears
            if search_lines:
                first_line = search_lines[0].strip()
                if first_line:
                    matching_lines = [i for i, ml in enumerate(method_lines) if ml.strip() == first_line]
                    if matching_lines:
                        print(f"    First SEARCH line found at method lines: {matching_lines}")
                    else:
                        print(f"    First SEARCH line NOT found in method")
                        print(f"    First SEARCH line: {repr(first_line)}")

def main():
    """Debug both bugs."""
    
    for bug in ['Chart_11', 'Chart_12']:
        try:
            debug_matching(bug, attempt_num=1)
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
