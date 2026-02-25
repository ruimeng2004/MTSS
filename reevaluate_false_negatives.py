#!/usr/bin/env python3
"""
重新评估假阴性案例
使用修复后的补丁应用器重新评估之前失败但有补丁的案例
"""
import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List

# 添加路径
sys.path.insert(0, '/home/base/mengrui/MTSS')

from evaluation.core.evaluator import D4JEvaluator
from evaluation.core.data_structures import BugInfo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_false_negatives(json_path: str, patches_dir: str) -> List[Dict]:
    """加载假阴性案例列表"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    results = data['results']
    false_negatives = []
    
    for bug_slug, result in results.items():
        if result['successful_attempt'] is None:
            # 检查是否有非空补丁
            has_patch = False
            for attempt in range(1, 11):
                patch_file = Path(patches_dir) / f"{bug_slug}_attempt_{attempt}.patch"
                if patch_file.exists() and patch_file.stat().st_size > 0:
                    has_patch = True
                    break
            
            if has_patch:
                false_negatives.append({
                    'bug_slug': bug_slug,
                    'original_failure': result['failure_reasons'][0] if result['failure_reasons'] else 'Unknown'
                })
    
    return false_negatives

def reevaluate_bug(bug_slug: str, patches_dir: str, evaluator: D4JEvaluator) -> Dict:
    """重新评估单个bug"""
    logger.info(f"重新评估 {bug_slug}")
    
    project, bug_id = bug_slug.split('_')
    
    # 创建BugInfo
    bug_info = BugInfo(
        project=project,
        bug_id=int(bug_id),
        bug_slug=bug_slug
    )
    
    # 收集所有补丁
    patches = []
    for attempt in range(1, 11):
        patch_file = Path(patches_dir) / f"{bug_slug}_attempt_{attempt}.patch"
        if patch_file.exists() and patch_file.stat().st_size > 0:
            with open(patch_file, 'r') as f:
                patch_content = f.read()
                patches.append({
                    'attempt': attempt,
                    'content': patch_content
                })
    
    if not patches:
        return {
            'bug_slug': bug_slug,
            'status': 'no_patches',
            'message': '没有找到有效的补丁'
        }
    
    # 尝试应用每个补丁
    for patch_info in patches:
        try:
            # 使用评估器测试补丁
            result = evaluator.evaluate_single_bug(
                bug_info=bug_info,
                patch_content=patch_info['content'],
                attempt_num=patch_info['attempt'],
                modeling_type='rewrite'
            )
            
            if result.success:
                return {
                    'bug_slug': bug_slug,
                    'status': 'fixed',
                    'attempt': patch_info['attempt'],
                    'message': f'补丁在attempt {patch_info["attempt"]}成功应用并通过测试'
                }
        
        except Exception as e:
            logger.warning(f"{bug_slug} attempt {patch_info['attempt']} 失败: {e}")
            continue
    
    return {
        'bug_slug': bug_slug,
        'status': 'still_failed',
        'message': '所有补丁仍然失败'
    }

def main():
    """主函数"""
    json_path = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/gen_batch_evaluation_results.json'
    patches_dir = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/patches'
    output_dir = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/reevaluation'
    
    # 创建输出目录
    Path(output_dir).mkdir(exist_ok=True)
    
    print("=" * 80)
    print("重新评估假阴性案例")
    print("=" * 80)
    
    # 加载假阴性案例
    false_negatives = load_false_negatives(json_path, patches_dir)
    print(f"\n找到 {len(false_negatives)} 个假阴性案例")
    
    # 选择一个样本进行测试
    sample_size = min(10, len(false_negatives))
    samples = false_negatives[:sample_size]
    
    print(f"测试前 {sample_size} 个案例...")
    print("-" * 80)
    
    # 初始化评估器
    evaluator = D4JEvaluator(
        output_dir=output_dir,
        timeout=300,
        max_attempts=10
    )
    
    results = []
    fixed_count = 0
    
    for i, case in enumerate(samples, 1):
        print(f"\n[{i}/{sample_size}] {case['bug_slug']}")
        print(f"  原始失败原因: {case['original_failure'][:100]}...")
        
        result = reevaluate_bug(case['bug_slug'], patches_dir, evaluator)
        results.append(result)
        
        print(f"  重评估结果: {result['status']}")
        print(f"  {result['message']}")
        
        if result['status'] == 'fixed':
            fixed_count += 1
    
    # 总结
    print("\n" + "=" * 80)
    print("重新评估总结")
    print("=" * 80)
    print(f"测试案例数: {sample_size}")
    print(f"修复成功数: {fixed_count}")
    print(f"修复率: {fixed_count/sample_size*100:.1f}%")
    
    # 保存结果
    output_file = Path(output_dir) / 'reevaluation_sample_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'total_tested': sample_size,
            'fixed': fixed_count,
            'results': results
        }, f, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    
    # 估算全部假阴性的可能修复率
    if fixed_count > 0:
        estimated_total_fixes = int(len(false_negatives) * (fixed_count / sample_size))
        print(f"\n估算: 如果对全部 {len(false_negatives)} 个假阴性重新评估,")
        print(f"      可能会额外修复约 {estimated_total_fixes} 个bug")

if __name__ == '__main__':
    main()
