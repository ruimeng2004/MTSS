#!/bin/bash

echo "🚀 ULTRA-FAST EVALUATION (3-HOUR TARGET)"
echo "========================================"
echo "Optimizations:"
echo "  - Timeout: 240s (was 600s, 60% reduction)"
echo "  - Early stop: After 3 failed attempts (was 10)"
echo "  - Workers: 200 (was 100, 2x increase)"
echo "  - Expected time: ~3 hours"
echo ""
echo "Starting..."

nohup python run_ultra_fast_eval.py \
    --workers 200 \
    --timeout 240 \
    --early-stop 3 \
    > ultra_fast_eval.log 2>&1 &

PID=$!
echo ""
echo "✅ Started with PID: $PID"
echo ""
echo "Monitor: tail -f ultra_fast_evaluation.log"
echo "Stop: kill $PID"
