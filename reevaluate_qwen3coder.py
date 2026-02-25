#!/usr/bin/env python3
"""
重新评估 qwen3coder30b_gen_20260107_025618 的补丁
使用修复后的补丁应用器
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from run_gen_batch_evaluation import GenBatchEvaluator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reevaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """重新评估主函数"""
    
    # 原始评估目录
    original_dir = Path('/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618')
    patches_dir = original_dir / 'patches'
    
    # 新的输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f'/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_REEVALUATED_{timestamp}')
    
    print("=" * 80)
    print("重新评估 Qwen3Coder-30B 补丁")
    print("=" * 80)
    print(f"\n原始目录: {original_dir}")
    print(f"补丁目录: {patches_dir}")
    print(f"输出目录: {output_dir}")
    
    # 加载原始结果,找出假阴性案例
    original_results_file = original_dir / 'gen_batch_evaluation_results.json'
    with open(original_results_file, 'r') as f:
        original_data = json.load(f)
    
    # 找出所有有补丁的失败案例(假阴性)
    false_negative_bugs = []
    for bug_slug, result in original_data['results'].items():
        if result['successful_attempt'] is None:
            # 检查是否有非空补丁
            has_patch = False
            for attempt in range(1, 11):
                patch_file = patches_dir / f"{bug_slug}_attempt_{attempt}.patch"
                if patch_file.exists() and patch_file.stat().st_size > 0:
                    has_patch = True
                    break
            
            if has_patch:
                false_negative_bugs.append(bug_slug)
    
    print(f"\n原始评估统计:")
    print(f"  总bug数: {original_data['total_bugs']}")
    print(f"  成功修复: {original_data['fixed_bugs']}")
    print(f"  失败数: {original_data['failed_bugs']}")
    print(f"  成功率: {original_data['success_rate']*100:.1f}%")
    
    print(f"\n假阴性案例:")
    print(f"  假阴性数: {len(false_negative_bugs)}")
    print(f"  占失败案例比例: {len(false_negative_bugs)/original_data['failed_bugs']*100:.1f}%")
    
    # 询问是否继续
    print("\n" + "=" * 80)
    print("重新评估选项:")
    print("=" * 80)
    print("1. 仅评估假阴性案例 (223个, 推荐, 较快)")
    print("2. 评估所有失败案例 (340个)")
    print("3. 评估全部案例 (698个, 完整重评估)")
    
    choice = input("\n请选择 (1/2/3) [默认: 1]: ").strip() or "1"
    
    if choice == "1":
        bugs_to_eval = false_negative_bugs
        eval_desc = "假阴性案例"
    elif choice == "2":
        bugs_to_eval = [slug for slug, res in original_data['results'].items() 
                       if res['successful_attempt'] is None]
        eval_desc = "所有失败案例"
    elif choice == "3":
        bugs_to_eval = list(original_data['results'].keys())
        eval_desc = "全部案例"
    else:
        print("无效选择,使用默认选项1")
        bugs_to_eval = false_negative_bugs
        eval_desc = "假阴性案例"
    
    print(f"\n将评估 {len(bugs_to_eval)} 个{eval_desc}")
    
    # 复制补丁到新目录
    import shutil
    output_dir.mkdir(parents=True, exist_ok=True)
    output_patches_dir = output_dir / 'patches'
    
    if output_patches_dir.exists():
        shutil.rmtree(output_patches_dir)
    shutil.copytree(patches_dir, output_patches_dir)
    
    print(f"补丁已复制到: {output_patches_dir}")
    
    # 创建bug列表文件
    bugs_file = output_dir / 'bugs_to_evaluate.txt'
    with open(bugs_file, 'w') as f:
        for bug_slug in bugs_to_eval:
            f.write(f"{bug_slug}\n")
    
    print(f"Bug列表已保存到: {bugs_file}")
    
    # 准备评估输入目录结构
    # GenBatchEvaluator期望input_dir下有bug目录,每个目录包含patches
    eval_input_dir = output_dir / 'input'
    eval_input_dir.mkdir(exist_ok=True)
    
    # 为每个bug创建目录并链接patch文件
    import os
    for bug_slug in bugs_to_eval:
        bug_dir = eval_input_dir / bug_slug
        bug_dir.mkdir(exist_ok=True)
        
        # 复制该bug的所有patch文件
        for attempt in range(1, 11):
            patch_file = output_patches_dir / f"{bug_slug}_attempt_{attempt}.patch"
            if patch_file.exists():
                target = bug_dir / f"attempt_{attempt}.patch"
                shutil.copy2(patch_file, target)
    
    # 使用GenBatchEvaluator
    print("\n" + "=" * 80)
    print("开始重新评估...")
    print("=" * 80)
    
    evaluator = GenBatchEvaluator(
        input_dir=str(eval_input_dir),
        output_dir=str(output_dir),
        d4j_path='/home/base/mengrui/defects4j',
        base_workspace='/tmp/d4j_workspaces',
        num_workers=8,  # 并行worker数量
        timeout=300,
        bug_limit=len(bugs_to_eval)
    )
    
    # 运行评估
    start_time = datetime.now()
    results_data = evaluator.evaluate_parallel()
    end_time = datetime.now()
    
    elapsed = (end_time - start_time).total_seconds()
    results = results_data.get('results', {})
    
    print("\n" + "=" * 80)
    print("重新评估完成!")
    print("=" * 80)
    print(f"耗时: {elapsed:.1f}秒")
    print(f"结果文件: {output_dir / 'gen_batch_evaluation_results.json'}")
    
    # 对比结果
    if results:
        new_success = sum(1 for r in results.values() if r.get('successful_attempt') is not None)
        new_failed = len(results) - new_success
        
        print(f"\n重新评估结果:")
        print(f"  评估数: {len(results)}")
        print(f"  成功: {new_success}")
        print(f"  失败: {new_failed}")
        print(f"  成功率: {new_success/len(results)*100:.1f}%")
        
        # 计算新增修复
        newly_fixed = new_success
        print(f"\n新增修复: {newly_fixed} 个bug")
        
        # 估算总体成功率
        total_success_estimate = original_data['fixed_bugs'] + newly_fixed
        total_rate_estimate = total_success_estimate / original_data['total_bugs'] * 100
        
        print(f"\n估算总体成功率:")
        print(f"  原始: {original_data['fixed_bugs']}/{original_data['total_bugs']} ({original_data['success_rate']*100:.1f}%)")
        print(f"  修复后: {total_success_estimate}/{original_data['total_bugs']} ({total_rate_estimate:.1f}%)")
        print(f"  提升: +{total_rate_estimate - original_data['success_rate']*100:.1f}%")

if __name__ == '__main__':
    main()
