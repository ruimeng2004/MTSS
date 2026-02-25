#!/bin/bash

# Watch evaluation progress with live updates

echo "Watching edit batch evaluation progress..."
echo "Press Ctrl+C to stop watching"
echo ""

# Check if process is running
PID=41302
if ! ps -p $PID > /dev/null 2>&1; then
    echo "Error: Evaluation process (PID: $PID) is not running"
    exit 1
fi

# Follow the log and filter for progress reports
tail -f edit_batch_evaluation.log | grep --line-buffered -E "(Progress Report|Fixed:|Elapsed:|Progress:.*Latest:)"
