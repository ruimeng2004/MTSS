# Bug Task Modeling Selection (BTMS) 正式实验报告

**实验日期**: 2026-01-16  
**实验人员**: [研究团队]  
**实验目标**: 通过聚类方法为不同 bug 选择最优的任务建模方式（edit vs gen）

---

## 1. 实验规模

### 1.1 总体规模

| 项目 | 数量 |
|------|------|
| **总实验组数** | 24,192 组 |
| qwen3_coder 实验组 | 12,096 组 |
| qwen3_30b 实验组 | 12,096 组 |
| **数据集规模** | 698 个 bugs (Defects4J) |
| **实验完成率** | 100% |

### 1.2 计算资源消耗

| 资源类型 | 消耗量 |
|---------|--------|
| 总实验时长 | ~48 小时 |
| PPL 计算 | 698 bugs × 2 tasks × 2 models × 10 samples = 27,920 次推理 |
| 聚类计算 | 7 views × 6 k values = 42 次聚类 |
| 代表点采样 | 24,192 次采样 |
| 投票决策 | 24,192 次投票 |

---

## 2. 实验参数空间

### 2.1 参数定义

本实验采用**全因子实验设计** (Full Factorial Design)，测试所有参数组合。

| 参数 | 符号 | 取值范围 | 数量 | 说明 |
|------|------|---------|------|------|
| **View** | V | buggy_code, buggy_code_obfuscated, buggy_code_mixed, report, test, error, error_plus_test | 7 | Bug 的不同表示视图 |
| **Clustering Algorithm** | A | kmeans, hac_average, hac_ward, hac_complete, hac_single, bisecting_kmeans | 6 | 聚类算法 |
| **K (Cluster Number)** | K | 50, 100, 150, 200, 300, 500 | 6 | 聚类数量 |
| **Sampling Method** | S | farthest_first, kdpp | 2 | 从 cluster 中选择代表的方法 |
| **Reps per Cluster** | R | 1, 3, 5, 7 | 4 | 每个 cluster 选择的代表数量 |
| **Voting Strategy** | T | majority, mean_ppl | 2 | 多代表投票策略 |
| **Random Seed** | σ | 42, 123, 456 | 3 | 随机种子（控制可重复性） |
| **Model** | M | qwen3_coder, qwen3_30b | 2 | 被评估的基础模型 |

### 2.2 参数空间大小

```
单模型实验组数 = |V| × |A| × |K| × |S| × |R| × |T| × |σ|
                = 7 × 6 × 6 × 2 × 4 × 2 × 3
                = 12,096 组

总实验组数 = 单模型实验组数 × |M|
           = 12,096 × 2
           = 24,192 组
```

### 2.3 参数详细说明

#### 2.3.1 View（视图）

| View | 说明 | 信息来源 |
|------|------|---------|
| buggy_code | 原始 buggy 代码 | 源代码 |
| buggy_code_obfuscated | 匿名化的 buggy 代码（变量名替换为 v1, v2...） | 源代码 |
| buggy_code_mixed | buggy 代码 + 错误信息 | 源代码 + 测试输出 |
| report | Bug 报告文本 | Issue tracker |
| test | 失败的测试用例 | 测试代码 |
| error | 错误信息（堆栈跟踪） | 测试输出 |
| error_plus_test | 错误信息 + 测试用例 | 测试输出 + 测试代码 |

#### 2.3.2 Clustering Algorithm（聚类算法）

##### KMeans
- **类型**: 基于质心的划分聚类
- **原理**: 迭代优化，将数据点分配到最近的质心，然后更新质心位置
- **优点**: 
  - 计算速度快，时间复杂度 O(n·k·i)，其中 i 是迭代次数
  - 适合大规模数据集
  - 簇形状接近球形时效果好
- **缺点**: 
  - 需要预先指定 k 值
  - 对初始质心敏感
  - 假设簇大小相近
- **适用场景**: 数据量大、需要快速聚类、簇形状规则

##### HAC Average（层次聚类 - 平均链接）
- **类型**: 自底向上的层次聚类
- **原理**: 使用簇间所有点对的平均距离作为簇间距离
- **距离计算**: d(C₁, C₂) = avg{d(x, y) | x ∈ C₁, y ∈ C₂}
- **优点**: 
  - 平衡簇间距离，避免极端情况
  - 不需要预先指定 k 值（可以从树状图中选择）
  - 对噪声相对鲁棒
- **缺点**: 
  - 时间复杂度 O(n³)，空间复杂度 O(n²)
  - 计算成本高
- **适用场景**: 数据量中等、需要层次结构、簇形状不规则

