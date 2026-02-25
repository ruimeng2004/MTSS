#!/usr/bin/env python3
"""
完整验证所有patches的正确性
"""

import json
from pathlib import Path
from verify_patch_correctness import (
    check_line_ordering,
    verify_patch_reversal,
    load_original_d4j_patch
)


def main():
    print("=" * 80)
    print("完整验证所有854个patches")
    print("=" * 80)
    print()
    
    patches_file = Path('bug_task_model_selection/data/artifacts/patches.jsonl')
    
    # 统计
    total = 0
    format_ok = 0
    semantic_ok = 0
    both_ok = 0
    failed_patches = []
    
    print("验证所有patches...")
    print()
    
    with open(patches_file, 'r') as f:
        for i, line in enumerate(f):
            item = json.loads(line)
            slug = item['slug']
            reversed_patch = item['text']
            project = item['metadata']['project']
            bug_id = item['metadata']['bug_id']
            
            total += 1
            
            # 格式验证
            format_valid, _ = check_line_ordering(reversed_patch)
            if format_valid:
                format_ok += 1
            
            # 语义验证
            semantic_valid = False
            original_patch = load_original_d4j_patch(project, bug_id)
            if original_patch:
                semantic_valid, msg = verify_patch_reversal(original_patch, reversed_patch)
                if semantic_valid:
                    semantic_ok += 1
                else:
                    failed_patches.append((slug, msg))
            
            if format_valid and semantic_valid:
                both_ok += 1
            
            # 进度显示
            if (i + 1) % 100 == 0:
                print(f"  已验证 {i + 1} patches...")
    
    print()
    print("=" * 80)
    print("验证结果")
    print("=" * 80)
    print(f"总patches数: {total}")
    print(f"格式验证通过: {format_ok}/{total} ({format_ok/total*100:.1f}%)")
    print(f"语义验证通过: {semantic_ok}/{total} ({semantic_ok/total*100:.1f}%)")
    print(f"完全正确: {both_ok}/{total} ({both_ok/total*100:.1f}%)")
    print()
    
    if failed_patches:
        print(f"失败的patches ({len(failed_patches)}):")
        for slug, msg in failed_patches[:10]:  # 只显示前10个
            print(f"  - {slug}: {msg}")
        if len(failed_patches) > 10:
            print(f"  ... 还有 {len(failed_patches) - 10} 个")
        print()
    
    if format_ok == total and semantic_ok == total:
        print("✅ 所有验证通过！Patches转换100%正确。")
        return 0
    else:
        print("⚠️ 部分patches验证失败。")
        return 1


if __name__ == '__main__':
    exit(main())
