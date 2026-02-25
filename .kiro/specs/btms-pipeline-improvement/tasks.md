# Implementation Plan: BTMS Pipeline Improvement

## Overview

本实现计划将 BTMS 流水线改进分为 6 个主要阶段：创建模块结构、实现聚类算法、实现采样算法、更新选择器、添加实验支持、更新 CLI。使用 Python 实现，与现有代码库保持一致。

## Tasks

- [x] 1. 创建新模块结构和抽象基类
  - [x] 1.1 创建 `src/btms/` 目录结构
    - 创建 clustering/, sampling/, selection/, data/, evaluation/, experiment/, utils/ 子目录
    - 创建各目录的 `__init__.py` 文件
    - _Requirements: 9.1-9.6_

  - [x] 1.2 实现聚类抽象基类 `BaseClusterer`
    - 创建 `clustering/base.py`
    - 定义 `ClusteringConfig` 和 `ClusteringResult` 数据类
    - 定义 `BaseClusterer` 抽象基类，包含 `fit()` 和 `export_assignments()` 方法
    - _Requirements: 1.1, 1.2, 1.4_

  - [x] 1.3 实现采样抽象基类 `BaseSampler`
    - 创建 `sampling/base.py`
    - 定义 `SamplingConfig` 和 `SamplingResult` 数据类
    - 定义 `BaseSampler` 抽象基类，包含 `sample()` 和 `export_representatives()` 方法
    - _Requirements: 5.1, 5.2, 5.4_

  - [x] 1.4 实现工具函数模块
    - 创建 `utils/math.py`，包含 L2 归一化、距离计算等函数
    - 创建 `utils/io.py`，包含 JSONL 读写函数
    - _Requirements: 9.6_

- [x] 2. 实现聚类算法
  - [x] 2.1 实现 KMeans 聚类器
    - 创建 `clustering/kmeans.py`
    - 继承 `BaseClusterer`
    - 支持 n_clusters, max_iter, seed 配置
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.2 编写 KMeans 属性测试
    - **Property 3: Cluster Count Correctness** (KMeans 部分)
    - **Property 4: Deterministic Results with Fixed Seed** (KMeans 部分)
    - **Validates: Requirements 2.2, 2.4**

  - [x] 2.3 实现 HAC 聚类器（支持 average 和 ward linkage）
    - 创建 `clustering/hac.py`
    - 继承 `BaseClusterer`
    - 支持 linkage 参数切换
    - Ward linkage 自动使用 euclidean metric
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 2.4 编写 HAC 属性测试
    - **Property 3: Cluster Count Correctness** (HAC 部分)
    - **Validates: Requirements 3.3**

  - [x] 2.5 实现 Bisecting KMeans 聚类器
    - 创建 `clustering/bisecting.py`
    - 继承 `BaseClusterer`
    - 支持 bisecting_strategy 配置
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 2.6 编写 Bisecting KMeans 属性测试
    - **Property 3: Cluster Count Correctness** (Bisecting KMeans 部分)
    - **Validates: Requirements 4.2**

  - [x] 2.7 实现聚类器工厂
    - 创建 `clustering/factory.py`
    - 实现 `ClustererFactory` 类
    - 支持算法注册和创建
    - _Requirements: 1.3, 10.3_

  - [ ]* 2.8 编写聚类输出格式属性测试
    - **Property 1: Clustering Output Format Consistency**
    - **Validates: Requirements 1.2, 2.5, 3.4, 4.4**

- [x] 3. Checkpoint - 聚类模块完成
  - 确保所有聚类测试通过
  - 验证输出格式与现有 `cluster_hac.py` 兼容
  - 如有问题请询问用户

- [x] 4. 实现采样算法
  - [x] 4.1 实现 Farthest-First 采样器
    - 创建 `sampling/farthest_first.py`
    - 继承 `BaseSampler`
    - 迁移现有 `cluster_representatives.py` 中的逻辑
    - 支持 reps_per_cluster 配置
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 4.2 编写 Farthest-First 属性测试
    - **Property 5: Representative Count Correctness**
    - **Validates: Requirements 5.2, 6.1, 6.2**

  - [x] 4.3 实现 k-DPP 采样器
    - 创建 `sampling/kdpp.py`
    - 继承 `BaseSampler`
    - 迁移现有 `_greedy_dpp_order` 逻辑
    - 支持 seed 配置
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 4.4 编写 k-DPP 属性测试
    - **Property 4: Deterministic Results with Fixed Seed** (k-DPP 部分)
    - **Validates: Requirements 7.3**

  - [x] 4.5 实现采样器工厂
    - 创建 `sampling/factory.py`
    - 实现 `SamplerFactory` 类
    - _Requirements: 5.3_

  - [ ]* 4.6 编写采样输出格式属性测试
    - **Property 2: Sampling Output Format Consistency**
    - **Validates: Requirements 5.4, 6.2, 7.4**

