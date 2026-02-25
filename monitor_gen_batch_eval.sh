#!/bin/bash
# Monitor gen batch evaluation progress

echo "=== Gen Batch Evaluation Monitor ==="
echo ""

# Check if process is running
if ps -p 73874 > /dev/null 2>&1; then
    echo "✓ Evaluation process is running (PID: 73874)"
else
    echo "✗ Evaluation process is not running"
fi

echo ""
echo "=== Latest Log Output ==="
tail -50 gen_batch_evaluation_output.log

echo ""
echo "=== Progress Summary ==="
echo "Total bugs to evaluate: 698"
echo ""

# Count completed bugs from log
completed=$(grep -c "Progress:" gen_batch_evaluation_output.log 2>/dev/null || echo "0")
echo "Completed: $completed"

# Get latest progress line
latest=$(grep "Progress:" gen_batch_evaluation_output.log 2>/dev/null | tail -1)
if [ ! -z "$latest" ]; then
    echo "Latest: $latest"
fi

echo ""
echo "=== Success/Failure Count ==="
fixed=$(grep -c "✓.*fixed" gen_batch_evaluation_output.log 2>/dev/null || echo "0")
failed=$(grep -c "✗.*failed" gen_batch_evaluation_output.log 2>/dev/null || echo "0")
echo "Fixed: $fixed"
echo "Failed: $failed"

if [ $completed -gt 0 ]; then
    success_rate=$(echo "scale=1; $fixed * 100 / $completed" | bc)
    echo "Success rate: ${success_rate}%"
fi

echo ""
echo "=== Output Directory ==="
output_dir=$(grep "Results saved to:" gen_batch_evaluation_output.log 2>/dev/null | tail -1 | awk '{print $NF}')
if [ ! -z "$output_dir" ]; then
    echo "Output: $output_dir"
    if [ -f "$output_dir" ]; then
        echo "✓ Results file exists"
    fi
fi

echo ""
echo "To view full log: tail -f gen_batch_evaluation_output.log"
echo "To stop evaluation: kill 73874"
