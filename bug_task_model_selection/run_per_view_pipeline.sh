#!/bin/bash
# Run clustering pipeline for each view separately

VIEWS="report test error error_plus_test buggy_code buggy_code_obfuscated buggy_code_mixed"
K=20

for VIEW in $VIEWS; do
    echo "=========================================="
    echo "Processing view: $VIEW"
    echo "=========================================="
    
    # 1. Prepare vectors (filtered by view)
    python -m bug_task_model_selection.src.cluster_prep \
        --embeddings bug_task_model_selection/data/embeddings/embeddings.jsonl \
        --outdir bug_task_model_selection/data/vectors_${VIEW} \
        --view $VIEW
    
    # 2. Hierarchical clustering
    python -m bug_task_model_selection.src.cluster_hac \
        --vectors bug_task_model_selection/data/vectors_${VIEW}/vectors.npy \
        --id-mapping bug_task_model_selection/data/vectors_${VIEW}/id_mapping.pkl \
        --metadata bug_task_model_selection/data/vectors_${VIEW}/metadata.pkl \
        --outdir bug_task_model_selection/data/clusters_${VIEW} \
        --ks $K
    
    # 3. Select representatives
    python -m bug_task_model_selection.src.cluster_representatives \
        --vectors bug_task_model_selection/data/vectors_${VIEW}/vectors.npy \
        --id-mapping bug_task_model_selection/data/vectors_${VIEW}/id_mapping.pkl \
        --metadata bug_task_model_selection/data/vectors_${VIEW}/metadata.pkl \
        --cuts-dir bug_task_model_selection/data/clusters_${VIEW}/cuts \
        --ks $K \
        --outdir bug_task_model_selection/data/representatives_${VIEW}
    
    # 4. Task model selection (qwen3_coder: edit vs gen)
    python -m bug_task_model_selection.src.task_model_selector \
        --representatives bug_task_model_selection/data/representatives_${VIEW}/k=${K}/representatives.jsonl \
        --ppl edit=bug_task_model_selection/data/ppl/qwen3_coder_edit.jsonl \
        --ppl gen=bug_task_model_selection/data/ppl/qwen3_coder_gen.jsonl \
        --outdir bug_task_model_selection/data/selection_${VIEW}/k=${K}_qwen3_coder
    
    # 5. Overall metrics
    python -m bug_task_model_selection.src.overall_metrics \
        --assignments bug_task_model_selection/data/clusters_${VIEW}/cuts/k=${K}/assignments.jsonl \
        --choices bug_task_model_selection/data/selection_${VIEW}/k=${K}_qwen3_coder/cluster_choices.json \
        --ppl edit=bug_task_model_selection/data/ppl/qwen3_coder_edit.jsonl \
        --ppl gen=bug_task_model_selection/data/ppl/qwen3_coder_gen.jsonl \
        --outdir bug_task_model_selection/data/overall_${VIEW}/k=${K}_qwen3_coder
    
    echo ""
done

echo "=========================================="
echo "All views processed. Comparing results..."
echo "=========================================="
