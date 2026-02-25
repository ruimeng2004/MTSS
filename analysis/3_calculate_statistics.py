#!/usr/bin/env python3
"""
脚本3：计算所有 case 的总和和平均数
"""

import json
import os
from pathlib import Path

def calculate_statistics(result_dir):
    """计算 ppl 和 nll 的统计数据"""
    ppl_sum = 0
    nll_sum = 0
    count = 0
    
    ppl_values = []
    nll_values = []
    
    for result_file in Path(result_dir).rglob('result.json'):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                if 'ppl' in data and 'avg_nll' in data:
                    ppl = data['ppl']
                    nll = data['avg_nll']
                    
                    ppl_sum += ppl
                    nll_sum += nll
                    count += 1
                    
                    ppl_values.append(ppl)
                    nll_values.append(nll)
        except Exception as e:
            print(f"Error reading {result_file}: {e}")
    
    return {
        'count': count,
        'ppl_sum': ppl_sum,
        'ppl_avg': ppl_sum / count if count > 0 else 0,
        'nll_sum': nll_sum,
        'nll_avg': nll_sum / count if count > 0 else 0,
        'ppl_values': ppl_values,
        'nll_values': nll_values
    }

def save_statistics(stats, output_dir):
    """保存统计结果"""
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, '03_statistics.txt')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("所有 Case 的 PPL 和 AvgNLL 统计\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"总样本数: {stats['count']}\n\n")
        
        f.write("PPL (Perplexity) 统计:\n")
        f.write("-" * 80 + "\n")
        f.write(f"总和:     {stats['ppl_sum']:.10f}\n")
        f.write(f"平均值:   {stats['ppl_avg']:.10f}\n")
        f.write(f"最小值:   {min(stats['ppl_values']):.10f}\n")
        f.write(f"最大值:   {max(stats['ppl_values']):.10f}\n")
        
        if len(stats['ppl_values']) > 1:
            import statistics
            f.write(f"中位数:   {statistics.median(stats['ppl_values']):.10f}\n")
            f.write(f"标准差:   {statistics.stdev(stats['ppl_values']):.10f}\n")
        
        f.write("\n")
        f.write("AvgNLL (Average Negative Log Likelihood) 统计:\n")
        f.write("-" * 80 + "\n")
        f.write(f"总和:     {stats['nll_sum']:.10f}\n")
        f.write(f"平均值:   {stats['nll_avg']:.10f}\n")
        f.write(f"最小值:   {min(stats['nll_values']):.10f}\n")
        f.write(f"最大值:   {max(stats['nll_values']):.10f}\n")
        
        if len(stats['nll_values']) > 1:
            import statistics
            f.write(f"中位数:   {statistics.median(stats['nll_values']):.10f}\n")
            f.write(f"标准差:   {statistics.stdev(stats['nll_values']):.10f}\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"✓ 统计结果已保存: {output_file}")

def main():
    result_dir = '/home/base/APR/D4C/ppl/result'
    output_dir = '/home/base/APR/D4C/analysis/result'
    
    print("计算统计数据...")
    stats = calculate_statistics(result_dir)
    
    print("\n" + "=" * 80)
    print("所有 Case 的 PPL 和 AvgNLL 统计")
    print("=" * 80)
    print(f"\n总样本数: {stats['count']}")
    print(f"\nPPL 统计:")
    print(f"  总和:   {stats['ppl_sum']:.10f}")
    print(f"  平均值: {stats['ppl_avg']:.10f}")
    print(f"  最小值: {min(stats['ppl_values']):.10f}")
    print(f"  最大值: {max(stats['ppl_values']):.10f}")
    
    if len(stats['ppl_values']) > 1:
        import statistics
        print(f"  中位数: {statistics.median(stats['ppl_values']):.10f}")
        print(f"  标准差: {statistics.stdev(stats['ppl_values']):.10f}")
    
    print(f"\nAvgNLL 统计:")
    print(f"  总和:   {stats['nll_sum']:.10f}")
    print(f"  平均值: {stats['nll_avg']:.10f}")
    print(f"  最小值: {min(stats['nll_values']):.10f}")
    print(f"  最大值: {max(stats['nll_values']):.10f}")
    
    if len(stats['nll_values']) > 1:
        import statistics
        print(f"  中位数: {statistics.median(stats['nll_values']):.10f}")
        print(f"  标准差: {statistics.stdev(stats['nll_values']):.10f}")
    
    print("\n保存结果...")
    save_statistics(stats, output_dir)
    print("\n完成！")

if __name__ == "__main__":
    main()
