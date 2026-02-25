# MTSS BTMS 预算分配路由 - 快速开始

## 🚀 立即开始

### 1️⃣ 验证安装（30秒）

```bash
cd /home/base/mengrui/MTSS
python test_btms_enhanced.py
```

如果看到 `All tests completed successfully!`，说明安装成功！

### 2️⃣ 查看配置（1分钟）

```bash
cat btms_config.yaml
```

默认配置使用**混合指标**（推荐）：
- PPL Gap 权重: 40%
- 投票权重: 40%  
- 大小权重: 20%

### 3️⃣ 运行示例（需要数据）

```bash
python run_btms_enhanced_eval.py \
  --config btms_config.yaml \
  --representatives <你的代表点文件> \
  --ppl-edit <你的edit PPL文件> \
  --ppl-gen <你的gen PPL文件> \
  --assignments <你的聚类分配文件> \
  --output evaluation_output/btms_test \
  --routing-output evaluation_output/routing.json
```

## 📁 需要准备的数据文件

### 1. representatives.jsonl
```json
{"cluster_id": 0, "slug": "Chart_1", "rank": 0, "item_id": "Chart_1"}
{"cluster_id": 0, "slug": "Chart_5", "rank": 1, "item_id": "Chart_5"}
```

### 2. edit_ppl.jsonl
```json
{"slug": "Chart_1", "value": 15.5}
{"slug": "Chart_2", "value": 18.2}
```

### 3. gen_ppl.jsonl
```json
{"slug": "Chart_1", "value": 20.3}
{"slug": "Chart_2", "value": 16.1}
```

### 4. assignments.jsonl
```json
{"slug": "Chart_1", "cluster_id": 0}
{"slug": "Chart_2", "cluster_id": 0}
```

## 🎯 三种使用模式

### 模式 1: 二元选择（原始方式）

修改 `btms_config.yaml`:
```yaml
selector_type: "binary"
```

输出: `decision: "edit"` 或 `"gen"`

### 模式 2: PPL Gap 指标

修改 `btms_config.yaml`:
```yaml
selector_type: "budget_allocator"
budget_allocator:
  metric: "ppl_gap"
```

输出: `ratio: {"edit": 0.65, "gen": 0.35}`

### 模式 3: 混合指标（推荐）

修改 `btms_config.yaml`:
```yaml
selector_type: "budget_allocator"
budget_allocator:
  metric: "hybrid"
  metric_params:
    ppl_weight: 0.4
    vote_weight: 0.4
    size_weight: 0.2
```

输出: `ratio: {"edit": 0.58, "gen": 0.42}` + `confidence: 0.78`

## 📊 输出文件说明

运行后会生成 3 个文件：

### 1. cluster_choices.json
簇级别的选择结果，包含每个簇的决策、比例和置信度。

### 2. selection_statistics.json
整体统计信息：
- 总簇数
- 各决策的数量分布
- 平均置信度
- Edit 比例分布（min/max/mean）

### 3. bug_routing.json（如果指定了 --routing-output）
Bug 级别的路由决策，可直接用于评测：
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

## 🔧 常见问题

### Q: 文件路径错误
**A**: 在配置文件中使用绝对路径或相对于工作目录的路径。

### Q: 置信度太低
**A**: 尝试调整参数：
```yaml
budget_allocator:
  metric_params:
    confidence_threshold: 0.3  # 降低阈值
```

### Q: 想要更多代表点
**A**: 调整自适应参数：
```yaml
adaptive_reps:
  divisor: 2  # 减小除数，增加代表点
  max_reps: 10  # 提高上限
```

## 📖 详细文档

- **使用指南**: [BTMS_ENHANCED_README.md](BTMS_ENHANCED_README.md)
- **实施总结**: [BTMS_IMPLEMENTATION_SUMMARY.md](BTMS_IMPLEMENTATION_SUMMARY.md)
- **设计文档**: `btms-budget-allocation/design-zh.md`

## 💡 下一步

1. ✅ 准备数据文件
2. ✅ 运行测试验证
3. ✅ 根据需要调整配置
4. ✅ 运行评测生成路由决策
5. ✅ 在评测流程中使用路由决策

## 🎓 学习路径

1. **理解基础**: 先运行测试，看各指标如何工作
2. **尝试配置**: 修改配置文件，观察输出变化
3. **实际应用**: 在真实数据上运行
4. **优化调整**: 根据结果调整参数

---

**需要帮助？** 查看详细文档或检查测试输出！