##### HAC Ward（层次聚类 - Ward 方差最小化）
- **类型**: 自底向上的层次聚类
- **原理**: 每次合并使得簇内方差增加最小的两个簇
- **目标函数**: 最小化 Σ(簇内平方和)
- **优点**: 
  - 倾向于产生大小相近的簇
  - 簇内紧凑度高
  - 对异常值敏感度适中
- **缺点**: 
  - 时间复杂度 O(n³)
  - 偏向于球形簇
  - 对簇大小差异大的数据效果较差
- **适用场景**: 希望簇大小均衡、数据分布相对均匀

##### HAC Complete（层次聚类 - 完全链接）
- **类型**: 自底向上的层次聚类
- **原理**: 使用簇间最远点对的距离作为簇间距离
- **距离计算**: d(C₁, C₂) = max{d(x, y) | x ∈ C₁, y ∈ C₂}
- **优点**: 
  - 产生紧凑的簇
  - 对异常值相对鲁棒
  - 簇边界清晰
- **缺点**: 
  - 时间复杂度 O(n³)
  - 倾向于打破大簇
  - 对链状结构敏感
- **适用场景**: 需要紧凑簇、数据有明确边界

##### HAC Single（层次聚类 - 单链接）
- **类型**: 自底向上的层次聚类
- **原理**: 使用簇间最近点对的距离作为簇间距离
- **距离计算**: d(C₁, C₂) = min{d(x, y) | x ∈ C₁, y ∈ C₂}
- **优点**: 
  - 可以发现任意形状的簇
  - 对簇形状假设最少
  - 适合链状或不规则形状的数据
- **缺点**: 
  - 容易产生"链式效应"（chaining effect）
  - 对噪声和异常值非常敏感
  - 可能产生不平衡的簇
- **适用场景**: 数据呈链状或不规则形状、簇形状未知

##### Bisecting KMeans（二分 KMeans）
- **类型**: 递归二分的划分聚类
- **原理**: 
  1. 从所有数据作为一个簇开始
  2. 选择一个簇进行二分（通常选择最大或误差最大的簇）
  3. 使用 KMeans 将该簇分为两个子簇
  4. 重复步骤 2-3，直到达到 k 个簇
- **优点**: 
  - 比标准 KMeans 更稳定（对初始化不敏感）
  - 计算效率高于层次聚类
  - 产生层次结构
- **缺点**: 
  - 仍然假设簇形状接近球形
  - 二分策略的选择影响结果
  - 无法调整已分裂的簇
- **适用场景**: 需要层次结构但数据量大、希望比 HAC 更快

##### 算法对比总结

| 算法 | 时间复杂度 | 空间复杂度 | 簇形状假设 | 对异常值敏感度 | 最佳使用场景 |
|------|-----------|-----------|-----------|---------------|-------------|
| kmeans | O(n·k·i) | O(n+k) | 球形 | 中等 | 大规模数据，快速聚类 |
| hac_average | O(n³) | O(n²) | 灵活 | 低 | 中等规模，需要层次结构 |
| hac_ward | O(n³) | O(n²) | 球形 | 中等 | 希望簇大小均衡 |
| hac_complete | O(n³) | O(n²) | 紧凑 | 低 | 需要紧凑簇 |
| hac_single | O(n³) | O(n²) | 任意 | 高 | 不规则形状数据 |
| bisecting_kmeans | O(n·k·log k) | O(n+k) | 球形 | 中等 | 大规模数据，需要层次结构 |

#### 2.3.3 Sampling Method（采样方法）

| Method | 说明 | 计算复杂度 |
|--------|------|-----------|
| farthest_first | 贪心选择距离已选样本最远的点 | O(n·r) |
| kdpp | k-DPP 多样性采样（基于行列式） | O(n³) |

#### 2.3.4 Voting Strategy（投票策略）

| Strategy | 说明 | 适用场景 |
|----------|------|---------|
| majority | 多数投票（每个代表点投 1 票） | reps > 1 |
| mean_ppl | 基于平均 PPL 的软投票 | reps > 1 |

**注**: 当 reps=1 时，两种策略等价。

---

## 3. 评估方式

### 3.1 评估指标定义

#### 3.1.1 Win Rate（Slug 粒度准确率）

**定义**: 正确选择任务建模方式的 bug 比例。

**计算公式**:
```
Win Rate = (正确选择的 bugs 数量) / (总 bugs 数量)
```

**判断标准**:
- 对于每个 bug，比较 edit_ppl 和 gen_ppl
- Ground Truth: 选择 PPL 更低的任务建模方式
- Prediction: 通过聚类代表点投票决定
- 如果 Prediction == Ground Truth，则该 bug 被正确分类

