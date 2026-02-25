# MTSS BTMS 预算分配路由增强 - 实施总结

## 任务完成情况

已成功将 `btms-budget-allocation` 项目中的预算分配方案应用到 MTSS 的评测路由机制中。

## 实施的功能

### 1. 核心架构（✅ 完成）

#### 基础选择器框架
- **文件**: `bug_task_model_selection/src/btms/selection/base_selector.py`
- **内容**:
  - `BaseSelector` - 抽象基类
  - `SelectionResult` - 选择结果数据结构
  - 支持二元决策和比例分配

#### 预算分配指标
- **文件**: `bug_task_model_selection/src/btms/selection/budget_metrics.py`
- **内容**:
  - `BudgetMetric` - 指标基类
  - `PPLGapMetric` - 基于困惑度差距
  - `VoteConsistencyMetric` - 投票与置信度结合
  - `SizeAdjustedMetric` - 簇大小调整
  - `HybridMetric` - 混合所有信号（推荐）

#### 预算分配器
- **文件**: `bug_task_model_selection/src/btms/selection/budget_allocator.py`
- **内容**:
  - `BudgetAllocator` - 实现比例分配
  - 支持四种指标切换
  - 比例边界约束（min_ratio, max_ratio）

#### 增强选择器
- **文件**: `bug_task_model_selection/src/btms/selection/enhanced_selector.py`
- **内容**:
  - `EnhancedTaskModelSelector` - 统一接口
  - `BinarySelector` - 二元选择实现
  - 支持从配置文件初始化
  - 自动保存统计信息

### 2. 自适应代表点（✅ 完成）

- **文件**: `bug_task_model_selection/src/btms/sampling/adaptive_reps.py`
- **功能**:
  - 根据簇大小动态确定代表点数量
  - 公式: `reps = min(max(min_reps, size // divisor), max_reps)`
  - 提供查找表生成

### 3. 异常值处理（✅ 完成）

- **文件**: `bug_task_model_selection/src/btms/sampling/outlier_handler.py`
- **功能**:
  - 检测小簇（size ≤ threshold）
  - 两种合并策略:
    - `single` - 合并到单一簇
    - `similarity` - 基于相似度分组
  - 应用映射到分配结果

### 4. 配置文件支持（✅ 完成）

- **文件**: `btms_config.yaml`
- **内容**:
  - 完整的配置选项
  - 四种指标的参数
  - 自适应代表点配置
  - 异常值处理配置
  - 消融研究示例配置

### 5. 评测脚本（✅ 完成）

- **文件**: `run_btms_enhanced_eval.py`
- **功能**:
  - 从配置文件加载设置
  - 运行任务建模选择
  - 生成簇级别和 bug 级别的路由决策
  - 保存统计信息

### 6. 测试验证（✅ 完成）

- **文件**: `test_btms_enhanced.py`
- **测试覆盖**:
  - ✅ 四种预算分配指标
  - ✅ 二元选择器和预算分配器
  - ✅ 自适应代表点计算
  - ✅ 异常值检测和合并
  - ✅ 端到端选择流程

### 7. 文档（✅ 完成）

- **文件**: `BTMS_ENHANCED_README.md`
- **内容**:
  - 完整的使用指南
  - API 文档
  - 配置说明
  - 示例代码
  - 故障排查

## 新增文件清单

```
MTSS/
├── bug_task_model_selection/src/btms/
│   ├── selection/
│   │   ├── base_selector.py           # 新增
│   │   ├── budget_allocator.py        # 新增
│   │   ├── budget_metrics.py          # 新增
│   │   ├── enhanced_selector.py       # 新增
│   │   └── __init__.py                # 已更新
│   └── sampling/
│       ├── adaptive_reps.py           # 新增
│       └── outlier_handler.py         # 新增
├── btms_config.yaml                   # 新增
├── run_btms_enhanced_eval.py          # 新增
├── test_btms_enhanced.py              # 新增
└── BTMS_ENHANCED_README.md            # 新增
```

## 核心设计理念

### 1. 模块化架构

所有组件都可以独立启用/禁用：
- 选择器类型（binary vs budget_allocator）
- 自适应代表点（enabled: true/false）
- 异常值处理（enabled: true/false）

### 2. 可插拔指标

四种预算分配指标可以灵活切换：
```python
budget_allocator:
  metric: "hybrid"  # 或 "ppl_gap", "vote_consistency", "size_adjusted"
```

### 3. 配置驱动

所有行为通过 YAML 配置文件控制，无需修改代码。

### 4. 向后兼容

保留了原有的二元选择器，可以通过配置切换。

## 技术实现亮点

### 1. 数学公式实现

准确实现了设计文档中的所有公式：

