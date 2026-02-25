#!/usr/bin/env python3
"""
详细的修复情况对比分析报告
"""
import pandas as pd
import json

analysis_dir = "/home/base/APR/D4C/analysis/result"
json_file = f"{analysis_dir}/03_case_fix_results.json"

# 读取 JSON 数据
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 生成详细报告
report = []
report.append("=" * 100)
report.append("修复情况详细对比分析报告")
report.append("=" * 100)
report.append("")

# 摘要统计
summary = data['summary']
report.append("【整体统计】")
report.append(f"分析的 Case 总数: {summary['total_cases']}")
report.append("")
report.append(f"GEN 方法:")
report.append(f"  - 总 Case 数: {summary['gen']['total']}")
report.append(f"  - 修复成功数: {summary['gen']['fixed']}")
report.append(f"  - 修复率: {summary['gen']['fix_rate']:.2f}%")
report.append("")
report.append(f"SR 方法:")
report.append(f"  - 总 Case 数: {summary['sr']['total']}")
report.append(f"  - 修复成功数: {summary['sr']['fixed']}")
report.append(f"  - 修复率: {summary['sr']['fix_rate']:.2f}%")
report.append("")

# 修复分布分析
both_fixed = []
only_gen_fixed = []
only_sr_fixed = []
neither_fixed = []

for case, info in data['cases'].items():
    if info['gen']['fixed'] and info['sr']['fixed']:
        both_fixed.append(case)
    elif info['gen']['fixed'] and not info['sr']['fixed']:
        only_gen_fixed.append(case)
    elif not info['gen']['fixed'] and info['sr']['fixed']:
        only_sr_fixed.append(case)
    else:
        neither_fixed.append(case)

report.append("【修复分布】")
report.append(f"1. 两个方法都修复成功: {len(both_fixed)} ({len(both_fixed)/summary['total_cases']*100:.1f}%)")
report.append(f"   {', '.join(both_fixed[:10])}{'...' if len(both_fixed) > 10 else ''}")
report.append("")

report.append(f"2. 仅 GEN 修复成功: {len(only_gen_fixed)} ({len(only_gen_fixed)/summary['total_cases']*100:.1f}%)")
if only_gen_fixed:
    report.append(f"   {', '.join(only_gen_fixed)}")
report.append("")

report.append(f"3. 仅 SR 修复成功: {len(only_sr_fixed)} ({len(only_sr_fixed)/summary['total_cases']*100:.1f}%)")
if only_sr_fixed:
    report.append(f"   {', '.join(only_sr_fixed)}")
report.append("")

report.append(f"4. 都未修复: {len(neither_fixed)} ({len(neither_fixed)/summary['total_cases']*100:.1f}%)")
report.append("")

# 难度分析
report.append("【难度分析 - 按修复难度分级】")
report.append("")

# 高难度（都未修复）
high_difficulty = sorted(
    [(case, info['total_diff']) for case, info in data['cases'].items() if case in neither_fixed],
    key=lambda x: x[1],
    reverse=True
)
report.append(f"高难度（都未修复，共{len(high_difficulty)}个，按总差值降序）:")
for i, (case, diff) in enumerate(high_difficulty[:10], 1):
    report.append(f"  {i}. {case:<30} 总差值: {diff:.6f}")
if len(high_difficulty) > 10:
    report.append(f"  ... 还有 {len(high_difficulty)-10} 个")
report.append("")

# 中等难度（仅一个方法修复）
medium_difficulty = []
for case in only_gen_fixed:
    diff = data['cases'][case]['total_diff']
    medium_difficulty.append((case, 'GEN', diff))
for case in only_sr_fixed:
    diff = data['cases'][case]['total_diff']
    medium_difficulty.append((case, 'SR', diff))
medium_difficulty.sort(key=lambda x: x[2], reverse=True)

report.append(f"中等难度（仅一个方法修复，共{len(medium_difficulty)}个）:")
for i, (case, method, diff) in enumerate(medium_difficulty, 1):
    report.append(f"  {i}. {case:<30} {method:3} 修复 | 总差值: {diff:.6f}")
report.append("")

# 低难度（都修复了）
low_difficulty = sorted(
    [(case, info['total_diff']) for case, info in data['cases'].items() if case in both_fixed],
    key=lambda x: x[1],
    reverse=True
)
report.append(f"低难度（都修复成功，共{len(low_difficulty)}个，按总差值降序）:")
for i, (case, diff) in enumerate(low_difficulty[:10], 1):
    report.append(f"  {i}. {case:<30} 总差值: {diff:.6f}")
if len(low_difficulty) > 10:
    report.append(f"  ... 还有 {len(low_difficulty)-10} 个")
report.append("")

# 方法对比分析
report.append("【方法对比分析】")
report.append("")
report.append(f"GEN 方法更优: {len(only_gen_fixed)} 个 Case")
report.append(f"SR 方法更优: {len(only_sr_fixed)} 个 Case")
report.append(f"方法性能差: {abs(len(only_gen_fixed) - len(only_sr_fixed))} 个 Case")
report.append("")

# 生成报告文件
report_file = f"{analysis_dir}/04_fix_analysis_report.txt"
with open(report_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('\n'.join(report))
print(f"\n\n报告已保存到: {report_file}")
