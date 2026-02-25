#!/bin/bash

# Check parallel evaluation progress with accurate counting

LOG_FILE="parallel_evaluation.log"

echo "======================================================================"
echo "  并行评估进度 (100线程)"
echo "======================================================================"
echo ""

# Count completed bugs (both success and failure)
COMPLETED=$(grep -E "\[Worker [0-9]+\] (✓|✗)" "$LOG_FILE" | wc -l | tr -d ' ')
SUCCESS=$(grep -E "\[Worker [0-9]+\] ✓" "$LOG_FILE" | wc -l | tr -d ' ')
FAILED=$(grep -E "\[Worker [0-9]+\] ✗" "$LOG_FILE" | wc -l | tr -d ' ')

# Total bugs
TOTAL=698

# Calculate percentage
if [ "$COMPLETED" -gt 0 ]; then
    PERCENT=$(echo "scale=1; $COMPLETED * 100 / $TOTAL" | bc)
    SUCCESS_RATE=$(echo "scale=1; $SUCCESS * 100 / $COMPLETED" | bc)
else
    PERCENT=0
    SUCCESS_RATE=0
fi

echo "总体进度: $COMPLETED/$TOTAL ($PERCENT%)"
echo "  ✓ 成功修复: $SUCCESS"
echo "  ✗ 修复失败: $FAILED"
echo "  成功率: $SUCCESS_RATE%"
echo ""

# Show latest completed bugs
echo "最近完成的10个bug:"
grep -E "\[Worker [0-9]+\] (✓|✗)" "$LOG_FILE" | tail -10
echo ""

# Check process status
PID=$(ps -ef | grep "run_parallel_evaluation.py" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "======================================================================"
    echo "进程状态: 运行中 (PID: $PID)"
    
    # Get process info
    PS_INFO=$(ps -p $PID -o %cpu,%mem,etime | tail -1)
    CPU=$(echo $PS_INFO | awk '{print $1}')
    MEM=$(echo $PS_INFO | awk '{print $2}')
    TIME=$(echo $PS_INFO | awk '{print $3}')
    
    echo "  CPU: ${CPU}%, 内存: ${MEM}%, 运行时间: ${TIME}"
    
    # Estimate remaining time
    if [ "$COMPLETED" -gt 0 ]; then
        # Get elapsed time in format HH:MM:SS or DD-HH:MM:SS
        ELAPSED=$(ps -p $PID -o etime= | tr -d ' ')
        
        # Convert to seconds (handle both formats)
        if [[ $ELAPSED == *-* ]]; then
            # Format: DD-HH:MM:SS
            DAYS=$(echo $ELAPSED | cut -d'-' -f1)
            HMS=$(echo $ELAPSED | cut -d'-' -f2)
            HOURS=$(echo $HMS | cut -d':' -f1)
            MINS=$(echo $HMS | cut -d':' -f2)
            SECS=$(echo $HMS | cut -d':' -f3)
            ELAPSED_SEC=$((DAYS * 86400 + HOURS * 3600 + MINS * 60 + SECS))
        else
            # Format: HH:MM:SS or MM:SS
            IFS=':' read -ra TIME_PARTS <<< "$ELAPSED"
            if [ ${#TIME_PARTS[@]} -eq 3 ]; then
                ELAPSED_SEC=$((${TIME_PARTS[0]} * 3600 + ${TIME_PARTS[1]} * 60 + ${TIME_PARTS[2]}))
            else
                ELAPSED_SEC=$((${TIME_PARTS[0]} * 60 + ${TIME_PARTS[1]}))
            fi
        fi
        
        # Calculate average time per bug
        AVG_TIME=$(echo "scale=2; $ELAPSED_SEC / $COMPLETED" | bc)
        
        # Calculate remaining bugs and time
        REMAINING=$((TOTAL - COMPLETED))
        REMAINING_SEC=$(echo "scale=0; $AVG_TIME * $REMAINING / 1" | bc)
        
        # Convert to hours and minutes
        REMAINING_HOURS=$((REMAINING_SEC / 3600))
        REMAINING_MINS=$(((REMAINING_SEC % 3600) / 60))
        
        echo "  平均每个bug: ${AVG_TIME}秒"
        echo "  预计剩余时间: ${REMAINING_HOURS}小时${REMAINING_MINS}分钟"
    fi
    
    echo "======================================================================"
else
    echo "======================================================================"
    echo "进程状态: 未运行"
    echo "======================================================================"
fi
