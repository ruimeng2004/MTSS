#!/usr/bin/env python3
"""
深度分析评测程序失误

识别哪些失败不是模型问题，而是评测程序的bug
"""

import json
from pathlib import Path
from collections import defaultdict
import re

EVAL_OUTPUT_DIR = Path("/home/base/mengrui/MTSS/evaluation_output")

def deep_analyze_failures():
    """深度分析所有失败原因"""
    
    configs = {
        'qwen30b_edit': ('parallel_evaluation_results.json', 'bug_results'),
        'qwen30b_gen': ('gen_batch_evaluation_results.json', 'results'),
        'qwencoder_edit': ('edit_batch_evaluation_results.json', 'bug_results'),
        'qwencoder_gen': ('gen_batch_evaluation_results.json', 'results'),
    }
    
    # 评测程序问题分类
    evaluator_issues = {
        'checkout_directory_conflict': [],  # 目录冲突
        'patch_path_detection_failed': [],  # 路径检测失败
        'patch_extraction_failed': [],      # 补丁提取失败
        'normalization_logic_error': [],    # 规范化逻辑错误
        'timeout_too_aggressive': [],       # 超时设置过于激进
        'file_encoding_issue': [],          # 文件编码问题
        'git_apply_not_tried_all': [],     # 未尝试所有-p层级
    }
    
    # 真实的模型失败
    model_failures = {
        'test_still_failing': [],           # 测试仍然失败
        'syntax_error': [],                 # 语法错误
        'wrong_logic': [],                  # 逻辑错误
    }
    
    all_failure_details = []
    
    for eval_name, (json_file, results_key) in configs.items():
        json_path = EVAL_OUTPUT_DIR / eval_name / json_file
        
        if not json_path.exists():
            continue
        
        print(f"\n{'='*80}")
        print(f"分析: {eval_name}")
        print(f"{'='*80}")
        
        with open(json_path) as f:
            data = json.load(f)
        
        if results_key == 'bug_results':
            bug_results = data["bug_results"]
        else:
            bug_results = list(data["results"].values())
        
        for result in bug_results:
            if result.get("successful_attempt") is not None:
                continue
            
            bug_slug = result["bug_slug"]
            failure_reasons = result.get("failure_reasons", [])
            
            for reason in failure_reasons:
                reason_lower = reason.lower()
                
                # 分类每个失败原因
                issue_type = None
                is_evaluator_issue = False
                
                # 1. Checkout目录冲突 - 明确的评测程序问题
                if "directory not empty" in reason_lower or ("checkout failed" in reason_lower and "timed out" in reason_lower):
                    issue_type = 'checkout_directory_conflict'
                    is_evaluator_issue = True
                
                # 2. 补丁路径检测失败 - 评测程序应该尝试多个-p层级
                elif "can't find file to patch" in reason_lower or "no file found" in reason_lower:
                    issue_type = 'patch_path_detection_failed'
                    is_evaluator_issue = True
                
                # 3. 空补丁 - 可能是提取逻辑问题
                elif "patch content is empty" in reason_lower:
                    issue_type = 'patch_extraction_failed'
                    is_evaluator_issue = True  # 需要进一步验证
                
                # 4. 规范化错误 - 评测程序的edit模式处理问题
                elif "normalization failed" in reason_lower or "no search blocks" in reason_lower:
                    issue_type = 'normalization_logic_error'
                    is_evaluator_issue = True
                
                # 5. 文件未找到 - 可能是路径问题
                elif "source file not found" in reason_lower:
                    issue_type = 'file_encoding_issue'
                    is_evaluator_issue = True
                
                # 6. 超时
                elif "timeout" in reason_lower:
                    issue_type = 'timeout_too_aggressive'
                    is_evaluator_issue = True  # 部分是
                
                # 真实的模型失败
                elif "test" in reason_lower and "fail" in reason_lower:
                    issue_type = 'test_still_failing'
                    is_evaluator_issue = False
                
                elif "syntax" in reason_lower or "compilation" in reason_lower:
                    issue_type = 'syntax_error'
                    is_evaluator_issue = False
                
                detail = {
                    'eval': eval_name,
                    'bug': bug_slug,
                    'reason': reason,
                    'type': issue_type or 'other',
                    'is_evaluator_issue': is_evaluator_issue
                }
                
                all_failure_details.append(detail)
                
                if is_evaluator_issue and issue_type:
                    evaluator_issues[issue_type].append(detail)
                elif issue_type in model_failures:
                    model_failures[issue_type].append(detail)
    
    return evaluator_issues, model_failures, all_failure_details

def print_evaluator_issues_report(evaluator_issues):
    """打印评测程序问题报告"""
    
    print("\n" + "=" * 80)
    print("评测程序问题报告")
    print("=" * 80)
    
    total_evaluator_issues = sum(len(cases) for cases in evaluator_issues.values())
    
    print(f"\n发现 {total_evaluator_issues} 个评测程序导致的假阴性")
    print("\n详细分类:\n")
    
    for issue_type, cases in sorted(evaluator_issues.items(), key=lambda x: len(x[1]), reverse=True):
        if not cases:
            continue
        
        print(f"{'='*80}")
        print(f"{issue_type.upper()}: {len(cases)} 个案例")
        print(f"{'='*80}")
        
        # 按评估类型分组
        by_eval = defaultdict(list)
        for case in cases:
            by_eval[case['eval']].append(case)
        
        for eval_name, eval_cases in by_eval.items():
            print(f"\n  {eval_name}: {len(eval_cases)} 个")
            # 显示前3个示例
            for case in eval_cases[:3]:
                print(f"    • {case['bug']}")
                print(f"      原因: {case['reason'][:100]}...")
            if len(eval_cases) > 3:
                print(f"    ... 还有 {len(eval_cases)-3} 个")

