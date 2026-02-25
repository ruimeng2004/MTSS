#!/usr/bin/env python3
"""
自动化修复假阴性的评估脚本
针对已识别的假阴性问题进行重新评估
"""

import sys
import json
from pathlib import Path

def reevaluate_failed_bugs(json_file, output_dir):
    """重新评估失败的bugs"""
    
    # 读取评估结果
    with open(json_file) as f:
        data = json.load(f)
    
    # 提取失败的bugs
    failed_bugs = []
    
    if 'bug_results' in data:
        for bug in data['bug_results']:
            if bug.get('successful_attempt') is None:
                failed_bugs.append(bug)
    elif 'results' in data:
        for bug_slug, bug in data['results'].items():
            if bug.get('successful_attempt') is None:
                failed_bugs.append(bug)
    
    print(f"找到 {len(failed_bugs)} 个失败的bugs")
    
    # 分类失败原因
    patch_failures = []
    checkout_failures = []
    
    for bug in failed_bugs:
        reasons = bug.get('failure_reasons', [])
        
        has_patch_failure = any('patch' in r.lower() or 'apply' in r.lower() for r in reasons)
        has_checkout_failure = any('checkout' in r.lower() for r in reasons)
        
        if has_patch_failure:
            patch_failures.append(bug)
        elif has_checkout_failure:
            checkout_failures.append(bug)
    
    print(f"补丁应用失败: {len(patch_failures)}")
    print(f"Checkout失败: {len(checkout_failures)}")
    
    # 生成重新评估列表
    reevaluation_list = {
        'patch_failures': [b.get('bug_slug') for b in patch_failures],
        'checkout_failures': [b.get('bug_slug') for b in checkout_failures]
    }
    
    # 保存到文件
    output_file = Path(output_dir) / 'reevaluation_list.json'
    with open(output_file, 'w') as f:
        json.dump(reevaluation_list, f, indent=2)
    
    print(f"\n重新评估列表已保存到: {output_file}")
    
    return reevaluation_list

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python auto_fix.py <evaluation_results.json>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = Path(json_file).parent
    
    reevaluate_failed_bugs(json_file, output_dir)
