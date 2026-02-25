## 背景
本变更旨在引入一套“基于聚类的路由/选择”流水线：对每个 bug 选择合适的任务建模形式。

仓库中已有组件包括：
- `prompt_list/<slug>/...`：每个 bug 的工件（例如 `query.txt`, `FAILED_TEST.txt`, `ERROR_MESSAGE.txt`, `BUGGY_CODE.txt` 等）
- `embedding/`：embedding 生成 + 向量存储（可选 GPU）
- `embedding/hierarchical_clustering.py`：当前的分层 K-means（center-based）聚类
- `dpp/kdpp_sampling.py`：基于 greedy DPP 的代表点选择（依赖簇中心）
- `ppl/` + `ppl/result/`：不同任务建模的 PPL 评估输出（例如 `d4j_gen`, `d4j_edit`），以 case 级 JSON 结果形式保存
- `fix/cluster_model_selector.py`：现有 baseline，基于代表点的“修复成功次数”在簇级选择 GEN vs SR

本提案的核心变化：
- 选择信号从“修复成功”迁移到“灰盒 PPL 指标”；
- 聚类从“分层 K-means”扩展为“凝聚式层次聚类（自底向上）”，以获得更强的可解释性（merge tree/dendrogram）；
- 引入多视角（report/test/code/obfuscated/mixed）以捕获更全面的潜在 bug 特征。

## 目标 / 非目标

### 目标
- 使用凝聚式层次聚类，对 bugs（及/或 bug views）提供可解释的多级聚类结果。
- 支持多种 bug 工件视角：
  - report 类（当前 `query.txt`）
  - test info（失败测试代码）
  - error info（stacktrace/exception）
  - buggy code
  - 派生视角：混淆后的 buggy code、混合/组合的 code 变体
- 为每个簇选择代表点（覆盖 + 多样性），便于人工检查与簇级决策。
- 读取并聚合 `ppl/result/` 中至少两种任务建模的 PPL 信号，并基于代表点为每个簇选择更合适的任务建模。
- 输出评估报告：对比路由策略与基线（PPL 口径）。

### 非目标
- 替换现有的修复流水线（GEN/SR）或替换 `ppl/` 的 scorer 实现。
- 训练新模型。
- 保证 PPL 与修复成功强相关（PPL 仅作为 proxy 信号）。

## 拟议流水线（高层）
1. **多视角 item 构造**：对每个 bug `slug`，构造一个或多个 item `(slug, view)`。
2. **Embedding**：对每个 item 计算 embedding，并写入向量存储（带 slug/view/source path 元数据）。
3. **凝聚式层次聚类**：在某个视角内对 items（或 bug-level 聚合向量）聚类，并导出：
   - merge tree（children + distances）
   - 多个 cut 粒度（如 k=10/20/50）
4. **代表点选择**：对每个 cut level，为每个簇选择代表点（≥1），并确保可复现。
5. **PPL 读取**：从 `ppl/result/` 加载同一批 slugs 在不同任务建模下的 PPL。
6. **簇级任务建模选择**：用代表点 PPL 为每个簇决定优先任务建模。
7. **评估与报告**：计算簇级与整体指标，并生成可读报告。

## 关键设计决策

### View schema
- 基础视角来自 `prompt_list/<slug>/` 下的文件。
- 派生视角（obfuscated/mixed）由确定性变换生成。

建议的 canonical view 名称：
- `report`（来自 `query.txt`）
- `error`（来自 `ERROR_MESSAGE.txt`，或从 `query.txt` 提取）
- `test`（来自 `FAILED_TEST.txt`）
- `buggy_code`（来自 `BUGGY_CODE.txt`）
- `buggy_code_obfuscated`（派生）
- `buggy_code_mixed`（派生，例如拼接/打乱策略）

### 稳定 ID 与元数据
每个 embedded item 都必须可追溯：
- `item_id`：`"{slug}__{view}"`（或等价稳定方案）
- 最小元数据：`slug`, `view`, `source_file`, `tokens`；可选 `transform_config`

### 凝聚式层次聚类实现
- 采用 `sklearn.cluster.AgglomerativeClustering`，开启 `compute_distances=True`。
- 默认距离/链接：
  - `metric = cosine`
  - `linkage = average`
- merge tree 导出使用 `children_` + `distances_`。

### 多级聚类输出
- 提供多个 cut 粒度：
  - `k`-cuts：例如 `k ∈ {10, 20, 50}`
  - 可选：`distance_threshold` cuts
- 每个 cut 输出至少包含：
  - cluster 列表（cluster_id, size）
  - 成员 item_ids
  - 用于后续采样的 cluster “center”（成员向量均值）和/或 medoid id

### 代表点选择
目标是在可解释、可复现的前提下，对每个簇采样代表点。

两种兼容方案：
- **复用现有 greedy DPP 采样器**：通过导出包含 `center` 的 per-cluster 结构来对齐。
- 若某些 view 不便复用 DPP，则回退：
  - 每簇 medoid 作为第一个代表点
  - 簇内 farthest-first 作为额外代表点

### PPL 读取
`ppl/result/` 中存在两种目录布局：
- 扁平：`.../<run_ts>/<slug>/result.json`
- 按 sample：`.../<run_ts>/<slug>/<sample_idx>/result.json`

读取器应：
- 发现 run 与 task（本变更明确聚焦 `d4j_gen` 与 `d4j_edit`）
- 至少提取 `ppl` 与 `avg_nll`（如果存在也可提取 `ppl_io` / `io_ppl`）
- 对 (slug, task, metric) 跨 samples 聚合（默认 median；可配置为 mean）
- 若同时存在 O 与 IO 两套口径，则两者都输出，使得路由/评估可在两套口径下分别执行

### 簇级任务建模选择规则
初版启发式（可配置）：
- 对每个簇，分别计算各 task model 在代表点上的聚合 PPL。
- 选择代表点聚合 PPL **更低**的 task model。
- 回退与 tie-break：
  - 若某个模型缺失数据，则选另一个
  - 若两者都缺失，则选默认（可配置）

### 评估
至少报告：
- 簇级：代表点 PPL 分布、选择的模型、差值（delta）
- 整体：路由策略 vs baselines：
  - always GEN
  - always SR
  - oracle per bug（跨模型取 min PPL）

## 风险 / 权衡
- 混淆质量：简单混淆可能破坏语义；更鲁棒的混淆需要解析/改写，成本更高。
- PPL 作为 proxy：更低 PPL 不一定对应更高修复成功率。
- 数据 join 复杂：不同 run_ts 与目录布局、缺失/部分结果需要可靠处理。
- 兼容性：`ppl/` 运行环境是 Python >= 3.13；选择器建议仅“读取输出”，并保持在 Python 3.10 可运行。

## 迁移计划
- 保留现有分层 K-means 聚类与 success-based selector baseline。
- 新流水线以 opt-in 脚本与独立输出形式引入。
- 可选提供对比报告：PPL-based routing vs success-based routing。

## 未决问题
- 聚类在 bug level（每 bug 一个向量）还是 view level（每 bug 多 item）执行，以及 multi-view 决策如何融合。

## 决策补充（明确化）
- 本变更的路由/选择范围限定为两种任务建模：`d4j_gen` vs `d4j_edit`。
- 若同时存在 O 与 IO 两种 PPL 口径，流水线 SHALL 同时支持两者，并分别产出 routed-by-cluster 的结果与评估对比，以判断哪种口径在下游更有效。
- 对按 sample 的结果，默认使用 median 进行聚合（可配置为 mean）。
