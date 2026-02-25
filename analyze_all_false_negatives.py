#!/usr/bin/env python3
"""
分析所有评估输出目录中的假阴性（False Negatives）

假阴性定义：
1. 模型生成的补丁实际上是正确的，但被评估为失败
2. 常见原因：
   - 补丁路径匹配问题（-p0/-p1等strip层级）
   - 补丁格式问题（缺少必要的上下文行）
   - 文件编码问题
   - checkout失败但补丁本身正确
   - 评估脚本的bug
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# 评估输出目录
EVAL_OUTPUT_DIR = Path("/home/base/mengrui/MTSS/evaluation_output")

# 4个主要评估目录
EVAL_DIRS = {
    "qwen30b_edit": "parallel_evaluation_results.json",
    "qwen30b_gen": "gen_batch_evaluation_results.json",
    "qwencoder_edit": "edit_batch_evaluation_results.json",
    "qwencoder_gen": "gen_batch_evaluation_results.json"
}

def load_json_results(json_path):
    """加载JSON结果文件"""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载失败 {json_path}: {e}")
        return None

def analyze_failure_reasons(data, eval_name):
    """分析失败原因，识别可能的假阴性"""
    
    # 根据不同的JSON结构提取结果
    if "bug_results" in data:
        # qwen30b_edit 格式
        bug_results = data["bug_results"]
    elif "results" in data:
        # gen 格式
        bug_results = list(data["results"].values())
    else:
        print(f"⚠️  未知的JSON格式: {eval_name}")
        return {}
    
    # 假阴性类别统计
    false_negative_categories = defaultdict(list)
    
    # 分析每个失败的bug
    for result in bug_results:
        bug_slug = result.get("bug_slug")
        successful_attempt = result.get("successful_attempt")
        failure_reasons = result.get("failure_reasons", [])
        
        # 只关注失败的案例
        if successful_attempt is not None:
            continue
            
        # 分类失败原因
        for reason in failure_reasons:
            reason_lower = reason.lower()
            
            # 1. Checkout失败 - 可能是环境问题，补丁本身可能正确
            if "checkout failed" in reason_lower or "directory not empty" in reason_lower:
                false_negative_categories["checkout_failure"].append({
                    "bug": bug_slug,
                    "reason": reason
                })
            
            # 2. 补丁应用失败 - 最可能的假阴性来源
            elif "patch" in reason_lower and "failed" in reason_lower:
                false_negative_categories["patch_apply_failure"].append({
                    "bug": bug_slug,
                    "reason": reason
                })
            
            # 3. 文件未找到 - 可能是路径匹配问题
            elif "file not found" in reason_lower or "no such file" in reason_lower:
                false_negative_categories["file_not_found"].append({
                    "bug": bug_slug,
                    "reason": reason
                })
            
            # 4. 补丁格式问题
            elif "corrupt" in reason_lower or "malformed" in reason_lower:
                false_negative_categories["patch_format_issue"].append({
                    "bug": bug_slug,
                    "reason": reason
                })
            
            # 5. 测试超时 - 可能补丁正确但测试慢
            elif "timeout" in reason_lower:
                false_negative_categories["timeout"].append({
                    "bug": bug_slug,
                    "reason": reason
                })
            
            # 6. 编译错误 - 可能是补丁格式问题而非逻辑问题
            elif "compile" in reason_lower or "compilation" in reason_lower:
                false_negative_categories["compilation_error"].append({
                    "bug": bug_slug,
                    "reason": reason
                })
            
            # 7. 其他失败
            else:
                false_negative_categories["other"].append({
                    "bug": bug_slug,
                    "reason": reason
                })
    
    return false_negative_categories

def print_analysis_report():
    """打印全面的假阴性分析报告"""
    
    print("=" * 80)
    print("假阴性分析报告 - 所有评估输出目录")
    print("=" * 80)
    print()
    
    all_results = {}
    
    for eval_name, json_file in EVAL_DIRS.items():
        json_path = EVAL_OUTPUT_DIR / eval_name / json_file
        
        print(f"\n📂 分析: {eval_name}")
        print(f"   文件: {json_path}")
        print("-" * 80)
        
        if not json_path.exists():
            print(f"   ⚠️  文件不存在")
            continue
        
        data = load_json_results(json_path)
        if not data:
            continue
        
        # 提取统计信息
        if "statistics" in data:
            stats = data["statistics"]
        else:
            stats = {
                "total_bugs": data.get("total_bugs", 0),
                "fixed_bugs": data.get("fixed_bugs", 0),
                "failed_bugs": data.get("failed_bugs", 0),
                "success_rate": data.get("success_rate", 0)
            }
        
        print(f"   总Bug数: {stats.get('total_bugs', 0)}")
        print(f"   成功修复: {stats.get('fixed_bugs', 0)}")
        print(f"   失败数量: {stats.get('failed_bugs', 0)}")
        print(f"   成功率: {stats.get('success_rate', 0):.2%}")
        print()
        
        # 分析假阴性
        false_negatives = analyze_failure_reasons(data, eval_name)
        all_results[eval_name] = false_negatives
        
        # 打印假阴性分类
        if false_negatives:
            print("   🔍 潜在假阴性分类:")
            for category, cases in sorted(false_negatives.items(), key=lambda x: len(x[1]), reverse=True):
                if cases:
                    print(f"\n   [{category.upper()}] - {len(cases)} 个案例")
                    # 显示前3个示例
                    for case in cases[:3]:
                        print(f"      • {case['bug']}: {case['reason'][:80]}...")
                    if len(cases) > 3:
                        print(f"      ... 还有 {len(cases) - 3} 个案例")
        else:
            print("   ✅ 未发现明显的假阴性模式")
    
    # 汇总统计
    print("\n" + "=" * 80)
    print("📊 假阴性汇总统计")
    print("=" * 80)
    
    category_totals = defaultdict(int)
    for eval_name, false_negatives in all_results.items():
        for category, cases in false_negatives.items():
            category_totals[category] += len(cases)
    
    if category_totals:
        print("\n跨所有评估的假阴性类别分布:")
        for category, count in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {category.upper()}: {count} 个案例")
    
    # 解决方案建议
    print("\n" + "=" * 80)
    print("💡 假阴性解决方案")
    print("=" * 80)
    print("""