**PPL Gap**:
```python
gap = avg_edit - avg_gen
ratio = 1.0 / (1.0 + exp(-gap / temperature))
```

**Vote Consistency**:
```python
ratio = 0.5 + (base_ratio - 0.5) * confidence
```

**Hybrid**:
```python
final_ratio = 0.5 + (weighted_ratio - 0.5) * overall_confidence
```

### 2. 边界约束

防止极端分配：
```python
edit_ratio = max(min_ratio, min(max_ratio, raw_ratio))
```

### 3. 自适应计算

动态确定代表点数量：
```python
reps = min(max(min_reps, cluster_size // divisor), max_reps)
```

### 4. 异常值合并

支持层次聚类的相似度合并：
```python
labels = fcluster(Z, threshold, criterion='distance')
```

## 测试结果

运行 `test_btms_enhanced.py` 的测试结果：

```
✅ PPL Gap Metric - edit ratio: 0.984, confidence: 0.413
✅ Vote Consistency Metric - edit ratio: 0.667, confidence: 1.000
✅ Size Adjusted Metric - edit ratio: 0.667, confidence: 1.000
✅ Hybrid Metric - edit ratio: 0.725, confidence: 0.765
✅ Binary Selector - decision: edit, confidence: 0.500
✅ Budget Allocator - ratio: {edit: 0.577, gen: 0.423}
✅ Adaptive Representatives - 根据簇大小正确计算
✅ Outlier Handler - 正确检测和合并
✅ End-to-End Flow - 完整流程运行成功
```

## 使用示例

### 基本使用

```bash
# 运行测试
python test_btms_enhanced.py

# 运行评测
python run_btms_enhanced_eval.py --config btms_config.yaml
```

### 编程使用

```python
from bug_task_model_selection.src.btms.selection import BudgetAllocator

allocator = BudgetAllocator(metric="hybrid")
result = allocator.select(
    cluster_id=0,
    cluster_size=10,
    representatives=[...],
    ppl_edit={...},
    ppl_gen={...}
)

print(f"Decision: {result.decision}")
print(f"Edit ratio: {result.ratio['edit']:.2f}")
```

## 与原方案的对应关系

| btms-budget-allocation | MTSS 实现 | 状态 |
|------------------------|-----------|------|
| BaseSelector | base_selector.py | ✅ |
| BudgetAllocator | budget_allocator.py | ✅ |
| PPLGapMetric | budget_metrics.py | ✅ |
| VoteConsistencyMetric | budget_metrics.py | ✅ |
| SizeAdjustedMetric | budget_metrics.py | ✅ |
| HybridMetric | budget_metrics.py | ✅ |
| AdaptiveRepresentatives | adaptive_reps.py | ✅ |
| OutlierHandler | outlier_handler.py | ✅ |
| config.yaml | btms_config.yaml | ✅ |

## 下一步建议

### 1. 集成到评测流程

修改现有的评测脚本（如 `run_gen_batch_evaluation.py`）来使用新的路由决策：

```python
# 加载路由决策
with open('bug_routing.json') as f:
    routing = json.load(f)

# 根据决策选择模式
for bug_slug in bugs:
    decision = routing[bug_slug]['decision']
    ratio = routing[bug_slug]['ratio']
    
    if decision == 'edit':
        use_edit_mode(bug_slug)
    elif decision == 'gen':
        use_gen_mode(bug_slug)
    else:  # mixed
        # 根据 ratio 决定策略
        if ratio['edit'] > 0.5:
            use_edit_mode(bug_slug)
        else:
            use_gen_mode(bug_slug)
```

### 2. 实验和调优

运行消融研究：
- Baseline: 二元选择
- Exp 1: PPL Gap 指标
- Exp 2: Vote Consistency 指标
- Exp 3: Size Adjusted 指标
- Exp 4: Hybrid 指标（推荐）

### 3. 参数优化

根据实验结果调整：
- `divisor` - 控制代表点数量
- `min_ratio/max_ratio` - 分配边界
- 混合指标权重 - `ppl_weight`, `vote_weight`, `size_weight`

### 4. 扩展功能

可能的扩展方向：
- 支持更多指标
- 动态权重调整
- 在线学习
- 多模型集成

## 总结

已成功实现了完整的 BTMS 预算分配路由增强系统，包括：

✅ 四种预算分配指标  
✅ 自适应代表点计算  
✅ 异常值检测和合并  
✅ 配置文件支持  
✅ 评测脚本  
✅ 测试验证  
✅ 完整文档  

所有代码已经过测试验证，可以直接使用。系统设计遵循模块化、可配置、可扩展的原则，可以方便地集成到现有的 MTSS 评测流程中。