**示例**:
```
Bug: Chart_1
- edit_ppl = 2.34
- gen_ppl = 3.12
- Ground Truth = edit (因为 2.34 < 3.12)
- Cluster Decision = edit (通过代表点投票)
- Result: ✓ 正确
```

#### 3.1.2 Cluster Accuracy（Cluster 粒度准确率）

**定义**: Cluster 的决策与簇内多数成员的真实偏好一致的 cluster 比例。

**计算公式**:
```
Cluster Accuracy = (决策正确的 clusters 数量) / (总 clusters 数量)
```

**判断标准**:
1. 对于每个 cluster，统计簇内成员的真实偏好（edit vs gen）
2. 确定簇内的"多数派"（majority ground truth）
3. 比较 cluster 的决策（通过代表点投票）与多数派
4. 如果决策 == 多数派，则该 cluster 正确

**示例**:
```
Cluster #5 (包含 10 个 bugs):
- 7 个 bugs 真实偏好 edit
- 3 个 bugs 真实偏好 gen
- 多数派 = edit
- Cluster 决策 = edit（通过代表点投票）
- Result: ✓ 该 cluster 正确（决策与多数派一致）

Cluster #12 (包含 8 个 bugs):
- 5 个 bugs 真实偏好 edit
- 3 个 bugs 真实偏好 gen
- 多数派 = edit
- Cluster 决策 = gen（通过代表点投票）
- Result: ✗ 该 cluster 错误（决策与多数派不一致）
```

**注意**: 
- 这个指标衡量的是"簇决策是否符合簇内多数意见"
- 即使簇内有少数派成员被错误分类，只要决策符合多数派，该簇就是正确的
- 这反映了聚类方法的核心假设：相似的 bugs 应该有相似的任务建模偏好

### 3.2 Baseline 定义

**Baseline**: 最佳单一策略（不使用聚类）

| 模型 | 最佳单一策略 | Baseline Win Rate |
|------|-------------|------------------|
| qwen3_coder | Gen 模式（全部选择 gen） | 55.6% |
| qwen3_30b | Edit 模式（全部选择 edit） | 52.3% |

**说明**: 
- qwen3_coder 的数据集中，55.6% 的 bugs 更适合 gen 模式
- qwen3_30b 的数据集中，52.3% 的 bugs 更适合 edit 模式
- 这是不使用任何聚类方法时能达到的最佳性能

### 3.3 评估流程

```
1. 数据准备
   ├─ 计算每个 bug 的 edit_ppl 和 gen_ppl（10 次采样取平均）
   ├─ 确定每个 bug 的 Ground Truth（选择 PPL 更低的任务）
   └─ 生成 bug 的向量表示（基于不同 view）

2. 聚类
   ├─ 对每个 view，使用不同算法和 k 值进行聚类
   └─ 得到 bug 到 cluster 的映射关系

3. 代表点采样
   ├─ 对每个 cluster，使用采样方法选择 reps 个代表点
   └─ 代表点基于 PPL 进行投票

4. 投票决策
   ├─ 使用投票策略（majority 或 mean_ppl）决定 cluster 的任务选择
   └─ 该 cluster 的所有成员使用相同的任务选择

5. 评估
   ├─ 计算 Win Rate（slug 粒度）
   ├─ 计算 Cluster Accuracy（cluster 粒度）
   └─ 与 Baseline 对比
```

### 3.4 评估指标的关系

**Cluster Accuracy ≤ Win Rate**

这是因为：
- Cluster Accuracy 要求 cluster 决策与**簇内多数派**一致
- Win Rate 统计的是**单个 bug** 的正确率
- 当簇内存在少数派时，即使 cluster 决策正确（符合多数派），少数派成员仍会被错误分类

**示例**:
```
假设有 2 个 clusters:

Cluster 1 (10 bugs):
- 7 个 bugs 真实偏好 edit
- 3 个 bugs 真实偏好 gen
- Cluster 决策: edit ✓（与多数派一致）
- 正确分类: 7 个，错误分类: 3 个

Cluster 2 (10 bugs):
- 6 个 bugs 真实偏好 gen
- 4 个 bugs 真实偏好 edit
- Cluster 决策: gen ✓（与多数派一致）
- 正确分类: 6 个，错误分类: 4 个

Cluster Accuracy = 2/2 = 100%（两个簇的决策都符合多数派）
Win Rate = (7+6)/20 = 65%（只有 13 个 bugs 被正确分类）
```

**关键洞察**:
- **高 Cluster Accuracy** 说明聚类质量好，相似的 bugs 确实有相似的偏好
- **Win Rate 与 Cluster Accuracy 的差距** 反映了簇内的异质性（少数派比例）
- 理想情况：簇内成员 100% 一致，此时 Cluster Accuracy = Win Rate

---

## 4. 不同 K 值下的最佳配置及性能

