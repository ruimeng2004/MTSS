#!/bin/bash
# Comprehensive monitoring script for parallel evaluation

clear
echo "======================================================================"
echo "  100线程并行评估 - 实时监控"
echo "======================================================================"
echo ""

# Check process status
PID=$(ps aux | grep "run_parallel_evaluation" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "✓ 评估进程运行中 (PID: $PID)"
    ps -p $PID -o %cpu,%mem,etime | tail -1 | awk '{printf "  CPU: %s%%, 内存: %s%%, 运行时间: %s\n", $1, $2, $3}'
else
    echo "✗ 评估进程未运行"
fi

echo ""
echo "======================================================================"

# Run Python analysis
python3 analyze_modeling_types.py

echo ""
echo "======================================================================"
echo "  最新日志 (最后15行)"
echo "======================================================================"
tail -15 parallel_evaluation.log 2>/dev/null | grep -E "(Worker|Progress|✓|✗)" || echo "暂无日志"

echo ""
echo "======================================================================"
echo "  持续监控命令:"
echo "    watch -n 10 ./monitor_full_stats.sh"
echo "======================================================================"
