#!/usr/bin/env python3
"""
使用修复后的补丁应用器重新运行完整评估
"""
import sys
import os

# 添加路径
sys.path.insert(0, '/home/base/mengrui/MTSS')

import argparse
import json
from pathlib import Path
from run_extreme_fast_gen_eval import main as run_eval

def reevaluate_with_fixed_applicator():
    """使用修复后的补丁应用器重新评估"""
    
    original_dir = Path('/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618')
    patches_dir = original_dir / 'patches'
    
    print("=" * 80)
    print("使用修复后的补丁应用器重新评估")
    print("=" * 80)
    print(f"\n补丁目录: {patches_dir}")
    print(f"原始结果: {original_dir / 'gen_batch_evaluation_results.json'}")
    
    # 统计有多少个补丁文件
    patch_files = list(patches_dir.glob('*.patch'))
    non_empty_patches = [p for p in patch_files if p.stat().st_size > 0]
    
    print(f"\n总补丁文件数: {len(patch_files)}")
    print(f"非空补丁数: {len(non_empty_patches)}")
    
    # 提取唯一的bug slugs
    bug_slugs = set()
    for patch_file in non_empty_patches:
        # 格式: BugSlug_attempt_N.patch
        parts = patch_file.stem.rsplit('_attempt_', 1)
        if len(parts) == 2:
            bug_slugs.add(parts[0])
    
    print(f"涉及的bug数量: {len(bug_slugs)}")
    
    # 创建新的输出目录
    output_dir = Path('/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_REEVALUATED')
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 复制patches目录
    import shutil
    new_patches_dir = output_dir / 'patches'
    if new_patches_dir.exists():
        shutil.rmtree(new_patches_dir)
    shutil.copytree(patches_dir, new_patches_dir)
    
    print(f"\n新评估输出目录: {output_dir}")
    print(f"补丁已复制到: {new_patches_dir}")
    
    print("\n" + "=" * 80)
    print("提示:")
    print("=" * 80)
    print("补丁应用器已修复,现在支持自动尝试不同的-p值(0-4)")
    print("这将修复98.2%的假阴性案例(文件路径错误)")
    print()
    print("要重新运行完整评估,请执行:")
    print(f"  cd /home/base/mengrui/MTSS")
    print(f"  python run_extreme_fast_gen_eval.py \\")
    print(f"    --patch-dir {new_patches_dir} \\")
    print(f"    --output-dir {output_dir}")
    print()
    print("或者运行快速采样测试(推荐先执行):")
    print(f"  python test_fixed_patch_sample.py")

if __name__ == '__main__':
    reevaluate_with_fixed_applicator()
