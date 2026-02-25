#!/bin/bash
# Real-time statistics from log file

echo "======================================================================"
echo "  Edit格式评估 - 实时统计"
echo "======================================================================"
echo ""

# Count from log
FIXED=$(grep -c "✓.*fixed" parallel_evaluation.log 2>/dev/null || echo "0")
FAILED=$(grep -c "✗.*failed" parallel_evaluation.log 2>/dev/null || echo "0")
TOTAL=$((FIXED + FAILED))

if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $FIXED * 100 / $TOTAL" | bc)
    PROGRESS=$(echo "scale=1; $TOTAL * 100 / 698" | bc)
    
    echo "总体进度: $TOTAL/698 ($PROGRESS%)"
    echo "  ✓ 成功修复: $FIXED"
    echo "  ✗ 修复失败: $FAILED"
    echo "  成功率: ${SUCCESS_RATE}%"
    echo ""
    
    echo "Edit格式 (SEARCH/REPLACE blocks):"
    echo "  总数: $TOTAL"
    echo "  成功: $FIXED (${SUCCESS_RATE}%)"
    echo "  失败: $FAILED"
    echo ""
    
    echo "Rewrite格式 (完整方法重写):"
    echo "  总数: 0 (当前评估使用Edit格式数据)"
    echo ""
else
    echo "暂无统计数据"
fi

# Process status
PID=$(ps aux | grep "run_parallel_evaluation" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "======================================================================"
    echo "进程状态: 运行中 (PID: $PID)"
    ps -p $PID -o %cpu,%mem,etime | tail -1 | awk '{printf "  CPU: %s%%, 内存: %s%%, 运行时间: %s\n", $1, $2, $3}'
else
    echo "======================================================================"
    echo "进程状态: 已完成或未运行"
fi

echo "======================================================================"
