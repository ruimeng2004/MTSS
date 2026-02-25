#!/usr/bin/env python3
"""
测试修复后的补丁应用器
"""
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

# 添加路径
sys.path.insert(0, '/home/base/mengrui/MTSS')

from evaluation.core.patch_applicator import PatchApplicator
from evaluation.core.data_structures import NormalizedPatch

def test_path_stripping():
    """测试路径剥离功能"""
    
    # 读取一个失败的案例
    json_path = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/gen_batch_evaluation_results.json'
    patches_dir = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/patches'
    
    # 测试案例
    test_bugs = ['Cli_29', 'Chart_10', 'Math_10']
    
    print("=" * 80)
    print("测试修复后的补丁应用器")
    print("=" * 80)
    
    for bug_slug in test_bugs:
        print(f"\n测试 {bug_slug}:")
        print("-" * 80)
        
        # 查找第一个非空补丁
        patch_file = None
        for attempt in range(1, 11):
            candidate = Path(patches_dir) / f"{bug_slug}_attempt_{attempt}.patch"
            if candidate.exists() and candidate.stat().st_size > 0:
                patch_file = candidate
                break
        
        if not patch_file:
            print(f"  ⚠ 未找到有效的补丁文件")
            continue
        
        print(f"  使用补丁: {patch_file.name}")
        
        # 读取补丁内容
        with open(patch_file, 'r') as f:
            patch_content = f.read()
        
        # 显示补丁路径信息
        lines = patch_content.split('\n')
        for line in lines[:5]:
            if line.startswith('---') or line.startswith('+++'):
                print(f"  {line}")
        
        # 检出bug
        print(f"\n  检出 {bug_slug}...")
        checkout_dir = tempfile.mkdtemp(prefix=f"test_{bug_slug}_")
        
        try:
            # 使用 defects4j checkout
            import subprocess
            result = subprocess.run(
                ['defects4j', 'checkout', '-p', bug_slug.split('_')[0], 
                 '-v', bug_slug.split('_')[1] + 'b', '-w', checkout_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"  ✗ 检出失败: {result.stderr}")
                continue
            
            print(f"  ✓ 检出成功到: {checkout_dir}")
            
            # 应用补丁
            print(f"\n  应用补丁...")
            applicator = PatchApplicator(Path(checkout_dir))
            
            # 创建 NormalizedPatch 对象
            normalized_patch = NormalizedPatch(
                bug_slug=bug_slug,
                attempt_num=1,
                diff_content=patch_content,
                target_files=[],
                modeling_type='rewrite'
            )
            
            result = applicator.apply(normalized_patch)
            
            if result.success:
                print(f"  ✓ 补丁应用成功!")
                print(f"    方法: {result.method}")
                if result.applied_files:
                    print(f"    应用的文件: {', '.join(result.applied_files)}")
            else:
                print(f"  ✗ 补丁应用失败")
                print(f"    错误: {result.error_message[:200]}")
        
        except Exception as e:
            print(f"  ✗ 测试失败: {e}")
        
        finally:
            # 清理
            try:
                shutil.rmtree(checkout_dir)
            except:
                pass
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == '__main__':
    test_path_stripping()
