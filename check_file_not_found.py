#!/usr/bin/env python3
"""
深入分析 File Not Found 错误
"""
import json
from pathlib import Path

def check_file_not_found(result_file, input_dir):
    with open(result_file, 'r') as f:
        data = json.load(f)
    
    file_not_found_cases = []
    
    for bug_slug, result in data['results'].items():
        if result['successful_attempt'] is None and result['failure_reasons']:
            first_reason = result['failure_reasons'][0]
            if "can't find file" in first_reason.lower():
                bug_dir = Path(input_dir) / bug_slug
                
                # 检查是否有result.json
                has_results = []
                for i in range(1, 11):
                    result_json = bug_dir / str(i) / 'result.json'
                    if result_json.exists():
                        with open(result_json, 'r') as rf:
                            try:
                                content = json.load(rf)
                                has_results.append({
                                    'attempt': i,
                                    'content': content
                                })
                            except:
                                pass
                
                file_not_found_cases.append({
                    'bug_slug': bug_slug,
                    'failure_reason': first_reason,
                    'has_results': len(has_results),
                    'results': has_results[:2]  # 只保留前2个
                })
    
    print(f"File Not Found 案例分析")
    print(f"=" * 80)
    print(f"总数: {len(file_not_found_cases)}")
    print(f"\n前10个案例详情:")
    print("=" * 80)
    
    for i, case in enumerate(file_not_found_cases[:10], 1):
        print(f"\n{i}. {case['bug_slug']}")
        print(f"   有result.json: {case['has_results']}个")
        print(f"   失败原因: {case['failure_reason'][:100]}...")
        
        if case['results']:
            print(f"   第1个result.json内容:")
            result = case['results'][0]['content']
            if 'fixed_code' in result:
                print(f"     - 有fixed_code字段")
            if 'patch' in result:
                patch_preview = str(result['patch'])[:200]
                print(f"     - patch: {patch_preview}...")

if __name__ == '__main__':
    result_file = '/home/base/mengrui/MTSS/evaluation_output/qwen30b_gen_20260214/gen_batch_evaluation_results.json'
    input_dir = '/home/base/mengrui/MTSS/ppl/result/20260106_030425'
    check_file_not_found(result_file, input_dir)
