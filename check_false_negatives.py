#!/usr/bin/env python3
"""
检查假阴性案例 - 查找有补丁但被标记为失败的案例
"""
import json
import os
import glob

def check_false_negatives(json_path):
    """检查假阴性"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    results = data['results']
    eval_dir = os.path.dirname(json_path)
    patches_dir = os.path.join(eval_dir, 'patches')
    
    false_negatives = []
    true_failures = []
    
    for bug_slug, result in results.items():
        if result['successful_attempt'] is None:
            # 这是一个失败案例,检查是否有非空补丁
            has_non_empty_patch = False
            patch_info = []
            
            for attempt in range(1, 11):
                patch_file = os.path.join(patches_dir, f"{bug_slug}_attempt_{attempt}.patch")
                if os.path.exists(patch_file):
                    size = os.path.getsize(patch_file)
                    if size > 0:
                        has_non_empty_patch = True
                        patch_info.append({
                            'attempt': attempt,
                            'size': size,
                            'file': patch_file
                        })
            
            if has_non_empty_patch:
                # 这可能是假阴性
                false_negatives.append({
                    'bug_slug': bug_slug,
                    'patches': patch_info,
                    'failure_reasons': result['failure_reasons'][:3] if result['failure_reasons'] else []
                })
            else:
                true_failures.append(bug_slug)
    
    print("=" * 80)
    print("假阴性分析结果")
    print("=" * 80)
    print(f"\n总失败案例数: {len(false_negatives) + len(true_failures)}")
    print(f"潜在假阴性数: {len(false_negatives)}")
    print(f"真实失败数: {len(true_failures)}")
    
    if false_negatives:
        print("\n" + "=" * 80)
        print(f"发现 {len(false_negatives)} 个潜在假阴性案例(有补丁但被标记为失败):")
        print("=" * 80)
        
        # 按项目分组
        projects = {}
        for case in false_negatives:
            project = case['bug_slug'].split('_')[0]
            if project not in projects:
                projects[project] = []
            projects[project].append(case)
        
        for project in sorted(projects.keys()):
            print(f"\n【{project}】 {len(projects[project])} 个假阴性:")
            for case in sorted(projects[project], key=lambda x: x['bug_slug']):
                print(f"\n  {case['bug_slug']}:")
                print(f"    生成的补丁: {len(case['patches'])} 个")
                for patch in case['patches'][:3]:  # 只显示前3个
                    print(f"      - Attempt {patch['attempt']}: {patch['size']} bytes")
                
                if case['failure_reasons']:
                    print(f"    失败原因样本:")
                    for reason in case['failure_reasons'][:2]:
                        # 提取关键部分
                        if ':' in reason:
                            reason_part = reason.split(':', 1)[1].strip()
                        else:
                            reason_part = reason
                        print(f"      - {reason_part}")
        
        # 分析失败原因类型
        print("\n" + "=" * 80)
        print("假阴性案例的失败原因分析:")
        print("=" * 80)
        
        failure_types = {}
        for case in false_negatives:
            if case['failure_reasons']:
                first_reason = case['failure_reasons'][0]
                if "can't find file to patch" in first_reason:
                    failure_type = "文件路径错误"
                elif "Normalization failed" in first_reason:
                    failure_type = "规范化失败"
                elif "Patch content is empty" in first_reason:
                    failure_type = "补丁为空(但实际有文件)" 
                elif "Test failed" in first_reason or "test failed" in first_reason:
                    failure_type = "测试失败"
                elif "Compilation" in first_reason or "compilation" in first_reason:
                    failure_type = "编译错误"
                else:
                    failure_type = "其他错误"
                
                failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        
        for ftype, count in sorted(failure_types.items(), key=lambda x: -x[1]):
            percentage = count / len(false_negatives) * 100
            print(f"  {ftype:30s}: {count:4d} ({percentage:5.1f}%)")
        
        # 查看一个具体的假阴性案例
        if false_negatives:
            print("\n" + "=" * 80)
            print("示例案例详情:")
            print("=" * 80)
            
            sample = false_negatives[0]
            print(f"\nBug: {sample['bug_slug']}")
            if sample['patches']:
                patch_file = sample['patches'][0]['file']
                print(f"\n补丁文件内容 ({patch_file}):")
                print("-" * 80)
                with open(patch_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    for i, line in enumerate(lines[:20], 1):  # 只显示前20行
                        print(f"{i:3d}: {line}")
                    if len(lines) > 20:
                        print(f"... (还有 {len(lines) - 20} 行)")
    
    else:
        print("\n✓ 未发现假阴性案例 - 所有失败案例都没有生成有效补丁")
    
    return {
        'false_negatives': len(false_negatives),
        'true_failures': len(true_failures),
        'details': false_negatives
    }

if __name__ == '__main__':
    json_path = '/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_gen_20260107_025618/gen_batch_evaluation_results.json'
    check_false_negatives(json_path)
