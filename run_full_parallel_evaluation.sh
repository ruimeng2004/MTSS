#!/bin/bash
# Run full parallel evaluation on all 698 bugs

echo "=========================================="
echo "Full Parallel D4J Fix Evaluation"
echo "=========================================="
echo ""
echo "Total bugs: 698"
echo "Workers: 100"
echo "Estimated time: 30-60 minutes"
echo ""
echo "WARNING: Using 100 threads will consume significant system resources!"
echo "Make sure you have:"
echo "  - At least 16GB RAM"
echo "  - Sufficient disk space (50GB+)"
echo "  - High file descriptor limit (ulimit -n should be > 10000)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Check and increase file descriptor limit if needed
CURRENT_LIMIT=$(ulimit -n)
echo ""
echo "Current file descriptor limit: $CURRENT_LIMIT"
if [ "$CURRENT_LIMIT" -lt 10000 ]; then
    echo "Increasing file descriptor limit to 10000..."
    ulimit -n 10000
    echo "New limit: $(ulimit -n)"
fi

echo ""
echo "Starting full evaluation with 100 workers..."
echo "=========================================="

# Run with 100 workers for maximum parallelism
python run_parallel_evaluation.py \
    --input-dir ppl/result/20260105_132306 \
    --workers 100 \
    --timeout 600

echo ""
echo "=========================================="
echo "Full Evaluation Complete!"
echo "=========================================="
echo ""
echo "Results saved to: evaluation_output/full_parallel_run/"
echo "Logs saved to: parallel_evaluation.log"
