#!/usr/bin/env python3
"""
严格验证patch转换的正确性

验证方法：
1. 格式验证：检查行排序（- 在 + 之前）
2. 语义验证：对比原始D4J patch和反转后的patch
3. 实际应用验证：尝试在真实代码上应用patch（可选）
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


def parse_hunk_changes(patch_text: str) -> List[Dict]:
    """
    解析patch中的所有修改块（hunks）
    返回每个hunk的删除和添加内容
    """
    hunks = []
    lines = patch_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 找到hunk头（@@ ... @@）
        if line.startswith('@@'):
            hunk = {
                'header': line,
                'deletions': [],
                'additions': [],
                'context': []
            }
            
            i += 1
            # 收集这个hunk的所有行
            while i < len(lines):
                curr = lines[i]
                
                # 遇到下一个hunk或diff结束
                if curr.startswith('@@') or curr.startswith('diff') or curr.startswith('Index:'):
                    break
                
                if curr.startswith('-') and not curr.startswith('---'):
                    hunk['deletions'].append(curr[1:])  # 去掉-符号
                elif curr.startswith('+') and not curr.startswith('+++'):
                    hunk['additions'].append(curr[1:])  # 去掉+符号
                elif curr.startswith(' '):
                    hunk['context'].append(curr[1:])  # 去掉空格
                
                i += 1
            
            hunks.append(hunk)
        else:
            i += 1
    
    return hunks


def verify_patch_reversal(original_patch: str, reversed_patch: str) -> Tuple[bool, str]:
    """
    验证反转是否正确
    
    原始D4J patch (fixed → buggy):
      - 行 = fixed代码（正确的）
      + 行 = buggy代码（错误的）
    
    反转后 (buggy → fixed):
      - 行 = buggy代码（错误的）
      + 行 = fixed代码（正确的）
    
    验证逻辑：
      原始的 - 行 应该等于 反转后的 + 行
      原始的 + 行 应该等于 反转后的 - 行
    """
    original_hunks = parse_hunk_changes(original_patch)
    reversed_hunks = parse_hunk_changes(reversed_patch)
    
    if len(original_hunks) != len(reversed_hunks):
        return False, f"Hunk数量不匹配: 原始{len(original_hunks)} vs 反转{len(reversed_hunks)}"
    
    for i, (orig, rev) in enumerate(zip(original_hunks, reversed_hunks)):
        # 验证：原始的删除 = 反转的添加
        if orig['deletions'] != rev['additions']:
            return False, f"Hunk {i}: 原始删除行 != 反转添加行"
        
        # 验证：原始的添加 = 反转的删除
        if orig['additions'] != rev['deletions']:
            return False, f"Hunk {i}: 原始添加行 != 反转删除行"
        
        # 上下文应该相同
        if orig['context'] != rev['context']:
            return False, f"Hunk {i}: 上下文不匹配"
    
    return True, "验证通过"


def check_line_ordering(patch_text: str) -> Tuple[bool, List[str]]:
    """
    检查patch中的行排序是否正确
    
    在unified diff中，在同一个连续的修改块中，删除行（-）必须在添加行（+）之前。
    但是被上下文行分隔的修改块可以独立处理。
    """
    lines = patch_text.split('\n')
    issues = []
    
    i = 0
    in_hunk = False
    
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('@@'):
            in_hunk = True
            i += 1
            continue
        
        if in_hunk and (line.startswith('diff') or line.startswith('Index:')):
            in_hunk = False
        
        if in_hunk:
            # 检查连续的修改块（不被上下文行分隔）
            if line.startswith('+') and not line.startswith('+++'):
                # 找到添加行，收集连续的添加行
                j = i + 1
                while j < len(lines) and lines[j].startswith('+') and not lines[j].startswith('+++'):
                    j += 1
                
                # 检查紧接着的下一行（不是上下文行）是否是删除行
                if j < len(lines):
                    next_line = lines[j]
                    # 只有当下一行是删除行（不是上下文行）时才报错
                    if next_line.startswith('-') and not next_line.startswith('---'):
                        issues.append(f"行{i}: 发现连续的 + 行后紧跟 - 行（错误顺序）")
        
        i += 1
    
    return len(issues) == 0, issues


def load_original_d4j_patch(project: str, bug_id: int) -> str:
    """加载原始的D4J patch"""
    d4j_root = Path('/Users/eulerai/代码/lith/work/MTSS-main/d4j/defects4j')
    patch_file = d4j_root / 'framework' / 'projects' / project / 'patches' / f'{bug_id}.src.patch'
    
    if not patch_file.exists():
        return None
    
    with open(patch_file, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def main():
    print("=" * 80)
    print("Patch转换正确性验证")
    print("=" * 80)
    print()
    
    patches_file = Path('bug_task_model_selection/data/artifacts/patches.jsonl')
    
    # 统计
    total = 0
    format_ok = 0
    semantic_ok = 0
    both_ok = 0
    
    # 详细测试前10个patches
    print("详细验证前10个patches...")
    print()
    
    with open(patches_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= 10:  # 详细测试前10个
                break
            
            item = json.loads(line)
            slug = item['slug']
            reversed_patch = item['text']
            project = item['metadata']['project']
            bug_id = item['metadata']['bug_id']
            
            total += 1
            
            print(f"[{i+1}] {slug}")
            print("-" * 60)
            
            # 1. 格式验证
            format_valid, format_issues = check_line_ordering(reversed_patch)
            if format_valid:
                print("  ✓ 格式验证: 通过（行排序正确）")
                format_ok += 1
            else:
                print(f"  ✗ 格式验证: 失败")
                for issue in format_issues:
                    print(f"    - {issue}")
            
            # 2. 语义验证（对比原始patch）
            original_patch = load_original_d4j_patch(project, bug_id)
            if original_patch:
                # 只取源代码patch部分（不包括测试）
                orig_src = original_patch.split('\n\n')[0] if '\n\n' in original_patch else original_patch
                rev_src = reversed_patch.split('\n\n')[0] if '\n\n' in reversed_patch else reversed_patch
                
                semantic_valid, semantic_msg = verify_patch_reversal(orig_src, rev_src)
                if semantic_valid:
                    print(f"  ✓ 语义验证: {semantic_msg}")
                    semantic_ok += 1
                else:
                    print(f"  ✗ 语义验证: {semantic_msg}")
            else:
                print("  ⚠ 语义验证: 无法加载原始patch")
            
            if format_valid and semantic_valid:
                both_ok += 1
            
            print()
    
    # 快速检查剩余的patches
    print("快速检查剩余patches...")
    print()
    
    with open(patches_file, 'r') as f:
        for i, line in enumerate(f):
            if i < 10:  # 跳过已经详细测试的
                continue
            
            item = json.loads(line)
            reversed_patch = item['text']
            
            total += 1
            
            # 只做格式检查
            format_valid, _ = check_line_ordering(reversed_patch)
            if format_valid:
                format_ok += 1
    
    # 总结
    print("=" * 80)
    print("验证总结")
    print("=" * 80)
    print(f"总patches数: {total}")
    print(f"格式验证通过: {format_ok}/{total} ({format_ok/total*100:.1f}%)")
    print(f"语义验证通过: {semantic_ok}/10 (前10个)")
    print(f"完全正确: {both_ok}/10 (前10个)")
    print()
    
    if format_ok == total and semantic_ok == 10:
        print("✅ 所有验证通过！Patches转换正确。")
    else:
        print("⚠️ 发现问题，需要检查。")


if __name__ == '__main__':
    main()
