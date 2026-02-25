#!/bin/bash

# Pre-checkout all bugs before evaluation
# This significantly reduces evaluation time by avoiding repeated checkouts

echo "Starting pre-checkout of all bugs..."
echo "This will checkout 698 bugs to 100 worker directories"
echo "Estimated time: 10-15 minutes"
echo ""

python pre_checkout_bugs.py \
    --input-dir ppl/result/20260106_113852 \
    --workspace ./parallel_workspace \
    --d4j-path /Users/mengrui/Desktop/D4J/defects4j \
    --workers 100

echo ""
echo "Pre-checkout complete!"
echo "You can now run evaluation with pre-checked out bugs"
