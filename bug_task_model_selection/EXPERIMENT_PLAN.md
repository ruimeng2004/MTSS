# BTMS 实验计划

## 背景

基于已有实验报告，我们知道：
- 数据：698 个 bug，7 个 view，2 个模型（qwen3_coder, qwen3_30b）
- Baseline：qwen3_coder 55.6% (gen)，qwen3_30b 52.3% (edit)
- 已有发现：k 越大效果越好，但泛化能力下降

## 新模块能力

btms 模块新增：
- 聚类算法：KMeans, HAC (average/ward/complete/single), Bisecting KMeans
- 采样方法：Farthest-First, k-DPP
- 多代表投票：majority, mean_ppl

---

## 实验组设计

### 实验 1：聚类算法对比（核心实验）

**目标**：比较不同聚类算法在相同条件下的效果

**参数**：
- Views: buggy_code, buggy_code_obfuscated, report（选 3 个代表性 view）
- Algorithms: kmeans, hac_average, hac_ward, bisecting_kmeans
- K: 50, 100, 150, 200
- Sampling: farthest_first
- Reps: 1
- Models: qwen3_coder, qwen3_30b

**组合数**：3 × 4 × 4 × 1 × 1 × 2 = **96 组**

**预期**：
- 验证 KMeans vs HAC 的差异
- Ward linkage 是否比 average 更好
- Bisecting KMeans 是否有优势

---

### 实验 2：采样方法对比

**目标**：比较 Farthest-First 和 k-DPP 的效果

**参数**：
- Views: buggy_code, buggy_code_obfuscated
- Algorithms: kmeans, hac_average
- K: 50, 100, 150
- Sampling: farthest_first, kdpp
- Reps: 1, 3, 5
- Models: qwen3_coder, qwen3_30b

**组合数**：2 × 2 × 3 × 2 × 3 × 2 = **144 组**

**预期**：
- k-DPP 是否比 Farthest-First 更多样化
- 多代表（reps > 1）是否提升投票准确性

---

### 实验 3：多代表投票深度分析

**目标**：验证多代表投票的效果

**参数**：
- Views: buggy_code
- Algorithms: kmeans
- K: 100
- Sampling: farthest_first, kdpp
- Reps: 1, 3, 5, 7, 9
- Models: qwen3_coder, qwen3_30b

**组合数**：1 × 1 × 1 × 2 × 5 × 2 = **20 组**

**预期**：
- 找到最佳 reps 数量
- 验证投票是否能减少噪声

---

### 实验 4：全 View 扫描（验证性）

**目标**：在最佳配置下验证所有 view

**参数**：
- Views: 全部 7 个
- Algorithms: 实验 1 的最佳算法
- K: 100, 150
- Sampling: 实验 2 的最佳方法
- Reps: 实验 3 的最佳数量
- Models: qwen3_coder, qwen3_30b

**组合数**：7 × 1 × 2 × 1 × 1 × 2 = **28 组**

---

## 实验优先级

| 优先级 | 实验 | 组合数 | 预计时间 | 目的 |
|--------|------|--------|----------|------|
| P0 | 实验 1 | 96 | ~30 min | 核心算法对比 |
| P1 | 实验 2 | 144 | ~45 min | 采样方法对比 |
| P2 | 实验 3 | 20 | ~10 min | 投票深度分析 |
| P3 | 实验 4 | 28 | ~10 min | 全 view 验证 |

**总计**：288 组实验，预计 ~2 小时

---

## 配置文件

### experiment_1_clustering.yaml
```yaml
name: "exp1_clustering_comparison"
embeddings_path: "bug_task_model_selection/data/embeddings/embeddings.jsonl"
ppl_paths:
  edit: "bug_task_model_selection/data/ppl/qwen3_coder_edit.jsonl"
  gen: "bug_task_model_selection/data/ppl/qwen3_coder_gen.jsonl"

views:
  - buggy_code
  - buggy_code_obfuscated
  - report

clustering_algorithms:
  - kmeans
  - hac_average
  - hac_ward
  - bisecting_kmeans

k_values:
  - 50
  - 100
  - 150
  - 200

sampling_methods:
  - farthest_first

reps_per_cluster_values:
  - 1

output_dir: "bug_task_model_selection/data/exp1_clustering"
seed: 42
parallel: false
skip_existing: true
```

### experiment_2_sampling.yaml
```yaml
name: "exp2_sampling_comparison"
embeddings_path: "bug_task_model_selection/data/embeddings/embeddings.jsonl"
ppl_paths:
  edit: "bug_task_model_selection/data/ppl/qwen3_coder_edit.jsonl"
  gen: "bug_task_model_selection/data/ppl/qwen3_coder_gen.jsonl"

views:
  - buggy_code
  - buggy_code_obfuscated

clustering_algorithms:
  - kmeans
  - hac_average

k_values:
  - 50
  - 100
  - 150

sampling_methods:
  - farthest_first
  - kdpp

reps_per_cluster_values:
  - 1
  - 3
  - 5

output_dir: "bug_task_model_selection/data/exp2_sampling"
seed: 42
parallel: false
skip_existing: true
```

### experiment_3_voting.yaml
```yaml
name: "exp3_voting_depth"
embeddings_path: "bug_task_model_selection/data/embeddings/embeddings.jsonl"
ppl_paths:
  edit: "bug_task_model_selection/data/ppl/qwen3_coder_edit.jsonl"
  gen: "bug_task_model_selection/data/ppl/qwen3_coder_gen.jsonl"

views:
  - buggy_code

clustering_algorithms:
  - kmeans

k_values:
  - 100

sampling_methods:
  - farthest_first
  - kdpp

reps_per_cluster_values:
  - 1
  - 3
  - 5
  - 7
  - 9

output_dir: "bug_task_model_selection/data/exp3_voting"
seed: 42
parallel: false
skip_existing: true
```

---

## 评估指标

1. **Win Rate**：正确选择 edit/gen 的比例
2. **vs Baseline**：相对于最佳单一策略的提升
3. **Cluster 路由准确率**：代表是否正确预测 cluster 多数派
4. **运行时间**：各算法的效率对比

---

## 注意事项

1. 需要分别用 qwen3_coder 和 qwen3_30b 的 PPL 运行
2. 实验 1 完成后再决定实验 4 的具体参数
3. 建议先跑小规模验证，再跑全量
