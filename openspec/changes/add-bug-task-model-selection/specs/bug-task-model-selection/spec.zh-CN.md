## ADDED Requirements

### Requirement: 多视角 Bug Item 化
系统 SHALL 基于多种工件视角（例如 report、test info、buggy code、派生/混淆变体）为每个 bug 构造一个或多个聚类 item。

#### Scenario: 从 prompt_list 工件构造 items
- **WHEN** `prompt_list/<slug>/` 下存在某个 bug `slug`
- **THEN** 系统 SHALL 为每个已配置且可用的视角构造 items `(slug, view)`
- **AND** 每个 item 至少 SHALL 携带可追溯元数据：`slug`、`view`、`source_file`

#### Scenario: 派生视角生成
- **WHEN** 启用某个派生视角（例如 `buggy_code_obfuscated`）
- **THEN** 系统 SHALL 从源工件确定性生成派生工件
- **AND** item 元数据 SHALL 记录所使用的 transform 配置

### Requirement: Bug Items 的 Embedding
系统 SHALL 为每个 `(slug, view)` item 计算 embedding，并以稳定标识符持久化。

#### Scenario: 稳定 embedding 标识符
- **WHEN** 对某个 item `(slug, view)` 生成 embedding
- **THEN** 系统 SHALL 分配一个由 `(slug, view)` 派生的稳定 `item_id`（例如 `{slug}__{view}`）
- **AND** embedding 存储 SHALL 保留从 `item_id` 到元数据的映射

### Requirement: 凝聚式层次聚类
系统 SHALL 支持对 embedded items 执行凝聚式（自底向上）层次聚类，并支持配置距离度量与 linkage。

#### Scenario: 使用 cosine + average 运行聚类
- **WHEN** 用户以 `metric=cosine` 且 `linkage=average` 对某个视角执行聚类
- **THEN** 系统 SHALL 产出覆盖全部输入 items 的层次聚类结果

#### Scenario: 为可解释性导出 merge tree
- **WHEN** 凝聚式层次聚类完成
- **THEN** 系统 SHALL 导出足以重建 dendrogram 的 merge tree 数据（例如 children merges 与 merge distances）

### Requirement: 多粒度切分（Multi-Level Cuts）
系统 SHALL 从层次树导出多种粒度（cuts）的聚类结果。

#### Scenario: 导出 k-cut 聚类分配
- **WHEN** 用户请求 cut levels `k ∈ {k1, k2, ...}`
- **THEN** 系统 SHALL 为每个请求的 `k` 输出 per-item 的簇分配
- **AND** 每个 cut 输出 SHALL 包含簇大小与成员 item_ids

### Requirement: 代表点选择（多样性采样）
系统 SHALL 在每个 cut level 上为每个簇选择代表 items，以支持可解释性与后续决策。

#### Scenario: 保证每簇覆盖
- **WHEN** 对某个 cut level 执行代表点选择
- **THEN** 系统 SHALL 为每个非空簇至少选择 1 个代表点

#### Scenario: 选择可复现
- **WHEN** 使用相同输入与 `seed`
- **THEN** 代表点选择结果 SHALL 可复现

### Requirement: PPL 结果读取
系统 SHALL 从 `ppl/result/` 读取多种任务建模的灰盒指标，并在 per-bug 维度进行聚合。

#### Scenario: 仅针对两种任务建模
- **WHEN** 执行本变更的路由流水线
- **THEN** 系统 SHALL 仅支持两种任务建模：`d4j_gen` 与 `d4j_edit`

#### Scenario: 解析扁平目录布局
- **WHEN** PPL 输出保存为 `ppl/result/<run_ts>/<slug>/result.json`
- **THEN** 系统 SHALL 提取配置的 PPL 指标，并将其关联到 `(slug, task_model)`

#### Scenario: 解析按 sample 的目录布局
- **WHEN** PPL 输出保存为 `ppl/result/<run_ts>/<slug>/<sample_idx>/result.json`
- **THEN** 系统 SHALL 以可配置的 reducer（默认 median）跨 samples 聚合出 per-slug 指标

#### Scenario: 同时读取 O 与 IO 两套口径
- **WHEN** 源结果中同时存在 O 与 IO 两套 PPL 口径
- **THEN** 系统 SHALL 同时读取与输出两套口径，使得后续路由与评估可分别在两套口径下执行

### Requirement: 簇级任务建模选择
系统 SHALL 基于代表点的聚合 PPL 信号，为每个簇选择优先任务建模。

#### Scenario: 选择代表点 PPL 更低的模型
- **WHEN** 某簇的代表点在多个任务建模下均存在有效 PPL
- **THEN** 系统 SHALL 选择代表点聚合 PPL 更低的任务建模

#### Scenario: 指标缺失的回退
- **WHEN** 某个任务建模缺失 PPL 指标
- **THEN** 系统 SHALL 回退选择另一个可用的任务建模
- **AND** 选择输出 SHALL 记录回退原因

### Requirement: 评估与报告
系统 SHALL 生成评估产物，用于对比“簇级路由任务建模”的策略与基线。

#### Scenario: 与基线对比 routed 策略
- **WHEN** 针对某个聚类 cut level 执行评估
- **THEN** 系统 SHALL 针对每个已配置的 PPL 口径（例如 O 与 IO）分别报告整体 PPL 指标，覆盖：
  - 按簇路由策略（routed-by-cluster）
  - always-model-A 基线
  - always-model-B 基线
  - per-bug oracle 基线（跨模型取 min PPL）
- **AND** 系统 SHALL 导出 human-readable 报告（例如 Markdown），包含 per-cluster 摘要
