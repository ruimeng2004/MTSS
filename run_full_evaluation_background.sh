#!/bin/bash
# Run full evaluation in background with logging

echo "Starting full evaluation in background..."
echo "Log file: full_evaluation.log"
echo "Progress can be monitored with: tail -f full_evaluation.log"
echo ""

nohup python test_full_evaluation.py > full_evaluation.log 2>&1 &
PID=$!

echo "Process started with PID: $PID"
echo "To check if it's still running: ps -p $PID"
echo "To stop it: kill $PID"
echo ""
echo "Monitoring first 20 lines..."
sleep 2
head -20 full_evaluation.log
