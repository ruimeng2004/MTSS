#!/bin/bash
# Monitor fast parallel evaluation progress

echo "=== Fast Parallel Gen Evaluation Monitor ==="
echo ""

while true; do
    clear
    echo "=== Fast Parallel Gen Evaluation Progress ==="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Get latest output directory
    LATEST_DIR=$(ls -td evaluation_output/fast_gen_eval_* 2>/dev/null | head -1)
    
    if [ -n "$LATEST_DIR" ]; then
        echo "Output Directory: $LATEST_DIR"
        echo ""
        
        # Count completed bugs
        COMPLETED=$(find "$LATEST_DIR/bug_results" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
        echo "Completed: $COMPLETED / 698"
        
        # Calculate progress percentage
        if [ "$COMPLETED" -gt 0 ]; then
            PERCENT=$(echo "scale=1; $COMPLETED * 100 / 698" | bc)
            echo "Progress: ${PERCENT}%"
        fi
        
        echo ""
        
        # Show recent log entries with progress
        echo "Recent Progress:"
        grep "Progress:" fast_parallel_gen_eval.log 2>/dev/null | tail -5
        
        echo ""
        echo "Recent Completions:"
        tail -10 fast_parallel_gen_eval.log 2>/dev/null | grep -E "(✓|✗|fixed|failed)"
        
    else
        echo "No evaluation output found yet..."
    fi
    
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    echo "Refreshing in 10 seconds..."
    
    sleep 10
done
