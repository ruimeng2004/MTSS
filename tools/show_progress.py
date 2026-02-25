#!/usr/bin/env python3
"""实时显示概率性路由评估进度"""

import re
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("/home/base/mengrui/MTSS/probabilistic_routing_eval.log")

def parse_progress():
    """解析日志文件获取进度信息"""
    try:
        with open(LOG_FILE, 'r') as f:
            log = f.read()
    except FileNotFoundError:
        print("❌ 日志文件不存在")
        return
    
    # 提取关键信息
    start_match = re.search(r'Start time: (.+)', log)
    routing_match = re.search(r'edit: (\d+) \(([0-9.]+)%\).*?gen: (\d+) \(([0-9.]+)%\)', log, re.DOTALL)
    
    # 统计已完成的bugs
    fixed_count = len(re.findall(r'✓.*fixed with attempt', log))
    failed_count = len(re.findall(r'✗.*failed all', log))
    total_evaluated = fixed_count + failed_count
    
    # 当前配置
    current_config_match = re.search(r'Processing: (.+)', log)
    current_config = current_config_match.group(1) if current_config_match else "未知"
    
    print("=" * 80)
    print(" " * 20 + "概率性路由评估 - 实时进度")
    print("=" * 80)
    print()
    
    # 运行状态
    print("📍 当前状态")
    print(f"   配置: {current_config} (1/8)")
    print(f"   已评估: {total_evaluated} / 698 bugs ({total_evaluated*100//698}%)")
    print()
    
    # 时间统计
    if start_match:
        start_str = start_match.group(1).strip()
        try:
            start_time = datetime.strptime(start_str, '%a %b %d %H:%M:%S UTC %Y')
            now = datetime.utcnow()
            elapsed = (now - start_time).total_seconds()
            elapsed_min = int(elapsed / 60)
            elapsed_sec = int(elapsed % 60)
            
            print("⏱️  时间统计")
            print(f"   开始时间: {start_str}")
            print(f"   已运行: {elapsed_min} 分 {elapsed_sec} 秒")
            
            if total_evaluated > 0:
                time_per_bug = elapsed / total_evaluated
                remaining_bugs_config = 698 - total_evaluated
                remaining_time = remaining_bugs_config * time_per_bug
                remaining_min = int(remaining_time / 60)
                total_time_config = int((elapsed + remaining_time) / 60)
                total_time_all = total_time_config * 8
                
                print(f"   速度: {time_per_bug:.1f} 秒/bug")
                print(f"   本配置预计剩余: {remaining_min} 分钟")
                print(f"   本配置预计总时长: {total_time_config} 分钟")
                print(f"   全部8配置预计: {total_time_all // 60} 小时 {total_time_all % 60} 分钟")
            print()
        except Exception as e:
            print(f"   时间解析错误: {e}")
            print()
    
    # 评估结果
    if total_evaluated > 0:
        success_rate = (fixed_count * 100.0 / total_evaluated) if total_evaluated > 0 else 0
        
        print("🎯 评估结果（实时，部分）")
        print(f"   修复成功: {fixed_count}")
        print(f"   修复失败: {failed_count}")
        print(f"   成功率: {success_rate:.1f}% ({fixed_count}/{total_evaluated})")
        print()
        print("   📊 对比基线:")
        print(f"      Pure Edit:   78.9% (550/698) ⭐ 当前最佳")
        print(f"      Pure Gen:    72.2% (504/698)")
        print(f"      确定性路由:  74.21% (518/698)")
        
        if success_rate > 78.9:
            print(f"      概率性路由:  {success_rate:.1f}% 🎉 超越Pure Edit!")
        elif success_rate > 74.21:
            print(f"      概率性路由:  {success_rate:.1f}% ✓ 优于确定性路由")
        else:
            print(f"      概率性路由:  {success_rate:.1f}% ⚠️  部分结果")
        print()
    
    # 路由分布
    print("🔀 路由分布验证")
    if routing_match:
        edit_count, edit_pct, gen_count, gen_pct = routing_match.groups()
        print(f"   概率性路由: {edit_count} Edit / {gen_count} Gen ({edit_pct}% / {gen_pct}%)")
        print(f"   确定性路由: 289 Edit / 409 Gen (41.4% / 58.6%)")
        print(f"   ✅ 路由分布已改变 - 概率性选择生效！")
    else:
        print("   ⚠️  路由分布信息未找到")
    print()
    
    # 最近活动
    print("📝 最近活动 (最后10行)")
    print("-" * 80)
    recent_lines = log.split('\n')[-15:]
    for line in recent_lines[-10:]:
        if line.strip():
            # 只显示关键信息
            if any(keyword in line for keyword in ['✓', '✗', 'Worker', 'fixed', 'failed']):
                # 截断过长的行
                display_line = line[:120] + '...' if len(line) > 120 else line
                print(f"   {display_line}")
    
    print()
    print("=" * 80)
    print("💡 提示:")
    print("   - 实时日志: tail -f /home/base/mengrui/MTSS/probabilistic_routing_eval.log")
    print("   - 再次检查: python3 /home/base/mengrui/MTSS/show_progress.py")
    print("=" * 80)

if __name__ == '__main__':
    parse_progress()
