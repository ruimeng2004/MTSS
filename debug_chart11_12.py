#!/usr/bin/env python3
"""Debug why Chart_11 and Chart_12 patches are empty."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer

def debug_bug(bug_slug: str, attempt_num: int = 1):
    """Debug a specific bug attempt."""
    
    print(f"\n{'='*70}")
    print(f"Debugging {bug_slug} - Attempt {attempt_num}")
    print(f"{'='*70}\n")
    
    # 1. Load model output
    model_output_file = Path(f"ppl/result/20260105_132306/{bug_slug}/{attempt_num}/model_output.txt")
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    # 2. Parse
    parser = OutputParser()
    parsed = parser.parse(model_output, bug_slug, attempt_num, modeling_type='edit')
    
    print(f"Parse successful: {parsed.parse_success}")
    if not parsed.parse_success:
        print(f"Parse error: {parsed.parse_error}")
        return
    
    print(f"SEARCH/REPLACE blocks: {len(parsed.search_replaces)}")
    
    if not parsed.search_replaces:
        print("No SEARCH/REPLACE blocks found!")
        return
    
    sr = parsed.search_replaces[0]
    print(f"\nMethod signature: {sr.method_signature}")
    print(f"SEARCH block ({len(sr.search_block)} chars):")
    print("---")
    print(sr.search_block)
    print("---")
    
    # 3. Checkout bug
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    repo_path = env_manager.checkout_bug(bug_slug)
    print(f"\nChecked out to: {repo_path}")
    
    # 4. Try to normalize with repo_path (should trigger tree-sitter search)
    normalizer = PatchNormalizer()
    
    print(f"\nCalling normalizer.normalize() with repo_path as source_file...")
    print(f"This should trigger tree-sitter search for the method")
    
    try:
        normalized = normalizer.normalize(parsed, repo_path)
        
        print(f"\n✓ Normalization succeeded!")
        print(f"  Match quality: {normalized.match_quality.value}")
        print(f"  Diff length: {len(normalized.diff_content)} chars")
        print(f"  Is valid: {normalized.is_valid}")
        
        if normalized.is_valid:
            print(f"\nDiff content (first 500 chars):")
            print("---")
            print(normalized.diff_content[:500])
            print("---")
        else:
            print(f"\n✗ Normalized patch is INVALID (empty diff)")
            
    except FileNotFoundError as e:
        print(f"\n✗ FileNotFoundError: {e}")
        print(f"  This means tree-sitter search failed to find the method")
        
    except Exception as e:
        print(f"\n✗ Normalization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Manual tree-sitter search
    print(f"\n{'='*70}")
    print("Manual tree-sitter search test")
    print(f"{'='*70}\n")
    
    method_sig = sr.method_signature
    print(f"Searching for method: {method_sig}")
    
    found_file = normalizer.find_source_file_for_method(
        repo_path=repo_path,
        method_signature=method_sig
    )
    
    if found_file:
        print(f"✓ Found file: {found_file}")
        print(f"  Relative to repo: {found_file.relative_to(repo_path)}")
        
        # Try to normalize with the found file
        print(f"\nTrying normalization with found file...")
        try:
            normalized2 = normalizer.normalize(parsed, found_file)
            print(f"✓ Normalization succeeded!")
            print(f"  Diff length: {len(normalized2.diff_content)} chars")
            print(f"  Is valid: {normalized2.is_valid}")
        except Exception as e:
            print(f"✗ Normalization failed: {e}")
    else:
        print(f"✗ Method not found in any Java file")
        
        # List some Java files to see what's available
        java_files = list(repo_path.rglob("*.java"))
        print(f"\nTotal Java files in repo: {len(java_files)}")
        print(f"First 10 Java files:")
        for jf in java_files[:10]:
            print(f"  - {jf.relative_to(repo_path)}")

def main():
    """Debug both bugs."""
    
    for bug in ['Chart_11', 'Chart_12']:
        try:
            debug_bug(bug, attempt_num=1)
        except Exception as e:
            print(f"\n✗ Error debugging {bug}: {e}")
            import traceback
            traceback.print_exc()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
