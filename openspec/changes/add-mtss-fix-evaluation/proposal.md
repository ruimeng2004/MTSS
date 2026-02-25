# Change: MTSS 路由决策接入实际修复采样与 Loss 评估

## Why
当前的 bug-task-model-selection 管道基于 PPL（困惑度）信号进行路由决策，但仅停留在 PPL 层面的评估。PPL 是一个代理指标，真正的目标是最大化实际的 bug 修复成功率。

我们需要：
- 将 MTSS 路由决策接入实际的 bug 修复采样流程
- 统计真实的 bugfix 成功数量（通过 Defects4J 验证）
- 计算 Loss 指标来衡量路由策略的实际修复效果
- 对比路由策略与基线策略在真实修复任务上的表现

这将验证 PPL 路由决策是否能转化为实际的修复成功率提升。

## What Changes
- 添加修复采样管道：根据路由决策执行实际的 patch 生成和验证
- 添加 bugfix 统计收集：记录每个 bug 的修复尝试次数、成功状态、首次成功索引
- 添加 Loss 指标计算：`Loss = (bugfix_multi - bugfix_router) / bugfix_multi`
  - bugfix_multi: 预算均分（5 for REW, 5 for EDIT）修复的 bug 数
  - bugfix_router: 路由策略按 router 决定的比例分配预算修复的 bug 数
  - Router 自主决定预算分配比例（如 3:7, 2:8, 5:5 等）
  - 负 Loss 表示路由策略优于均分基线
- 添加基线对比：multi-budget（5:5 均分）、always-REW、always-EDIT、fixed-ratio（固定比例）、oracle
- 添加评估报告生成：生成包含成功率、Loss 对比、统计显著性检验的报告
- 集成现有 Defects4J 基础设施（generator/、validator/）

## Impact
- **Affected specs:** `bug-task-model-selection`（MODIFIED - 扩展评估能力）
- **Affected code (expected):**
  - 新增模块：`bug_task_model_selection/src/btms/fix_sampling.py`、`loss_calculator.py`
  - 新增脚本：`bug_task_model_selection/scripts/run_fix_evaluation.py`
  - 集成现有：`generator/d4j_*.py`、`validator/` 模块
  - 结果存储：`bug_task_model_selection/data/fix_results/`
- **Breaking changes:** None（扩展现有管道，不影响已有功能）
- **Router 预算分配能力:** Router 能够自主决定预算分配比例（如 1:9, 2:8, 3:7, 5:5, 7:3, 8:2, 9:1），而非简单的二元选择（10:0 或 0:10）。这允许 router 基于簇特征和 PPL 信号学习最佳分配策略。
