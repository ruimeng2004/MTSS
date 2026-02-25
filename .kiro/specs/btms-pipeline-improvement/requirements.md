# Requirements Document

## Introduction

本项目旨在改进 Bug Task Model Selection (BTMS) 流水线，用于预测 bug 修复应该使用 edit（编辑式）还是 gen（生成式）任务建模。当前方案通过 embedding 聚类 → 多样性采样选代表 → 用代表的 PPL 决定 cluster 策略。实验发现聚类粒度越细效果越好，但 cluster 内部一致性差（50-60%），说明 embedding 聚类难以有效区分 edit/gen 偏好。

本次改进包含三个主要方向：
1. 扩展聚类算法支持
2. 改进多样性采样机制
3. 重构代码结构以提高可维护性

## Glossary

- **BTMS**: Bug Task Model Selection，bug 任务建模选择系统
- **Clustering_Engine**: 聚类引擎，负责将 bug embedding 分组
- **Sampling_Engine**: 采样引擎，负责从每个 cluster 选择代表性样本
- **Task_Model_Selector**: 任务模型选择器，根据代表的 PPL 决定 cluster 策略
- **HAC**: Hierarchical Agglomerative Clustering，层次凝聚聚类
- **KMeans**: K-Means 聚类算法
- **Bisecting_KMeans**: 二分 K-Means 聚类算法
- **k-DPP**: k-Determinantal Point Process，k-行列式点过程采样
- **PPL**: Perplexity，困惑度，用于评估模型对代码的理解程度
- **Representative**: 代表，从 cluster 中选出的代表性样本
- **assignments.jsonl**: 聚类分配结果文件，格式为 `{"item_id": str, "cluster_id": int}`

## Requirements

### Requirement 1: 聚类算法抽象基类

**User Story:** As a developer, I want a unified clustering interface, so that I can easily switch between different clustering algorithms without changing downstream code.

#### Acceptance Criteria

1. THE Clustering_Engine SHALL define an abstract base class `BaseClusterer` with a `fit` method that accepts vectors and returns cluster assignments
2. THE Clustering_Engine SHALL define a `cluster` method that outputs assignments in the standard `assignments.jsonl` format
3. WHEN a new clustering algorithm is added, THE Clustering_Engine SHALL require only implementing the abstract interface without modifying existing code
4. THE Clustering_Engine SHALL support configuration via a unified parameter dictionary

### Requirement 2: KMeans 聚类实现

**User Story:** As a researcher, I want to use KMeans clustering, so that I can evaluate different clustering algorithms for bug task model selection.

#### Acceptance Criteria

1. THE Clustering_Engine SHALL implement KMeans clustering that inherits from `BaseClusterer`
2. WHEN KMeans clustering is executed, THE Clustering_Engine SHALL support configurable number of clusters (k)
3. WHEN KMeans clustering is executed, THE Clustering_Engine SHALL support configurable maximum iterations
4. WHEN KMeans clustering is executed, THE Clustering_Engine SHALL support configurable random seed for reproducibility
5. THE Clustering_Engine SHALL output assignments in the same `assignments.jsonl` format as HAC

### Requirement 3: HAC Ward Linkage 实现

**User Story:** As a researcher, I want to use HAC with Ward linkage, so that I can evaluate different linkage methods for clustering quality.

#### Acceptance Criteria

1. THE Clustering_Engine SHALL implement HAC with Ward linkage that inherits from `BaseClusterer`
2. WHEN HAC Ward clustering is executed, THE Clustering_Engine SHALL minimize within-cluster variance
3. THE Clustering_Engine SHALL support the same cut-level (k) interface as existing HAC average linkage
4. THE Clustering_Engine SHALL output assignments in the same `assignments.jsonl` format

### Requirement 4: Bisecting KMeans 实现

**User Story:** As a researcher, I want to use Bisecting KMeans clustering, so that I can evaluate hierarchical divisive clustering for cluster quality.

#### Acceptance Criteria

1. THE Clustering_Engine SHALL implement Bisecting KMeans that inherits from `BaseClusterer`
2. WHEN Bisecting KMeans is executed, THE Clustering_Engine SHALL recursively bisect clusters until reaching the target number of clusters
3. THE Clustering_Engine SHALL support configurable bisection strategy (largest cluster first)
4. THE Clustering_Engine SHALL output assignments in the same `assignments.jsonl` format

### Requirement 5: 采样算法抽象基类

**User Story:** As a developer, I want a unified sampling interface, so that I can easily switch between different sampling algorithms for representative selection.

#### Acceptance Criteria