def generate_fixes(evaluator_issues):
    """生成针对每种评测问题的修复方案"""
    
    fixes = {}
    
    # 1. Checkout目录冲突
    if evaluator_issues['checkout_directory_conflict']:
        fixes['checkout_fix'] = {
            'issue': 'Checkout目录冲突',
            'count': len(evaluator_issues['checkout_directory_conflict']),
            'fix_type': '强制清理 + 独立工作目录',
            'code_file': 'fix_checkout_conflicts.py',
            'description': '确保每次checkout前完全清理目录，使用UUID隔离不同bug的工作目录'
        }
    
    # 2. 补丁路径检测
    if evaluator_issues['patch_path_detection_failed']:
        fixes['patch_path_fix'] = {
            'issue': '补丁路径检测失败',
            'count': len(evaluator_issues['patch_path_detection_failed']),
            'fix_type': '智能多层级尝试',
            'code_file': 'fix_smart_patch_apply.py',
            'description': '自动尝试-p0到-p4，选择第一个成功的层级'
        }
    
    # 3. 补丁提取
    if evaluator_issues['patch_extraction_failed']:
        fixes['patch_extraction_fix'] = {
            'issue': '补丁提取失败（空内容）',
            'count': len(evaluator_issues['patch_extraction_failed']),
            'fix_type': '改进补丁提取逻辑',
            'code_file': 'fix_patch_extraction.py',
            'description': '检查模型输出解析逻辑，支持多种补丁格式'
        }
    
    # 4. 规范化错误
    if evaluator_issues['normalization_logic_error']:
        fixes['normalization_fix'] = {
            'issue': '规范化逻辑错误',
            'count': len(evaluator_issues['normalization_logic_error']),
            'fix_type': '改进edit模式处理',
            'code_file': 'fix_normalization.py',
            'description': '更宽松的SEARCH block检测，支持更多格式'
        }
    
    return fixes

def main():
    print("=" * 80)
    print("深度分析评测程序失误")
    print("=" * 80)
    
    evaluator_issues, model_failures, all_details = deep_analyze_failures()
    
    # 打印报告
    print_evaluator_issues_report(evaluator_issues)
    
    # 统计
    total_eval_issues = sum(len(cases) for cases in evaluator_issues.values())
    total_model_issues = sum(len(cases) for cases in model_failures.values())
    
    print("\n" + "=" * 80)
    print("总体统计")
    print("=" * 80)
    print(f"\n评测程序导致的假阴性: {total_eval_issues} 个")
    print(f"真实的模型失败: {total_model_issues} 个")
    print(f"假阴性占比: {total_eval_issues/(total_eval_issues+total_model_issues)*100:.1f}%")
    
    # 生成修复方案
    print("\n" + "=" * 80)
    print("修复方案")
    print("=" * 80)
    
    fixes = generate_fixes(evaluator_issues)
    
    for fix_name, fix_info in fixes.items():
        print(f"\n【{fix_info['issue']}】")
        print(f"  影响案例: {fix_info['count']} 个")
        print(f"  修复方法: {fix_info['fix_type']}")
        print(f"  实现文件: {fix_info['code_file']}")
        print(f"  说明: {fix_info['description']}")
    
    # 保存详细报告
    report = {
        'total_evaluator_issues': total_eval_issues,
        'total_model_failures': total_model_issues,
        'evaluator_issues_breakdown': {
            k: len(v) for k, v in evaluator_issues.items()
        },
        'fixes_needed': fixes,
        'detailed_cases': all_details[:100]  # 保存前100个详细案例
    }
    
    report_file = EVAL_OUTPUT_DIR / 'evaluator_issues_analysis.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ 详细报告已保存: {report_file}")
    
    print("\n" + "=" * 80)
    print("优先级建议")
    print("=" * 80)
    print("""
基于影响范围，修复优先级：

1. 【P0 - 最高优先级】补丁提取失败 (约6193个案例)
   如果这是评测程序的bug，修复后可能有巨大提升
   需要检查：模型是否真的生成了补丁，但被错误地判断为空
   
2. 【P1 - 高优先级】补丁路径检测 (456个案例)
   修复相对简单，效果明确
   实现智能多层级尝试即可
   
3. 【P2 - 中优先级】规范化逻辑 (约240个案例)
   需要深入理解edit模式的格式要求
   可能需要调整规范化逻辑
   
4. 【P3 - 中优先级】Checkout冲突 (255个案例)
   改进目录隔离和清理逻辑
   
建议行动：
1. 首先深入检查"空补丁"问题 - 查看原始模型输出
2. 实现并测试智能补丁应用器
3. 改进checkout隔离机制
4. 分析规范化错误的具体模式
""")

if __name__ == "__main__":
    main()
