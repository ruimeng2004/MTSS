#!/usr/bin/env python3
"""Test if indentation normalization fixes the matching issue."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer

def main():
    """Test Chart_13 with indentation normalization."""
    
    # 1. Checkout Chart_13
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    repo_path = env_manager.checkout_bug('Chart_13')
    print(f"Checked out to: {repo_path}\n")
    
    # 2. Find source file
    source_file = repo_path / 'source/org/jfree/chart/block/BorderArrangement.java'
    
    # 3. Parse model output
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
    
    print(f"Parsed {len(parsed.search_replaces)} SEARCH/REPLACE blocks\n")
    
    # 4. Try to normalize with new indentation-aware matching
    normalizer = PatchNormalizer(context_lines=3)
    
    try:
        normalized = normalizer.normalize(parsed, source_file)
        
        print("✓ NORMALIZATION SUCCEEDED!")
        print(f"  Match quality: {normalized.match_quality.value}")
        print(f"  Diff length: {len(normalized.diff_content)} chars")
        print(f"  Target files: {normalized.target_files}")
        
        if normalized.metadata:
            blocks = normalized.metadata.get('blocks', [])
            print(f"  Successful blocks: {len(blocks)}/{normalized.metadata.get('total_blocks', 0)}")
            
            for i, block in enumerate(blocks, 1):
                print(f"\n  Block {i}:")
                print(f"    Method: {block.get('method_signature', 'N/A')}")
                print(f"    Lines: {block.get('start_line')}-{block.get('end_line')}")
                print(f"    Quality: {block.get('match_quality', 'N/A')}")
        
        # Show first 500 chars of diff
        print("\n  Diff preview:")
        print("  " + "=" * 66)
        for line in normalized.diff_content.split('\n')[:20]:
            print(f"  {line}")
        print("  " + "=" * 66)
        
        return 0
        
    except Exception as e:
        print(f"✗ NORMALIZATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
