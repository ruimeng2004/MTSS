#!/usr/bin/env python3
"""实时对比修复前后的成功率"""
import json
import time
from pathlib import Path

def get_stats(result_file):
    """获取评估统计"""
    if not Path(result_file).exists():
        return None
    
    try:
        with open(result_file) as f:
            data = json.load(f)
        return {
            'total': data['total_bugs'],
            'fixed': data['fixed_bugs'],
            'failed': data['failed_bugs'],
            'rate': data['success_rate'] * 100
        }
    except:
        return None

# 原始评估结果
original = get_stats('/home/base/mengrui/MTSS/evaluation_output/qwen30b_gen_20260214/gen_batch_evaluation_results.json')

# 新评估结果
new = get_stats('/home/base/mengrui/MTSS/evaluation_output/qwen30b_gen_PATH_FIXED/gen_batch_evaluation_results.json')

print("=" * 80)
print("修复前后对比")
print("=" * 80)

if original:
    print(f"\n📊 修复前 (20260214):")
    print(f"   成功: {original['fixed']}/{original['total']} ({original['rate']:.1f}%)")
    print(f"   失败: {original['failed']}")
else:
    print("\n⚠️  原始结果未找到")

if new:
    print(f"\n📊 修复后 (PATH_FIXED):")
    print(f"   成功: {new['fixed']}/{new['total']} ({new['rate']:.1f}%)")
    print(f"   失败: {new['failed']}")
    
    if original:
        improvement = new['fixed'] - original['fixed']
        rate_improvement = new['rate'] - original['rate']
        print(f"\n✨ 改进:")
        print(f"   新增成功: +{improvement} 个")
        print(f"   成功率提升: +{rate_improvement:.1f}%")
        
        if rate_improvement > 15:
            print(f"\n🎉 巨大成功！路径修复效果显著！")
        elif rate_improvement > 5:
            print(f"\n👍 效果良好！")
        else:
            print(f"\n🤔 提升有限，可能还有其他问题")
else:
    print("\n⏳ 新评估尚未完成...")
    
    # 检查日志进度
    log_file = '/home/base/mengrui/MTSS/gen_eval_path_fixed.log'
    if Path(log_file).exists():
        with open(log_file) as f:
            lines = f.readlines()
        
        # 查找最新进度
        for line in reversed(lines[-50:]):
            if 'Progress:' in line:
                progress = line.split('Progress:')[1].strip()
                print(f"\n   当前进度: {progress}")
                break

print("\n" + "=" * 80)