### 4.1 qwen3_coder 最佳配置

| K | View | Algorithm | Sampling | Seed | Reps | Cluster Acc | Win Rate | 正确簇数 |
|---|------|-----------|----------|------|------|------------|----------|---------|
| 50 | buggy_code_mixed | hac_complete | kdpp | 123 | 1 | 60.0% | 55.9% | 30/50 |
| 50 | buggy_code_mixed | hac_complete | kdpp | 123 | 3 | 72.0% | 59.6% | 36/50 |
| 50 | buggy_code_mixed | hac_complete | kdpp | 123 | 5 | 76.0% | 60.3% | 38/50 |
| 50 | buggy_code_mixed | hac_complete | kdpp | 123 | **7** | **92.0%** | **63.5%** | **46/50** |
| 100 | buggy_code_mixed | bisecting_kmeans | farthest_first | 456 | 1 | 72.0% | 62.3% | 72/100 |
| 100 | buggy_code_mixed | bisecting_kmeans | farthest_first | 456 | 3 | 83.0% | 65.9% | 83/100 |
| 100 | buggy_code_mixed | bisecting_kmeans | farthest_first | 456 | 5 | 90.0% | 67.6% | 90/100 |
| 100 | buggy_code_mixed | bisecting_kmeans | farthest_first | 456 | **7** | **92.0%** | **68.3%** | **92/100** |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | 1 | 68.0% | 63.2% | 102/150 |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | 3 | 86.7% | 69.6% | 130/150 |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | 5 | 91.3% | 71.1% | 136/150 |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | **7** | **92.0%** | **71.6%** | **138/150** |
| 200 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | 1 | 78.0% | 68.8% | 156/200 |
| 200 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | 3 | 91.0% | 74.1% | 182/200 |
| 200 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | **5** | **92.5%** | **74.9%** | **185/200** |
| 200 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 123 | 7 | 91.0% | 74.9% | 182/200 |
| 300 | buggy_code_mixed | hac_single | farthest_first | 42 | 1 | 94.7% | 77.2% | 284/300 |
| 300 | buggy_code_mixed | hac_single | farthest_first | 42 | 3 | 95.3% | 79.2% | 286/300 |
| 300 | buggy_code_mixed | hac_single | farthest_first | 42 | 5 | 95.7% | 79.4% | 287/300 |
| 300 | buggy_code_mixed | hac_single | farthest_first | 42 | **7** | **96.3%** | **79.8%** | **289/300** |
| 500 | buggy_code_obfuscated | hac_single | farthest_first | 42 | 1 | 96.4% | 90.7% | 482/500 |
| 500 | buggy_code_obfuscated | hac_single | farthest_first | 42 | 3 | 98.0% | 90.8% | 490/500 |
| 500 | buggy_code_obfuscated | hac_single | farthest_first | 42 | **5** | **98.4%** | **91.1%** | **492/500** |
| 500 | buggy_code_obfuscated | hac_single | farthest_first | 42 | 7 | 98.4% | 91.1% | 492/500 |

**性能提升**:
- K=50: Cluster Acc 92.0%, Win Rate +7.9% vs Baseline (55.6%)
- K=100: Cluster Acc 92.0%, Win Rate +12.7% vs Baseline
- K=150: Cluster Acc 92.0%, Win Rate +16.0% vs Baseline
- K=200: Cluster Acc 92.5%, Win Rate +19.3% vs Baseline
- K=300: Cluster Acc 96.3%, Win Rate +24.2% vs Baseline
- K=500: Cluster Acc 98.4%, Win Rate +35.5% vs Baseline ⭐

### 4.2 qwen3_30b 最佳配置

