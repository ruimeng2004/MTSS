#!/usr/bin/env python3
"""
脚本2：计算每个 case 的两个建模的 ppl 和 avgnll 差的大小，降序排序
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import csv

def collect_case_metrics(result_dir):
    """按 case 收集两个模型的指标"""
    case_data = defaultdict(dict)
    
    for timestamp_dir in Path(result_dir).iterdir():
        if not timestamp_dir.is_dir():
            continue
        
        for case_dir in timestamp_dir.iterdir():
            if not case_dir.is_dir():
                continue
            
            result_file = case_dir / 'result.json'
            if not result_file.exists():
                continue
            
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    slug = data.get('slug', case_dir.name)
                    run_ts = data.get('run_ts')
                    
                    if 'ppl' in data and 'avg_nll' in data:
                        if slug not in case_data:
                            case_data[slug] = {}
                        case_data[slug][run_ts] = {
                            'ppl': data['ppl'],
                            'avg_nll': data['avg_nll']
                        }
            except Exception as e:
                print(f"Error reading {result_file}: {e}")
    
    return case_data

def calculate_differences(case_data):
    """计算差值"""
    differences = []
    
    for slug, timestamps in case_data.items():
        # 需要至少有两个时间戳的数据
        if len(timestamps) >= 2:
            timestamps_list = sorted(timestamps.items())
            
            # 计算相邻时间戳之间的差
            for i in range(len(timestamps_list) - 1):
                ts1, data1 = timestamps_list[i]
                ts2, data2 = timestamps_list[i + 1]
                
                ppl_diff = abs(data2['ppl'] - data1['ppl'])
                nll_diff = abs(data2['avg_nll'] - data1['avg_nll'])
                
                differences.append({
                    'case': slug,
                    'model1_ts': ts1,
                    'model2_ts': ts2,
                    'ppl_diff': ppl_diff,
                    'avgnll_diff': nll_diff,
                    'total_diff': ppl_diff + nll_diff  # 用作排序依据
                })
        elif len(timestamps) == 1:
            # 单个时间戳的情况
            ts, data = list(timestamps.items())[0]
            differences.append({
                'case': slug,
                'model1_ts': ts,
                'model2_ts': 'N/A',
                'ppl_diff': 0,
                'avgnll_diff': 0,
                'total_diff': 0
            })
    
    # 按 total_diff 降序排序
    differences.sort(key=lambda x: x['total_diff'], reverse=True)
    return differences

def save_differences(differences, output_dir):
    """保存差值到 CSV 文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, '02_case_differences.csv')
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['case', 'model1_ts', 'model2_ts', 'ppl_diff', 'avgnll_diff', 'total_diff'])
        writer.writeheader()
        writer.writerows(differences)
    
    print(f"✓ 差值结果已保存: {output_file}")
    
    # 同时保存为易读的文本格式
    txt_file = os.path.join(output_dir, '02_case_differences.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("Case 差值分析 (按总差值降序排列)\n")
        f.write("=" * 100 + "\n")
        f.write(f"{'Case':<40} {'PPL差':<15} {'AvgNLL差':<20} {'总差':<15}\n")
        f.write("-" * 100 + "\n")
        
        for diff in differences[:100]:  # 显示前100个
            f.write(f"{diff['case']:<40} {diff['ppl_diff']:<15.6f} {diff['avgnll_diff']:<20.6f} {diff['total_diff']:<15.6f}\n")
    
    print(f"✓ 文本版本已保存: {txt_file}")

def main():
    result_dir = '/home/base/APR/D4C/ppl/result'
    output_dir = '/home/base/APR/D4C/analysis/result'
    
    print("收集 case 指标数据...")
    case_data = collect_case_metrics(result_dir)
    print(f"找到 {len(case_data)} 个 cases")
    
    print("计算差值...")
    differences = calculate_differences(case_data)
    
    print(f"有差值数据的 cases: {len([d for d in differences if d['total_diff'] > 0])}")
    
    print("\n保存结果...")
    save_differences(differences, output_dir)
    
    # 打印前10个差值最大的
    print("\n顶部 10 个差值最大的 cases:")
    print(f"{'排名':<5} {'Case':<35} {'PPL差':<15} {'AvgNLL差':<20}")
    print("-" * 75)
    for i, diff in enumerate(differences[:10], 1):
        print(f"{i:<5} {diff['case']:<35} {diff['ppl_diff']:<15.6f} {diff['avgnll_diff']:<20.6f}")
    
    print("\n完成！")

if __name__ == "__main__":
    main()
