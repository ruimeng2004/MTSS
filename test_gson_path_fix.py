#!/usr/bin/env python3
"""Test script to verify Gson path handling fix."""

import sys
from pathlib import Path

# Add evaluation module to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.patch_normalizer import PatchNormalizer


def test_extract_relative_path():
    """Test _extract_relative_path with Gson project."""
    normalizer = PatchNormalizer()
    
    # Test cases
    test_cases = [
        # (filepath, bug_slug, expected_result)
        (
            Path("/workspace/gson/src/main/java/com/google/gson/Gson.java"),
            "Gson_12",
            "gson/src/main/java/com/google/gson/Gson.java"
        ),
        (
            Path("/workspace/gson/src/main/java/com/google/gson/JsonParser.java"),
            "Gson_13",
            "gson/src/main/java/com/google/gson/JsonParser.java"
        ),
        (
            Path("/workspace/src/main/java/org/apache/commons/Lang.java"),
            "Lang_1",
            "src/main/java/org/apache/commons/Lang.java"
        ),
        (
            Path("/workspace/Chart_1/source/org/jfree/chart/Chart.java"),
            "Chart_1",
            "source/org/jfree/chart/Chart.java"
        ),
    ]
    
    print("Testing _extract_relative_path with Gson handling:\n")
    
    all_passed = True
    for filepath, bug_slug, expected in test_cases:
        result = normalizer._extract_relative_path(filepath, bug_slug)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {bug_slug}")
        print(f"  Input:    {filepath}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print()
    
    if all_passed:
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed! ✗")
        return 1


if __name__ == "__main__":
    sys.exit(test_extract_relative_path())
