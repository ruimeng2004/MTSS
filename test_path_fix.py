#!/usr/bin/env python3
"""Quick test to verify path extraction fix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.patch_normalizer import PatchNormalizer

def test_path_extraction():
    """Test the _extract_relative_path method."""
    normalizer = PatchNormalizer()
    
    test_cases = [
        (
            "test_workspace/Chart_1_b/source/org/jfree/chart/renderer/category/AbstractCategoryItemRenderer.java",
            "source/org/jfree/chart/renderer/category/AbstractCategoryItemRenderer.java"
        ),
        (
            "/absolute/path/test_workspace/Chart_1_b/src/main/java/com/example/Test.java",
            "src/main/java/com/example/Test.java"
        ),
        (
            "workspace/Bug_1/src/Test.java",
            "src/Test.java"
        ),
    ]
    
    print("Testing path extraction:")
    print("=" * 70)
    
    all_passed = True
    for input_path, expected in test_cases:
        result = normalizer._extract_relative_path(Path(input_path))
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✓" if passed else "✗"
        print(f"\n{status} Input:    {input_path}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(test_path_extraction())
