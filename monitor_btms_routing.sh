#!/bin/bash
# Monitor BTMS routing evaluation progress

LOG_FILE=$(ls -t /home/base/mengrui/MTSS/btms_routing_baseline3-size-adjusted_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "No log file found"
    exit 1
fi

echo "监控日志: $LOG_FILE"
echo "=========================================="
echo ""

while true; do
    clear
    echo "=== BTMS路由评测实时监控 ==="
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "日志: $LOG_FILE"
    echo ""
    
    # 统计成功和失败数量
    SUCCESS=$(grep -c "✓" "$LOG_FILE" 2>/dev/null || echo 0)
    FAIL=$(grep -c "✗" "$LOG_FILE" 2>/dev/null || echo 0)
    TOTAL=$((SUCCESS + FAIL))
    
    if [ $TOTAL -gt 0 ]; then
        SUCCESS_RATE=$(echo "scale=2; $SUCCESS * 100 / $TOTAL" | bc)
    else
        SUCCESS_RATE="0.00"
    fi
    
    echo "📊 当前进度:"
    echo "  总计: $TOTAL / 698"
    echo "  成功: $SUCCESS (${SUCCESS_RATE}%)"
    echo "  失败: $FAIL"
    echo ""
    
    # 显示最近10条结果
    echo "📝 最近10条结果:"
    grep -E "\[Worker.*\] [A-Za-z_0-9]+: [✓✗]" "$LOG_FILE" | tail -10
    echo ""
    
    # 检查进程是否还在运行
    if pgrep -f "run_btms_routing_eval.py" > /dev/null; then
        echo "✅ 评测进程运行中..."
    else
        echo "⚠️ 评测进程已结束"
        
        # 显示最终统计
        if [ -f "/home/base/mengrui/MTSS/evaluation_output/btms_routing_baseline3-size-adjusted/btms_routing_results.json" ]; then
            echo ""
            echo "=== 最终结果 ==="
            python3 -c "
import json
with open('/home/base/mengrui/MTSS/evaluation_output/btms_routing_baseline3-size-adjusted/btms_routing_results.json', 'r') as f:
    data = json.load(f)
    print(f\"总bugs: {data['total_bugs']}\")
    print(f\"修复成功: {data['fixed_bugs']}\")
    print(f\"成功率: {data['success_rate']*100:.2f}%\")
    print(f\"Edit成功: {data['edit_success']}\")
    print(f\"Gen成功: {data['gen_success']}\")
" 2>/dev/null || echo "结果文件未找到"
        fi
        break
    fi
    
    sleep 10
done

echo ""
echo "监控结束"
