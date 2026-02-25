# Design: MTSS 路由引导的 Bug 修复评估

## Context
bug-task-model-selection 管道当前基于 PPL 信号将 bug 路由到任务建模（d4j_gen vs d4j_edit），并使用 PPL 指标评估路由质量。然而，PPL 是代理指标——最终目标是最大化实际的 bug 修复成功率。本设计扩展管道以执行真实的修复尝试，并使用真实修复结果衡量路由有效性。

**约束条件：**
- 必须集成现有 Defects4J 基础设施（generator/、validator/）
- 必须支持可配置的采样预算以管理计算成本
- 必须保持可重现性（固定种子、确定性采样）
- 必须处理部分结果（某些 bug 可能超时或生成失败）

**利益相关者：**
- 评估路由策略的研究人员
- 比较任务建模有效性的用户
- 自适应路由和元学习的未来工作

## Goals / Non-Goals

**Goals:**
- 使用路由的任务建模执行实际的 bug 修复尝试
- 收集全面的 bugfix 统计（成功率、尝试次数）
- 计算衡量真实修复结果上路由质量的 Loss 指标
- 生成对比路由策略 vs 基线的评估报告
- 初期支持 Defects4J 数据集（可扩展到 DebugBench）

**Non-Goals:**
- 实时路由（这是离线评估）
- 交互式调试或人工干预
- 跨数据集路由（先专注 Defects4J）
- patch 生成的超参数调优（使用现有配置）

## Decisions

### Decision 1: 两阶段评估架构
**What:** 将 PPL 路由（阶段 1）与修复执行（阶段 2）分离

**Why:**
- PPL 路由快速且成本低（已计算）
- 修复执行昂贵（需要 LLM 调用 + 验证）
- 允许缓存路由决策并在多个修复实验中重用
- 支持比较多个路由策略而无需重新运行修复

**考虑的替代方案：**
- 端到端管道：因缺乏模块化和高重计算成本而拒绝
- 交错路由和修复：因复杂性和难以重现实验而拒绝

### Decision 2: 采样预算模型
**What:** 支持可配置的采样预算（每个 bug k 次尝试），首次成功时提前停止

**Why:**
- 匹配现有 D4C 评估协议（Defects4J 10 个样本）
- 允许跨策略公平比较（所有策略相同预算）
- 提前停止在 bug 修复时降低成本
- 支持研究"成功所需尝试次数"作为指标

**配置：**
```yaml
fix_evaluation:
  sampling_budget: 10  # 每个 bug 的最大尝试次数
  early_stop: true     # 首次成功时停止
  timeout_per_attempt: 600  # 秒
```

### Decision 3: Loss 指标定义
**What:** 基于预算分配对比的 Loss 指标，衡量路由策略相对于均分预算基线的改进

**Loss 定义：**
```
Loss = (bugfix_multi - bugfix_router) / bugfix_multi
```

其中：
- **bugfix_multi**: 将预算均分给两种建模（5 for REW, 5 for EDIT）所能修复的 bug 数量
- **bugfix_router**: 将预算按 router 决定的比例分配给两种建模所能修复的 bug 数量
  - Router 输出分配比例，如 `{rew_ratio: 0.3, edit_ratio: 0.7}` 表示 3:7 分配
  - 对于 budget=10: 3 次尝试用 REW，7 次尝试用 EDIT
  - Router 可以自由选择任何比例：1:9, 2:8, 3:7, 4:6, 5:5, 6:4, 7:3, 8:2, 9:1
- **sample budget**: 默认为 10 次尝试

**Loss 解释：**
- **Loss < 0**: 路由策略优于均分基线（修复更多 bug）
- **Loss = 0**: 路由策略与均分基线相当
- **Loss > 0**: 路由策略劣于均分基线（修复更少 bug）

**Why:**
- 直接衡量路由决策的实际价值：router 选择的比例是否比简单均分更好
- 考虑了预算约束下的修复效果
- 可解释性强：负 loss 表示 router 比例选择带来的改进
- 与研究目标一致：验证任务建模选择方法和预算分配策略的有效性

