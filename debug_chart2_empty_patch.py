#!/usr/bin/env python3
"""Debug why Chart_2 attempt 3 produces an empty patch."""

import sys
from pathlib import Path

# Add evaluation module to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.environment_manager import EnvironmentManager

def main():
    """Debug Chart_2 empty patch issue."""
    
    # Paths
    model_output_file = Path("ppl/result/20260105_132306/Chart_2/3/model_output.txt")
    result_json_file = Path("ppl/result/20260105_132306/Chart_2/3/result.json")
    
    # Read model output
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    print("=" * 80)
    print("CHART_2 ATTEMPT 3 DEBUG")
    print("=" * 80)
    
    # Parse the output
    parser = OutputParser()
    parsed = parser.parse(
        model_output=model_output,
        bug_slug="Chart_2",
        attempt_num=3,
        modeling_type="edit"
    )
    
    print(f"\nParse Success: {parsed.parse_success}")
    print(f"Modeling Type: {parsed.modeling_type}")
    print(f"Number of SEARCH/REPLACE blocks: {len(parsed.search_replaces)}")
    
    if not parsed.parse_success:
        print(f"Parse Error: {parsed.parse_error}")
        return
    
    # Print each search/replace block
    for i, sr in enumerate(parsed.search_replaces):
        print(f"\n--- Block {i+1} ---")
        print(f"Method: {sr.method_signature}")
        print(f"Search lines: {len(sr.search_block.split(chr(10)))}")
        print(f"Replace lines: {len(sr.replace_block.split(chr(10)))}")
        print(f"Search block preview (first 200 chars):")
        print(sr.search_block[:200])
    
    # Now try to normalize
    print("\n" + "=" * 80)
    print("NORMALIZATION ATTEMPT")
    print("=" * 80)
    
    # First checkout Chart_2
    env_manager = EnvironmentManager(
        d4j_path=Path("/Users/mengrui/Desktop/D4J/defects4j"),
        workspace_dir=Path("./test_workspace")
    )
    
    print("\nChecking out Chart_2...")
    repo_path = env_manager.checkout_bug("Chart_2")
    
    if not repo_path or not repo_path.exists():
        print(f"Checkout failed")
        return
    
    print(f"Checked out to: {repo_path}")
    
    # Try to normalize
    normalizer = PatchNormalizer(context_lines=3)
    
    try:
        normalized = normalizer.normalize(
            parsed_patch=parsed,
            source_file=repo_path
        )
        
        print(f"\nNormalization Success!")
        print(f"Diff content length: {len(normalized.diff_content)}")
        print(f"Target files: {normalized.target_files}")
        print(f"Match quality: {normalized.match_quality}")
        
        if normalized.diff_content:
            print(f"\nDiff preview (first 500 chars):")
            print(normalized.diff_content[:500])
        else:
            print("\n!!! DIFF CONTENT IS EMPTY !!!")
            print(f"Metadata: {normalized.metadata}")
            
    except Exception as e:
        print(f"\nNormalization failed with exception:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
