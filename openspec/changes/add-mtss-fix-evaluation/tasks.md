# Implementation Tasks

## 1. 修复采样基础设施
- [ ] 1.1 创建 `FixSampler` 类，根据路由决策执行修复尝试
- [ ] 1.2 集成 `generator/d4j_gen.py` 和 `generator/d4j_SR.py` 进行 patch 生成
- [ ] 1.3 集成 `validator/` 模块进行 patch 验证
- [ ] 1.4 实现可配置的采样预算（每个 bug 的尝试次数）
- [ ] 1.5 实现结果持久化（成功/失败、生成的 patch、验证日志）

## 2. Bugfix 统计收集
- [ ] 2.1 创建 `BugfixStatsCollector` 类用于聚合修复结果
- [ ] 2.2 实现 per-bug 统计（尝试次数、成功状态、首次成功索引）
- [ ] 2.3 实现 per-cluster 统计（簇级别成功率）
- [ ] 2.4 实现整体统计（全局成功率、覆盖率）
- [ ] 2.5 添加统计导出功能（JSON 和 CSV 格式）

## 3. Loss 指标计算
- [ ] 3.1 创建 `RouterLossCalculator` 类实现 Loss 指标
- [ ] 3.2 实现 multi-budget 基线结果收集（5 for REW, 5 for EDIT）
- [ ] 3.3 实现 router 策略结果收集（按 router 决定的比例分配预算）
- [ ] 3.4 实现 Loss 计算：`(bugfix_multi - bugfix_router) / bugfix_multi`
- [ ] 3.5 实现比例到尝试次数的转换逻辑（处理舍入）
- [ ] 3.6 实现簇级别 Loss 聚合
- [ ] 3.7 添加 Loss 解释和可视化（负值表示改进）

## 4. 基线对比
- [ ] 4.1 实现 multi-budget 基线（预算均分：5 for REW, 5 for EDIT）
- [ ] 4.2 实现 always-REW 基线（所有 bug 使用 REW，全部 10 次预算，比例 10:0）
- [ ] 4.3 实现 always-EDIT 基线（所有 bug 使用 EDIT，全部 10 次预算，比例 0:10）
- [ ] 4.4 实现 fixed-ratio 基线（固定比例：2:8, 3:7, 7:3, 8:2 等）
- [ ] 4.5 实现 oracle 基线（per-bug 最佳比例分配）
- [ ] 4.6 添加统计显著性检验（McNemar's test：router vs multi-budget）

## 5. 评估报告生成
- [ ] 5.1 创建修复评估报告生成器
- [ ] 5.2 添加 per-cluster 成功率表格
- [ ] 5.3 添加整体对比表格（router vs 基线）
- [ ] 5.4 添加 Loss 指标对比图表
- [ ] 5.5 添加 router 比例选择分析（各簇选择的比例分布）
- [ ] 5.6 生成 Markdown 报告和可视化

## 6. Router 预算分配实现
- [ ] 6.1 设计 router 输出格式（比例字典：`{rew_ratio: float, edit_ratio: float}`）
- [ ] 6.2 实现比例到尝试次数的转换（处理舍入和预算约束）
- [ ] 6.3 实现基于簇特征的比例决策逻辑（初期可用简单规则或分类器）
- [ ] 6.4 添加比例验证（确保和为 1.0，范围 [0, 1]）
- [ ] 6.5 实现 per-bug 比例决策记录和导出

## 7. 管道集成
- [ ] 7.1 创建端到端脚本 `run_fix_evaluation.py`
- [ ] 7.2 添加修复评估实验的配置 schema（包括 router 比例配置）
- [ ] 7.3 集成现有实验运行器基础设施
- [ ] 7.4 添加进度跟踪和断点续传支持
- [ ] 7.5 添加实验结果缓存（包括所有比例的尝试结果）

## 8. 测试与验证
- [ ] 8.1 在小规模 Defects4J 子集上测试修复采样
- [ ] 8.2 验证统计收集的准确性
- [ ] 8.3 验证 loss 计算的正确性（包括不同比例）
- [ ] 8.4 测试基线对比逻辑（包括 fixed-ratio 基线）
- [ ] 8.5 验证 router 比例决策逻辑
- [ ] 8.6 使用样本数据验证报告生成

## 9. 文档
- [ ] 9.1 文档化修复评估配置选项（包括 router 比例配置）
- [ ] 9.2 添加运行修复实验的使用示例
- [ ] 9.3 文档化 Loss 指标定义和 router 比例分配机制
- [ ] 9.4 添加评估报告的解读指南（包括比例选择分析）