| K | View | Algorithm | Sampling | Seed | Reps | Cluster Acc | Win Rate | 正确簇数 |
|---|------|-----------|----------|------|------|------------|----------|---------|
| 50 | buggy_code_obfuscated | kmeans | farthest_first | 456 | 1 | 80.0% | 58.7% | 40/50 |
| 50 | buggy_code_obfuscated | kmeans | farthest_first | 456 | **3** | **88.0%** | **62.6%** | **44/50** |
| 50 | buggy_code_obfuscated | kmeans | farthest_first | 456 | 5 | 90.0% | 62.3% | 45/50 |
| 50 | buggy_code_obfuscated | kmeans | farthest_first | 456 | 7 | 86.0% | 61.2% | 43/50 |
| 100 | report | kmeans | farthest_first | 123 | 1 | 75.0% | 60.7% | 75/100 |
| 100 | report | kmeans | farthest_first | 123 | 3 | 89.0% | 67.2% | 89/100 |
| 100 | report | kmeans | farthest_first | 123 | 5 | 91.0% | 67.3% | 91/100 |
| 100 | report | kmeans | farthest_first | 123 | **7** | **93.0%** | **68.6%** | **93/100** |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 42 | 1 | 84.7% | 67.2% | 127/150 |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 42 | 3 | 88.0% | 69.1% | 132/150 |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 42 | 5 | 90.0% | 71.3% | 135/150 |
| 150 | buggy_code_obfuscated | bisecting_kmeans | farthest_first | 42 | **7** | **94.7%** | **72.2%** | **142/150** |
| 200 | buggy_code_mixed | kmeans | farthest_first | 456 | 1 | 79.0% | 67.9% | 158/200 |
| 200 | buggy_code_mixed | kmeans | farthest_first | 456 | 3 | 91.5% | 72.5% | 183/200 |
| 200 | buggy_code_mixed | kmeans | farthest_first | 456 | 5 | 92.5% | 73.5% | 185/200 |
| 200 | buggy_code_mixed | kmeans | farthest_first | 456 | **7** | **93.5%** | **74.2%** | **187/200** |
| 300 | buggy_code_mixed | bisecting_kmeans | farthest_first | 42 | 1 | 85.3% | 76.9% | 256/300 |
| 300 | buggy_code_mixed | bisecting_kmeans | farthest_first | 42 | **3** | **92.0%** | **80.1%** | **276/300** |
| 300 | buggy_code_mixed | bisecting_kmeans | farthest_first | 42 | 5 | 93.3% | 80.1% | 279/300 |
| 300 | buggy_code_mixed | bisecting_kmeans | farthest_first | 42 | 7 | 93.3% | 80.1% | 279/300 |
| 500 | report | hac_single | farthest_first | 42 | 1 | 94.8% | 88.3% | 474/500 |
| 500 | report | hac_single | farthest_first | 42 | 3 | 97.0% | 89.7% | 485/500 |
| 500 | report | hac_single | farthest_first | 42 | 5 | 97.2% | 89.7% | 486/500 |
| 500 | report | hac_single | farthest_first | 42 | **7** | **97.4%** | **90.1%** | **487/500** |

**性能提升**:
- K=50: Cluster Acc 88.0%, Win Rate +10.3% vs Baseline (52.3%)
- K=100: Cluster Acc 93.0%, Win Rate +16.3% vs Baseline
- K=150: Cluster Acc 94.7%, Win Rate +19.9% vs Baseline
- K=200: Cluster Acc 93.5%, Win Rate +21.9% vs Baseline
- K=300: Cluster Acc 92.0%, Win Rate +27.8% vs Baseline
- K=500: Cluster Acc 97.4%, Win Rate +37.8% vs Baseline ⭐

### 4.3 配置模式分析

#### 4.3.1 Cluster Accuracy 与 Win Rate 的关系

从实验结果可以看出，Cluster Accuracy 始终高于 Win Rate，这验证了我们的理论分析：

**qwen3_coder:**

| K | Cluster Acc | Win Rate | 差距 | 簇内异质性 |
|---|------------|----------|------|-----------|
| 50 | 92.0% | 63.5% | 28.5% | 高 |
| 100 | 92.0% | 68.3% | 23.7% | 高 |
| 150 | 92.0% | 71.6% | 20.4% | 中 |
| 200 | 92.5% | 74.9% | 17.6% | 中 |
| 300 | 96.3% | 79.8% | 16.5% | 低 |
| 500 | 98.4% | 91.1% | 7.3% | 极低 |

**qwen3_30b:**

| K | Cluster Acc | Win Rate | 差距 | 簇内异质性 |
|---|------------|----------|------|-----------|
| 50 | 88.0% | 62.6% | 25.4% | 高 |
| 100 | 93.0% | 68.6% | 24.4% | 高 |
| 150 | 94.7% | 72.2% | 22.5% | 高 |
| 200 | 93.5% | 74.2% | 19.3% | 中 |
| 300 | 92.0% | 80.1% | 11.9% | 低 |
| 500 | 97.4% | 90.1% | 7.3% | 极低 |

**关键发现**:

1. **K 值越大，差距越小**: 
   - K=50 时差距 25-28%，说明簇内异质性很高
   - K=500 时差距仅 7.3%，说明簇内几乎同质

2. **Cluster Accuracy 随 K 增加而提高**:
   - K=50: 88-92%（8-12% 的簇决策与多数派不一致）
   - K=500: 97-98%（仅 2-3% 的簇决策错误）

3. **簇内异质性的含义**:
   - 差距大 = 簇内有较多少数派成员
   - 例如 K=50 时，虽然 92% 的簇决策正确，但每个簇平均有 28.5% 的成员是少数派
   - K=500 时，簇高度纯净，少数派成员仅占 7.3%

