#!/usr/bin/env python3
"""
重新评估Checkout失败的案例

这些案例的补丁很可能是正确的，只是因为环境问题（目录冲突）导致无法验证
重新评估时确保环境干净
"""

import json
from pathlib import Path
import subprocess
import sys
import shutil

EVAL_OUTPUT_DIR = Path("/home/base/mengrui/MTSS/evaluation_output")

def collect_checkout_failures():
    """收集所有checkout失败的案例"""
    
    all_checkout_failures = {}
    
    configs = {
        'qwen30b_edit': 'parallel_evaluation_results.json',
        'qwencoder_edit': 'edit_batch_evaluation_results.json',
    }
    
    for eval_name, json_file in configs.items():
        json_path = EVAL_OUTPUT_DIR / eval_name / json_file
        
        if not json_path.exists():
            print(f"⚠️  {json_path} 不存在")
            continue
        
        with open(json_path) as f:
            data = json.load(f)
        
        # 提取bug_results
        if "bug_results" in data:
            bug_results = data["bug_results"]
        else:
            continue
        
        checkout_failures = []
        for result in bug_results:
            if result.get("successful_attempt") is None:
                failure_reasons = result.get("failure_reasons", [])
                for reason in failure_reasons:
                    if "Checkout failed" in reason:
                        checkout_failures.append(result["bug_slug"])
                        break
        
        all_checkout_failures[eval_name] = list(set(checkout_failures))
        print(f"{eval_name}: {len(all_checkout_failures[eval_name])} 个checkout失败")
    
    return all_checkout_failures

def generate_reevaluation_script(checkout_failures, output_file="reevaluate_checkout.sh"):
    """生成重新评估的shell脚本"""
    
    script_lines = [
        "#!/bin/bash",
        "# 重新评估checkout失败的案例",
        "# 自动生成于: comprehensive_false_negative_fix.py",
        "",
        "set -e",
        "",
        "MTSS_DIR=/home/base/mengrui/MTSS",
        "OUTPUT_DIR=$MTSS_DIR/evaluation_output",
        "",
        "echo '==================================='",
        "echo '重新评估Checkout失败案例'",
        "echo '==================================='",
        "echo",
        ""
    ]
    
    for eval_name, bugs in checkout_failures.items():
        if not bugs:
            continue
        
        script_lines.append(f"# {eval_name} - {len(bugs)} 个bugs")
        script_lines.append(f"echo 'Processing {eval_name}...'")
        script_lines.append("")
        
        # 根据eval_name确定原始批次目录
        if eval_name == 'qwen30b_edit':
            batch_dir = "ppl/result/20260106_113852"  # 需要从JSON中提取
        elif eval_name == 'qwencoder_edit':
            batch_dir = "ppl/result/20260106_113852"
        else:
            continue
        
        # 创建bug列表文件
        bug_list_file = f"checkout_failures_{eval_name}.txt"
        script_lines.append(f"cat > $MTSS_DIR/{bug_list_file} << 'EOF'")
        for bug in bugs:
            script_lines.append(bug)
        script_lines.append("EOF")
        script_lines.append("")
        
        # 生成重新评估命令
        output_subdir = f"{eval_name}_checkout_fixed"
        script_lines.append(f"# 重新评估 {eval_name}")
        script_lines.append(f"python $MTSS_DIR/evaluate.py \\")
        script_lines.append(f"  --input-batch {batch_dir} \\")
        script_lines.append(f"  --output-dir $OUTPUT_DIR/{output_subdir} \\")
        script_lines.append(f"  --bug-list $MTSS_DIR/{bug_list_file} \\")
        script_lines.append(f"  --num-workers 32 \\")
        script_lines.append(f"  --force-clean")
        script_lines.append("")
        script_lines.append(f"echo '✓ {eval_name} 完成'")
        script_lines.append("echo")
        script_lines.append("")
    
    script_lines.append("echo 'All reevaluations complete!'")
    
    # 写入脚本文件
    output_path = Path(output_file)
    with open(output_path, 'w') as f:
        f.write('\n'.join(script_lines))
    
    # 添加执行权限
    output_path.chmod(0o755)
    
    return output_path

def main():
    print("=" * 80)
    print("收集Checkout失败案例并生成重新评估脚本")
    print("=" * 80)
    print()
    
    # 收集失败案例
    checkout_failures = collect_checkout_failures()
    
    total = sum(len(bugs) for bugs in checkout_failures.values())
    print(f"\n总计: {total} 个checkout失败案例")
    
    if total == 0:
        print("没有需要重新评估的案例")
        return
    
    # 生成重新评估脚本
    script_path = generate_reevaluation_script(checkout_failures)
    
    print(f"\n✓ 重新评估脚本已生成: {script_path}")
    print("\n执行方式:")
    print(f"  ./{script_path}")
    print("\n或分步执行:")
    print(f"  cat {script_path}")
    
    print("\n" + "=" * 80)
    print("重要说明")
    print("=" * 80)
    print("""
1. 执行前确保：
   - defects4j环境正常
   - 有足够的磁盘空间
   - 清理旧的临时目录

2. 预期结果：
   - 255个checkout失败案例将被重新评估
   - 保守估计：50-150个可能成功修复
   - 乐观估计：可能更高，取决于原始补丁质量

3. 时间估计：
   - 使用32个worker并行评估
   - 预计1-3小时完成

4. 注意事项：
   - 如果再次出现checkout失败，可能是：
     a) defects4j环境问题
     b) 网络问题（某些项目需要下载依赖）
     c) 权限问题
   - 可以进一步减少并发数来避免目录冲突
""")

if __name__ == "__main__":
    main()
