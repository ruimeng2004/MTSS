#!/bin/bash
# Continuously watch evaluation progress

while true; do
    clear
    python check_fast_eval_progress.py
    echo ""
    echo "Refreshing in 30 seconds... (Ctrl+C to stop)"
    sleep 30
done
