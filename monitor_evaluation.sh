#!/bin/bash
# Monitor evaluation progress

echo "=== D4J Fix Evaluation Monitor ==="
echo ""

# Check if log file exists
if [ ! -f "evaluation_full_run.log" ]; then
    echo "❌ Log file not found. Evaluation may not be running."
    exit 1
fi

# Show last 30 lines of log
echo "📊 Recent activity:"
echo "-------------------"
tail -30 evaluation_full_run.log

echo ""
echo "-------------------"

# Count completed bugs
completed=$(grep -c "Evaluating bug:" evaluation_full_run.log 2>/dev/null || echo "0")
echo "✅ Bugs processed: $completed / 698"

# Show current bug being evaluated
current=$(grep "Evaluating bug:" evaluation_full_run.log | tail -1 | awk '{print $NF}')
if [ ! -z "$current" ]; then
    echo "🔄 Current bug: $current"
fi

# Check for errors
errors=$(grep -c "ERROR" evaluation_full_run.log 2>/dev/null || echo "0")
echo "⚠️  Errors encountered: $errors"

# Estimate progress
if [ "$completed" -gt 0 ]; then
    progress=$(echo "scale=2; $completed * 100 / 698" | bc)
    echo "📈 Progress: ${progress}%"
fi

echo ""
echo "💡 Tip: Run 'tail -f evaluation_full_run.log' to watch live updates"
