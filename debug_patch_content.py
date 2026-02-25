#!/usr/bin/env python3
"""Debug script to inspect generated patch content."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.input_handler import InputHandler
from evaluation.core.output_parser import OutputParser
from evaluation.core.patch_normalizer import PatchNormalizer
from evaluation.core.environment_manager import EnvironmentManager

def main():
    """Debug patch generation for Chart_1."""
    
    # Setup
    result_folder = Path("ppl/result/20260105_132306")
    bug_slug = "Chart_1"
    
    # 1. Load input
    input_handler = InputHandler(result_folder)
    
    # Find the bug's attempt directory
    bug_dir = result_folder / bug_slug
    if not bug_dir.exists():
        print(f"Bug directory not found: {bug_dir}")
        return 1
    
    # Get first attempt
    attempt_dirs = sorted([d for d in bug_dir.iterdir() if d.is_dir()])
    if not attempt_dirs:
        print(f"No attempts found for {bug_slug}")
        return 1
    
    attempt_dir = attempt_dirs[0]
    attempt_num = int(attempt_dir.name)
    
    # Load attempt data
    model_output_file = attempt_dir / "model_output.txt"
    result_json_file = attempt_dir / "result.json"
    
    if not model_output_file.exists():
        print(f"model_output.txt not found in {attempt_dir}")
        return 1
    
    with open(model_output_file, 'r') as f:
        model_output = f.read()
    
    # Determine modeling type from result.json
    import json
    with open(result_json_file, 'r') as f:
        result_data = json.load(f)
    
    # Extract modeling type from task field
    task = result_data.get('task', 'd4j_edit')
    if 'edit' in task.lower():
        modeling_type = 'edit'
    elif 'rewrite' in task.lower():
        modeling_type = 'rewrite'
    else:
        modeling_type = 'edit'  # default
    
    class Attempt:
        def __init__(self, num, output, mtype):
            self.attempt_num = num
            self.model_output = output
            self.modeling_type = mtype
    
    attempt = Attempt(attempt_num, model_output, modeling_type)
    print(f"Processing {bug_slug}, attempt {attempt.attempt_num}")
    print(f"Modeling type: {attempt.modeling_type}")
    print("=" * 70)
    
    # 2. Parse output
    parser = OutputParser()
    parsed_patch = parser.parse(
        model_output=attempt.model_output,
        bug_slug=bug_slug,
        attempt_num=attempt.attempt_num,
        modeling_type=attempt.modeling_type
    )
    
    print(f"\nParsed patch:")
    print(f"  Bug: {parsed_patch.bug_slug}")
    print(f"  Type: {parsed_patch.modeling_type}")
    if parsed_patch.modeling_type == 'edit':
        print(f"  Search/Replace blocks: {len(parsed_patch.search_replaces)}")
    else:
        print(f"  Rewrites: {len(parsed_patch.rewrites)}")
    
    # 3. Checkout bug
    env_manager = EnvironmentManager(
        d4j_path=Path('/Users/mengrui/Desktop/D4J/defects4j'),
        workspace_dir=Path('./test_workspace')
    )
    
    repo_path = env_manager.checkout_bug(bug_slug)
    print(f"\nChecked out to: {repo_path}")
    
    # 4. Locate source file
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
    
    if result.returncode != 0:
        print(f"Failed to get modified classes: {result.stderr}")
        return 1
    
    modified_classes = result.stdout.strip().split('\n')
    class_name = modified_classes[0].strip()
    file_path = class_name.replace('.', '/') + '.java'
    
    # Search for file
    source_file = None
    for src_dir in ['source', 'src/main/java', 'src/java', 'src']:
        full_path = repo_path / src_dir / file_path
        if full_path.exists():
            source_file = full_path
            break
    
    if not source_file:
        print(f"Source file not found for {class_name}")
        return 1
    
    print(f"Source file: {source_file}")
    
    # 5. Normalize patch
    normalizer = PatchNormalizer()
    try:
        normalized_patch = normalizer.normalize(parsed_patch, source_file)
        
        print(f"\nNormalized patch:")
        print(f"  Target files: {normalized_patch.target_files}")
        print(f"  Match quality: {normalized_patch.match_quality}")
        print(f"\nDiff content:")
        print("=" * 70)
        print(normalized_patch.diff_content)
        print("=" * 70)
        
        # Save to file for inspection
        debug_patch_file = Path("debug_patch_content.patch")
        with open(debug_patch_file, 'w') as f:
            f.write(normalized_patch.diff_content)
        
        print(f"\nPatch saved to: {debug_patch_file}")
        
        # Check if diff is empty or malformed
        lines = normalized_patch.diff_content.strip().split('\n')
        print(f"\nPatch analysis:")
        print(f"  Total lines: {len(lines)}")
        print(f"  Has --- header: {'---' in normalized_patch.diff_content}")
        print(f"  Has +++ header: {'+++' in normalized_patch.diff_content}")
        print(f"  Has @@ hunk: {'@@' in normalized_patch.diff_content}")
        
        # Count change lines
        add_lines = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
        del_lines = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))
        print(f"  Added lines: {add_lines}")
        print(f"  Deleted lines: {del_lines}")
        
        if add_lines == 0 and del_lines == 0:
            print("\n⚠️  WARNING: No actual changes in patch!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Normalization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
