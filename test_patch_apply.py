#!/usr/bin/env python3
"""Test if Chart_13 patch can be applied."""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.environment_manager import EnvironmentManager
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer

def main():
    """Test Chart_13 patch application."""
    
    # 1. Checkout
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    repo_path = env_manager.checkout_bug('Chart_13')
    print(f"✓ Checked out to: {repo_path}\n")
    
    # 2. Parse and normalize
    model_output_file = Path("ppl/result/20260105_132306/Chart_13/1/model_output.txt")
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    parser = OutputParser()
    parsed = parser.parse(model_output, 'Chart_13', 1, 'edit')
    
    source_file = repo_path / 'source/org/jfree/chart/block/BorderArrangement.java'
    normalizer = PatchNormalizer()
    normalized = normalizer.normalize(parsed, source_file)
    
    print(f"✓ Normalized patch ({len(normalized.diff_content)} chars)\n")
    
    # 3. Write patch to file
    patch_file = Path('./test_chart13.patch')
    with open(patch_file, 'w') as f:
        f.write(normalized.diff_content)
    
    print(f"✓ Wrote patch to {patch_file}\n")
    
    # 4. Try to apply with git apply
    print("Attempting to apply patch with git apply...")
    patch_file_abs = patch_file.absolute()
    result = subprocess.run(
        ['git', 'apply', '--check', str(patch_file_abs)],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ git apply --check PASSED\n")
        
        # Actually apply it
        result2 = subprocess.run(
            ['git', 'apply', str(patch_file_abs)],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result2.returncode == 0:
            print("✓ git apply SUCCEEDED!\n")
            
            # Show the modified file
            print("Modified file content (first 20 lines around change):")
            result3 = subprocess.run(
                ['sed', '-n', '438,458p', str(source_file)],
                capture_output=True,
                text=True
            )
            print(result3.stdout)
            
            return 0
        else:
            print(f"✗ git apply FAILED:")
            print(result2.stderr)
            return 1
    else:
        print(f"✗ git apply --check FAILED:")
        print(result.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
