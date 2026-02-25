#!/bin/bash
# Run routing evaluation for multiple configurations:
# 1. New "Fixed 50-50" baseline
# 2. General recommendation (Exp 2 - Balanced)
# 3. High reliability recommendation (Exp 5 - Size Heavy)

# Stop on error
set -e

# Base directories
BASE_DIR="/home/base/mengrui/MTSS/btms_budget_experiments"
DATA_DIR="${BASE_DIR}/data/qwen3_coder_k100_r3"
RESULTS_DIR="${BASE_DIR}/qwencoder_experiments/results"
OUTPUT_BASE="/home/base/mengrui/MTSS/evaluation_output"

# Common parameters
ASSIGNMENTS="${DATA_DIR}/assignments.jsonl"
EDIT_RESULTS="/home/base/mengrui/MTSS/ppl/result/Qwencoder_edit"
GEN_RESULTS="/home/base/mengrui/MTSS/ppl/result/Qwencoder_gen"
D4J_PATH="/home/base/mengrui/defects4j"
WORKSPACE="/home/base/mengrui/MTSS/btms_routing_workspace"
WORKERS=32
TIMEOUT=300

# 1. Generate Fixed 50-50 Baseline
echo "Step 1: Generating Fixed 50-50 Baseline configuration..."
python3 "${BASE_DIR}/create_fixed_50_50_eval_config.py" \
    --assignments "${ASSIGNMENTS}" \
    --output-dir "${RESULTS_DIR}/fixed-50-50"

# List of configurations to evaluate
# format: "config_name|path_to_cluster_choices.json"
declare -a CONFIGS=(
    "fixed-50-50|${RESULTS_DIR}/fixed-50-50/cluster_choices.json"
    "exp2-hybrid-balanced|${RESULTS_DIR}/exp2-hybrid-balanced/cluster_choices.json"
    "exp5-size-heavy|${RESULTS_DIR}/exp5-size-heavy/cluster_choices.json"
)

# 2. Run Evaluations
echo "Step 2: running evaluations..."

for config_entry in "${CONFIGS[@]}"; do
    IFS="|" read -r config_name choices_path <<< "${config_entry}"
    
    echo "Running evaluation for: ${config_name}"
    OUTPUT_DIR="${OUTPUT_BASE}/btms_routing_${config_name}"
    mkdir -p "${OUTPUT_DIR}"
    
    LOG_FILE="${OUTPUT_DIR}/eval_log_$(date +%Y%m%d_%H%M%S).txt"
    
    echo "  Choices: ${choices_path}"
    echo "  Output: ${OUTPUT_DIR}"
    echo "  Log: ${LOG_FILE}"
    
    # Run evaluation script
    # We use 'time' to measure total duration
    if python3 "${BASE_DIR}/../run_btms_routing_eval.py" \
        --cluster-choices "${choices_path}" \
        --assignments "${ASSIGNMENTS}" \
        --edit-results "${EDIT_RESULTS}" \
        --gen-results "${GEN_RESULTS}" \
        --output "${OUTPUT_DIR}" \
        --d4j-path "${D4J_PATH}" \
        --workspace "${WORKSPACE}" \
        --workers "${WORKERS}" \
        --timeout "${TIMEOUT}" > "${LOG_FILE}" 2>&1; then
        echo "  [SUCCESS] Evaluation completed for ${config_name}"
    else
        echo "  [FAILURE] Evaluation failed for ${config_name}. Check log: ${LOG_FILE}"
        # We continue even if one fails
    fi
    echo ""
done

echo "All evaluations requested."
