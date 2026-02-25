# 方案1实施：概率性路由实验

## 实施日期
2026-02-23

## 问题背景

在完成参数修复后的实验中，我们发现：
- **Cluster层面**：参数修复成功，ratio标准差从0.003提升至0.075（+25倍）
- **Bug层面**：所有8个配置产生相同的路由结果（289 Edit / 409 Gen）
- **成功率**：所有配置都是518/698 (74.21%)，低于Pure Edit基线78.9%

## 根本原因

Evaluation代码中使用了**确定性阈值映射**：
```python
# run_btms_routing_eval.py 第165行（修改前）
elif decision == 'mixed':
    edit_ratio = ratio.get('edit', 0.5)
    modeling_type = 'edit' if edit_ratio >= 0.5 else 'gen'  # 确定性
```

**问题**：即使cluster的ratio从0.500变化到0.518，只要都≥0.5，都会映射到Edit
- 67个Mixed clusters的ratio分布：0.24-0.68
- 但最终都通过0.5阈值映射为确定性选择
- **结果**：不同配置的cluster决策差异被抹平，Bug层面路由完全相同

## 解决方案（方案1）

### 代码修改

修改 `run_btms_routing_eval.py`:

**1. 统一设置随机种子（确保可重复性）**
```python
# 第106-107行（原第111行）
random.seed(42)
logger.info("Set random seed to 42 for reproducible probabilistic routing")
```

**2. Mixed决策改为概率性选择**
```python
# 第171-174行（原第161-166行）
elif decision == 'mixed':
    # For mixed, use ratio for probabilistic selection
    edit_ratio = ratio.get('edit', 0.5)
    random_val = random.random()
    modeling_type = 'edit' if random_val < edit_ratio else 'gen'
```

### 关键改进

| 项目 | 修改前（确定性） | 修改后（概率性） |
|------|-----------------|-----------------|
| **选择方式** | `edit_ratio >= 0.5` | `random() < edit_ratio` |
| **ratio=0.51** | 100% Edit | 51% Edit, 49% Gen |
| **ratio=0.68** | 100% Edit | 68% Edit, 32% Gen |
| **ratio=0.24** | 100% Gen | 24% Edit, 76% Gen |
| **可重复性** | ✓ | ✓ (seed=42) |

## 实验配置

### 评估设置
- **Worker数量**: 100并行
- **超时时间**: 300秒/bug
- **配置数量**: 8个（3个baseline + 5个experiments）
- **数据来源**: results_fixed（参数修复后的选择结果）
- **结果目录**: evaluation_output_probabilistic

### 配置列表
1. `baseline1-ppl-only` - 仅PPL权重
2. `baseline2-vote-only` - 仅Vote权重
3. `baseline3-size-adjusted` - Size调整权重
4. `exp1-hybrid-default` - 混合默认(1:1:1)
5. `exp2-hybrid-balanced` - 混合平衡(2:2:1)
6. `exp3-ppl-heavy` - PPL主导(4:1:1)
7. `exp4-vote-heavy` - Vote主导(1:4:1)
8. `exp5-size-heavy` - Size主导(1:1:4)

## 预期效果验证

### 立即可见的改进（已验证）

**路由分布变化** (baseline1-ppl-only):
```
旧（确定性）：289 Edit / 409 Gen (41.4% / 58.6%)
新（概率性）：347 Edit / 351 Gen (49.7% / 50.3%)
```

✅ **验证成功**：路由分布发生显著变化，概率性选择生效

### 待验证的效果

完成所有8个配置评估后，预期看到：

1. **不同配置产生不同路由**
   - 不再是所有配置都289/409
   - 根据权重配置不同，Edit/Gen比例应该有差异
   
2. **成功率差异**
   - 不再是所有配置都74.21%
   - 不同配置应该产生不同的Fix Success Rate
   
3. **有配置超越Pure Edit基线**
   - Pure Edit: 78.9% (550/698)
   - 目标：至少一个配置 > 78.9%

## 运行状态

### 启动信息
- **开始时间**: 2026-02-23 02:43:09
- **进程ID**: 1819799
- **日志文件**: `/home/base/mengrui/MTSS/probabilistic_routing_eval.log`

### 监控脚本
```bash
bash /home/base/mengrui/MTSS/check_probabilistic_progress.sh
```