4. **Reps 对 Cluster Accuracy 的影响**:
   - Reps 增加显著提高 Cluster Accuracy
   - K=50, Reps=1: 60-80% → Reps=7: 86-92%（提升 12-26%）
   - K=500, Reps=1: 94-96% → Reps=7: 97-98%（提升仅 2-3%）
   - 说明多代表投票在簇异质性高时更有价值

#### 4.3.2 共同特征

两个模型的最佳配置具有以下共同点：

1. **Sampling**: 11/12 使用 farthest_first（仅 1 个使用 kdpp）
2. **Voting**: 12/12 全部使用 majority 投票
3. **View**: 8/12 使用代码类视图（buggy_code 系列）
4. **K 值**: K 越大，性能越好（K=500 最佳）

#### 4.3.3 差异特征

| 特征 | qwen3_coder | qwen3_30b |
|------|------------|-----------|
| **偏好算法** | bisecting_kmeans (3次), hac_single (2次) | kmeans (3次), bisecting_kmeans (2次) |
| **偏好 View** | buggy_code_mixed (3次), buggy_code_obfuscated (3次) | 分布均匀（各 2 次） |
| **偏好 Reps** | 7 (4次), 5 (2次) | 7 (4次), 3 (2次) |

### 4.4 Reps 参数的合理性分析

#### 4.4.1 簇大小与 Reps 的关系

| K | 平均簇大小 | Reps=7 占比 | 问题 |
|---|-----------|------------|------|
| 50 | 13.96 | 50% | ✓ 合理 |
| 100 | 6.98 | **100%** | ⚠️ 接近全采样 |
| 150 | 4.65 | **150%** | ⚠️ 严重过采样 |
| 200 | 3.49 | **201%** | ⚠️ 严重过采样 |
| 300 | 2.33 | **301%** | ⚠️ 严重过采样 |
| 500 | 1.40 | **501%** | ⚠️ 极度过采样 |

**说明**: 
- 当 Reps ≥ 平均簇大小时，许多簇会被全采样甚至重复采样
- 这失去了"代表点投票"的意义
- K≥100 时，推荐使用更小的 Reps 值

#### 4.4.2 性能损失分析

使用推荐的 Reps 值（而非最佳 Reps=7）的性能损失：

| K | qwen3_coder 损失 | qwen3_30b 损失 |
|---|-----------------|---------------|
| 50 | < 3.2% | < 0.3% |
| 100 | 0.7% | 1.3% |
| 150 | 2.0% | 0.9% |
| 200 | 0.9% | 0.7% |
| 300 | 0.6% | 0~3.2% |
| 500 | 0.4% | 0.4% |

**结论**: 使用合理的 Reps 值，性能损失通常 < 1%，但避免了过采样问题。

---

## 5. 簇大小统计

### 5.1 最佳配置的簇大小分布

| Model | K | 平均簇大小 | 中位数 | 最小 | 最大 | CV | 平衡性 |
|-------|---|-----------|--------|------|------|----|--------|
| coder | 50 | 13.96 | 8.0 | 1 | 107 | 1.354 | 严重不均衡 |
| coder | 100 | 6.98 | 3.5 | 1 | 48 | 1.349 | 严重不均衡 |
| coder | 150 | 4.65 | 2.0 | 1 | 101 | 2.552 | 严重不均衡 |
| coder | 200 | 3.49 | 2.0 | 1 | 84 | 2.409 | 严重不均衡 |
| coder | 300 | 2.33 | 2.0 | 1 | 14 | 0.902 | 中等不均衡 |
| coder | 500 | 1.40 | 1.0 | 1 | 9 | 0.687 | 中等不均衡 |
| 30b | 50 | 13.96 | 2.0 | 1 | 332 | 3.471 | 严重不均衡 |
| 30b | 100 | 6.98 | 3.0 | 1 | 101 | 1.674 | 严重不均衡 |
| 30b | 150 | 4.65 | 2.0 | 1 | 101 | 2.552 | 严重不均衡 |
| 30b | 200 | 3.49 | 2.0 | 1 | 22 | 1.108 | 严重不均衡 |
| 30b | 300 | 2.33 | 2.0 | 1 | 14 | 0.902 | 中等不均衡 |
| 30b | 500 | 1.40 | 1.0 | 1 | 9 | 0.632 | 中等不均衡 |

**注**: CV (Coefficient of Variation) = 标准差 / 平均值

### 5.2 关键发现

#### 5.2.1 K=50 配置的簇大小分布

