#!/bin/bash
# Run evaluation with probabilistic routing for all configurations

set -e

BASE_DIR="/home/base/mengrui/MTSS"
CONFIG_DIR="$BASE_DIR/btms_budget_experiments/qwencoder_experiments/configs"
SELECTIONS_DIR="$BASE_DIR/btms_budget_experiments/qwencoder_experiments/results_fixed"
EVAL_OUTPUT_DIR="$BASE_DIR/btms_budget_experiments/qwencoder_experiments/evaluation_output_probabilistic"
CLUSTER_DATA_DIR="$BASE_DIR/btms_budget_experiments/data/qwen3_coder_k100_r3"
EDIT_RESULTS_DIR="$BASE_DIR/ppl/result/Qwencoder_edit"
GEN_RESULTS_DIR="$BASE_DIR/ppl/result/Qwencoder_gen"
D4J_PATH="/home/base/mengrui/defects4j"
WORKSPACE_BASE="/home/base/mengrui/btms_routing_workspace"

NUM_WORKERS=100
TIMEOUT=300

CONFIGS=(
    "baseline1-ppl-only"
    "baseline2-vote-only"
    "baseline3-size-adjusted"
    "exp1-hybrid-default"
    "exp2-hybrid-balanced"
    "exp3-ppl-heavy"
    "exp4-vote-heavy"
    "exp5-size-heavy"
)

echo "=========================================="
echo "Probabilistic Routing Evaluation Pipeline"
echo "=========================================="
echo "Start time: $(date)"
echo "Configs: ${#CONFIGS[@]}"
echo "Workers: $NUM_WORKERS"
echo ""

mkdir -p "$EVAL_OUTPUT_DIR"

TOTAL_START=$(date +%s)

for config_name in "${CONFIGS[@]}"; do
    echo ""
    echo "=========================================="
    echo "Processing: $config_name"
    echo "=========================================="
    
    CONFIG_FILE="$CONFIG_DIR/${config_name}.yaml"
    SELECTIONS_PATH="$SELECTIONS_DIR/${config_name}/cluster_choices.json"
    ASSIGNMENTS_PATH="$CLUSTER_DATA_DIR/assignments.jsonl"
    OUTPUT_DIR="$EVAL_OUTPUT_DIR/${config_name}"
    
    CONFIG_START=$(date +%s)
    
    echo ""
    echo "Step 1: Evaluation with probabilistic routing"
    echo "Time: $(date)"
    
    cd "$BASE_DIR"
    python3 run_btms_routing_eval.py \
        --cluster-choices "$SELECTIONS_PATH" \
        --assignments "$ASSIGNMENTS_PATH" \
        --edit-results "$EDIT_RESULTS_DIR" \
        --gen-results "$GEN_RESULTS_DIR" \
        --output "$OUTPUT_DIR" \
        --d4j-path "$D4J_PATH" \
        --workspace "$WORKSPACE_BASE" \
        --workers $NUM_WORKERS \
        --timeout $TIMEOUT
    
    CONFIG_END=$(date +%s)
    CONFIG_DURATION=$((CONFIG_END - CONFIG_START))
    
    echo ""
    echo "✓ Completed $config_name in ${CONFIG_DURATION}s ($(($CONFIG_DURATION / 60))m)"
    echo ""
done

TOTAL_END=$(date +%s)
TOTAL_DURATION=$((TOTAL_END - TOTAL_START))

echo ""
echo "=========================================="
echo "All evaluations completed!"
echo "=========================================="
echo "Total time: ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)"
echo "End time: $(date)"
echo ""
echo "Results saved to:"
echo "  - Evaluation output: $EVAL_OUTPUT_DIR"
echo ""
