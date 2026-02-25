#!/usr/bin/env python3
"""Analyze specific interesting cases in detail."""

import json
from pathlib import Path
from typing import Dict


def load_patch(slug: str) -> Dict:
    """Load patch for a specific bug."""
    path = Path("bug_task_model_selection/data/artifacts/patches.jsonl")
    
    if path.exists():
        with open(path, 'r') as f:
            for line in f:
                obj = json.loads(line)
                if obj['slug'] == slug:
                    return obj
    
    return {}


def load_ppl_data(slug: str) -> Dict:
    """Load PPL data for a specific bug."""
    result = {}
    
    for model in ['qwen3_coder', 'qwen3_30b']:
        result[model] = {}
        for task in ['edit', 'gen']:
            path = Path(f"bug_task_model_selection/data/ppl/{model}_{task}.jsonl")
            if path.exists():
                with open(path, 'r') as f:
                    for line in f:
                        obj = json.loads(line)
                        if obj['slug'] == slug:
                            result[model][f'{task}_ppl'] = obj['value']
    
    return result


def analyze_case(slug: str):
    """Analyze a specific case in detail."""
    print("\n" + "=" * 100)
    print(f"案例分析: {slug}")
    print("=" * 100)
    
    # Load patch
    patch_data = load_patch(slug)
    if not patch_data:
        print(f"未找到 {slug} 的 patch 数据")
        return
    
    # Load PPL
    ppl_data = load_ppl_data(slug)
    
    # Print metadata
    print("\n## 基本信息\n")
    if 'metadata' in patch_data:
        meta = patch_data['metadata']
        print(f"**项目**: {meta.get('project', 'N/A')}")
        print(f"**Bug ID**: {meta.get('bug_id', 'N/A')}")
        print(f"**文件**: {meta.get('file_path', 'N/A')}")
        print(f"**修改**: +{meta.get('additions', 0)} -{meta.get('deletions', 0)}")
    
    # Print PPL comparison
    print("\n## PPL 对比\n")
    print("| 模型 | Edit PPL | Gen PPL | Gap | 偏好 |")
    print("|------|----------|---------|-----|------|")
    
    for model in ['qwen3_coder', 'qwen3_30b']:
        if model in ppl_data:
            edit_ppl = ppl_data[model].get('edit_ppl', 0)
            gen_ppl = ppl_data[model].get('gen_ppl', 0)
            if edit_ppl > 0 and gen_ppl > 0:
                gap = abs(edit_ppl - gen_ppl) / min(edit_ppl, gen_ppl) * 100
                preferred = 'edit' if edit_ppl < gen_ppl else 'gen'
                print(f"| {model} | {edit_ppl:.2e} | {gen_ppl:.2e} | {gap:.2f}% | {preferred} |")
    
    # Print patch
    print("\n## Patch 内容\n")
    if 'text' in patch_data:
        patch_text = patch_data['text']
        
        # Extract the actual code changes
        lines = patch_text.split('\n')
        
        # Find the actual diff part (skip headers)
        diff_start = 0
        for i, line in enumerate(lines):
            if line.startswith('@@'):
                diff_start = i
                break
        
        print("```diff")
        for line in lines[diff_start:]:
            print(line)
        print("```")
    
    # Analyze the change
    print("\n## 变更分析\n")
    
    if 'text' in patch_data:
        patch_text = patch_data['text']
        lines = patch_text.split('\n')
        
        added = [l for l in lines if l.startswith('+') and not l.startswith('+++')]
        removed = [l for l in lines if l.startswith('-') and not l.startswith('---')]
        
        print(f"**变更类型**:")
        
        # Analyze change type
        if len(added) == 1 and len(removed) == 1:
            print("- 单行替换")
            print(f"\n**删除**: `{removed[0][1:].strip()}`")
            print(f"**添加**: `{added[0][1:].strip()}`")
            
            # Check for specific patterns
            removed_text = removed[0][1:].strip()
            added_text = added[0][1:].strip()
            
            if '!=' in removed_text and '==' in added_text:
                print("\n**模式**: 条件反转 (!= → ==)")
            elif '==' in removed_text and '!=' in added_text:
                print("\n**模式**: 条件反转 (== → !=)")
            elif 'true' in removed_text.lower() and 'false' in added_text.lower():
                print("\n**模式**: 布尔值反转 (true → false)")
            elif 'false' in removed_text.lower() and 'true' in added_text.lower():
                print("\n**模式**: 布尔值反转 (false → true)")
            elif removed_text.replace(' ', '') == added_text.replace(' ', ''):
                print("\n**模式**: 仅空格/格式变更")
            else:
                # Check for operator changes
                ops = ['<', '>', '<=', '>=', '==', '!=', '+', '-', '*', '/']
                removed_ops = [op for op in ops if op in removed_text]
                added_ops = [op for op in ops if op in added_text]
                if removed_ops != added_ops:
                    print(f"\n**模式**: 运算符变更 ({removed_ops} → {added_ops})")
        
        elif len(added) == 0 and len(removed) > 0:
            print("- 纯删除")
            print(f"- 删除了 {len(removed)} 行")
        
        elif len(removed) == 0 and len(added) > 0:
            print("- 纯添加")
            print(f"- 添加了 {len(added)} 行")
        
        else:
            print(f"- 复杂变更: +{len(added)} -{len(removed)}")
        
        # Check for common bug patterns
        print(f"\n**Bug 模式检测**:")
        
        all_lines = ' '.join(added + removed).lower()
        
        patterns = []
        if 'null' in all_lines:
            patterns.append("空指针相关")
        if 'index' in all_lines or 'length' in all_lines or 'size' in all_lines:
            patterns.append("索引/边界相关")
        if '==' in all_lines or '!=' in all_lines:
            patterns.append("相等性判断")
        if 'if' in all_lines:
            patterns.append("条件逻辑")
        if 'return' in all_lines:
            patterns.append("返回值")
        if 'throw' in all_lines or 'exception' in all_lines:
            patterns.append("异常处理")
        
        if patterns:
            for p in patterns:
                print(f"- {p}")
        else:
            print("- 未检测到常见模式")


def main():
    """Main analysis function."""
    print("=" * 100)
    print("特定案例深度分析")
    print("=" * 100)
    
    # Analyze the most interesting cases
    cases = [
        'Jsoup_5',
        'Math_52', 
        'Lang_53',
        'Jsoup_41',
        'Cli_13'
    ]
    
    for slug in cases:
        analyze_case(slug)
    
    print("\n" + "=" * 100)
    print("分析完成")
    print("=" * 100)


if __name__ == "__main__":
    main()