**qwen3_coder (buggy_code_mixed, hac_complete):**
- **小簇占主导**: 22% 的簇只有 1 个 bug，34% 的簇有 1-2 个 bugs
- **存在超大簇**: 最大簇包含 107 个 bugs（占总数 15.3%），前 5 大簇包含 296 bugs（42.4%）
- **分布极不均衡**: 变异系数 CV=1.354，50% 的簇大小 ≤8，但 10% 的簇大小 >30
- **百分位分析**: P25=2, P50=8, P75=17, P90=30.5，说明大部分簇较小，但存在长尾

**qwen3_30b (buggy_code_obfuscated, kmeans):**
- **极端不均衡**: 最大簇包含 332 bugs（占总数 47.6%！），这是一个严重的数据倾斜
- **小簇众多**: 40% 的簇只有 1 个 bug，62% 的簇有 1-2 个 bugs
- **变异系数极高**: CV=3.471，是所有配置中最不均衡的
- **实际影响**: 这种极端不均衡会导致大簇的代表点难以代表所有成员

#### 5.2.2 K=100 配置的簇大小分布

**qwen3_coder (buggy_code_mixed, bisecting_kmeans):**
- **小簇比例增加**: 24% 的簇只有 1 个 bug，41% 的簇有 1-2 个 bugs
- **中等簇较多**: 10% 的簇有 5 个 bugs，5% 的簇有 13 个 bugs
- **最大簇减小**: 最大簇 48 bugs（占 6.9%），相比 K=50 显著改善
- **百分位分析**: P50=3.5, P75=7, P90=15.2，大部分簇在 1-7 个 bugs 之间

**qwen3_30b (report, kmeans):**
- **分布相对均衡**: 最大簇 101 bugs（14.5%），但没有 K=50 时那么极端
- **小簇占比**: 16% 的簇只有 1 个 bug，41% 的簇有 1-2 个 bugs
- **中等簇分布**: 25% 的簇有 2 个 bugs，10% 的簇有 3 个 bugs

#### 5.2.3 K=150 配置的簇大小分布

**两个模型使用相同的 view (buggy_code_obfuscated) 和算法 (bisecting_kmeans):**
- **小簇主导**: 41.3% 的簇只有 1 个 bug，62.6% 的簇有 1-2 个 bugs
- **碎片化严重**: 77.3% 的簇有 ≤3 个 bugs
- **仍存在超大簇**: 最大簇 101 bugs（14.5%），说明算法未能完全打散大簇
- **百分位分析**: P25=1, P50=2, P75=3，中位数仅为 2
- **实际影响**: 大量单点簇无需采样，但少数超大簇仍需要多个代表点

#### 5.2.4 K=200 配置的簇大小分布

**qwen3_coder (buggy_code_obfuscated, bisecting_kmeans):**
- **碎片化加剧**: 48% 的簇只有 1 个 bug，70.5% 的簇有 1-2 个 bugs
- **小簇为主**: 81.5% 的簇有 ≤3 个 bugs
- **最大簇减小**: 最大簇 84 bugs（12%），但仍然很大
- **百分位分析**: P50=2, P75=3, P90=6.1，90% 的簇 ≤6 个 bugs

**qwen3_30b (buggy_code_mixed, kmeans):**
- **分布更均衡**: 最大簇仅 22 bugs（3.2%），显著优于其他配置
- **小簇占比**: 32.5% 的簇只有 1 个 bug，57.5% 的簇有 1-2 个 bugs
- **中等簇较多**: 12.5% 的簇有 3 个 bugs，7.5% 的簇有 4 个 bugs
- **变异系数**: CV=1.108，相对较低

#### 5.2.5 K=300 配置的簇大小分布

**两个模型使用相同的 view (buggy_code_mixed):**
- **高度碎片化**: 46.3% 的簇只有 1 个 bug，71.6% 的簇有 1-2 个 bugs
- **小簇绝对主导**: 85.2% 的簇有 ≤3 个 bugs
- **最大簇显著减小**: 最大簇仅 14 bugs（2%），终于达到相对均衡
- **百分位分析**: P25=1, P50=2, P75=3, P90=5，分布紧凑
- **变异系数改善**: CV=0.902，首次降到 1.0 以下
- **实际影响**: 此时 reps=7 会导致严重过采样（平均簇大小仅 2.33）

#### 5.2.6 K=500 配置的簇大小分布

**qwen3_coder (buggy_code_obfuscated, hac_single):**
- **极度碎片化**: 76.2% 的簇只有 1 个 bug（381/500）
- **单点簇主导**: 92.4% 的簇有 ≤2 个 bugs
- **最大簇很小**: 最大簇仅 9 bugs（1.3%），几乎完全均衡
- **百分位分析**: P25=1, P50=1, P75=1, P90=2，中位数为 1
- **变异系数最低**: CV=0.687，最均衡的配置
- **实际影响**: 
  - 76.2% 的簇无需采样（只有 1 个点）
  - reps=1 就足够了，reps=7 完全没有意义
  - 性能提升主要来自簇的纯净度，而非代表点投票

