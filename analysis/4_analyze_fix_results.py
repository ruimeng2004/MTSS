#!/usr/bin/env python3
"""
分析两个任务建模方法(GEN和SR)的修复情况
"""
import pandas as pd
import json
from pathlib import Path

# 读取两个结果文件
gen_file = "/home/data/result_from_135/sen/GEN10/eval_full_1shot_deepseek-chat_10try_temp=1.0.csv"
sr_file = "/home/data/result_from_135/sen/SR10/eval_full_1shot_deepseek-chat_10try_temp=1.0.csv"

print("读取 GEN 数据...")
gen_df = pd.read_csv(gen_file)
print(f"GEN 数据行数: {len(gen_df)}")

print("读取 SR 数据...")
sr_df = pd.read_csv(sr_file)
print(f"SR 数据行数: {len(sr_df)}")

# 分析GEN修复情况
print("\n分析 GEN 修复情况...")
gen_fixed = {}
for _, row in gen_df.iterrows():
    slug = row['slug']
    # reward=True 表示成功修复
    is_fixed = row['reward'] is True or row['reward'] == 'True' or str(row['reward']).lower() == 'true'
    
    if slug not in gen_fixed:
        gen_fixed[slug] = {'fixed': False, 'attempts': 0}
    
    gen_fixed[slug]['attempts'] += 1
    if is_fixed:
        gen_fixed[slug]['fixed'] = True

# 分析SR修复情况  
print("分析 SR 修复情况...")
sr_fixed = {}
for _, row in sr_df.iterrows():
    slug = row['slug']
    # reward=True 表示成功修复（处理字符串类型）
    is_fixed = row['reward'] is True or row['reward'] == 'True' or str(row['reward']).lower() == 'true'
    
    if slug not in sr_fixed:
        sr_fixed[slug] = {'fixed': False, 'attempts': 0}
    
    sr_fixed[slug]['attempts'] += 1
    if is_fixed:
        sr_fixed[slug]['fixed'] = True

# 统计信息
print("\n统计信息:")
print(f"GEN 总 Case 数: {len(gen_fixed)}")
print(f"GEN 修复成功数: {sum(1 for v in gen_fixed.values() if v['fixed'])}")
print(f"GEN 修复率: {sum(1 for v in gen_fixed.values() if v['fixed']) / len(gen_fixed) * 100:.2f}%")

print(f"\nSR 总 Case 数: {len(sr_fixed)}")
print(f"SR 修复成功数: {sum(1 for v in sr_fixed.values() if v['fixed'])}")
print(f"SR 修复率: {sum(1 for v in sr_fixed.values() if v['fixed']) / len(sr_fixed) * 100:.2f}%")

# 从当前分析文件中获取 case 列表
analysis_file = "/home/base/APR/D4C/analysis/result/02_case_differences.txt"
with open(analysis_file, 'r') as f:
    content = f.read()

# 解析 case 列表
cases = []
lines = content.split('\n')
for line in lines[3:]:  # 跳过头部
    if line.startswith('----'):
        continue
    if line.strip():
        parts = line.split()
        if len(parts) >= 1:
            case_name = parts[0]
            if case_name and case_name not in ['Case', '====']:
                cases.append(case_name)

print(f"\n已解析 {len(cases)} 个 case")

# 创建增强版分析文件
output_file = "/home/base/APR/D4C/analysis/result/03_case_fix_results.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("Case 修复情况分析 (GEN vs SR)\n")
    f.write("=" * 120 + "\n")
    f.write(f"{'Case':<35} {'PPL差':<15} {'AvgNLL差':<15} {'总差':<15} {'GEN修复':<12} {'SR修复':<12}\n")
    f.write("-" * 120 + "\n")
    
    # 从原文件提取数据
    case_data = {}
    for line in lines[3:]:
        if line.startswith('----') or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 4:
            case = parts[0]
            if case and case not in ['Case', '====']:
                try:
                    ppl_diff = float(parts[1])
                    avgnll_diff = float(parts[2])
                    total_diff = float(parts[3])
                    case_data[case] = {
                        'ppl': ppl_diff,
                        'avgnll': avgnll_diff,
                        'total': total_diff
                    }
                except:
                    pass
    
    # 输出增强数据
    for case in cases:
        if case in case_data:
            data = case_data[case]
            gen_status = "✓" if gen_fixed.get(case, {}).get('fixed') else "✗"
            sr_status = "✓" if sr_fixed.get(case, {}).get('fixed') else "✗"
            
            f.write(f"{case:<35} {data['ppl']:<15.6f} {data['avgnll']:<15.6f} {data['total']:<15.6f} {gen_status:<12} {sr_status:<12}\n")

print(f"\n增强分析文件已保存到: {output_file}")

# 也生成 JSON 格式的详细数据
json_output = "/home/base/APR/D4C/analysis/result/03_case_fix_results.json"
json_data = {
    'summary': {
        'total_cases': len(cases),
        'gen': {
            'total': len(gen_fixed),
            'fixed': sum(1 for v in gen_fixed.values() if v['fixed']),
            'fix_rate': sum(1 for v in gen_fixed.values() if v['fixed']) / len(gen_fixed) * 100
        },
        'sr': {
            'total': len(sr_fixed),
            'fixed': sum(1 for v in sr_fixed.values() if v['fixed']),
            'fix_rate': sum(1 for v in sr_fixed.values() if v['fixed']) / len(sr_fixed) * 100
        }
    },
    'cases': {}
}

for case in cases:
    if case in case_data:
        json_data['cases'][case] = {
            'ppl_diff': case_data[case]['ppl'],
            'avgnll_diff': case_data[case]['avgnll'],
            'total_diff': case_data[case]['total'],
            'gen': {
                'fixed': gen_fixed.get(case, {}).get('fixed', False),
                'attempts': gen_fixed.get(case, {}).get('attempts', 0)
            },
            'sr': {
                'fixed': sr_fixed.get(case, {}).get('fixed', False),
                'attempts': sr_fixed.get(case, {}).get('attempts', 0)
            }
        }

with open(json_output, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, indent=2, ensure_ascii=False)

print(f"JSON 详细数据已保存到: {json_output}")

# 打印统计摘要
print("\n" + "=" * 60)
print("修复情况分布")
print("=" * 60)

both_fixed = sum(1 for case in cases if gen_fixed.get(case, {}).get('fixed') and sr_fixed.get(case, {}).get('fixed'))
only_gen_fixed = sum(1 for case in cases if gen_fixed.get(case, {}).get('fixed') and not sr_fixed.get(case, {}).get('fixed'))
only_sr_fixed = sum(1 for case in cases if not gen_fixed.get(case, {}).get('fixed') and sr_fixed.get(case, {}).get('fixed'))
neither_fixed = sum(1 for case in cases if not gen_fixed.get(case, {}).get('fixed') and not sr_fixed.get(case, {}).get('fixed'))

print(f"两个方法都修复成功: {both_fixed} ({both_fixed/len(cases)*100:.1f}%)")
print(f"仅 GEN 修复成功: {only_gen_fixed} ({only_gen_fixed/len(cases)*100:.1f}%)")
print(f"仅 SR 修复成功: {only_sr_fixed} ({only_sr_fixed/len(cases)*100:.1f}%)")
print(f"都未修复: {neither_fixed} ({neither_fixed/len(cases)*100:.1f}%)")