1. THE Sampling_Engine SHALL define an abstract base class `BaseSampler` with a `sample` method
2. THE Sampling_Engine SHALL support configurable number of representatives per cluster (`reps_per_cluster`)
3. WHEN a new sampling algorithm is added, THE Sampling_Engine SHALL require only implementing the abstract interface
4. THE Sampling_Engine SHALL output representatives in the standard `representatives.jsonl` format

### Requirement 6: 多代表采样支持

**User Story:** As a researcher, I want to select multiple representatives per cluster, so that I can improve the robustness of cluster strategy decisions through voting.

#### Acceptance Criteria

1. THE Sampling_Engine SHALL support configurable `reps_per_cluster` parameter with values 1, 3, 5, 7
2. WHEN multiple representatives are selected, THE Sampling_Engine SHALL output all representatives with rank ordering
3. THE Sampling_Engine SHALL maintain backward compatibility with single representative selection (reps_per_cluster=1)

### Requirement 7: k-DPP 采样实现

**User Story:** As a researcher, I want to use k-DPP sampling, so that I can select diverse representatives that better cover the cluster's distribution.

#### Acceptance Criteria

1. THE Sampling_Engine SHALL implement k-DPP sampling that inherits from `BaseSampler`
2. WHEN k-DPP sampling is executed, THE Sampling_Engine SHALL maximize diversity among selected representatives
3. THE Sampling_Engine SHALL support configurable random seed for reproducibility
4. THE Sampling_Engine SHALL output representatives in the same format as farthest-first sampling

### Requirement 8: 多代表投票机制

**User Story:** As a researcher, I want the task model selector to support voting among multiple representatives, so that cluster strategy decisions are more robust.

#### Acceptance Criteria

1. WHEN multiple representatives exist for a cluster, THE Task_Model_Selector SHALL aggregate their PPL scores
2. THE Task_Model_Selector SHALL support majority voting among representatives
3. WHEN votes are tied, THE Task_Model_Selector SHALL use mean PPL score as tiebreaker
4. THE Task_Model_Selector SHALL record voting details in the output for analysis

### Requirement 9: 代码结构重构

**User Story:** As a developer, I want a well-organized code structure, so that the codebase is maintainable and extensible.

#### Acceptance Criteria

1. THE BTMS codebase SHALL organize clustering algorithms under `src/btms/clustering/` directory
2. THE BTMS codebase SHALL organize sampling algorithms under `src/btms/sampling/` directory
3. THE BTMS codebase SHALL organize selection logic under `src/btms/selection/` directory
4. THE BTMS codebase SHALL organize data processing under `src/btms/data/` directory
5. THE BTMS codebase SHALL organize evaluation metrics under `src/btms/evaluation/` directory
6. THE BTMS codebase SHALL organize utility functions under `src/btms/utils/` directory
7. WHEN code is refactored, THE BTMS codebase SHALL maintain all existing CLI interfaces and output formats

### Requirement 10: 算法切换配置

**User Story:** As a user, I want to switch clustering and sampling algorithms via configuration, so that I can easily run experiments with different algorithm combinations.

#### Acceptance Criteria

1. THE BTMS pipeline SHALL support algorithm selection via command-line arguments
2. THE BTMS pipeline SHALL support algorithm selection via configuration file
3. WHEN an invalid algorithm name is provided, THE BTMS pipeline SHALL return a descriptive error message
4. THE BTMS pipeline SHALL provide default algorithm settings that match current behavior (HAC average + farthest_first)

### Requirement 11: 批量实验支持

**User Story:** As a researcher, I want to run batch experiments with different parameter combinations, so that I can efficiently explore the parameter space for optimal settings.

#### Acceptance Criteria

1. THE BTMS pipeline SHALL support batch experiment configuration via YAML/JSON file
2. THE BTMS pipeline SHALL support parameter grid specification for clustering algorithms (algorithm type, k values, linkage types)
3. THE BTMS pipeline SHALL support parameter grid specification for sampling algorithms (method, reps_per_cluster values)
4. WHEN batch experiments are executed, THE BTMS pipeline SHALL generate unique output directories for each parameter combination
5. THE BTMS pipeline SHALL support parallel execution of independent experiment configurations
6. THE BTMS pipeline SHALL generate a summary report aggregating results across all experiment configurations

### Requirement 12: 实验结果追踪

**User Story:** As a researcher, I want to track experiment configurations and results, so that I can reproduce experiments and compare different settings.

#### Acceptance Criteria

1. THE BTMS pipeline SHALL record full experiment configuration in each output directory
2. THE BTMS pipeline SHALL record algorithm parameters, random seeds, and input data paths
3. THE BTMS pipeline SHALL generate consistent output directory naming based on experiment parameters
4. WHEN experiments are completed, THE BTMS pipeline SHALL output metrics in a machine-readable format (JSON/CSV)
5. THE BTMS pipeline SHALL support incremental experiment runs (skip already completed configurations)
