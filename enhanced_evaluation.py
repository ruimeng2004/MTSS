#!/usr/bin/env python3
'''
增强版评估脚本 - Enhanced Evaluation Script
自动处理假阴性问题 (修复补丁应用并运行测试)
'''

import sys
import json
import argparse
import subprocess
from pathlib import Path

# 导入改进的评估器
from false_negative_solutions import ImprovedEvaluator

def run_d4j_test(work_dir, timeout=300):
    """运行Defects4J测试"""
    try:
        # 运行测试
        cmd = ['defects4j', 'test']
        print(f"    Running defects4j test in {work_dir}...")
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # 检查是否 failing tests
        if result.returncode == 0:
            # 检查输出中是否有 failing tests
            output = result.stdout
            if "Failing tests: 0" in output:
                return True, "Tests passed"
            else:
                # 提取失败数量
                lines = output.split('\n')
                for line in lines:
                    if "Failing tests:" in line:
                        return False, f"Tests failed: {line.strip()}"
                return False, "Tests failed (unknown count)"
        else:
            return False, f"Test execution failed (return code {result.returncode})"
            
    except subprocess.TimeoutExpired:
        return False, "Test execution timed out"
    except Exception as e:
        return False, f"Test execution error: {str(e)}"

def reevaluate_with_fixes(bug_list, output_dir):
    '''重新评估带修复的bugs'''
    
    evaluator = ImprovedEvaluator()
    results = []
    
    total = len(bug_list)
    print(f"Starting re-evaluation of {total} bugs...")
    
    for idx, bug_slug in enumerate(bug_list):
        print(f"\n[{idx+1}/{total}] Re-evaluating {bug_slug}...")
        
        # 1. 清理并checkout
        success, msg = evaluator.clean_and_checkout(bug_slug)
        if not success:
            print(f"  ✗ Checkout failed: {msg}")
            results.append({'bug': bug_slug, 'status': 'checkout_failed', 'reasons': [msg]})
            continue
        
        print(f"  ✓ Checkout: {msg}")
        
        # 2. 查找补丁文件
        patch_dir = Path(output_dir) / 'patches'
        patch_candidates = sorted(list(patch_dir.glob(f"{bug_slug}_attempt_*.patch")))
        
        # 如果找不到 attempt 格式的，尝试找直接命名的
        if not patch_candidates:
            direct_patch = patch_dir / f"{bug_slug}.patch"
            if direct_patch.exists():
                patch_candidates = [direct_patch]
        
        if not patch_candidates:
            print(f"  ✗ Patch not found for {bug_slug}")
            results.append({'bug': bug_slug, 'status': 'patch_not_found', 'reasons': ['No patch files found']})
            continue
            
        # 只尝试第一个补丁 (Attempt 1)
        patch_file = patch_candidates[0]
        print(f"  -> Using patch: {patch_file.name}")
        
        # 3. 验证补丁
        valid, msg = evaluator.validate_patch(patch_file)
        if not valid:
            print(f"  ✗ Patch invalid: {msg}")
            results.append({'bug': bug_slug, 'status': 'invalid_patch', 'reasons': [msg]})
            continue
        
        # 4. 标准化补丁
        evaluator.normalize_patch_format(patch_file)
        
        # 5. 智能应用补丁
        work_dir = evaluator.work_dir / bug_slug
        success, msg = evaluator.smart_patch_apply(patch_file, work_dir)
        
        if success:
            print(f"  ✓ Patch applied: {msg}")
            
            # 6. 运行测试
            test_success, test_msg = run_d4j_test(work_dir)
            
            if test_success:
                print(f"  ✓ {test_msg}")
                results.append({'bug': bug_slug, 'status': 'success', 'successful_attempt': 'retry', 'method': msg})
            else:
                print(f"  ✗ {test_msg}")
                results.append({'bug': bug_slug, 'status': 'test_failed', 'reasons': [test_msg], 'patch_method': msg})
                
        else:
            print(f"  ✗ Patch failed: {msg}")
            results.append({'bug': bug_slug, 'status': 'patch_failed', 'reasons': [msg]})
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Re-evaluate false negative bugs.')
    parser.add_argument('list_file', help='Path to reevaluation_list.json')
    
    args = parser.parse_args()
    
    list_file_path = Path(args.list_file)
    if not list_file_path.exists():
        print(f"Error: File not found: {list_file_path}")
        sys.exit(1)
        
    output_dir = list_file_path.parent
    
    print(f"Loading bugs from {list_file_path}")
    with open(list_file_path, 'r') as f:
        data = json.load(f)
        
    # 合并所有需要重测的 bug
    bugs_to_test = set()
    if 'bug_list' in data:
        # 如果是 comprehensive_false_negative_fix.py 生成的
        bugs_to_test.update(data['bug_list'])
    elif isinstance(data, dict):
        # 如果是 auto_fix_false_negatives.py 生成的 (patch_failures, checkout_failures)
        for key, val in data.items():
            if isinstance(val, list):
                bugs_to_test.update(val)
    
    bug_list = sorted(list(bugs_to_test))
    print(f"Found {len(bug_list)} unique bugs to re-evaluate.")
    
    if not bug_list:
        print("No bugs to re-evaluate.")
        sys.exit(0)
        
    results = reevaluate_with_fixes(bug_list, output_dir)
    
    # 统计结果
    success_count = sum(1 for r in results if r.get('status') == 'success')
    print(f"\nRe-evaluation Complete.")
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(results) - success_count}")
    
    # 保存结果
    output_file = output_dir / 'rerun_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