1. Checkout失败 (Directory not empty)
   - 原因：并发评估时目录冲突，或清理不完全
   - 解决：
     * 确保每个bug有独立的工作目录
     * 评估前彻底清理旧目录
     * 使用更好的目录隔离机制
     * 重新评估这些案例

2. 补丁应用失败 (Patch apply failure)
   - 原因：补丁路径层级不匹配（-p0 vs -p1）
   - 解决：
     * 自动检测并尝试多个-p层级 (p0, p1, p2)
     * 标准化补丁生成格式
     * 使用智能路径匹配算法
     * 参考: auto_fix_false_negatives.py

3. 文件未找到 (File not found)
   - 原因：补丁中的文件路径与实际路径不匹配
   - 解决：
     * 检查补丁路径是否包含项目根目录
     * 验证文件确实存在于checkout的版本中
     * 使用模糊匹配定位正确文件

4. 超时 (Timeout)
   - 原因：测试执行时间过长，可能补丁正确但测试慢
   - 解决：
     * 增加超时时间
     * 优化测试执行
     * 手动验证超时案例的补丁正确性

5. 编译错误 (Compilation error)
   - 原因：补丁格式导致语法错误，或缺少依赖
   - 解决：
     * 验证生成的代码语法正确性
     * 确保补丁完整性（没有截断）
     * 检查缩进和格式

6. 补丁格式问题 (Malformed patch)
   - 原因：补丁缺少必要的上下文行或格式不正确
   - 解决：
     * 使用标准diff格式
     * 确保足够的上下文行（通常3行）
     * 验证补丁完整性

推荐行动:
1. 运行 auto_fix_false_negatives.py 修复路径匹配问题
2. 运行 reevaluate_qwen3coder.py 重新评估修复的案例
3. 对checkout失败的案例单独重新评估
4. 手动检查top失败案例，确定是否为真阳性
""")

if __name__ == "__main__":
    print_analysis_report()
