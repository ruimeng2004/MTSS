#!/usr/bin/env python3
"""Test evaluation on a single bug with debug output."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.input_handler import InputHandler
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.environment_manager import EnvironmentManager
from evaluation.utils.logging_config import setup_logging

def main():
    """Test evaluation on Chart_1 with debug."""
    setup_logging()
    
    print("=" * 60)
    print("Debug Test: Chart_1 Patch Application")
    print("=" * 60)
    
    # Configuration
    config = {
        'evaluation_config': {
            'd4j_path': '/Users/mengrui/Desktop/D4J/defects4j',
            'workspace_dir': './test_workspace'
        }
    }
    
    result_folder = Path("ppl/result/20260105_132306")
    
    # 1. Load first attempt
    handler = InputHandler(result_folder)
    attempt = handler.load_attempt("Chart_1", 1)
    
    print(f"\n1. Loaded attempt: Chart_1/1")
    print(f"   Modeling type: {attempt.modeling_type}")
    
    # 2. Parse output
    parser = OutputParser()
    parsed = parser.parse(
        attempt.model_output,
        "Chart_1",
        1,
        attempt.modeling_type
    )
    
    print(f"\n2. Parsed output:")
    print(f"   Success: {parsed.parse_success}")
    print(f"   Patches: {parsed.patch_count}")
    
    # 3. Checkout bug
    env_manager = EnvironmentManager(
        d4j_path=Path(config['evaluation_config']['d4j_path']),
        workspace_dir=Path(config['evaluation_config']['workspace_dir'])
    )
    
    repo_path = env_manager.checkout_bug("Chart_1")
    print(f"\n3. Checked out to: {repo_path}")
    
    # 4. Find source file
    import subprocess
    result = subprocess.run(
        [
            str(env_manager.d4j_path / 'framework' / 'bin' / 'defects4j'),
            'export',
            '-p', 'classes.modified',
            '-w', str(repo_path)
        ],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    modified_classes = result.stdout.strip().split('\n')
    class_name = modified_classes[0].strip()
    file_path = class_name.replace('.', '/') + '.java'
    
    print(f"\n4. Modified class: {class_name}")
    print(f"   File path: {file_path}")
    
    # Search for file
    for src_dir in ['source', 'src/main/java', 'src/java', 'src']:
        full_path = repo_path / src_dir / file_path
        if full_path.exists():
            print(f"   Found at: {full_path}")
            source_file = full_path
            break
    
    # 5. Normalize patch
    normalizer = PatchNormalizer()
    normalized = normalizer.normalize(parsed, source_file)
    
    print(f"\n5. Normalized patch:")
    print(f"   Target files: {normalized.target_files}")
    print(f"   Diff preview:")
    print("   " + "\n   ".join(normalized.diff_content.split('\n')[:15]))
    
    # 6. Save patch for inspection
    patch_file = Path("debug_patch.patch")
    patch_file.write_text(normalized.diff_content)
    print(f"\n6. Saved patch to: {patch_file}")
    
    # 7. Try to apply manually
    print(f"\n7. Manual patch test:")
    print(f"   cd {repo_path}")
    print(f"   patch -p0 < ../../debug_patch.patch")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
