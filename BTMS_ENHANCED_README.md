# MTSS 增强路由机制 - BTMS 预算分配

本文档描述了如何使用新的 BTMS（Bug Task Modeling Selection）预算分配增强功能来改进 MTSS 评测中的路由决策。

## 概述

基于 `btms-budget-allocation` 项目的设计，我们在 MTSS 中实现了以下增强功能：

### 新增功能

1. **预算分配器（Budget Allocator）**
   - 支持 edit 和 gen 模式之间的比例分配
   - 提供四种不同的分配指标：
     - PPL Gap：基于困惑度差距
     - Vote Consistency：结合投票与置信度
     - Size Adjusted：根据簇大小调整
     - Hybrid：混合所有信号（推荐）

2. **自适应代表点（Adaptive Representatives）**
   - 根据簇大小动态确定代表点数量
   - 公式：`reps = min(max(1, cluster_size // divisor), max_reps)`

3. **异常值处理器（Outlier Handler）**
   - 检测小簇（size ≤ threshold）
   - 支持合并策略：单一合并或基于相似度分组

## 架构

新增的模块位于 `bug_task_model_selection/src/btms/selection/` 和 `bug_task_model_selection/src/btms/sampling/`：

```
MTSS/
├── bug_task_model_selection/src/btms/
│   ├── selection/
│   │   ├── base_selector.py         # 基础选择器接口
│   │   ├── budget_allocator.py      # 预算分配器
│   │   ├── budget_metrics.py        # 四种分配指标
│   │   └── enhanced_selector.py     # 增强选择器
│   └── sampling/
│       ├── adaptive_reps.py         # 自适应代表点
│       └── outlier_handler.py       # 异常值处理
├── btms_config.yaml                 # 配置文件
├── run_btms_enhanced_eval.py        # 运行脚本
└── test_btms_enhanced.py            # 测试脚本
```

## 使用方法

### 1. 配置文件

编辑 `btms_config.yaml` 来配置路由策略：

```yaml
# 选择器类型：binary 或 budget_allocator
selector_type: "budget_allocator"

# 预算分配器配置
budget_allocator:
  metric: "hybrid"        # 使用混合指标
  min_ratio: 0.2          # 最小比例 20%
  max_ratio: 0.8          # 最大比例 80%
  
  metric_params:
    ppl_weight: 0.4       # PPL gap 权重
    vote_weight: 0.4      # 投票权重
    size_weight: 0.2      # 大小权重
    temperature: 1.0
    confidence_threshold: 0.5
    size_normalization_factor: 10

# 自适应代表点
adaptive_reps:
  enabled: true
  divisor: 3              # 簇大小除以此值得到基础代表点数
  max_reps: 7            # 最大代表点数
  min_reps: 1            # 最小代表点数

# 异常值检测
outlier_detection:
  enabled: true
  threshold: 2           # 大小 ≤ 2 的簇被视为异常值
  merge_strategy: "single"  # 或 "similarity"
```

### 2. 运行测试

验证实现是否正常工作：

```bash
cd /home/base/mengrui/MTSS
python test_btms_enhanced.py
```

这将测试：
- 四种预算分配指标
- 二元选择器和预算分配器
- 自适应代表点计算
- 异常值检测和合并
- 端到端选择流程

### 3. 运行增强评测

使用新的路由机制运行评测：

```bash
python run_btms_enhanced_eval.py \
  --config btms_config.yaml \
  --representatives data/sampling/representatives.jsonl \
  --ppl-edit data/ppl/edit_ppl.jsonl \
  --ppl-gen data/ppl/gen_ppl.jsonl \
  --assignments data/clustering/assignments.jsonl \
  --output evaluation_output/btms_enhanced \
  --routing-output evaluation_output/bug_routing.json
```

### 4. 输出结果

脚本会生成：

1. **cluster_choices.json** - 簇级别的选择结果
   ```json
   {
     "0": {
       "cluster_id": 0,
       "decision": "edit",
       "ratio": {"edit": 0.65, "gen": 0.35},
       "confidence": 0.78,
       "metadata": {...}
     }
   }
   ```

2. **selection_statistics.json** - 统计信息
   ```json
   {
     "total_clusters": 500,
     "selector_type": "budget_allocator",
     "decision_counts": {"edit": 300, "gen": 150, "mixed": 50},
     "average_confidence": 0.72,
     "edit_ratio": {"mean": 0.58, "min": 0.20, "max": 0.80}
   }
   ```

3. **bug_routing.json** - bug 级别的路由决策
   ```json
   {
     "Chart_1": {
       "slug": "Chart_1",
       "cluster_id": 0,
       "decision": "edit",
       "ratio": {"edit": 0.65, "gen": 0.35},
       "confidence": 0.78
     }
   }
   ```

## 四种分配指标详解

### 1. PPL Gap（困惑度差距）

基于 edit 和 gen PPL 的差距计算比例：

```python
gap = mean(edit_ppls) - mean(gen_ppls)
ratio_edit = sigmoid(-gap / temperature)
```

- **优点**：连续平滑，直接反映模型偏好强度
- **缺点**：忽略投票一致性，不考虑簇大小

### 2. Vote Consistency（投票一致性）

结合离散投票和连续置信度：

