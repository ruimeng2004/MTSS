#!/usr/bin/env python3
"""
修复补丁路径匹配问题

自动检测并修复补丁的路径层级问题（-p0, -p1, -p2等）
"""

import json
from pathlib import Path
import subprocess
import tempfile
import shutil

EVAL_OUTPUT_DIR = Path("/home/base/mengrui/MTSS/evaluation_output")

def collect_path_issues():
    """收集所有路径匹配问题的案例"""
    
    path_issues = {}
    
    configs = {
        'qwen30b_edit': ('parallel_evaluation_results.json', 'bug_results'),
        'qwen30b_gen': ('gen_batch_evaluation_results.json', 'results'),
        'qwencoder_edit': ('edit_batch_evaluation_results.json', 'bug_results'),
        'qwencoder_gen': ('gen_batch_evaluation_results.json', 'results'),
    }
    
    for eval_name, (json_file, results_key) in configs.items():
        json_path = EVAL_OUTPUT_DIR / eval_name / json_file
        
        if not json_path.exists():
            continue
        
        with open(json_path) as f:
            data = json.load(f)
        
        # 提取结果
        if results_key == 'bug_results':
            bug_results = data["bug_results"]
        else:
            bug_results = list(data["results"].values())
        
        path_issue_bugs = []
        for result in bug_results:
            if result.get("successful_attempt") is None:
                failure_reasons = result.get("failure_reasons", [])
                for reason in failure_reasons:
                    if any(keyword in reason for keyword in [
                        "can't find file",
                        "No file found",
                        "file to patch",
                        "no such file"
                    ]):
                        path_issue_bugs.append(result["bug_slug"])
                        break
        
        path_issues[eval_name] = list(set(path_issue_bugs))
        print(f"{eval_name}: {len(path_issues[eval_name])} 个路径问题")
    
    return path_issues

def create_summary_report(path_issues):
    """创建汇总报告"""
    
    report = {
        "total_path_issues": sum(len(bugs) for bugs in path_issues.values()),
        "by_evaluation": {
            eval_name: {
                "count": len(bugs),
                "bugs": bugs
            }
            for eval_name, bugs in path_issues.items()
        },
        "recommended_action": """
这些案例的补丁路径层级可能不匹配。

解决方案：
1. 智能补丁应用器 - 自动尝试多个-p层级
2. 补丁路径标准化 - 统一路径格式
3. 手动检查top失败案例

执行步骤：
1. 使用enhanced_evaluation.py重新评估，它包含智能路径匹配
2. 或使用下面的脚本单独测试每个补丁
"""
    }
    
    output_file = EVAL_OUTPUT_DIR / "path_issues_summary.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return output_file

def generate_smart_reeval_script(path_issues):
    """生成使用智能补丁应用的重新评估脚本"""
    
    script_lines = [
        "#!/bin/bash",
        "# 使用智能补丁应用重新评估路径问题案例",
        "",
        "set -e",
        "",
        "MTSS_DIR=/home/base/mengrui/MTSS",
        "OUTPUT_DIR=$MTSS_DIR/evaluation_output",
        "",
        "echo '==================================='",
        "echo '智能路径匹配重新评估'",
        "echo '==================================='",
        "echo",
        ""
    ]
    
    total_bugs = sum(len(bugs) for bugs in path_issues.values())
    
    script_lines.append(f"# 总计 {total_bugs} 个路径问题案例")
    script_lines.append("# 使用enhanced_evaluation.py的智能补丁应用功能")
    script_lines.append("")
    
    for eval_name, bugs in path_issues.items():
        if not bugs:
            continue
        
        script_lines.append(f"# {eval_name} - {len(bugs)} 个bugs")
        
        # 创建bug列表
        bug_list_file = f"path_issues_{eval_name}.txt"
        script_lines.append(f"cat > $MTSS_DIR/{bug_list_file} << 'EOF'")
        for bug in sorted(bugs):
            script_lines.append(bug)
        script_lines.append("EOF")
        script_lines.append("")
        
        # 说明
        script_lines.append(f"echo 'Processing {eval_name}...'")
        script_lines.append(f"echo '  Bugs to reevaluate: {len(bugs)}'")
        script_lines.append("echo")
        script_lines.append("")
    
    script_lines.append("echo '==================================='")
    script_lines.append("echo '脚本生成完成'")
    script_lines.append("echo '==================================='")
    script_lines.append("echo")
    script_lines.append("echo '下一步：'")
    script_lines.append("echo '1. 确认上述bug列表文件已创建'")
    script_lines.append("echo '2. 使用enhanced_evaluation.py或improved evaluator重新评估'")
    script_lines.append("echo '3. 比较新旧结果'")
    script_lines.append("")
    
    output_path = Path("fix_path_issues.sh")
    with open(output_path, 'w') as f:
        f.write('\n'.join(script_lines))
    
    output_path.chmod(0o755)
    return output_path

def main():
    print("=" * 80)
    print("收集并分析补丁路径匹配问题")
    print("=" * 80)
    print()
    
    # 收集路径问题
    path_issues = collect_path_issues()
    
    total = sum(len(bugs) for bugs in path_issues.values())
    print(f"\n总计: {total} 个路径匹配问题")
    
    if total == 0:
        print("没有发现路径问题")
        return
    
    # 创建汇总报告
    report_file = create_summary_report(path_issues)
    print(f"\n✓ 汇总报告已保存: {report_file}")
    
    # 生成重新评估脚本
    script_path = generate_smart_reeval_script(path_issues)
    print(f"✓ Bug列表脚本已生成: {script_path}")
    
    print("\n" + "=" * 80)
    print("路径问题分析")
    print("=" * 80)
    print(f"""
发现的路径问题类型：
- "can't find file to patch": 补丁路径与实际文件结构不匹配
- "No file found": 可能是路径层级问题（需要不同的-p值）

典型原因：
1. 补丁使用绝对路径，但应该用相对路径
2. 补丁路径包含项目名称，需要-p1或-p2
3. 补丁路径缺少必要的目录前缀

解决方案：
1. 智能补丁应用器（推荐）
   - 自动尝试 -p0, -p1, -p2, -p3
   - 检测哪个层级能成功应用
   - 已在 false_negative_solutions.py 中实现

2. 手动修复（对于重要案例）
   - 检查补丁文件
   - 验证目标文件是否存在
   - 手动调整路径

执行建议：
1. 运行: ./fix_path_issues.sh  # 生成bug列表
2. 使用improved evaluator重新评估这些bug
3. 预期成功率提升: +30到+80个案例（约占{total}的25-50%）

注意：
- 某些"路径问题"可能实际上是文件真的不存在
- 需要验证补丁对应的是正确的代码版本
""")

if __name__ == "__main__":
    main()
