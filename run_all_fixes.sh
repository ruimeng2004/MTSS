#!/bin/bash

# MTSS Root
MTSS_DIR="/home/base/mengrui/MTSS"
EVAL_DIR="$MTSS_DIR/evaluation_output"

# Add defects4j to PATH
export PATH="/home/base/mengrui/defects4j/framework/bin:$PATH"
echo "Using defects4j from: $(which defects4j)"

# Define configurations: "DIR_NAME:JSON_FILE"
CONFIGS=(
    "qwen30b_edit:parallel_evaluation_results.json"
    "qwen30b_gen:gen_batch_evaluation_results.json"
    "qwencoder_edit:edit_batch_evaluation_results.json"
    "qwencoder_gen:gen_batch_evaluation_results.json"
)

echo "Starting comprehensive re-evaluation..."

for config in "${CONFIGS[@]}"; do
    DIR__=${config%%:*}
    JSON_FILE=${config#*:}
    
    FULL_JSON_PATH="$EVAL_DIR/$DIR__/$JSON_FILE"
    LIST_FILE="$EVAL_DIR/$DIR__/reevaluation_list.json"
    
    echo "----------------------------------------------------------------"
    echo "Processing $DIR__ ..."
    echo "Target: $FULL_JSON_PATH"
    
    if [ ! -f "$FULL_JSON_PATH" ]; then
        echo "Error: Result file not found: $FULL_JSON_PATH"
        continue
    fi
    
    # Step 1: Generate list
    echo "Generating re-evaluation list..."
    python3 "$MTSS_DIR/auto_fix_false_negatives.py" "$FULL_JSON_PATH"
    
    # Step 2: Run enhanced evaluation
    if [ -f "$LIST_FILE" ]; then
        echo "Running enhanced evaluation..."
        python3 "$MTSS_DIR/enhanced_evaluation.py" "$LIST_FILE"
    else
        echo "Skipping re-evaluation (list not generated or empty)."
    fi
    
    echo "Done with $DIR__"
done

echo "----------------------------------------------------------------"
echo "All processing complete."