### 预计完成时间
- 每个配置约30分钟（100 workers）
- 8个配置总计：~4小时
- 预计完成：2026-02-23 06:45

## 下一步行动

### 评估完成后立即执行

1. **对比路由分布**
   ```bash
   # 对比所有8个配置的routing分布
   for config in baseline{1,2,3} exp{1,2,3,4,5}*; do
     echo "=== $config ==="
     grep "Routing distribution" evaluation_output_probabilistic/$config/btms_routing_results.json
   done
   ```

2. **分析成功率差异**
   - 提取每个配置的Fix Success Rate
   - 与Pure Edit (78.9%)、Pure Gen (72.2%)对比
   - 找出最佳配置

3. **验证假设**
   - 确认不同权重配置产生不同路由
   - 确认概率性路由提升了性能
   - 分析哪些配置表现最好

### 如果成功（任一配置>78.9%）

✅ **方案1成功** - 撰写成功报告：
- 确认动态路由可行性
- 分析最佳权重配置
- 量化性能提升
- 准备发表/汇报

### 如果失败（所有配置≤78.9%）

❌ **方案1失败** - 转向方案2：
1. 分析Edit/Gen Strong Bugs
2. 理解为什么动态路由underperform
3. 考虑Negative Result发表
4. 重新评估BTMS方法论

## 技术细节

### 文件修改摘要
- **修改文件**: `run_btms_routing_eval.py`
- **修改行数**: 2处（第106-107行，第171-174行）
- **修改性质**: 逻辑变更（确定性→概率性）
- **兼容性**: 向后兼容（原有参数保持不变）

### 随机种子策略
- **种子值**: 42（固定）
- **原因**: 确保实验可重复
- **影响范围**: 仅Mixed决策的概率选择
- **确定性决策**: Edit/Gen决策不受影响

### 数据流
1. Cluster Selection (results_fixed) → 生成cluster_choices.json
2. Cluster Choices → 概率性映射 → Bug-level routing
3. Bug-level routing → D4JFixEvaluator → Fix Success/Failure
4. Evaluation Results → JSON报告 + Markdown总结

## 关键指标对比

| 指标 | 参数修复后（确定性） | 方案1（概率性） | 预期变化 |
|------|---------------------|----------------|----------|
| Cluster Ratio Std | 0.075 | 0.075 | 不变 |
| Bug路由分布 | 289/409（相同） | 变化 | ✓ 不同配置不同 |
| Fix Success Rate | 74.21%（相同） | 变化 | ✓ 不同配置不同 |
| 最佳配置性能 | 74.21% | ? | ✓ 期望>78.9% |

## 实验日志关键点

### 成功启动标志
```
2026-02-23 02:43:09,409 - INFO - Set random seed to 42 for reproducible probabilistic routing
2026-02-23 02:43:09,410 - INFO - Routing distribution:
2026-02-23 02:43:09,410 - INFO -   edit: 347 (49.7%)
2026-02-23 02:43:09,410 - INFO -   gen: 351 (50.3%)
```

### 进度跟踪
- 实时进度：`tail -f /home/base/mengrui/MTSS/probabilistic_routing_eval.log`
- 快速检查：`bash /home/base/mengrui/MTSS/check_probabilistic_progress.sh`
- 结果位置：`/home/base/mengrui/MTSS/btms_budget_experiments/qwencoder_experiments/evaluation_output_probabilistic/`

## 风险与备份

### 风险点
1. ✓ 随机性导致不可重复 → **已缓解**：固定seed=42
2. ? 概率性路由可能降低性能 → **待验证**：完成评估后分析
3. ✓ Worker资源竞争 → **已优化**：100 workers并行

### 回退方案
如需回退到确定性路由：
```python
# 修改run_btms_routing_eval.py第171-174行
modeling_type = 'edit' if edit_ratio >= 0.5 else 'gen'
```

### 数据备份
- 原始数据保留在：`evaluation_output_fixed/`
- 新实验数据保存在：`evaluation_output_probabilistic/`
- 两者独立，互不影响

---

**实验负责人**: GitHub Copilot  
**实施时间**: 2026-02-23 02:43  
**状态**: 🟢 RUNNING (166/698 bugs evaluated)
