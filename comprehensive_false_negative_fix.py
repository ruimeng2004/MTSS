#!/usr/bin/env python3
"""
假阴性综合解决方案

基于分析结果，提供针对性的假阴性修复方案
"""

import json
from pathlib import Path
from collections import defaultdict
import subprocess
import sys

EVAL_OUTPUT_DIR = Path("/home/base/mengrui/MTSS/evaluation_output")

class FalseNegativeFixer:
    """假阴性修复器"""
    
    def __init__(self, eval_dir_name, json_filename):
        self.eval_dir = EVAL_OUTPUT_DIR / eval_dir_name
        self.json_path = self.eval_dir / json_filename
        self.eval_name = eval_dir_name
        
        # 加载评估结果
        with open(self.json_path) as f:
            self.data = json.load(f)
    
    def extract_failed_cases(self):
        """提取失败案例并分类"""
        
        # 根据JSON结构提取结果
        if "bug_results" in self.data:
            bug_results = self.data["bug_results"]
        elif "results" in self.data:
            bug_results = list(self.data["results"].values())
        else:
            return {}
        
        categorized = {
            'checkout_failures': [],
            'patch_path_issues': [],
            'empty_patches': [],
            'normalization_errors': [],
            'timeout_issues': [],
            'other': []
        }
        
        for result in bug_results:
            if result.get("successful_attempt") is not None:
                continue
            
            bug_slug = result.get("bug_slug")
            failure_reasons = result.get("failure_reasons", [])
            
            for reason in failure_reasons:
                reason_lower = reason.lower()
                
                # 分类
                if "checkout failed" in reason_lower:
                    categorized['checkout_failures'].append(bug_slug)
                elif "can't find file" in reason_lower or "no file found" in reason_lower:
                    categorized['patch_path_issues'].append(bug_slug)
                elif "patch content is empty" in reason_lower:
                    categorized['empty_patches'].append(bug_slug)
                elif "normalization failed" in reason_lower or "no search blocks" in reason_lower:
                    categorized['normalization_errors'].append(bug_slug)
                elif "timeout" in reason_lower:
                    categorized['timeout_issues'].append(bug_slug)
                else:
                    categorized['other'].append(bug_slug)
        
        # 去重
        for key in categorized:
            categorized[key] = list(set(categorized[key]))
        
        return categorized
    
    def generate_reevaluation_list(self, categories_to_fix):
        """生成需要重新评估的bug列表"""
        
        failed_cases = self.extract_failed_cases()
        
        bugs_to_reevaluate = []
        for category in categories_to_fix:
            bugs_to_reevaluate.extend(failed_cases.get(category, []))
        
        bugs_to_reevaluate = list(set(bugs_to_reevaluate))
        
        output = {
            'eval_source': self.eval_name,
            'total_bugs': len(bugs_to_reevaluate),
            'categories_fixed': categories_to_fix,
            'bug_list': sorted(bugs_to_reevaluate),
            'breakdown': {cat: len(failed_cases.get(cat, [])) for cat in categories_to_fix}
        }
        
        output_file = self.eval_dir / 'reevaluation_list.json'
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        return output, output_file

def main():
    """主函数"""
    
    print("=" * 80)
    print("假阴性综合修复方案")
    print("=" * 80)
    print()
    
    # 配置：每个评估目录的假阴性修复策略
    fix_configs = {
        'qwen30b_edit': {
            'json_file': 'parallel_evaluation_results.json',
            'priority_categories': ['checkout_failures', 'patch_path_issues'],
            'description': 'edit模式评估，主要修复checkout和路径问题'
        },
        'qwen30b_gen': {
            'json_file': 'gen_batch_evaluation_results.json',
            'priority_categories': ['checkout_failures', 'patch_path_issues'],
            'description': 'gen模式评估，空补丁较多，优先修复环境问题'
        },
        'qwencoder_edit': {
            'json_file': 'edit_batch_evaluation_results.json',
            'priority_categories': ['checkout_failures', 'patch_path_issues', 'normalization_errors'],
            'description': 'qwencoder edit模式，修复checkout、路径和规范化问题'
        },
        'qwencoder_gen': {
            'json_file': 'gen_batch_evaluation_results.json',
            'priority_categories': ['checkout_failures', 'patch_path_issues'],
            'description': 'qwencoder gen模式，空补丁较多，优先修复环境问题'
        }
    }
    
    all_results = {}
    
    for eval_name, config in fix_configs.items():
        print(f"\n{'='*80}")
        print(f"处理: {eval_name}")
        print(f"说明: {config['description']}")
        print(f"{'='*80}")
        
        try:
            fixer = FalseNegativeFixer(eval_name, config['json_file'])
            
            # 分析失败案例
            failed_cases = fixer.extract_failed_cases()
            
            print("\n失败案例分类:")
            for category, bugs in sorted(failed_cases.items(), key=lambda x: len(x[1]), reverse=True):
                if bugs:
                    print(f"  • {category}: {len(bugs)} 个")
            
            # 生成重新评估列表
            output, output_file = fixer.generate_reevaluation_list(config['priority_categories'])
            
            print(f"\n✓ 生成重新评估列表: {output_file}")
            print(f"  待重新评估的bugs: {output['total_bugs']} 个")
            print(f"  包含类别: {', '.join(config['priority_categories'])}")
            
            all_results[eval_name] = output
            
        except Exception as e:
            print(f"✗ 处理失败: {e}")
    
    # 汇总报告
    print("\n" + "=" * 80)
    print("汇总报告")
    print("=" * 80)
    
    total_bugs_to_fix = sum(r['total_bugs'] for r in all_results.values())
    print(f"\n总计需要重新评估的bugs: {total_bugs_to_fix} 个")
    
    for eval_name, result in all_results.items():
        print(f"\n{eval_name}:")
        print(f"  数量: {result['total_bugs']}")
        for cat, count in result['breakdown'].items():
            print(f"    - {cat}: {count}")
    
    # 执行建议
    print("\n" + "=" * 80)
    print("执行建议")
    print("=" * 80)
    print("""
下一步行动：

1. 【最高优先级】修复 Checkout 失败（255个案例）
   这些案例的补丁很可能是正确的，只是环境问题导致无法验证
   
   执行命令：
   python reevaluate_checkout_failures.py
   
   预期提升: +50到+150个成功案例

2. 【高优先级】修复补丁路径匹配问题（145个案例）
   使用智能路径匹配，自动尝试 -p0, -p1, -p2
   
   执行命令：
   python fix_patch_path_issues.py
   
   预期提升: +30到+80个成功案例

3. 【中优先级】分析规范化错误（部分可修复）
   检查"No SEARCH blocks"等错误的根本原因
   
   执行命令：
   python analyze_normalization_errors.py
   
   预期提升: +10到+50个成功案例

4. 【低优先级】空补丁问题（6193个案例）
   需要检查是模型问题还是提取逻辑问题
   如果是提取问题，修复后可能大幅提升
   
   执行命令：
   python analyze_empty_patches.py

总预期成功率提升:
- 保守估计: +5% 到 +10%
- 乐观估计: +10% 到 +20%
- 如果空补丁问题是提取bug: 可能 +30% 以上

建议先执行1和2，这两项风险最低，收益最确定。
""")

if __name__ == "__main__":
    main()
