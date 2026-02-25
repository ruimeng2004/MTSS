#!/bin/bash
# Run BTMS routing evaluation with the best performing configuration
# Best config: baseline3-size-adjusted (置信度0.343)

set -e

# Configuration
BEST_CONFIG="baseline3-size-adjusted"
EXPERIMENT_DIR="/home/base/mengrui/MTSS/btms_budget_experiments/qwencoder_experiments"
DATA_DIR="/home/base/mengrui/MTSS/btms_budget_experiments/data/qwen3_coder_k100_r3"
OUTPUT_DIR="/home/base/mengrui/MTSS/evaluation_output/btms_routing_${BEST_CONFIG}"

# Paths
CLUSTER_CHOICES="${EXPERIMENT_DIR}/results/${BEST_CONFIG}/cluster_choices.json"
ASSIGNMENTS="${DATA_DIR}/assignments.jsonl"
EDIT_RESULTS="/home/base/mengrui/MTSS/ppl/result/Qwencoder_edit"
GEN_RESULTS="/home/base/mengrui/MTSS/ppl/result/Qwencoder_gen"
D4J_PATH="/home/base/mengrui/defects4j"
WORKSPACE="/home/base/mengrui/MTSS/btms_routing_workspace"

# Log file
LOG_FILE="btms_routing_${BEST_CONFIG}_$(date +%Y%m%d_%H%M%S).log"

echo "=========================================="
echo "BTMS Routing Evaluation"
echo "=========================================="
echo "Configuration: ${BEST_CONFIG}"
echo "Cluster choices: ${CLUSTER_CHOICES}"
echo "Assignments: ${ASSIGNMENTS}"
echo "Edit results: ${EDIT_RESULTS}"
echo "Gen results: ${GEN_RESULTS}"
echo "Output: ${OUTPUT_DIR}"
echo "Log file: ${LOG_FILE}"
echo "=========================================="
echo ""

# Verify files exist
if [ ! -f "${CLUSTER_CHOICES}" ]; then
    echo "ERROR: Cluster choices file not found: ${CLUSTER_CHOICES}"
    exit 1
fi

if [ ! -f "${ASSIGNMENTS}" ]; then
    echo "ERROR: Assignments file not found: ${ASSIGNMENTS}"
    exit 1
fi

if [ ! -d "${EDIT_RESULTS}" ]; then
    echo "ERROR: Edit results directory not found: ${EDIT_RESULTS}"
    exit 1
fi

if [ ! -d "${GEN_RESULTS}" ]; then
    echo "ERROR: Gen results directory not found: ${GEN_RESULTS}"
    exit 1
fi

# Run evaluation
echo "Starting BTMS routing evaluation..."
echo ""

python3 run_btms_routing_eval.py \
    --cluster-choices "${CLUSTER_CHOICES}" \
    --assignments "${ASSIGNMENTS}" \
    --edit-results "${EDIT_RESULTS}" \
    --gen-results "${GEN_RESULTS}" \
    --output "${OUTPUT_DIR}" \
    --d4j-path "${D4J_PATH}" \
    --workspace "${WORKSPACE}" \
    --workers 32 \
    --timeout 300 \
    2>&1 | tee "${LOG_FILE}"

echo ""
echo "=========================================="
echo "Evaluation completed!"
echo "Results saved to: ${OUTPUT_DIR}"
echo "Log file: ${LOG_FILE}"
echo "=========================================="
