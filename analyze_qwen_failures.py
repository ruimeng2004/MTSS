#!/usr/bin/env python3
"""
分析 qwen3coder30b 失败案例,查找假阴性(false negative)案例
"""
import json
import os
import sys

def analyze_failures(json_path):
    """分析失败案例"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    results = data['results']
    
    # 统计信息
    failed_cases = []
    failure_types = {}
    
    for bug_slug, result in results.items():
        if result['successful_attempt'] is None:
            failed_cases.append({
                'bug_slug': bug_slug,
                'failure_reasons': result['failure_reasons'],
                'total_attempts': result['total_attempts']
            })
            
            # 统计失败类型
            if result['failure_reasons']:
                # 获取第一个失败原因作为分类
                first_reason = result['failure_reasons'][0]
                if 'empty' in first_reason.lower():
                    failure_type = 'Empty Patch'
                elif 'timeout' in first_reason.lower():
                    failure_type = 'Timeout'
                elif 'test failed' in first_reason.lower():
                    failure_type = 'Test Failed'
                elif 'compilation' in first_reason.lower() or 'compile' in first_reason.lower():
                    failure_type = 'Compilation Error'
                elif 'not found' in first_reason.lower():
                    failure_type = 'File Not Found'
                else:
                    failure_type = 'Other'
                
                failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
    
    print("=" * 80)
    print(f"失败案例总数: {len(failed_cases)}")
    print(f"成功案例总数: {data['fixed_bugs']}")
    print(f"总案例数: {data['total_bugs']}")
    print(f"成功率: {data['success_rate']:.2%}")
    print("=" * 80)
    
    print("\n失败类型统计:")
    print("-" * 80)
    for failure_type, count in sorted(failure_types.items(), key=lambda x: -x[1]):
        percentage = count / len(failed_cases) * 100
        print(f"{failure_type:30s}: {count:4d} ({percentage:5.1f}%)")
    
    print("\n" + "=" * 80)
    print("失败案例详细信息:")
    print("=" * 80)
    
    # 按项目分组
    project_failures = {}
    for case in failed_cases:
        project = case['bug_slug'].split('_')[0]
        if project not in project_failures:
            project_failures[project] = []
        project_failures[project].append(case)
    
    for project in sorted(project_failures.keys()):
        print(f"\n项目: {project} ({len(project_failures[project])} 个失败)")
        print("-" * 80)
        for case in sorted(project_failures[project], key=lambda x: x['bug_slug']):
            print(f"\n  Bug: {case['bug_slug']}")
            if case['failure_reasons']:
                # 只显示第一个失败原因的关键部分
                first_reason = case['failure_reasons'][0]
                # 提取关键信息
                if ':' in first_reason:
                    reason_part = first_reason.split(':', 1)[1].strip()
                else:
                    reason_part = first_reason
                print(f"    失败原因: {reason_part}")
            else:
                print("    失败原因: 未知")
    
    # 检查可能的假阴性 - 查找输出目录中的patch文件
    print("\n" + "=" * 80)
    print("假阴性检测 - 检查是否有生成的补丁文件:")
    print("=" * 80)
    
    eval_dir = os.path.dirname(json_path)
    potential_false_negatives = []
    
    for case in failed_cases:
        bug_slug = case['bug_slug']
        # 检查是否有patch文件存在
        potential_patch_files = []
        
        # 检查各种可能的patch文件位置
        for attempt in range(1, 11):
            patch_path = os.path.join(eval_dir, bug_slug, f'attempt_{attempt}', 'patch.diff')
            if os.path.exists(patch_path):
                # 检查文件是否非空
                if os.path.getsize(patch_path) > 0:
                    potential_patch_files.append((attempt, patch_path))
        
        if potential_patch_files:
            potential_false_negatives.append({
                'bug_slug': bug_slug,
                'patch_files': potential_patch_files
            })
    
    if potential_false_negatives:
        print(f"\n发现 {len(potential_false_negatives)} 个潜在假阴性案例:")
        for case in potential_false_negatives:
            print(f"\n  {case['bug_slug']}:")
            for attempt, path in case['patch_files']:
                size = os.path.getsize(path)
                print(f"    Attempt {attempt}: {path} ({size} bytes)")
    else:
        print("\n未发现明显的假阴性案例")
    
    return {
        'total_failed': len(failed_cases),
        'failure_types': failure_types,
        'potential_false_negatives': potential_false_negatives
    }

if __name__ == '__main__':
    json_path = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/gen_batch_evaluation_results.json'
    
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    
    analyze_failures(json_path)
