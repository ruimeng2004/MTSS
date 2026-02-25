#!/bin/bash

# Run edit batch evaluation in background with nohup
# This allows the evaluation to continue even if terminal is closed

echo "Starting edit batch evaluation in background..."
echo "Input: ppl/result/20260106_113852"
echo "Workers: 100"
echo "Timeout: 240s (optimized from 600s)"
echo ""

nohup python run_edit_batch_evaluation.py \
    --input-dir ppl/result/20260106_113852 \
    --workers 100 \
    --timeout 240 \
    > edit_batch_evaluation_output.log 2>&1 &

PID=$!
echo "Evaluation started with PID: $PID"
echo "Logs: edit_batch_evaluation.log and edit_batch_evaluation_output.log"
echo ""
echo "To monitor progress:"
echo "  tail -f edit_batch_evaluation.log"
echo ""
echo "To check if still running:"
echo "  ps -p $PID"
echo ""
echo "To stop evaluation:"
echo "  kill $PID"
