#!/usr/bin/env python3
"""Diagnostic test to identify evaluation issues."""

import sys
from pathlib import Path

# Add evaluation module to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.input_handler import InputHandler
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.utils.logging_config import setup_logging

def test_input_loading():
    """Test if input loading works correctly."""
    print("=" * 60)
    print("Test 1: Input Loading")
    print("=" * 60)
    
    result_folder = Path("ppl/result/20260105_132306")
    handler = InputHandler(result_folder)
    
    # Validate structure
    if not handler.validate_structure():
        print("❌ Structure validation failed")
        return False
    
    print("✓ Structure validation passed")
    
    # List bugs
    bugs = handler.list_bugs()
    print(f"✓ Found {len(bugs)} bugs")
    
    # Load first bug's first attempt
    if bugs:
        bug_slug = bugs[0]
        attempts = handler.list_attempts(bug_slug)
        print(f"✓ Bug {bug_slug} has {len(attempts)} attempts")
        
        if attempts:
            attempt = handler.load_attempt(bug_slug, attempts[0])
            if attempt:
                print(f"✓ Loaded attempt {bug_slug}/{attempts[0]}")
                print(f"  Modeling type: {attempt.modeling_type}")
                print(f"  Model output length: {len(attempt.model_output)}")
                return True
            else:
                print(f"❌ Failed to load attempt")
                return False
    
    return False

def test_output_parsing():
    """Test if output parsing works correctly."""
    print("\n" + "=" * 60)
    print("Test 2: Output Parsing")
    print("=" * 60)
    
    result_folder = Path("ppl/result/20260105_132306")
    handler = InputHandler(result_folder)
    parser = OutputParser()
    
    bugs = handler.list_bugs()
    if not bugs:
        print("❌ No bugs found")
        return False
    
    bug_slug = bugs[0]
    attempts = handler.list_attempts(bug_slug)
    if not attempts:
        print("❌ No attempts found")
        return False
    
    attempt = handler.load_attempt(bug_slug, attempts[0])
    if not attempt:
        print("❌ Failed to load attempt")
        return False
    
    # Parse the output
    parsed = parser.parse(
        attempt.model_output,
        bug_slug,
        attempts[0],
        attempt.modeling_type
    )
    
    if not parsed.parse_success:
        print(f"❌ Parse failed: {parsed.parse_error}")
        return False
    
    print(f"✓ Parse succeeded")
    print(f"  Modeling type: {parsed.modeling_type}")
    print(f"  Patch count: {parsed.patch_count}")
    
    if parsed.is_edit_format:
        print(f"  SEARCH/REPLACE blocks: {len(parsed.search_replaces)}")
        if parsed.search_replaces:
            sr = parsed.search_replaces[0]
            print(f"  First block method: {sr.method_signature}")
            print(f"  Search lines: {len(sr.search_block.split(chr(10)))}")
            print(f"  Replace lines: {len(sr.replace_block.split(chr(10)))}")
    
    return True

def test_patch_applicator_method():
    """Test if patch applicator method signature matches evaluator usage."""
    print("\n" + "=" * 60)
    print("Test 3: Patch Applicator Method Signature")
    print("=" * 60)
    
    from evaluation.core.patch_applicator import PatchApplicator
    
    # Check if apply method accepts NormalizedPatch
    import inspect
    sig = inspect.signature(PatchApplicator.apply)
    params = list(sig.parameters.keys())
    
    print(f"  PatchApplicator.apply parameters: {params}")
    
    # Check evaluator.py to see what it passes
    evaluator_file = Path("evaluation/core/evaluator.py")
    evaluator_content = evaluator_file.read_text()
    
    # Look for the apply call
    if "applicator.apply(normalized_patch)" in evaluator_content:
        print("✓ evaluator.py passes NormalizedPatch object")
        if 'patch' in params:
            print("✓ PatchApplicator.apply() expects NormalizedPatch")
            return True
        else:
            print("❌ Mismatch: evaluator passes NormalizedPatch but apply() doesn't expect it")
            return False
    elif "applicator.apply(normalized_patch.diff_content)" in evaluator_content:
        print("❌ evaluator.py passes diff_content string")
        print("   But PatchApplicator.apply() expects NormalizedPatch object")
        return False
    else:
        print("⚠ Could not find apply() call in evaluator.py")
        return False

def main():
    """Run all diagnostic tests."""
    setup_logging()
    
    print("D4J Fix Evaluation System - Diagnostic Tests")
    print()
    
    tests = [
        ("Input Loading", test_input_loading),
        ("Output Parsing", test_output_parsing),
        ("Patch Applicator", test_patch_applicator_method),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' raised exception:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
