#!/usr/bin/env python3
"""
假阴性解决方案 - 改进版评估器
包含自动修复和重试机制
"""

import json
import os
import subprocess
import shutil
from pathlib import Path
import time
import re

class ImprovedEvaluator:
    """改进的评估器，处理假阴性问题"""
    
    def __init__(self, work_dir="/tmp/eval_work"):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(exist_ok=True)
        
    def smart_patch_apply(self, patch_file, target_dir, max_attempts=5):
        """
        智能补丁应用
        自动尝试不同的策略
        """
        strategies = [
            # 策略1: git apply with different -p levels
            *[('git', f'-p{i}') for i in range(5)],
            # 策略2: patch command with different -p levels
            *[('patch', f'-p{i}') for i in range(5)],
        ]
        
        for strategy_type, p_level in strategies:
            try:
                if strategy_type == 'git':
                    # 先检查
                    check_cmd = ['git', 'apply', p_level, '--check', str(patch_file)]
                    check_result = subprocess.run(
                        check_cmd,
                        cwd=target_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if check_result.returncode == 0:
                        # 实际应用
                        apply_cmd = ['git', 'apply', p_level, str(patch_file)]
                        apply_result = subprocess.run(
                            apply_cmd,
                            cwd=target_dir,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if apply_result.returncode == 0:
                            return True, f"Success with git apply {p_level}"
                
                elif strategy_type == 'patch':
                    # 使用patch命令
                    dry_run_cmd = ['patch', p_level, '--dry-run', '-i', str(patch_file)]
                    dry_result = subprocess.run(
                        dry_run_cmd,
                        cwd=target_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if dry_result.returncode == 0:
                        apply_cmd = ['patch', p_level, '-i', str(patch_file)]
                        apply_result = subprocess.run(
                            apply_cmd,
                            cwd=target_dir,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if apply_result.returncode == 0:
                            return True, f"Success with patch {p_level}"
                        
            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                continue
        
        return False, "All patch strategies failed"
    
    def clean_and_checkout(self, bug_slug, max_retries=3):
        """
        清理并checkout，带重试机制
        """
        for attempt in range(max_retries):
            try:
                # 运行defects4j checkout
                cmd = ['defects4j', 'checkout', '-p', bug_slug.split('_')[0], 
                       '-v', bug_slug.split('_')[1] + 'b', '-w', str(self.work_dir / bug_slug)]
                
                # 如果目录存在，先清理
                bug_dir = self.work_dir / bug_slug
                if bug_dir.exists():
                    shutil.rmtree(bug_dir, ignore_errors=True)
                    time.sleep(1)  # 等待文件系统同步
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                if result.returncode == 0:
                    return True, "Checkout successful"
                
                # 如果失败，等待后重试
                time.sleep(2 ** attempt)  # 指数退避
                
            except subprocess.TimeoutExpired:
                return False, "Checkout timeout"
            except Exception as e:
                if attempt == max_retries - 1:
                    return False, f"Checkout failed: {e}"
        
        return False, "Checkout failed after all retries"
    
    def validate_patch(self, patch_file):
        """
        验证补丁文件
        """
        if not os.path.exists(patch_file):
            return False, "Patch file not found"
        
        try:
            with open(patch_file, 'r') as f:
                content = f.read()
            
            # 检查空补丁
            if not content.strip():
                return False, "Patch is empty"
            
            # 检查是否包含diff标记
            if 'diff' not in content and '---' not in content and '+++' not in content:
                return False, "Invalid patch format"
            
            # 检查是否只有空行
            lines = [line for line in content.split('\n') if line.strip()]
            if not lines:
                return False, "Patch contains only whitespace"
            
            return True, "Patch is valid"
            
        except Exception as e:
            return False, f"Patch validation error: {e}"
    
    def normalize_patch_format(self, patch_file):
        """
        标准化补丁格式
        """
        try:
            with open(patch_file, 'r') as f:
                content = f.read()
            
            # 创建备份
            backup = f"{patch_file}.bak"
            shutil.copy2(patch_file, backup)
            
            # 修复常见问题
            lines = content.split('\n')
            normalized = []
            
            for line in lines:
                # 确保diff头部格式正确
                if line.startswith('diff --git'):
                    # 提取路径
                    match = re.search(r'diff --git a/(\S+) b/(\S+)', line)
                    if match:
                        path_a = match.group(1)
                        path_b = match.group(2)
                        # 确保路径一致
                        if path_a != path_b:
                            line = f'diff --git a/{path_a} b/{path_a}'
                
                normalized.append(line)
            
            # 写回
            with open(patch_file, 'w') as f:
                f.write('\n'.join(normalized))
            
            return True, "Patch normalized"
            
        except Exception as e:
            # 恢复备份
            if os.path.exists(backup):
                shutil.copy2(backup, patch_file)
            return False, f"Normalization failed: {e}"

def create_enhanced_evaluation_script():
    """
    创建增强版评估脚本
    """
    script = """#!/usr/bin/env python3
'''
增强版评估脚本
自动处理假阴性问题
'''

import sys
from pathlib import Path

# 导入改进的评估器
from false_negative_solutions import ImprovedEvaluator

def reevaluate_with_fixes(bug_list, output_dir):
    '''重新评估带修复的bugs'''
    
    evaluator = ImprovedEvaluator()
    results = []
    
    for bug_slug in bug_list:
        print(f"\\nRe-evaluating {bug_slug}...")
        
        # 1. 清理并checkout
        success, msg = evaluator.clean_and_checkout(bug_slug)
        if not success:
            print(f"  Checkout failed: {msg}")
            results.append({'bug': bug_slug, 'status': 'checkout_failed', 'reason': msg})
            continue
        
        print(f"  Checkout: {msg}")
        
        # 2. 查找补丁文件
        patch_file = Path(output_dir) / 'patches' / f"{bug_slug}.patch"
        if not patch_file.exists():
            print(f"  Patch not found: {patch_file}")
            results.append({'bug': bug_slug, 'status': 'patch_not_found'})
            continue
        
        # 3. 验证补丁
        valid, msg = evaluator.validate_patch(patch_file)
        if not valid:
            print(f"  Patch invalid: {msg}")
            results.append({'bug': bug_slug, 'status': 'invalid_patch', 'reason': msg})
            continue
        
        # 4. 标准化补丁
        evaluator.normalize_patch_format(patch_file)
        
        # 5. 智能应用补丁
        work_dir = evaluator.work_dir / bug_slug
        success, msg = evaluator.smart_patch_apply(patch_file, work_dir)
        
        if success:
            print(f"  Patch applied: {msg}")
            results.append({'bug': bug_slug, 'status': 'success', 'method': msg})
        else:
            print(f"  Patch failed: {msg}")
            results.append({'bug': bug_slug, 'status': 'patch_failed', 'reason': msg})
    
    return results

if __name__ == "__main__":
    # 示例用法
    print("增强版评估脚本")
    print("用法: python enhanced_eval.py <reevaluation_list.json>")
"""
    
    output_file = "/home/base/mengrui/MTSS/enhanced_evaluation.py"
    with open(output_file, 'w') as f:
        f.write(script)
    
    os.chmod(output_file, 0o755)
    return output_file

def main():
    print("=" * 80)
    print("假阴性解决方案")
    print("=" * 80)
    
    # 创建增强版评估脚本
    script_file = create_enhanced_evaluation_script()
    print(f"\n✓ 增强版评估脚本已创建: {script_file}")
    
    print("\n" + "=" * 80)
    print("关键改进点:")
    print("=" * 80)
    
    improvements = [
        ("1. 智能补丁应用", [
            "自动尝试 git apply -p0 到 -p4",
            "自动尝试 patch -p0 到 -p4",
            "支持多种补丁格式"
        ]),
        ("2. 自动重试机制", [
            "Checkout失败自动重试（指数退避）",
            "清理工作目录后重试",
            "超时保护"
        ]),
        ("3. 补丁验证", [
            "检查补丁文件存在性",
            "验证补丁格式",
            "检测空补丁"
        ]),
        ("4. 路径标准化", [
            "自动修复路径不一致",
            "标准化diff头部格式",
            "支持备份和回滚"
        ])
    ]
    
    for title, items in improvements:
        print(f"\n{title}:")
        for item in items:
            print(f"  • {item}")
    
    print("\n" + "=" * 80)
    print("使用步骤:")
    print("=" * 80)
    
    steps = [
        "1. 运行 auto_fix_false_negatives.py 提取失败的bugs",
        "   python auto_fix_false_negatives.py evaluation_output/qwencoder_edit/edit_batch_evaluation_results.json",
        "",
        "2. 查看生成的 reevaluation_list.json",
        "   cat evaluation_output/qwencoder_edit/reevaluation_list.json",
        "",
        "3. 使用增强版评估器重新评估补丁失败的bugs",
        "   python enhanced_evaluation.py evaluation_output/qwencoder_edit/reevaluation_list.json",
        "",
        "4. 对于checkout失败的bugs，先清理环境:",
        "   rm -rf /tmp/defects4j_*",
        "   然后重新运行评估"
    ]
    
    for step in steps:
        print(f"  {step}")
    
    print("\n" + "=" * 80)
    print("预期效果:")
    print("=" * 80)
    
    effects = [
        "• 补丁应用失败: 从 6338 次降低 60-80%",
        "• Checkout失败: 从 255 次降低 80-90%",
        "• 总体成功率提升: 预计从 51-58% 提升到 65-75%"
    ]
    
    for effect in effects:
        print(f"  {effect}")

if __name__ == "__main__":
    main()
