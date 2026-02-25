#!/bin/bash
# Monitor sampled gen evaluation progress

echo "=== Sampled Gen Evaluation Monitor ==="
echo ""

# Check if process is running
if pgrep -f "run_sampled_gen_evaluation.py" > /dev/null; then
    echo "✓ Evaluation is running"
    PID=$(pgrep -f "run_sampled_gen_evaluation.py")
    echo "  PID: $PID"
    echo ""
else
    echo "✗ Evaluation is not running"
    echo ""
fi

# Show latest progress
echo "=== Latest Progress ==="
tail -30 sampled_gen_evaluation.log | grep -E "(Progress|Fixed|Failed|Success|REPORT|COMPLETE)" | tail -15

echo ""
echo "=== Full log ==="
echo "  tail -f sampled_gen_evaluation.log"