```python
base_ratio = edit_votes / total_votes
confidence = min(avg_gap / threshold, 1.0)
ratio_edit = 0.5 + (base_ratio - 0.5) * confidence
```

- **优点**：结合投票和 PPL gap 强度
- **缺点**：不考虑簇大小可靠性

### 3. Size Adjusted（大小调整）

根据簇大小调整置信度：

```python
vote_ratio = edit_votes / total_votes
size_factor = min(cluster_size / size_norm, 1.0)
ratio_edit = 0.5 + (vote_ratio - 0.5) * size_factor
```

- **优点**：考虑簇大小，小簇更保守
- **缺点**：只用投票，忽略 PPL gap 强度

### 4. Hybrid（混合）**（推荐）**

加权组合三个信号：

```python
final_ratio = 0.5 + (weighted_ratio - 0.5) * overall_confidence
```

其中：
- `weighted_ratio` 结合 PPL gap、投票和大小
- `overall_confidence` 综合所有置信度

- **优点**：综合所有优势，更鲁棒
- **缺点**：参数较多，需要调优

## 自适应代表点示例

使用 `divisor=3, max_reps=7, min_reps=1`：

| 簇大小 | 代表点数 |
|-------|---------|
| 1-2   | 1       |
| 3-5   | 1       |
| 6-8   | 2       |
| 9-11  | 3       |
| 12-14 | 4       |
| 15-17 | 5       |
| 18-20 | 6       |
| 21+   | 7 (上限) |

## 异常值处理示例

假设有以下簇大小（threshold=2）：

```python
cluster_sizes = {0: 1, 1: 2, 2: 10, 3: 1, 4: 15}
```

- **异常值簇**：0, 1, 3（size ≤ 2）
- **正常簇**：2, 4

**单一合并策略**：
```python
{0: -1, 1: -1, 3: -1}  # 所有异常值合并到簇 -1
```

## 消融研究配置

配置文件包含了多种实验配置示例：

### Baseline 1: 原始二元选择
```yaml
selector_type: "binary"
adaptive_reps:
  enabled: false
outlier_detection:
  enabled: false
```

### Baseline 2: 仅 PPL Gap
```yaml
selector_type: "budget_allocator"
budget_allocator:
  metric: "ppl_gap"
```

### 推荐配置: Hybrid + 自适应 + 异常值处理
```yaml
selector_type: "budget_allocator"
budget_allocator:
  metric: "hybrid"
adaptive_reps:
  enabled: true
outlier_detection:
  enabled: true
```

## API 使用示例

### 编程方式使用

```python
from bug_task_model_selection.src.btms.selection import (
    EnhancedTaskModelSelector,
    BudgetAllocator
)

# 方式 1: 使用配置文件
from run_btms_enhanced_eval import BTMSEnhancedEvaluator

evaluator = BTMSEnhancedEvaluator('btms_config.yaml')
cluster_choices = evaluator.run_selection()

# 方式 2: 直接使用选择器
selector = BudgetAllocator(
    metric="hybrid",
    min_ratio=0.2,
    max_ratio=0.8,
    metric_params={
        "ppl_weight": 0.4,
        "vote_weight": 0.4,
        "size_weight": 0.2
    }
)

result = selector.select(
    cluster_id=0,
    cluster_size=10,
    representatives=[...],
    ppl_edit={...},
    ppl_gen={...}
)

print(f"Decision: {result.decision}")
print(f"Ratio: {result.ratio}")
print(f"Confidence: {result.confidence}")
```

## 与现有评测系统集成

新的路由机制可以无缝集成到现有的 MTSS 评测流程中：

1. **生成路由决策**：使用 `run_btms_enhanced_eval.py` 生成 bug 级别的路由决策
2. **应用到评测**：读取 `bug_routing.json` 并根据 decision 选择 edit 或 gen 模式
3. **混合策略**：对于 `decision: "mixed"` 的 bug，可以：
   - 同时运行 edit 和 gen
   - 根据 ratio 分配计算资源
   - 优先使用置信度高的模式

## 性能优化建议

1. **缓存 PPL 分数**：避免重复计算
2. **并行处理簇**：簇级别选择可以并行化
3. **预计算簇大小**：避免重复统计
4. **调优参数**：
   - `divisor`：控制代表点数量，影响计算成本
   - `min_ratio/max_ratio`：防止极端分配
   - 指标权重：根据实验结果调整

## 故障排查

### 问题：找不到模块

确保正确设置 Python 路径：
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### 问题：PPL 分数缺失

检查 PPL 文件格式：
```json
{"slug": "Chart_1", "value": 15.5}
{"slug": "Chart_2", "value": 18.2}
```

### 问题：置信度过低

尝试调整参数：
- 增加 `confidence_threshold`
- 调整权重分配
- 使用不同的指标

## 参考

- 设计文档：`btms-budget-allocation/design-zh.md`
- 混合指标设计：`btms-budget-allocation/HYBRID_METRIC_DESIGN.md`
- 配置示例：`btms-budget-allocation/config-example.yaml`

## 下一步

1. 在真实数据上运行评测
2. 比较不同指标的性能
3. 进行消融研究
4. 根据结果优化参数
5. 集成到完整的 MTSS 评测流程
