#!/usr/bin/env python3
"""
快速测试修复后的补丁应用器
从假阴性案例中抽取样本进行测试
"""
import sys
import os
import json
import tempfile
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, '/home/base/mengrui/MTSS')

from evaluation.core.patch_applicator import PatchApplicator
from evaluation.core.data_structures import NormalizedPatch

def test_sample_bugs():
    """测试样本bug"""
    
    json_path = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/gen_batch_evaluation_results.json'
    patches_dir = Path('/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/patches')
    
    # 加载结果
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # 找出假阴性案例
    false_negatives = []
    for bug_slug, result in data['results'].items():
        if result['successful_attempt'] is None:
            # 检查是否有非空补丁
            for attempt in range(1, 11):
                patch_file = patches_dir / f"{bug_slug}_attempt_{attempt}.patch"
                if patch_file.exists() and patch_file.stat().st_size > 0:
                    false_negatives.append({
                        'bug_slug': bug_slug,
                        'patch_file': patch_file,
                        'failure_reason': result['failure_reasons'][0] if result['failure_reasons'] else 'Unknown'
                    })
                    break
    
    print("=" * 80)
    print(f"快速测试修复后的补丁应用器")
    print("=" * 80)
    print(f"\n找到 {len(false_negatives)} 个假阴性案例")
    
    # 选择不同项目的样本
    samples = {}
    for case in false_negatives:
        project = case['bug_slug'].split('_')[0]
        if project not in samples and len(samples) < 5:
            samples[project] = case
    
    print(f"测试 {len(samples)} 个不同项目的案例\n")
    
    success_count = 0
    total_count = len(samples)
    
    for i, (project, case) in enumerate(samples.items(), 1):
        bug_slug = case['bug_slug']
        patch_file = case['patch_file']
        
        print(f"[{i}/{total_count}] 测试 {bug_slug}")
        print("-" * 80)
        
        # 读取补丁
        with open(patch_file, 'r') as f:
            patch_content = f.read()
        
        # 显示补丁路径
        for line in patch_content.split('\n')[:3]:
            if line.startswith('---') or line.startswith('+++'):
                print(f"  {line}")
        
        # 检出bug
        checkout_dir = tempfile.mkdtemp(prefix=f"test_{bug_slug}_")
        
        try:
            proj, vid = bug_slug.split('_')
            cmd = ['defects4j', 'checkout', '-p', proj, '-v', f'{vid}b', '-w', checkout_dir]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"  ✗ 检出失败")
                continue
            
            print(f"  ✓ 检出成功")
            
            # 测试补丁应用
            applicator = PatchApplicator(Path(checkout_dir))
            normalized_patch = NormalizedPatch(
                bug_slug=bug_slug,
                attempt_num=1,
                diff_content=patch_content,
                target_files=[],
                modeling_type='rewrite'
            )
            
            apply_result = applicator.apply(normalized_patch)
            
            if apply_result.success:
                print(f"  ✓ 补丁应用成功!")
                print(f"    方法: {apply_result.method}")
                success_count += 1
            else:
                print(f"  ✗ 补丁应用失败")
                error_msg = apply_result.error_message[:150]
                print(f"    错误: {error_msg}")
        
        except subprocess.TimeoutExpired:
            print(f"  ✗ 检出超时")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
        finally:
            # 清理
            try:
                shutil.rmtree(checkout_dir)
            except:
                pass
        
        print()
    
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"测试案例数: {total_count}")
    print(f"应用成功数: {success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    if success_count > 0:
        # 估算全部假阴性的修复情况
        estimated_fixes = int(len(false_negatives) * (success_count / total_count))
        print(f"\n估算: 在 {len(false_negatives)} 个假阴性中,")
        print(f"      约 {estimated_fixes} 个可通过修复后的应用器成功应用补丁")
        
        # 更新成功率估算
        original_success = data['fixed_bugs']
        total_bugs = data['total_bugs']
        new_estimated_success = original_success + estimated_fixes
        new_success_rate = new_estimated_success / total_bugs * 100
        
        print(f"\n真实成功率估算:")
        print(f"  原始: {original_success}/{total_bugs} ({data['success_rate']*100:.1f}%)")
        print(f"  修复后估算: {new_estimated_success}/{total_bugs} ({new_success_rate:.1f}%)")
        print(f"  提升: +{new_success_rate - data['success_rate']*100:.1f}%")

if __name__ == '__main__':
    test_sample_bugs()
