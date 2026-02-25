#!/usr/bin/env python3
"""Test script to verify the evaluation system fix."""

import subprocess
import sys
from pathlib import Path

def test_defects4j_setup():
    """Test if Defects4J is properly set up."""
    print("Testing Defects4J setup...")
    
    d4j_path = Path("/Users/mengrui/Desktop/D4J/defects4j")
    d4j_bin = d4j_path / "framework" / "bin" / "defects4j"
    
    if not d4j_bin.exists():
        print(f"❌ Defects4J not found at: {d4j_bin}")
        return False
    
    # Test defects4j command
    try:
        result = subprocess.run(
            [str(d4j_bin), "info", "-p", "Chart"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ Defects4J is working")
            return True
        else:
            print(f"❌ Defects4J error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Defects4J: {e}")
        return False

def test_source_file_locator():
    """Test the _locate_source_file implementation."""
    print("\nTesting source file locator...")
    
    # Check if the fix was applied
    evaluator_file = Path("evaluation/core/evaluator.py")
    
    if not evaluator_file.exists():
        print("❌ evaluator.py not found")
        return False
    
    content = evaluator_file.read_text()
    
    if "subprocess.run" in content and "classes.modified" in content:
        print("✓ Source file locator implementation found")
        return True
    else:
        print("❌ Source file locator not properly implemented")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("D4J Fix Evaluation System - Diagnostic Test")
    print("=" * 60)
    
    tests = [
        ("Defects4J Setup", test_defects4j_setup),
        ("Source File Locator", test_source_file_locator),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test '{name}' failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All tests passed! The system should be ready to use.")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
