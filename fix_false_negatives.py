#!/usr/bin/env python3
"""
修复假阴性问题的实用工具
提供自动化解决方案来处理常见的假阴性原因
"""

import json
import os
import subprocess
from pathlib import Path
import shutil
import re

class FalseNegativeFixer:
    """假阴性修复器"""
    
    def __init__(self, eval_output_dir="/home/base/mengrui/MTSS/evaluation_output"):
        self.eval_output_dir = Path(eval_output_dir)
        self.fixes_applied = []
        
    def fix_patch_application_issues(self, bug_slug, patch_file, work_dir):
        """
        修复补丁应用问题
        尝试不同的-p参数和策略
        """
        if not os.path.exists(patch_file):
            return False, f"Patch file not found: {patch_file}"
        
        # 读取补丁内容
        with open(patch_file, 'r') as f:
            patch_content = f.read()
        
        # 检查空补丁
        if not patch_content.strip() or 'diff' not in patch_content:
            return False, "Patch content is empty or invalid"
        
        # 尝试不同的-p参数 (0-4)
        for p_level in range(5):
            try:
                result = subprocess.run(
                    ['git', 'apply', f'-p{p_level}', '--check', patch_file],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # 应用成功，实际执行
                    apply_result = subprocess.run(
                        ['git', 'apply', f'-p{p_level}', patch_file],
                        cwd=work_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if apply_result.returncode == 0:
                        return True, f"Patch applied successfully with -p{p_level}"
                        
            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                continue
        
        # 尝试使用patch命令
        for p_level in range(5):
            try:
                result = subprocess.run(
                    ['patch', f'-p{p_level}', '--dry-run', '-i', patch_file],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    apply_result = subprocess.run(
                        ['patch', f'-p{p_level}', '-i', patch_file],
                        cwd=work_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if apply_result.returncode == 0:
                        return True, f"Patch applied with patch command -p{p_level}"
                        
            except Exception as e:
                continue
        
        return False, "All patch application strategies failed"
    
    def fix_checkout_issues(self, bug_slug, work_dir):
        """
        修复checkout问题
        清理工作目录并重试
        """
        try:
            # 清理工作目录
            if os.path.exists(work_dir):
                # 尝试git clean
                subprocess.run(
                    ['git', 'clean', '-fdx'],
                    cwd=work_dir,
                    capture_output=True,
                    timeout=60
                )
                
                # 尝试git reset
                subprocess.run(
                    ['git', 'reset', '--hard', 'HEAD'],
                    cwd=work_dir,
                    capture_output=True,
                    timeout=60
                )
                
                return True, "Checkout directory cleaned"
            
            return False, "Work directory does not exist"
            
        except Exception as e:
            return False, f"Checkout cleanup failed: {e}"
    
    def normalize_patch_paths(self, patch_file):
        """
        标准化补丁路径
        修复常见的路径问题
        """
        try:
            with open(patch_file, 'r') as f:
                content = f.read()
            
            # 备份原文件
            backup_file = f"{patch_file}.backup"
            shutil.copy2(patch_file, backup_file)
            
            # 修复常见路径问题
            # 1. 移除多余的目录前缀
            content = re.sub(r'^\+\+\+ [ab]/(\w+/)+', '--- a/', content, flags=re.MULTILINE)
            content = re.sub(r'^--- [ab]/(\w+/)+', '+++ b/', content, flags=re.MULTILINE)
            
            # 2. 确保路径一致性
            lines = content.split('\n')
            normalized_lines = []
            
            for line in lines:
                # 标准化diff头部
                if line.startswith('diff --git'):
                    # 提取文件路径
                    match = re.search(r'diff --git a/(.*) b/(.*)', line)
                    if match:
                        path = match.group(1)
                        normalized_lines.append(f'diff --git a/{path} b/{path}')
                        continue
                
                normalized_lines.append(line)
            
            normalized_content = '\n'.join(normalized_lines)
            
            # 写回文件
            with open(patch_file, 'w') as f:
                f.write(normalized_content)
            
            return True, "Patch paths normalized"
            
        except Exception as e:
            # 恢复备份
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, patch_file)
            return False, f"Path normalization failed: {e}"
    
    def generate_fix_report(self, model_dirs):
        """
        生成修复报告
        """
        report = []
        report.append("=" * 80)
        report.append("假阴性修复报告 - False Negative Fix Report")
        report.append("=" * 80)
        report.append("")
        
        for model_name in model_dirs:
            model_dir = self.eval_output_dir / model_name
            
            if not model_dir.exists():
                continue
            
            report.append(f"\n模型: {model_name}")
            report.append("-" * 80)
            
            # 检查bug_results目录
            bug_results_dir = model_dir / "bug_results"
            if bug_results_dir.exists():
                failed_bugs = []
                
                for bug_dir in bug_results_dir.iterdir():
                    if bug_dir.is_dir():
                        # 检查是否有失败标记
                        result_file = bug_dir / "result.json"
                        if result_file.exists():
                            try:
                                with open(result_file) as f:
                                    result_data = json.load(f)
                                    
                                if not result_data.get('success', False):
                                    failed_bugs.append({
                                        'slug': bug_dir.name,
                                        'reason': result_data.get('failure_reason', 'Unknown')
                                    })
                            except Exception:
                                pass
                
                report.append(f"\n失败的bugs: {len(failed_bugs)}")
                
                # 分类失败原因
                patch_failures = [b for b in failed_bugs if 'patch' in b['reason'].lower() or 'apply' in b['reason'].lower()]
                checkout_failures = [b for b in failed_bugs if 'checkout' in b['reason'].lower()]
                
                report.append(f"  - 补丁应用失败: {len(patch_failures)}")
                report.append(f"  - Checkout失败: {len(checkout_failures)}")
                report.append(f"  - 其他失败: {len(failed_bugs) - len(patch_failures) - len(checkout_failures)}")
        
        return "\n".join(report)

def create_automated_fix_script():
    """
    创建自动化修复脚本
    """
    script_content = """#!/usr/bin/env python3
\"\"\"
自动化修复假阴性的评估脚本
针对已识别的假阴性问题进行重新评估
\"\"\"

import sys
import json
from pathlib import Path

def reevaluate_failed_bugs(json_file, output_dir):
    \"\"\"重新评估失败的bugs\"\"\"
    
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
    
    print(f"\\n重新评估列表已保存到: {output_file}")
    
    return reevaluation_list

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python auto_fix.py <evaluation_results.json>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = Path(json_file).parent
    
    reevaluate_failed_bugs(json_file, output_dir)
"""
    
    script_path = "/home/base/mengrui/MTSS/auto_fix_false_negatives.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"自动化修复脚本已创建: {script_path}")

def main():
    print("假阴性修复工具")
    print("=" * 80)
    
    fixer = FalseNegativeFixer()
    
    # 生成修复报告
    model_dirs = ['qwen30b_edit', 'qwen30b_gen', 'qwencoder_edit', 'qwencoder_gen']
    report = fixer.generate_fix_report(model_dirs)
    print(report)
    
    # 创建自动化修复脚本
    print("\n\n正在创建自动化修复脚本...")
    create_automated_fix_script()
    
    print("\n\n【后续步骤】")
    print("1. 使用 auto_fix_false_negatives.py 提取需要重新评估的bugs")
    print("2. 针对补丁应用失败的bugs，尝试不同的-p参数")
    print("3. 针对checkout失败的bugs，清理工作目录后重试")
    print("4. 更新评估脚本以包含自动重试逻辑")

if __name__ == "__main__":
    main()
