#!/bin/bash
# Monitor progress of probabilistic routing evaluation

LOG_FILE="/home/base/mengrui/MTSS/probabilistic_routing_eval.log"

echo "================================================================================"
echo "Probabilistic Routing Evaluation - Progress Monitor"
echo "================================================================================"
echo ""

# Check if running
if ps aux | grep "run_probabilistic_routing_eval.sh" | grep -v grep > /dev/null; then
    echo "✓ Status: RUNNING"
else
    echo "✗ Status: NOT RUNNING (completed or failed)"
fi
echo ""

# Check current config being processed
echo "Current Activity:"
echo "----------------"
tail -50 "$LOG_FILE" | grep -E "Processing:|Step 1:|Completed" | tail -5
echo ""

# Check routing distribution (should be different from old deterministic routing)
echo "Routing Distribution (baseline1-ppl-only):"
echo "-------------------------------------------"
grep -A 3 "Routing distribution:" "$LOG_FILE" | head -4
echo ""
echo "Note: Old deterministic routing was 289 Edit / 409 Gen (41.4% / 58.6%)"
echo "      New probabilistic should show ~347 Edit / 351 Gen (49.7% / 50.3%)"
echo ""

# Check for any errors
echo "Recent Errors/Warnings:"
echo "----------------------"
grep -E "ERROR|error:" "$LOG_FILE" | tail -5
if [ $? -ne 0 ]; then
    echo "(No errors found)"
fi
echo ""

# Count completed bugs
echo "Progress Stats:"
echo "---------------"
TOTAL_BUGS=698
COMPLETED=$(grep -c "✓.*fixed with attempt\|✗.*failed all" "$LOG_FILE" || echo "0")
echo "Bugs evaluated: $COMPLETED / $TOTAL_BUGS"
if [ "$COMPLETED" -gt 0 ]; then
    PROGRESS=$(echo "scale=1; $COMPLETED * 100 / $TOTAL_BUGS" | bc)
    echo "Progress: ${PROGRESS}%"
fi
echo ""

# Estimate time remaining (rough estimate based on first config)
echo "Configurations:"
echo "---------------"
grep "Processing:" "$LOG_FILE" | sed 's/^.*Processing: /  - /'
echo ""

echo "================================================================================"
echo "Real-time log tail (last 10 lines):"
echo "================================================================================"
tail -10 "$LOG_FILE"
echo ""
echo "To view full log: tail -f $LOG_FILE"
echo "To check results: ls -la /home/base/mengrui/MTSS/btms_budget_experiments/qwencoder_experiments/evaluation_output_probabilistic/"
