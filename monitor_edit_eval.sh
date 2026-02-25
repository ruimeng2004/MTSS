#!/bin/bash

# Monitor edit batch evaluation progress

echo "=== Edit Batch Evaluation Monitor ==="
echo ""

# Check if process is running
PID=31268
if ps -p $PID > /dev/null 2>&1; then
    echo "✓ Process is running (PID: $PID)"
    echo ""
else
    echo "✗ Process is not running"
    exit 1
fi

# Count completed bugs
OUTPUT_DIR="evaluation_output/edit_batch_eval_20260205_235929"
if [ -d "$OUTPUT_DIR/bug_results" ]; then
    COMPLETED=$(ls "$OUTPUT_DIR/bug_results" 2>/dev/null | wc -l | tr -d ' ')
    echo "Completed bugs: $COMPLETED / 698"
    echo ""
fi

# Show recent activity
echo "Recent activity (last 10 lines):"
tail -10 edit_batch_evaluation.log | grep -E "(Trying attempt|SUCCESS|FAILED|TIMEOUT|Evaluation complete)" || echo "Still initializing workers..."
echo ""

# Calculate estimated time
TOTAL_BUGS=698
if [ "$COMPLETED" -gt 0 ]; then
    ELAPSED_SECONDS=$(($(date +%s) - $(date -j -f "%Y-%m-%d %H:%M:%S" "2026-02-05 23:59:43" +%s)))
    RATE=$(echo "scale=2; $COMPLETED / ($ELAPSED_SECONDS / 60)" | bc)
    REMAINING=$((TOTAL_BUGS - COMPLETED))
    ETA_MINUTES=$(echo "scale=0; $REMAINING / $RATE" | bc)
    echo "Progress rate: $RATE bugs/minute"
    echo "Estimated time remaining: $ETA_MINUTES minutes"
fi
