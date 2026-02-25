#!/bin/bash

# Base directories
BASE_DIR="/home/base/mengrui/MTSS"
EVAL_SCRIPT="${BASE_DIR}/run_btms_routing_eval.py"
OUTPUT_ROOT="${BASE_DIR}/evaluation_output"
RESULTS_ROOT="${BASE_DIR}/btms_budget_experiments/qwencoder_experiments/results"

# Common inputs (we can use any existing cluster choices since we'll ignore it)
ASSIGNMENTS="/home/base/mengrui/MTSS/bug_task_model_selection/data/exp1_clustering_coder/buggy_code_kmeans_k100_farthest_first_r1/assignments.jsonl"
CLUSTER_CHOICES="${RESULTS_ROOT}/fixed-50-50/cluster_choices.json" # Just as a placeholder

# Edit/Gen result pools
EDIT_RESULTS="/home/base/mengrui/MTSS/ppl/result/Qwencoder_edit"

GEN_RESULTS="/home/base/mengrui/MTSS/ppl/result/Qwencoder_gen"

# 1. Pure Edit Strategy
echo "Running Pure Edit Evaluation..."
python3 "${EVAL_SCRIPT}" \
    --cluster-choices "${CLUSTER_CHOICES}" \
    --assignments "${ASSIGNMENTS}" \
    --edit-results "${EDIT_RESULTS}" \
    --gen-results "${GEN_RESULTS}" \
    --output "${OUTPUT_ROOT}/btms_routing_pure-edit" \
    --force-strategy "pure-edit"

# 2. Pure Gen Strategy
echo "Running Pure Gen Evaluation..."
python3 "${EVAL_SCRIPT}" \
    --cluster-choices "${CLUSTER_CHOICES}" \
    --assignments "${ASSIGNMENTS}" \
    --edit-results "${EDIT_RESULTS}" \
    --gen-results "${GEN_RESULTS}" \
    --output "${OUTPUT_ROOT}/btms_routing_pure-gen" \
    --force-strategy "pure-gen"

# 3. Random 50:50 Strategy
echo "Running Random 50:50 Evaluation..."
python3 "${EVAL_SCRIPT}" \
    --cluster-choices "${CLUSTER_CHOICES}" \
    --assignments "${ASSIGNMENTS}" \
    --edit-results "${EDIT_RESULTS}" \
    --gen-results "${GEN_RESULTS}" \
    --output "${OUTPUT_ROOT}/btms_routing_random-50-50" \
    --force-strategy "random-50-50"

echo "Control experiments completed."
