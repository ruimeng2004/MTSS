#!/bin/bash
# Run remaining routing evaluations
# 1. baseline1-ppl-only
# 2. baseline2-vote-only
# 3. exp1-hybrid-default
# 4. exp3-ppl-heavy
# 5. exp4-vote-heavy

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

# List of configurations to evaluate
declare -a CONFIGS=(
    "baseline1-ppl-only|${RESULTS_DIR}/baseline1-ppl-only/cluster_choices.json"
    "baseline2-vote-only|${RESULTS_DIR}/baseline2-vote-only/cluster_choices.json"
    "exp1-hybrid-default|${RESULTS_DIR}/exp1-hybrid-default/cluster_choices.json"
    "exp3-ppl-heavy|${RESULTS_DIR}/exp3-ppl-heavy/cluster_choices.json"
    "exp4-vote-heavy|${RESULTS_DIR}/exp4-vote-heavy/cluster_choices.json"
)

# Run Evaluations
echo "Step 3: Running remaining evaluations..."

for config_entry in "${CONFIGS[@]}"; do
    IFS="|" read -r config_name choices_path <<< "${config_entry}"
    
    echo "Running evaluation for: ${config_name}"
    OUTPUT_DIR="${OUTPUT_BASE}/btms_routing_${config_name}"
    mkdir -p "${OUTPUT_DIR}"
    
    LOG_FILE="${OUTPUT_DIR}/eval_log_$(date +%Y%m%d_%H%M%S).txt"
    
    echo "  Choices: ${choices_path}"
    echo "  Output: ${OUTPUT_DIR}"
    echo "  Log: ${LOG_FILE}"
    
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
    fi
    echo ""
done

echo "All remaining evaluations completed."
