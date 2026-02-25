# BTMS预算分配实验 - 完整数据说明

## 数据概览

已成功准备完整的Defects4J实验数据集，用于BTMS混合指标预算分配实验。

### 📊 数据规模

```json
{
  "qwen3_coder_k100_r3": {
    "description": "Qwen3-Coder, K=100, KDpp采样r=3",
    "bugs": 698,
    "clusters": 100,
    "representatives": 291
  },
  "qwen3_30b_k100_r3": {
    "description": "Qwen3-30B, K=100, KDpp采样r=3",
    "bugs": 698,
    "clusters": 100,
    "representatives": 291
  }
}
```

### 📁 数据目录结构

```
btms_budget_experiments/data/
├── datasets_info.json                    # 数据集元信息
├── qwen3_coder_k100_r3/                 # Qwen3-Coder数据集
│   ├── edit_ppl.jsonl                   # Edit模式PPL分数 (698行)
│   ├── gen_ppl.jsonl                    # Gen模式PPL分数 (698行)
│   ├── assignments.jsonl                # Bug到簇的分配 (698行)
│   └── representatives.jsonl            # 簇代表点 (291行)
└── qwen3_30b_k100_r3/                   # Qwen3-30B数据集
    ├── edit_ppl.jsonl                   # Edit模式PPL分数 (698行)
    ├── gen_ppl.jsonl                    # Gen模式PPL分数 (698行)
    ├── assignments.jsonl                # Bug到簇的分配 (698行)
    └── representatives.jsonl            # 簇代表点 (291行)
```

## 数据文件格式

### 1. edit_ppl.jsonl / gen_ppl.jsonl

**格式**: 每行一个JSON对象
```json
{"slug": "Chart_1", "value": 9.67145393500724e-06}
{"slug": "Chart_10", "value": 0.008792192200906537}
```

**字段说明**:
- `slug`: Bug标识符 (项目名_编号)
- `value`: 困惑度(PPL)分数，越小表示模型对该任务建模越好

### 2. representatives.jsonl

**格式**: 每行一个JSON对象
```json
{"cluster_id": 0, "rank": 1, "item_id": "Math_45__buggy_code", "slug": "Math_45", "view": "buggy_code"}
{"cluster_id": 0, "rank": 2, "item_id": "Math_3__buggy_code", "slug": "Math_3", "view": "buggy_code"}
```

**字段说明**:
- `cluster_id`: 簇ID (0-99)
- `rank`: 代表点在簇内的排名 (1-based)
- `item_id`: 项目标识符
- `slug`: Bug简称
- `view`: 视图类型 (buggy_code)

**统计**: 100个簇，共291个代表点，平均每簇2.9个代表点

### 3. assignments.jsonl

**格式**: 每行一个JSON对象
```json
{"slug": "Chart_1", "cluster_id": 42, "view": "buggy_code"}
{"slug": "Chart_10", "cluster_id": 15, "view": "buggy_code"}
```

**字段说明**:
- `slug`: Bug标识符
- `cluster_id`: 该bug所属的簇ID
- `view`: 视图类型

**统计**: 698个bugs分配到100个簇

## 数据来源

### 原始数据位置

- **PPL分数**: `/MTSS/bug_task_model_selection/data/ppl/`
  - `qwen3_coder_edit.jsonl` (698行)
  - `qwen3_coder_gen.jsonl` (698行)
  - `qwen3_30b_edit.jsonl` (698行)
  - `qwen3_30b_gen.jsonl` (698行)

- **聚类数据**: `/MTSS/bug_task_model_selection/data/exp3_voting_coder/buggy_code_kmeans_k100_kdpp_r3/`
  - `representatives.jsonl` (291行)
  - `assignments.jsonl` (698行)

### 数据生成方法

1. **PPL分数计算**: 
   - 使用Qwen3-Coder和Qwen3-30B模型
   - 分别对edit和gen两种任务建模方式计算困惑度
   - 在Defects4J数据集的698个bugs上测试

2. **聚类算法**:
   - 方法: K-means聚类
   - 簇数: K=100
   - 代表点采样: KDpp (k-DPP, Determinantal Point Process) 采样
   - 采样参数: r=3 (每簇最多3个代表点)
   - 视图: buggy_code (使用有bug的代码)

## 使用方式

### 在实验配置中引用

所有8个混合指标实验配置已更新为使用完整数据集：

```yaml
data_paths:
  edit_ppl: "../../data/qwen3_coder_k100_r3/edit_ppl.jsonl"
  gen_ppl: "../../data/qwen3_coder_k100_r3/gen_ppl.jsonl"
  assignments: "../../data/qwen3_coder_k100_r3/assignments.jsonl"
  representatives: "../../data/qwen3_coder_k100_r3/representatives.jsonl"
```

### 运行实验

```bash
cd /home/base/mengrui/MTSS/btms_budget_experiments/hybrid_metric_experiments

# 运行所有8个实验
./run_all_experiments.sh

# 或运行单个实验
./run_single_experiment.sh baseline1-ppl-only
```

## 数据质量验证

### 完整性检查

✅ **PPL数据**: 
- 698个bugs，每个都有edit和gen两个PPL分数
- 无缺失值

✅ **聚类数据**:
- 698个bugs全部分配到100个簇
- 100个簇都有代表点（平均2.9个/簇）

✅ **数据一致性**:
- PPL文件和聚类文件中的slug完全匹配
- 所有代表点都在assignments中有记录

### 数据分布

- **簇大小分布**: 1-20个bugs/簇（需要运行分析脚本查看详细分布）
- **代表点分布**: 1-3个/簇（KDpp采样保证）
- **PPL范围**: 1e-6 到 1e-2（对数正态分布）

## 与测试数据对比

| 特性 | 测试数据 (btms_demo) | 完整数据 (qwen3_coder_k100_r3) |
|------|---------------------|-------------------------------|
| Bugs数 | 27 | 698 |
| 簇数 | 5 | 100 |
| 代表点数 | 11 | 291 |
| 数据来源 | 演示样本 | 完整Defects4J |
| 用途 | 快速测试 | 正式实验 |

## 后续扩展

可以准备更多数据集变体：

1. **不同模型**: Qwen3-30B数据集已准备
2. **不同聚类配置**: K=50, K=150, K=200
3. **不同采样策略**: KDpp r=1, r=5, Farthest First等
4. **不同视图**: error, test, report等

这些数据已经在系统中，可以使用 `prepare_full_data.py` 脚本生成。

## 参考文档

- 混合指标设计: `/btms-budget-allocation/HYBRID_METRIC_DESIGN.md`
- BTMS实现总结: `/MTSS/BTMS_IMPLEMENTATION_SUMMARY.md`
- 实验配置: `/MTSS/btms_budget_experiments/hybrid_metric_experiments/README.md`
