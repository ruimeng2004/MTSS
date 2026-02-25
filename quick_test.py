#!/usr/bin/env python3
"""Quick test to verify line ending normalization works."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.utils.logging_config import setup_logging

def main():
    """Quick test."""
    setup_logging()
    
    print("=" * 60)
    print("Quick Test: Line Ending Normalization")
    print("=" * 60)
    
    # Setup
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    # Checkout
    print("\n1. Checking out Chart_1...")
    repo_path = env_manager.checkout_bug("Chart_1")
    print(f"   ✓ Checked out to: {repo_path}")
    
    # Check line endings
    test_file = repo_path / "source/org/jfree/chart/renderer/category/AbstractCategoryItemRenderer.java"
    
    if test_file.exists():
        content = test_file.read_bytes()
        has_crlf = b'\r\n' in content
        has_cr = b'\r' in content
        
        print(f"\n2. Line ending check:")
        print(f"   File: {test_file.name}")
        print(f"   Has CRLF (\\r\\n): {has_crlf}")
        print(f"   Has CR (\\r): {has_cr}")
        
        if not has_crlf and not has_cr:
            print("   ✓ File uses LF only - normalization worked!")
            return 0
        else:
            print("   ✗ File still has CRLF/CR - normalization failed!")
            return 1
    else:
        print(f"   ✗ File not found: {test_file}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
