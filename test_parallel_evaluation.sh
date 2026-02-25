#!/bin/bash
# Test parallel evaluation with a small subset of bugs

echo "=========================================="
echo "Testing Parallel Evaluation"
echo "=========================================="

# Test with 10 bugs using 4 workers
echo ""
echo "Running 10 bugs with 4 workers..."
python run_parallel_evaluation.py \
    --input-dir ppl/result/20260105_132306 \
    --output-dir evaluation_output/parallel_test_10 \
    --workers 4 \
    --max-bugs 10 \
    --timeout 600

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Check results in: evaluation_output/parallel_test_10/"
echo "Check logs in: parallel_evaluation.log"
