#!/usr/bin/env python3
"""
分析 qwen3coder30b_FIXED_20260214 的假阴性案例
"""
import json
import os
from pathlib import Path
from collections import defaultdict

def analyze_false_negatives(result_file, input_dir):
    """分析假阴性案例"""
    
    with open(result_file, 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("Qwen3Coder-30B FIXED 评估结果分析")
    print("=" * 80)
    print(f"\n总体统计:")
    print(f"  总bug数: {data['total_bugs']}")
    print(f"  成功修复: {data['fixed_bugs']}")
    print(f"  失败数: {data['failed_bugs']}")
    print(f"  成功率: {data['success_rate']*100:.1f}%")
    
    # 分析失败案例
    failed_cases = []
    failure_type_stats = defaultdict(int)
    
    for bug_slug, result in data['results'].items():
        if result['successful_attempt'] is None:
            # 检查是否有生成的补丁
            bug_dir = Path(input_dir) / bug_slug
            has_output = False
            attempt_count = 0
            
            if bug_dir.exists():
                for i in range(1, 11):
                    attempt_dir = bug_dir / str(i)
                    if attempt_dir.exists():
                        attempt_count += 1
                        result_json = attempt_dir / 'result.json'
                        if result_json.exists():
                            has_output = True
            
            # 分类失败原因
            if result['failure_reasons']:
                first_reason = result['failure_reasons'][0]
                
                if 'Normalization failed' in first_reason:
                    failure_type = 'Normalization Failed'
                elif 'empty patch' in first_reason.lower():
                    failure_type = 'Empty Patch'
                elif 'Test failed' in first_reason or 'test failed' in first_reason:
                    failure_type = 'Test Failed'
                elif 'Compilation failed' in first_reason or 'compilation' in first_reason.lower():
                    failure_type = 'Compilation Error'
                elif 'Timeout' in first_reason or 'timeout' in first_reason.lower():
                    failure_type = 'Timeout'
                elif "can't find file" in first_reason.lower():
                    failure_type = 'File Not Found'
                elif 'Apply failed' in first_reason:
                    failure_type = 'Apply Failed'
                else:
                    failure_type = 'Other'
                
                failure_type_stats[failure_type] += 1
            else:
                failure_type = 'Unknown'
                failure_type_stats[failure_type] += 1
            
            failed_cases.append({
                'bug_slug': bug_slug,
                'has_output': has_output,
                'attempt_count': attempt_count,
                'failure_type': failure_type,
                'failure_reason': result['failure_reasons'][0] if result['failure_reasons'] else 'No reason'
            })
    
    print(f"\n" + "=" * 80)
    print("失败类型统计:")
    print("=" * 80)
    for ftype, count in sorted(failure_type_stats.items(), key=lambda x: -x[1]):
        percentage = count / len(failed_cases) * 100
        print(f"  {ftype:30s}: {count:4d} ({percentage:5.1f}%)")
    
    # 识别假阴性：有输出但评估失败
    potential_false_negatives = [c for c in failed_cases if c['has_output']]
    
    print(f"\n" + "=" * 80)
    print("假阴性检测:")
    print("=" * 80)
    print(f"失败案例总数: {len(failed_cases)}")
    print(f"有生成输出的失败案例: {len(potential_false_negatives)}")
    print(f"潜在假阴性率: {len(potential_false_negatives)/len(failed_cases)*100:.1f}%")
    
    # 按失败类型分组假阴性
    false_neg_by_type = defaultdict(list)
    for case in potential_false_negatives:
        false_neg_by_type[case['failure_type']].append(case)
    
    print(f"\n假阴性按类型分布:")
    for ftype, cases in sorted(false_neg_by_type.items(), key=lambda x: -len(x[1])):
        print(f"  {ftype:30s}: {len(cases):4d}")
    
    # 详细分析主要失败类型
    print(f"\n" + "=" * 80)
    print("主要失败类型详情:")
    print("=" * 80)
    
    for ftype in ['Normalization Failed', 'Empty Patch', 'Apply Failed', 'Test Failed']:
        if ftype in false_neg_by_type:
            cases = false_neg_by_type[ftype]
            print(f"\n【{ftype}】 ({len(cases)} 个案例)")
            print("-" * 80)
            
            # 显示前5个案例
            for case in cases[:5]:
                print(f"\n  {case['bug_slug']}:")
                print(f"    尝试次数: {case['attempt_count']}")
                reason_preview = case['failure_reason'][:150]
                print(f"    失败原因: {reason_preview}...")
    
    # 检查特定的模式
    print(f"\n" + "=" * 80)
    print("问题分析:")
    print("=" * 80)
    
    normalization_failed = [c for c in potential_false_negatives if c['failure_type'] == 'Normalization Failed']
    empty_patch = [c for c in potential_false_negatives if c['failure_type'] == 'Empty Patch']
    
    print(f"\n1. Normalization Failed ({len(normalization_failed)} 个)")
    print("   问题: 补丁生成了,但无法规范化(找不到方法或文件)")
    print("   可能原因:")
    print("   - 生成的代码格式不正确")
    print("   - 方法签名不匹配")
    print("   - 文件路径错误")
    
    print(f"\n2. Empty Patch ({len(empty_patch)} 个)")
    print("   问题: 规范化后补丁为空")
    print("   可能原因:")
    print("   - 生成的代码与原代码完全相同")
    print("   - 解析失败导致没有提取到有效变更")
    
    # 统计有多少是真正的假阴性
    real_false_negatives = normalization_failed + empty_patch
    
    print(f"\n" + "=" * 80)
    print("真实假阴性估算:")
    print("=" * 80)
    print(f"Normalization/Empty Patch问题: {len(real_false_negatives)} 个")
    print(f"占失败案例比例: {len(real_false_negatives)/len(failed_cases)*100:.1f}%")
    
    print(f"\n如果修复这些问题,估算成功率:")
    estimated_success = data['fixed_bugs'] + len(real_false_negatives) * 0.5  # 假设50%能修复
    estimated_rate = estimated_success / data['total_bugs'] * 100
    print(f"  保守估计(50%修复): {estimated_success:.0f}/{data['total_bugs']} ({estimated_rate:.1f}%)")
    
    estimated_success_opt = data['fixed_bugs'] + len(real_false_negatives) * 0.7
    estimated_rate_opt = estimated_success_opt / data['total_bugs'] * 100
    print(f"  乐观估计(70%修复): {estimated_success_opt:.0f}/{data['total_bugs']} ({estimated_rate_opt:.1f}%)")
    
    return {
        'total_failed': len(failed_cases),
        'potential_false_negatives': potential_false_negatives,
        'real_false_negatives': real_false_negatives
    }

if __name__ == '__main__':
    result_file = '/home/base/mengrui/MTSS/evaluation_output/qwen30b_gen_20260214/gen_batch_evaluation_results.json'
    input_dir = '/home/base/mengrui/MTSS/ppl/result/20260106_030425'
    
    analyze_false_negatives(result_file, input_dir)
