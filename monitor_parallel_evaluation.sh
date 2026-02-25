#!/bin/bash
# Monitor parallel evaluation progress

echo "=========================================="
echo "Parallel Evaluation Monitor"
echo "=========================================="
echo ""

# Check if process is running
PID=$(ps aux | grep "run_parallel_evaluation" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "✓ Parallel evaluation is running (PID: $PID)"
    # Get CPU and memory usage
    ps -p $PID -o %cpu,%mem,etime | tail -1 | awk '{print "  CPU: "$1"%, Memory: "$2"%, Runtime: "$3}'
else
    echo "✗ Parallel evaluation process not found"
fi

echo ""
echo "Latest log entries:"
echo "------------------------------------------"
tail -30 parallel_evaluation.log 2>/dev/null || echo "Log file not found yet"

echo ""
echo "------------------------------------------"
echo "Statistics:"
echo "------------------------------------------"

# Count completed bugs
if [ -f parallel_evaluation.log ]; then
    completed=$(grep -c "✓.*fixed" parallel_evaluation.log 2>/dev/null || echo "0")
    failed=$(grep -c "✗.*failed" parallel_evaluation.log 2>/dev/null || echo "0")
    total=$((completed + failed))
    
    echo "Completed bugs: $total"
    echo "  - Fixed: $completed"
    echo "  - Failed: $failed"
    
    if [ $total -gt 0 ]; then
        success_rate=$(echo "scale=1; $completed * 100 / $total" | bc)
        echo "  - Success rate: ${success_rate}%"
    fi
fi

echo ""
echo "To monitor continuously, run:"
echo "  watch -n 5 ./monitor_parallel_evaluation.sh"
