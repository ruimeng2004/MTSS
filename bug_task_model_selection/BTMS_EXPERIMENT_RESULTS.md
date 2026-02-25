# BTMS 实验结果报告

**实验日期**: 2026-01-16  
**总实验数**: 260 组（全部成功）

## Baseline

| 模型 | always_edit | always_gen | 最佳单一策略 |
|------|-------------|------------|--------------|
| qwen3_coder | 44.4% | **55.6%** | gen |
| qwen3_30b | **52.3%** | 47.7% | edit |

---

## 实验 1：聚类算法对比

**配置**: 3 views × 4 algorithms × 4 k values × 1 sampling × 1 reps = 48 组/模型

### qwen3_coder 结果

| 算法 | 平均 Win Rate | vs Baseline |
|------|---------------|-------------|
| hac_average | **63.9%** | +8.3% |
| kmeans | 62.9% | +7.3% |
| bisecting_kmeans | 62.4% | +6.8% |
| hac_ward | 62.3% | +6.7% |

**最佳配置**: buggy_code + hac_average + k=200 → **69.6%** (+14.0%)

### qwen3_30b 结果

| 算法 | 平均 Win Rate | vs Baseline |
|------|---------------|-------------|
| hac_average | **62.4%** | +10.1% |
| bisecting_kmeans | 61.9% | +9.6% |
| kmeans | 61.3% | +9.0% |
| hac_ward | 61.1% | +8.8% |

**最佳配置**: buggy_code_obfuscated + hac_average + k=200 → **71.2%** (+18.9%)

### K 值影响

| k | coder | 30b |
|---|-------|-----|
| 50 | 57.8% | 54.7% |
| 100 | 61.1% | 60.3% |
| 150 | 64.8% | 64.5% |
| 200 | 67.8% | 67.2% |

**结论**: HAC (average linkage) 略优于其他算法，k 越大效果越好。

---

## 实验 2：采样方法对比

**配置**: 2 views × 2 algorithms × 3 k values × 2 sampling × 3 reps = 72 组/模型

### 采样方法对比

| 方法 | coder | 30b |
|------|-------|-----|
| farthest_first | **62.7%** | **60.6%** |
| kdpp | 60.2% | 59.2% |

**结论**: Farthest-First 略优于 k-DPP（约 +1.5%）

### 代表数量 (reps) 影响

| reps | coder | 30b |
|------|-------|-----|
| 1 | 59.4% | 58.8% |
| 3 | 62.0% | 59.7% |
| 5 | **63.0%** | **61.3%** |

**结论**: 多代表投票有效，reps=5 效果最好（约 +2-3%）

---

## 实验 3：投票深度分析

**配置**: kmeans + k=100 + buggy_code，测试 reps=1,3,5,7,9

### qwen3_coder

| reps | farthest_first | kdpp |
|------|----------------|------|
| 1 | 60.6% | 59.2% |
| 3 | 65.0% | 64.6% |
| 5 | 66.2% | 66.2% |
| 7 | 66.5% | 66.8% |
| 9 | **67.3%** | 67.0% |

### qwen3_30b

| reps | farthest_first | kdpp |
|------|----------------|------|
| 1 | 59.9% | 58.5% |
| 3 | 64.3% | 62.2% |
| 5 | 64.2% | 65.0% |
| 7 | 64.9% | 66.3% |
| 9 | **66.5%** | 66.9% |

**结论**: 
- reps 增加持续提升效果，但边际收益递减
- reps=5 是性价比较高的选择
- reps≥7 时 farthest_first 和 kdpp 效果接近

---

## 关键发现

### 1. 聚类算法
- **HAC (average)** 略优于 KMeans 和其他算法
- 差异不大（约 1%），KMeans 计算更快

### 2. 采样方法
- **Farthest-First** 略优于 k-DPP
- 差异约 1.5%，Farthest-First 更简单高效

### 3. 代表数量
- **多代表投票有效**，reps=5 是较好的平衡点
- 从 reps=1 到 reps=5，提升约 3-4%

### 4. K 值
- **k 越大效果越好**，与之前实验一致
- k=200 时 win rate 达到 67-71%

### 5. View
- **buggy_code** 和 **buggy_code_obfuscated** 效果最好
- report 效果稍差

---

## 推荐配置

| 参数 | 推荐值 | 备选 |
|------|--------|------|
| 聚类算法 | hac_average | kmeans |
| K 值 | 150-200 | 100 |
| 采样方法 | farthest_first | kdpp |
| 代表数量 | 5 | 3 |
| View | buggy_code | buggy_code_obfuscated |

**预期效果**: 
- qwen3_coder: 65-70% (+10-15% vs baseline)
- qwen3_30b: 65-71% (+13-19% vs baseline)

---

## 实验数据位置

```
bug_task_model_selection/data/
├── exp1_clustering_coder/    # 实验1 coder 结果
├── exp1_clustering_30b/      # 实验1 30b 结果
├── exp2_sampling_coder/      # 实验2 coder 结果
├── exp2_sampling_30b/        # 实验2 30b 结果
├── exp3_voting_coder/        # 实验3 coder 结果
└── exp3_voting_30b/          # 实验3 30b 结果
```

每个目录包含:
- `experiment_summary.json` - 汇总统计
- `experiment_results.csv` - 详细结果表
- `<config>/` - 每个配置的详细输出
