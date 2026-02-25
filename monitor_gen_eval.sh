#!/bin/bash
# Monitor gen batch evaluation progress

LOG_FILE="gen_batch_evaluation_restart.log"
PID=93040

clear
echo "==================================================================="
echo "           Gen Batch Evaluation Monitor"
echo "==================================================================="
echo ""

while true; do
    # Move cursor to top
    tput cup 4 0
    
    # Check if process is running
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ 进程运行中 (PID: $PID)                    "
    else
        echo "✗ 进程已停止                                "
        echo ""
        echo "评测已完成或异常停止"
        break
    fi
    
    echo ""
    echo "==================================================================="
    
    # Get progress
    completed=$(grep "Progress:" $LOG_FILE | tail -1 | grep -oE "[0-9]+/698" | cut -d'/' -f1)
    if [ -z "$completed" ]; then
        completed=0
    fi
    
    percentage=$(echo "scale=1; $completed * 100 / 698" | bc)
    
    echo "📊 总体进度: $completed / 698 ($percentage%)                    "
    
    # Progress bar
    bar_length=50
    filled=$(echo "scale=0; $completed * $bar_length / 698" | bc)
    printf "["
    for ((i=0; i<$filled; i++)); do printf "█"; done
    for ((i=$filled; i<$bar_length; i++)); do printf " "; done
    printf "]"
    echo ""
    echo ""
    
    # Success/Failure stats
    fixed=$(grep "\[Worker.*\] ✓" $LOG_FILE | wc -l | tr -d ' ')
    failed=$(grep "\[Worker.*\] ✗" $LOG_FILE | wc -l | tr -d ' ')
    
    if [ $completed -gt 0 ]; then
        success_rate=$(echo "scale=1; $fixed * 100 / $completed" | bc)
    else
        success_rate="0.0"
    fi
    
    echo "✓ 修复成功: $fixed                              "
    echo "✗ 修复失败: $failed                              "
    echo "成功率: ${success_rate}%                         "
    echo ""
    
    # Checkout timeout check
    timeout_count=$(grep -c "timed out" $LOG_FILE 2>/dev/null || echo "0")
    if [ $timeout_count -eq 0 ]; then
        echo "🔍 Checkout超时: $timeout_count 个 ✓              "
    else
        echo "⚠️  Checkout超时: $timeout_count 个              "
    fi
    echo ""
    
    # Time estimation
    start_time=$(head -1 $LOG_FILE | awk '{print $1" "$2}')
    current_time=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Calculate elapsed time in minutes
    start_epoch=$(date -j -f "%Y-%m-%d %H:%M:%S" "$start_time" +%s 2>/dev/null || echo "0")
    current_epoch=$(date +%s)
    elapsed_sec=$((current_epoch - start_epoch))
    elapsed_min=$((elapsed_sec / 60))
    
    if [ $completed -gt 0 ] && [ $elapsed_min -gt 0 ]; then
        avg_time=$(echo "scale=2; $elapsed_min / $completed" | bc)
        remaining=$((698 - completed))
        remaining_min=$(echo "scale=0; $avg_time * $remaining / 1" | bc)
        remaining_hours=$((remaining_min / 60))
        remaining_mins=$((remaining_min % 60))
        
        finish_epoch=$((current_epoch + remaining_min * 60))
        finish_time=$(date -r $finish_epoch '+%H:%M')
        
        echo "⏱️  已运行: ${elapsed_min} 分钟                    "
        echo "平均速度: ${avg_time} 分钟/bug                "
        echo "预计剩余: ${remaining_hours}小时${remaining_mins}分钟           "
        echo "预计完成: ${finish_time}                        "
    else
        echo "⏱️  已运行: ${elapsed_min} 分钟                    "
        echo "计算中...                                    "
    fi
    
    echo ""
    echo "==================================================================="
    echo ""
    
    # Latest progress
    echo "📝 最新进度:"
    grep "Progress:" $LOG_FILE | tail -3 | while read line; do
        echo "  $(echo $line | grep -oE 'Progress:.*')"
    done
    
    echo ""
    echo "最后更新: $(date '+%H:%M:%S')                    "
    echo ""
    echo "按 Ctrl+C 退出监控"
    echo ""
    
    # Wait 10 seconds before next update
    sleep 10
done
