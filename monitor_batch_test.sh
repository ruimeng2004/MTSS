#!/bin/bash
# Monitor batch test progress

echo "==================================================================="
echo "Batch Test Monitor"
echo "==================================================================="
echo ""

# Find latest output directory
LATEST_DIR=$(ls -td evaluation_output/batch_5_test_* 2>/dev/null | head -1)

if [ -z "$LATEST_DIR" ]; then
    echo "No batch test directory found"
    exit 1
fi

echo "Monitoring: $LATEST_DIR"
echo ""

# Check if process is running
if ps aux | grep -v grep | grep "test_batch_20.py" > /dev/null; then
    echo "✓ Process is running"
else
    echo "✗ Process is not running"
fi

echo ""
echo "-------------------------------------------------------------------"
echo "Directory Contents:"
echo "-------------------------------------------------------------------"
ls -lh "$LATEST_DIR"

echo ""
echo "-------------------------------------------------------------------"
echo "Bug Results:"
echo "-------------------------------------------------------------------"
if [ -d "$LATEST_DIR/bug_results" ]; then
    ls -lh "$LATEST_DIR/bug_results" | tail -20
    echo ""
    echo "Total bug results: $(ls -1 "$LATEST_DIR/bug_results" 2>/dev/null | wc -l)"
else
    echo "No bug_results directory yet"
fi

echo ""
echo "-------------------------------------------------------------------"
echo "Patches:"
echo "-------------------------------------------------------------------"
if [ -d "$LATEST_DIR/patches" ]; then
    ls -lh "$LATEST_DIR/patches" | tail -20
    echo ""
    echo "Total patches: $(ls -1 "$LATEST_DIR/patches" 2>/dev/null | wc -l)"
else
    echo "No patches directory yet"
fi

echo ""
echo "-------------------------------------------------------------------"
echo "JSON Files:"
echo "-------------------------------------------------------------------"
if [ -f "$LATEST_DIR/batch_evaluation.json" ]; then
    echo "✓ batch_evaluation.json exists"
    echo "  Size: $(ls -lh "$LATEST_DIR/batch_evaluation.json" | awk '{print $5}')"
else
    echo "✗ batch_evaluation.json not created yet"
fi

if [ -f "$LATEST_DIR/statistics.json" ]; then
    echo "✓ statistics.json exists"
    echo "  Size: $(ls -lh "$LATEST_DIR/statistics.json" | awk '{print $5}')"
else
    echo "✗ statistics.json not created yet"
fi

echo ""
echo "==================================================================="
echo "Last updated: $(date)"
echo "==================================================================="
