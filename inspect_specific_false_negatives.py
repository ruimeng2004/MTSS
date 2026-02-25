#!/usr/bin/env python3
"""
深入检查具体的假阴性案例
"""

import json
from pathlib import Path

EVAL_OUTPUT_DIR = Path("/home/base/mengrui/MTSS/evaluation_output")

def inspect_patch_apply_failures():
    """检查补丁应用失败的具体案例"""
    
    print("=" * 80)
    print("深入检查: 补丁应用失败案例")
    print("=" * 80)
    
    # 检查 qwen30b_gen 的一个失败案例
    gen_path = EVAL_OUTPUT_DIR / "qwen30b_gen" / "gen_batch_evaluation_results.json"
    with open(gen_path) as f:
        gen_data = json.load(f)
    
    # 找一个补丁应用失败的案例
    failed_cases = []
    for bug_slug, result in gen_data["results"].items():
        if result["successful_attempt"] is None:
            failure_reasons = result.get("failure_reasons", [])
            for reason in failure_reasons:
                if "Patch content is empty" in reason:
                    failed_cases.append({
                        "bug": bug_slug,
                        "reason": reason,
                        "attempts": result["total_attempts"]
                    })
                    if len(failed_cases) >= 5:
                        break
        if len(failed_cases) >= 5:
            break
    
    print("\n示例: 空补丁内容失败案例")
    for i, case in enumerate(failed_cases, 1):
        print(f"\n{i}. Bug: {case['bug']}")
        print(f"   尝试次数: {case['attempts']}")
        print(f"   失败原因: {case['reason']}")
        
        # 检查补丁文件
        patch_dir = EVAL_OUTPUT_DIR / "qwen30b_gen" / "patches" / case['bug']
        if patch_dir.exists():
            patches = list(patch_dir.glob("*.patch"))
            print(f"   补丁文件数: {len(patches)}")
            if patches:
                # 读取第一个补丁查看内容
                with open(patches[0]) as f:
                    content = f.read()
                    print(f"   补丁大小: {len(content)} bytes")
                    if len(content) < 200:
                        print(f"   补丁内容预览:\n{content[:200]}")
    
    # 检查路径匹配问题
    print("\n" + "=" * 80)
    print("检查: 文件路径匹配问题")
    print("=" * 80)
    
    edit_path = EVAL_OUTPUT_DIR / "qwencoder_edit" / "edit_batch_evaluation_results.json"
    with open(edit_path) as f:
        edit_data = json.load(f)
    
    path_issues = []
    for result in edit_data["bug_results"]:
        if result["successful_attempt"] is None:
            failure_reasons = result.get("failure_reasons", [])
            for reason in failure_reasons:
                if "can't find file to patch" in reason or "No file found" in reason:
                    path_issues.append({
                        "bug": result["bug_slug"],
                        "reason": reason
                    })
                    if len(path_issues) >= 5:
                        break
        if len(path_issues) >= 5:
            break
    
    print("\n示例: 文件路径匹配失败案例")
    for i, case in enumerate(path_issues, 1):
        print(f"\n{i}. Bug: {case['bug']}")
        print(f"   失败原因: {case['reason'][:150]}")
        
        # 检查补丁文件
        patch_dir = EVAL_OUTPUT_DIR / "qwencoder_edit" / "patches" / case['bug']
        if patch_dir.exists():
            patches = list(patch_dir.glob("*.patch"))
            if patches:
                print(f"   补丁文件: {patches[0].name}")
                with open(patches[0]) as f:
                    lines = f.readlines()
                    # 显示补丁的文件路径行
                    for line in lines[:10]:
                        if line.startswith('---') or line.startswith('+++'):
                            print(f"   {line.rstrip()}")
    
    # 检查checkout失败
    print("\n" + "=" * 80)
    print("检查: Checkout失败案例")
    print("=" * 80)
    
    checkout_failures = []
    for result in edit_data["bug_results"]:
        if result["successful_attempt"] is None:
            failure_reasons = result.get("failure_reasons", [])
            for reason in failure_reasons:
                if "Checkout failed" in reason and "Directory not empty" in reason:
                    checkout_failures.append({
                        "bug": result["bug_slug"],
                        "reason": reason
                    })
                    if len(checkout_failures) >= 10:
                        break
        if len(checkout_failures) >= 10:
            break
    
    print(f"\n发现 {len(checkout_failures)} 个checkout失败案例")
    print("这些案例的补丁可能是正确的，但由于环境问题导致无法验证")
    print("\nCheckout失败的bug列表:")
    for case in checkout_failures:
        print(f"  • {case['bug']}")

def check_patch_files_exist():
    """检查补丁文件是否存在"""
    print("\n" + "=" * 80)
    print("检查补丁文件存在性")
    print("=" * 80)
    
    for eval_name in ["qwen30b_edit", "qwen30b_gen", "qwencoder_edit", "qwencoder_gen"]:
        patch_dir = EVAL_OUTPUT_DIR / eval_name / "patches"
        if patch_dir.exists():
            bug_dirs = [d for d in patch_dir.iterdir() if d.is_dir()]
            total_patches = sum(len(list(d.glob("*.patch"))) for d in bug_dirs)
            print(f"\n{eval_name}:")
            print(f"  Bug目录数: {len(bug_dirs)}")
            print(f"  补丁文件总数: {total_patches}")
        else:
            print(f"\n{eval_name}: 补丁目录不存在")

if __name__ == "__main__":
    inspect_patch_apply_failures()
    check_patch_files_exist()
    
    print("\n" + "=" * 80)
    print("💡 建议的假阴性修复策略")
    print("=" * 80)
    print("""
基于以上分析，假阴性主要来自以下几类：

1. **补丁内容为空** (最多，约3283+2910=6193个案例)
   - 问题：模型生成的补丁为空或格式不正确
   - 这可能不是假阴性，而是模型真的没生成有效补丁
   - 需要检查：是模型输出问题还是补丁提取逻辑问题
   
2. **文件路径不匹配** (约86+59=145个案例)
   - 问题：补丁路径层级与实际文件结构不匹配
   - 这是典型的假阴性！补丁逻辑可能正确
   - 解决：运行 auto_fix_false_negatives.py 自动修复
   
3. **Checkout失败** (约255个案例)
   - 问题：环境冲突，目录未清理
   - 这是假阴性！补丁可能完全正确
   - 解决：重新评估这些案例，确保环境干净
   
4. **其他规范化失败** (约1151个案例)
   - 问题："No SEARCH blocks found"等
   - 可能是edit模式的特定问题
   - 需要检查edit模式的补丁格式要求

推荐执行顺序：
1. 先修复checkout失败（重新评估）- 潜在成功率最高
2. 修复路径匹配问题 - 使用现有工具
3. 分析"空补丁"问题的根源 - 确定是否为真失败
4. 检查规范化失败的具体原因
""")