**实现细节：**
```python
class RouterLossCalculator:
    def __init__(self, budget: int = 10):
        self.budget = budget
        self.half_budget = budget // 2
    
    def calculate_loss(
        self,
        router_allocation: Dict[str, float],  # Router 决定的分配比例
        rew_results: List[BugFixResult],      # REW 建模所有尝试结果
        edit_results: List[BugFixResult]      # EDIT 建模所有尝试结果
    ) -> float:
        """计算路由策略的 Loss
        
        Args:
            router_allocation: Router 输出的分配比例，如 {'rew': 0.3, 'edit': 0.7}
            rew_results: REW 建模的修复尝试结果（最多 budget 次）
            edit_results: EDIT 建模的修复尝试结果（最多 budget 次）
        """
        # 计算 router 分配的尝试次数
        rew_attempts = int(self.budget * router_allocation['rew'])
        edit_attempts = int(self.budget * router_allocation['edit'])
        
        # bugfix_router: router 比例分配修复的 bug 数
        bugfix_router = 0
        for rew_r, edit_r in zip(rew_results, edit_results):
            # 如果任一建模在分配的尝试次数内修复成功，计为修复
            if rew_r.success_within(rew_attempts) or \
               edit_r.success_within(edit_attempts):
                bugfix_router += 1
        
        # bugfix_multi: 均分预算（5:5）修复的 bug 数
        bugfix_multi = 0
        for rew_r, edit_r in zip(rew_results, edit_results):
            # 如果任一建模在前 5 次内修复成功，计为修复
            if rew_r.success_within(self.half_budget) or \
               edit_r.success_within(self.half_budget):
                bugfix_multi += 1
        
        # 计算 Loss
        if bugfix_multi == 0:
            return 0.0  # 避免除零
        
        return (bugfix_multi - bugfix_router) / bugfix_multi
```

### Decision 4: 基线策略
**What:** 将路由策略与以下基线比较：
1. **Multi-Budget (均分预算):** 将预算均分给两种建模（5 for REW, 5 for EDIT）- 这是 Loss 计算的基线
2. **Always-REW:** 所有 bug 使用 REW (d4j_gen) 任务建模，全部 10 次预算
3. **Always-EDIT:** 所有 bug 使用 EDIT (d4j_SR) 任务建模，全部 10 次预算
4. **Fixed-Ratio Baselines (可选):** 固定比例分配策略
   - 2:8, 3:7, 4:6, 6:4, 7:3, 8:2 等固定比例
   - 用于验证 router 动态选择比例是否优于固定比例
5. **Oracle (可选):** per-bug 最佳预算分配比例（需要运行所有比例组合）

**Why:**
- Multi-Budget (5:5): Loss 指标的核心基线，验证 router 是否优于简单均分
- Always-REW/EDIT: 显示 router 相对于单一策略的价值
- Fixed-Ratio: 验证 router 动态选择比例的价值（vs 固定比例策略）
- Oracle: router 有效性的理论上界（完美预算分配）
- 统计显著性：使用 McNemar's test 进行配对比较

### Decision 5: 结果存储 Schema
**What:** 在 `bug_task_model_selection/data/fix_results/` 下以结构化格式存储修复结果

**Schema:**
```
fix_results/
├── <experiment_id>/
│   ├── config.yaml              # 实验配置
│   ├── routing_decisions.json   # per-bug 路由决策
│   ├── raw_results/             # per-bug 原始输出
│   │   ├── <slug>/
│   │   │   ├── attempt_0.json   # Patch、验证结果
│   │   │   ├── attempt_1.json
│   │   │   └── ...
│   ├── statistics.json          # 聚合统计
│   ├── loss_metrics.json        # Loss 计算
│   └── report.md                # 人类可读报告
```

**Bug 结果格式：**
```json
{
  "slug": "Chart_1",
  "routed_task_model": "d4j_gen",
  "cluster_id": 5,
  "attempts": [
    {
      "attempt_idx": 0,
      "patch": "...",
      "validation_result": "fail",
      "validation_log": "...",
      "timestamp": "2026-02-03T10:00:00Z"
    }
  ],
  "first_success_idx": 3,
  "total_attempts": 4,
  "success": true
}
```

