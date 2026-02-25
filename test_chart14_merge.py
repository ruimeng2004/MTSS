#!/usr/bin/env python3
"""Test Chart_14 to verify multiple SEARCH/REPLACE blocks merge correctly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.patch_applicator import PatchApplicator
from evaluation.core.test_executor import TestExecutor

def main():
    """Test Chart_14 with multiple SEARCH/REPLACE blocks."""
    
    print("=" * 70)
    print("Testing Chart_14 - Multiple SEARCH/REPLACE Blocks Merge")
    print("=" * 70)
    
    bug_slug = "Chart_14"
    attempt_num = 1
    
    # 1. Load model output
    model_output_file = Path(f"ppl/result/20260105_132306/{bug_slug}/{attempt_num}/model_output.txt")
    
    if not model_output_file.exists():
        print(f"✗ Model output not found: {model_output_file}")
        return 1
    
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    # 2. Parse
    parser = OutputParser()
    parsed = parser.parse(model_output, bug_slug, attempt_num, modeling_type='edit')
    
    if not parsed.parse_success:
        print(f"✗ Parse failed: {parsed.parse_error}")
        return 1
    
    print(f"✓ Parse successful")
    print(f"  SEARCH/REPLACE blocks: {len(parsed.search_replaces)}")
    
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
        return 1
    
    # 4. Find source file
    normalizer = PatchNormalizer()
    
    # Get method signature from first block
    method_sig = parsed.search_replaces[0].method_signature
    found_file = normalizer.find_source_file_for_method(
        repo_path=repo_path,
        method_signature=method_sig
    )
    
    if not found_file:
        print(f"✗ Could not find source file for method: {method_sig}")
        return 1
    
    print(f"✓ Found source file: {found_file.name}")
    
    # 5. Normalize patch
    try:
        normalized = normalizer.normalize(parsed, found_file)
        print(f"✓ Normalization successful")
        print(f"  Match quality: {normalized.match_quality.value}")
        print(f"  Diff length: {len(normalized.diff_content)} chars")
        print(f"  Is valid: {normalized.is_valid}")
        
        if not normalized.is_valid:
            print(f"✗ Normalized patch is invalid (empty)")
            return 1
        
        # Show diff
        print(f"\nGenerated diff:")
        print("-" * 70)
        print(normalized.diff_content[:1000])
        if len(normalized.diff_content) > 1000:
            print(f"... (truncated, total {len(normalized.diff_content)} chars)")
        print("-" * 70)
        
        # Count how many patch headers (should be only 1)
        header_count = normalized.diff_content.count('--- a/')
        print(f"\nPatch headers count: {header_count}")
        if header_count > 1:
            print(f"✗ WARNING: Multiple patch headers detected!")
            print(f"  This means patches were not properly merged")
        else:
            print(f"✓ Single unified patch (correct)")
        
    except Exception as e:
        print(f"✗ Normalization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 6. Try to apply patch
    print(f"\nApplying patch...")
    applicator = PatchApplicator(repo_path)
    
    try:
        apply_result = applicator.apply(normalized)
        
        if apply_result.success:
            print(f"✓ Patch applied successfully!")
            
            # 7. Run tests
            print(f"\nRunning tests...")
            executor = TestExecutor(
                repo_path,
                timeout=600,
                d4j_path=env_manager.d4j_path
            )
            test_result = executor.run_tests(bug_slug)
            
            if test_result.success:
                print(f"✓ Tests passed! Bug fixed!")
            else:
                print(f"✗ Tests failed: {test_result.failed_tests}/{test_result.total_tests} failed")
            
            # Rollback
            applicator.rollback()
            print(f"✓ Rolled back changes")
            
        else:
            print(f"✗ Patch application failed:")
            print(f"  {apply_result.error_message}")
            return 1
            
    except Exception as e:
        print(f"✗ Error applying patch: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Cleanup
    env_manager.cleanup(repo_path)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