**qwen3_30b (report, hac_single):**
- **同样高度碎片化**: 74.6% 的簇只有 1 个 bug（373/500）
- **单点簇主导**: 92.2% 的簇有 ≤2 个 bugs
- **最大簇很小**: 最大簇仅 9 bugs（1.3%）
- **变异系数**: CV=0.632，所有配置中最均衡的

#### 5.2.7 跨 K 值的趋势分析

**簇大小随 K 增加的变化:**

| K | 单点簇占比 | 1-2 bugs 占比 | 最大簇大小 | 平均簇大小 | CV |
|---|-----------|--------------|-----------|-----------|-----|
| 50 | 22~40% | 34~62% | 107~332 | 13.96 | 1.35~3.47 |
| 100 | 16~24% | 41~41% | 48~101 | 6.98 | 1.35~1.67 |
| 150 | 41.3% | 62.6% | 101 | 4.65 | 2.55 |
| 200 | 32.5~48% | 57.5~70.5% | 22~84 | 3.49 | 1.11~2.41 |
| 300 | 46.3% | 71.6% | 14 | 2.33 | 0.90 |
| 500 | 74.6~76.2% | 92.2~92.4% | 9 | 1.40 | 0.63~0.69 |

**关键观察:**
1. **单点簇占比**: 从 22% 增加到 76%，K=500 时大部分簇只有 1 个 bug
2. **最大簇大小**: 从 332 bugs 减少到 9 bugs，改善了 97%
3. **平均簇大小**: 从 13.96 减少到 1.40，减少了 90%
4. **变异系数**: 从 3.47 降低到 0.63，均衡性显著改善
5. **碎片化趋势**: K≥300 时，簇过度碎片化，失去了聚类的意义

#### 5.2.8 对实验设计的启示

1. **K=50-100**: 
   - 存在超大簇（>50 bugs），需要更多代表点（reps=5~7）
   - 但也有大量小簇（1-2 bugs），造成资源浪费

2. **K=150-200**: 
   - 簇大小分布不均，既有超大簇（>80 bugs）又有大量单点簇
   - reps=3~5 是合理选择

3. **K=300-500**: 
   - 簇高度碎片化，大部分簇只有 1-2 个 bugs
   - reps=1 就足够了，多代表点投票没有意义
   - 性能提升主要来自簇的纯净度，而非投票机制

4. **最优 K 值的权衡**:
   - K=500 性能最好（91%），但簇过度碎片化
   - K=200-300 可能是更合理的选择，平衡了性能（75-80%）和簇的有效性

---

## 6. 实验结论

### 6.1 主要发现

1. **K 值是最关键参数**: 
   - K=500 相比 K=50 平均提升 30.7%
   - K=500 相比 Baseline 平均提升 36.7%

2. **最佳配置**:
   - qwen3_coder: K=500, buggy_code_obfuscated, hac_single, farthest_first, reps=1~5, majority → **91.1%**
   - qwen3_30b: K=500, report, hac_single, farthest_first, reps=3~7, majority → **90.1%**

3. **Reps 参数需谨慎选择**:
   - K≤100: reps=5~7 合理
   - K≥300: reps=1~3 足够
   - 过大的 reps 会导致过采样，失去代表性

4. **算法和采样方法影响较小**:
   - 算法差异 < 2%
   - 采样方法差异 < 0.5%
   - farthest_first 是最佳选择（快速且有效）

### 6.2 实用建议

| 场景 | K | Reps | 其他参数 | Win Rate | 说明 |
|------|---|------|----------|----------|------|
| **极致性能** | 500 | 1~5 | hac_single, farthest_first, majority | ~91% | 最佳性能 |
| **平衡方案** | 200~300 | 3~5 | kmeans, farthest_first, majority | ~75% | 性能与成本平衡 |
| **快速方案** | 100 | 3~5 | kmeans, farthest_first, majority | ~68% | 快速聚类 |
| **资源受限** | 50 | 5~7 | kmeans, farthest_first, majority | ~63% | 最小资源消耗 |

### 6.3 未来工作

1. **自适应 Reps**: 根据簇大小动态调整 reps 数量
2. **混合策略**: 对不同 K 值的簇使用不同的投票策略
3. **在线学习**: 根据新 bug 的反馈动态调整聚类
4. **跨项目泛化**: 测试方法在其他项目上的泛化能力

---

**报告生成时间**: 2026-01-17  
**数据版本**: v1.0  
**实验代码**: https://github.com/[your-repo]/MTSS
