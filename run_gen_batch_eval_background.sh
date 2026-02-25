#!/bin/bash
# Run gen batch evaluation in background with nohup

nohup python run_gen_batch_evaluation.py \
    --input-dir ppl/result/20260106_113852 \
    --workers 20 \
    --timeout 240 \
    --bug-limit 20 \
    > gen_batch_evaluation_output.log 2>&1 &

echo "Gen batch evaluation started in background"
echo "PID: $!"
echo "Log file: gen_batch_evaluation.log"
echo "Output file: gen_batch_evaluation_output.log"
echo ""
echo "Monitor progress with:"
echo "  tail -f gen_batch_evaluation.log"
echo "  ./monitor_gen_eval.sh"
