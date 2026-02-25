#!/bin/bash
# Monitor 100-worker gen evaluation progress

LOG_FILE="gen_batch_evaluation_100w.log"

while true; do
    clear
    echo "======================================================================"
    echo "Gen评测进度监控 (100 Workers)"
    echo "======================================================================"
    echo ""
    
    # 当前时间
    echo "当前时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 最新进度
    echo "最新进度:"
    grep "Progress:" "$LOG_FILE" | tail -1
    echo ""
    
    # 成功/失败统计
    echo "成功/失败统计:"
    SUCCESS=$(grep "\[Worker.*\] ✓" "$LOG_FILE" | wc -l | tr -d ' ')
    FAILED=$(grep "\[Worker.*\] ✗" "$LOG_FILE" | wc -l | tr -d ' ')
    TOTAL=$((SUCCESS + FAILED))
    
    if [ $TOTAL -gt 0 ]; then
        SUCCESS_RATE=$(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)
        echo "✓ 修复成功: $SUCCESS"
        echo "✗ 修复失败: $FAILED"
        echo "成功率: ${SUCCESS_RATE}%"
    else
        echo "等待第一个bug完成..."
    fi
    
    echo ""
    echo "======================================================================"
    echo "按 Ctrl+C 退出监控"
    echo "======================================================================"
    
    sleep 10
done