### Decision 6: 与现有基础设施集成
**What:** 以最小修改重用现有 generator 和 validator 模块

**集成点：**
1. **Generator:** 根据路由调用 `generator/d4j_gen.py` 或 `generator/d4j_SR.py`
2. **Validator:** 通过 `validator/` 模块使用现有 Defects4J 验证
3. **Configuration:** 用修复评估部分扩展现有 `config.yaml`

**Why:**
- 避免重复 patch 生成逻辑
- 保持与现有 D4C 实验的一致性
- 利用现有的超时和重试机制

## Risks / Trade-offs

### Risk 1: 计算成本
**Risk:** 在完整 Defects4J 上运行修复实验（835 bugs × 10 attempts）成本高昂

**缓解措施：**
- 支持实验子集（例如，采样 100 个 bug 进行快速验证）
- 实现结果缓存和断点续传
- 运行实验前提供成本估算
- 支持跨多个 GPU/机器并行执行

### Risk 2: 验证可靠性
**Risk:** Defects4J 验证可能不稳定（超时、环境问题）

**缓解措施：**
- 使用现有超时配置（默认 600s）
- 记录所有验证失败以供人工检查
- 支持重新运行失败的验证
- 单独报告验证失败率和修复失败率

### Risk 3: 基线公平性
**Risk:** Oracle 基线需要运行两种任务建模（2× 成本）

**缓解措施：**
- 使 oracle 基线可选（快速实验可跳过）
- 缓存 oracle 结果以在路由实验中重用
- 将 oracle 记录为上界（实践中无法实现）

## Migration Plan

**Phase 1: 核心实现（第 1-2 周）**
1. 实现 FixSampler 和 BugfixStatsCollector
2. 实现基本 loss 计算器（0-1 loss）
3. 在小规模 Defects4J 子集上测试（10 bugs）

**Phase 2: 基线和报告（第 3 周）**
4. 实现基线策略
5. 实现报告生成
6. 在 50 个 bug 上运行试点实验

**Phase 3: 完整评估（第 4 周）**
7. 运行完整 Defects4J 评估
8. 生成综合报告
9. 文档化发现和使用方法

**回滚:** 如果修复评估证明过于昂贵或不可靠，回退到仅 PPL 评估（对现有管道无代码更改）。

## Open Questions

1. **Q:** 除了 Defects4J，是否应支持 DebugBench？
   **A:** 仅从 Defects4J 开始。如需要，在未来变更中添加 DebugBench 支持。

2. **Q:** 如何处理两种任务建模都失败的 bug？
   **A:** 记录为所有策略的失败。单独报告"无法解决的 bug"数量。

3. **Q:** 除了成功率，是否应跟踪 token 成本？
   **A:** 是的，添加可选的 token 跟踪。对成本效益分析有用。

4. **Q:** 如何处理非确定性 patch 生成？
   **A:** 使用固定种子以保证可重现性。在实验配置中记录种子。

5. **Q:** Router 如何决定预算分配比例？
   **A:** Router 应该能够自主决定预算分配比例，而不是简单的二元选择：
   - **Router 输出格式：** `{rew_ratio: 0.3, edit_ratio: 0.7}` 表示 30% 预算给 REW，70% 给 EDIT
   - **可选比例范围：** 对于 budget=10，router 可以选择 0:10, 1:9, 2:8, 3:7, 4:6, 5:5, 6:4, 7:3, 8:2, 9:1, 10:0
   - **实现方式：** 
     - 基于簇特征和 PPL 信号，router 学习最佳分配比例
     - 可以使用分类器输出比例，或基于规则的启发式方法
     - 初期可以简化为几个离散选项（如 2:8, 3:7, 5:5, 7:3, 8:2）
   - **评估目标：** 验证 router 动态选择的比例是否优于固定比例（特别是 5:5 均分基线）