- [x] 5. Checkpoint - 采样模块完成
  - 确保所有采样测试通过
  - 验证输出格式与现有 `cluster_representatives.py` 兼容
  - 如有问题请询问用户

- [x] 6. 更新选择器支持多代表投票
  - [x] 6.1 实现投票机制
    - 创建 `selection/voting.py`
    - 实现 `VotingMechanism` 类
    - 支持 majority 和 mean_ppl 策略
    - 实现平局时的 mean PPL 打破逻辑
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 6.2 编写投票机制属性测试
    - **Property 6: Voting Mechanism Correctness**
    - **Validates: Requirements 8.1, 8.2, 8.3**

  - [x] 6.3 更新 TaskModelSelector
    - 创建 `selection/selector.py`
    - 支持读取所有 rank 的代表
    - 集成 VotingMechanism
    - 输出包含投票详情
    - _Requirements: 8.4_

- [x] 7. Checkpoint - 选择器模块完成
  - 确保投票测试通过
  - 验证与现有 `task_model_selector.py` 输出兼容
  - 如有问题请询问用户

- [x] 8. 实现实验支持
  - [x] 8.1 实现实验配置加载
    - 创建 `experiment/config.py`
    - 实现 `ExperimentConfig` 数据类
    - 支持 YAML 配置文件解析
    - _Requirements: 10.2, 11.1_

  - [x] 8.2 实现参数网格展开
    - 在 `experiment/runner.py` 中实现 `_generate_combinations()`
    - 生成所有参数组合
    - _Requirements: 11.2, 11.3_

  - [ ]* 8.3 编写参数网格属性测试
    - **Property 8: Parameter Grid Expansion Correctness**
    - **Validates: Requirements 11.2, 11.3**

  - [x] 8.4 实现实验运行器
    - 创建 `experiment/runner.py`
    - 实现 `ExperimentRunner` 类
    - 支持顺序和并行执行
    - 实现增量运行（跳过已完成）
    - _Requirements: 11.4, 11.5, 12.5_

  - [ ]* 8.5 编写实验配置属性测试
    - **Property 7: Experiment Configuration Uniqueness**
    - **Property 10: Incremental Experiment Skip**
    - **Validates: Requirements 11.4, 12.1, 12.3, 12.5**

  - [x] 8.6 实现报告生成
    - 创建 `experiment/report.py`
    - 生成 JSON 和 CSV 格式报告
    - 包含配置和结果汇总
    - _Requirements: 11.6, 12.1, 12.2, 12.4_

- [x] 9. Checkpoint - 实验模块完成
  - 确保实验测试通过
  - 验证报告格式正确
  - 如有问题请询问用户

- [x] 10. 更新 CLI 和集成
  - [x] 10.1 创建统一 CLI 入口
    - 创建 `scripts/run_experiment.py`
    - 支持命令行参数和配置文件
    - 支持算法选择参数
    - _Requirements: 10.1, 10.2, 10.4_

  - [ ]* 10.2 编写错误处理属性测试
    - **Property 9: Invalid Algorithm Error Handling**
    - **Validates: Requirements 10.3**

  - [x] 10.3 创建配置模板
    - 创建 `configs/experiment_template.yaml`
    - 包含所有可配置参数的示例
    - _Requirements: 11.1_

  - [x] 10.4 更新模块导出
    - 更新各 `__init__.py` 文件
    - 确保公共 API 可访问
    - _Requirements: 9.7_

- [x] 11. 最终验证
  - [x] 11.1 运行完整测试套件
    - 运行所有单元测试
    - 运行所有属性测试
    - 确保测试覆盖率达标

  - [x] 11.2 端到端集成测试
    - 使用小数据集运行完整流水线
    - 验证所有算法组合工作正常
    - 验证输出格式正确

  - [x] 11.3 向后兼容性验证
    - 验证默认配置产生与旧代码相同的结果
    - 验证现有脚本仍可运行

- [x] 12. Final Checkpoint
  - 确保所有测试通过
  - 确保文档完整
  - 如有问题请询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- 使用 `hypothesis` 库进行属性测试，每个属性测试至少运行 100 次
