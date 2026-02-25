#!/bin/bash
# Run sampled gen evaluation in background

nohup python run_sampled_gen_evaluation.py \
    --input-dir ppl/result/20260106_113852 \
    --bug-list sampled_bugs.json \
    --workers 20 \
    --timeout 240 \
    > sampled_gen_evaluation_output.log 2>&1 &

echo "Sampled gen evaluation started in background"
echo "PID: $!"
echo "Log file: sampled_gen_evaluation.log"
echo "Output file: sampled_gen_evaluation_output.log"
echo ""
echo "Evaluating 84 bugs (5 from each project type)"
echo ""
echo "Monitor progress with:"
echo "  tail -f sampled_gen_evaluation.log"
echo "  ./monitor_sampled_eval.sh"
