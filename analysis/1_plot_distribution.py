#!/usr/bin/env python3
"""
脚本1：绘制 PPL 和 AvgNLL 的分布图表
"""

import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# 配置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def collect_metrics(result_dir):
    """收集所有 result.json 文件中的 ppl 和 avg_nll 数据"""
    ppl_values = []
    nll_values = []
    
    for result_file in Path(result_dir).rglob('result.json'):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                if 'ppl' in data and 'avg_nll' in data:
                    ppl_values.append(data['ppl'])
                    nll_values.append(data['avg_nll'])
        except Exception as e:
            print(f"Error reading {result_file}: {e}")
    
    return ppl_values, nll_values

def plot_distribution(ppl_values, nll_values, output_dir):
    """创建分布图表"""
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建两列的图表
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # PPL 分布
    axes[0].hist(ppl_values, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
    axes[0].set_xlabel('PPL (Perplexity)', fontsize=12)
    axes[0].set_ylabel('频次 (Frequency)', fontsize=12)
    axes[0].set_title('PPL 分布', fontsize=14, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].text(0.98, 0.98, f'总数: {len(ppl_values)}\n平均: {np.mean(ppl_values):.4f}\n中位数: {np.median(ppl_values):.4f}',
                verticalalignment='top', horizontalalignment='right', transform=axes[0].transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontsize=10)
    
    # AvgNLL 分布
    axes[1].hist(nll_values, bins=50, color='lightcoral', edgecolor='black', alpha=0.7)
    axes[1].set_xlabel('AvgNLL (Average Negative Log Likelihood)', fontsize=12)
    axes[1].set_ylabel('频次 (Frequency)', fontsize=12)
    axes[1].set_title('AvgNLL 分布', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    axes[1].text(0.98, 0.98, f'总数: {len(nll_values)}\n平均: {np.mean(nll_values):.4f}\n中位数: {np.median(nll_values):.4f}',
                verticalalignment='top', horizontalalignment='right', transform=axes[1].transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), fontsize=10)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, '01_ppl_avgnll_distribution.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 分布图已保存: {output_file}")
    plt.close()

def main():
    result_dir = '/home/base/APR/D4C/ppl/result'
    output_dir = '/home/base/APR/D4C/analysis/result'
    
    print("收集数据...")
    ppl_values, nll_values = collect_metrics(result_dir)
    
    print(f"找到 {len(ppl_values)} 个样本")
    print(f"PPL - 最小: {min(ppl_values):.4f}, 最大: {max(ppl_values):.4f}, 平均: {np.mean(ppl_values):.4f}")
    print(f"AvgNLL - 最小: {min(nll_values):.4f}, 最大: {max(nll_values):.4f}, 平均: {np.mean(nll_values):.4f}")
    
    print("\n绘制分布图...")
    plot_distribution(ppl_values, nll_values, output_dir)
    print("完成！")

if __name__ == "__main__":
    main()
