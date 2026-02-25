#!/usr/bin/env python3
"""Analyze why Chart_1, Chart_11, Chart_12 failed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer

def analyze_bug(bug_slug: str, attempt_num: int = 1):
    """Analyze a specific bug attempt."""
    
    print(f"\n{'='*70}")
    print(f"Analyzing {bug_slug} - Attempt {attempt_num}")
    print(f"{'='*70}\n")
    
    # 1. Check if model output exists
    model_output_file = Path(f"ppl/result/20260105_132306/{bug_slug}/{attempt_num}/model_output.txt")
    if not model_output_file.exists():
        print(f"✗ Model output not found: {model_output_file}")
        return
    
    print(f"✓ Model output found")
    
    # 2. Parse model output
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    parser = OutputParser()
    parsed = parser.parse(model_output, bug_slug, attempt_num, modeling_type='edit')
    
    if not parsed.parse_success:
        print(f"✗ Parse failed: {parsed.parse_error}")
        return
    
    print(f"✓ Parse successful")
    print(f"  Format: {parsed.modeling_type}")
    print(f"  SEARCH/REPLACE blocks: {len(parsed.search_replaces)}")
    
    if parsed.search_replaces:
        sr = parsed.search_replaces[0]
        print(f"  Method: {sr.method_signature}")
        print(f"  SEARCH block length: {len(sr.search_block)} chars")
        print(f"  REPLACE block length: {len(sr.replace_block)} chars")
    
    # 3. Checkout bug
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    try:
        repo_path = env_manager.checkout_bug(bug_slug)
        print(f"✓ Checked out to: {repo_path}")
    except Exception as e:
        print(f"✗ Checkout failed: {e}")
        return
    
    # 4. Find source file
    # Try to get from parsed patch or search
    if parsed.search_replaces:
        # Try to infer file from method signature
        method_sig = parsed.search_replaces[0].method_signature
        print(f"\n  Looking for source file containing: {method_sig[:50]}...")
    
    # Search for Java files
    java_files = list(repo_path.rglob("*.java"))
    print(f"  Found {len(java_files)} Java files in repository")
    
    # 5. Try to normalize
    if parsed.search_replaces and java_files:
        # Try first few Java files
        normalizer = PatchNormalizer()
        
        for java_file in java_files[:5]:
            try:
                normalized = normalizer.normalize(parsed, java_file)
                if normalized.is_valid:
                    print(f"\n✓ Normalization succeeded with: {java_file.name}")
                    print(f"  Match quality: {normalized.match_quality.value}")
                    print(f"  Diff length: {len(normalized.diff_content)} chars")
                    
                    # Show first few lines of diff
                    diff_lines = normalized.diff_content.split('\n')[:15]
                    print(f"\n  Diff preview:")
                    for line in diff_lines:
                        print(f"    {line}")
                    break
            except Exception as e:
                continue
        else:
            print(f"\n✗ Could not normalize patch with any of the first 5 Java files")
            print(f"  This suggests SEARCH block doesn't match source code")
    
    # 6. Check generated patch
    patch_file = Path(f"evaluation_output/batch_5_test_20260204_140011/patches/{bug_slug}_attempt_{attempt_num}.patch")
    if patch_file.exists():
        size = patch_file.stat().st_size
        print(f"\n✓ Generated patch exists: {size} bytes")
        
        if size == 0:
            print(f"  ✗ Patch is EMPTY - SEARCH block matching failed")
        else:
            print(f"  ✓ Patch has content")
            # Read and show patch
            with open(patch_file, 'r') as f:
                patch_content = f.read()
            print(f"\n  Patch content:")
            for line in patch_content.split('\n')[:20]:
                print(f"    {line}")
    else:
        print(f"\n✗ Generated patch not found")

def main():
    """Analyze all three failed bugs."""
    
    bugs = ['Chart_1', 'Chart_11', 'Chart_12']
    
    for bug in bugs:
        try:
            analyze_bug(bug, attempt_num=1)
        except Exception as e:
            print(f"\n✗ Error analyzing {bug}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print("Analysis Summary")
    print(f"{'='*70}\n")
    
    print("Chart_1: Check if patch logic is correct (seems to invert condition)")
    print("Chart_11: Check if SEARCH block matches source")
    print("Chart_12: Check if SEARCH block matches source")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
