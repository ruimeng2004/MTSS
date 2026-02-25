## ADDED Requirements

### Requirement: Multi-View Bug Itemization
The system SHALL construct one or more clustering items per bug using multiple artifact views (e.g. report, test info, buggy code, derived/obfuscated variants).

#### Scenario: Build items from prompt_list artifacts
- **WHEN** a bug `slug` exists under `prompt_list/<slug>/`
- **THEN** the system SHALL build items `(slug, view)` for each configured view that is available
- **AND** each item SHALL include traceable metadata at minimum: `slug`, `view`, and `source_file`

#### Scenario: Derived view generation
- **WHEN** a derived view (e.g. `buggy_code_obfuscated`) is enabled
- **THEN** the system SHALL generate the derived artifact deterministically from the source artifact
- **AND** the item metadata SHALL record the transform configuration used

### Requirement: Embedding for Bug Items
The system SHALL compute embeddings for each `(slug, view)` item and persist them with stable identifiers.

#### Scenario: Stable embedding identifiers
- **WHEN** an item `(slug, view)` is embedded
- **THEN** the system SHALL assign a stable `item_id` derived from `(slug, view)` (e.g. `{slug}__{view}`)
- **AND** the embedding store SHALL preserve the mapping from `item_id` to metadata

### Requirement: Agglomerative Hierarchical Clustering
The system SHALL support agglomerative (bottom-up) hierarchical clustering over embedded items with configurable distance metric and linkage.

#### Scenario: Run clustering with cosine + average
- **WHEN** clustering is executed for a view with `metric=cosine` and `linkage=average`
- **THEN** the system SHALL produce a hierarchical clustering result covering all input items

#### Scenario: Export merge tree for explainability
- **WHEN** agglomerative clustering completes
- **THEN** the system SHALL export merge tree data (e.g. children merges and merge distances) sufficient to reconstruct a dendrogram

### Requirement: Multi-Level Cluster Cuts
The system SHALL export multiple clustering granularities (cuts) from the hierarchical tree.

#### Scenario: Export k-cut cluster assignments
- **WHEN** the user requests cut levels `k ∈ {k1, k2, ...}`
- **THEN** the system SHALL output per-item cluster assignments for each requested `k`
- **AND** each cut output SHALL include cluster sizes and member item_ids

### Requirement: Representative Selection (Diversity Sampling)
The system SHALL select representative items per cluster for each cut level to support interpretability and downstream decision making.

#### Scenario: Guarantee per-cluster coverage
- **WHEN** representatives are selected for a cut level
- **THEN** the system SHALL select at least one representative for each non-empty cluster

#### Scenario: Reproducible selection
- **WHEN** the same inputs and `seed` are used
- **THEN** representative selection SHALL be reproducible

### Requirement: PPL Result Ingestion
The system SHALL ingest grey-box metrics from `ppl/result/` for multiple task modelings and aggregate them per bug.

#### Scenario: Target exactly two task modelings
- **WHEN** this change's routing pipeline is executed
- **THEN** the system SHALL support exactly two task modelings: `d4j_gen` and `d4j_edit`

#### Scenario: Parse flat result layout
- **WHEN** PPL outputs are stored as `ppl/result/<run_ts>/<slug>/result.json`
- **THEN** the system SHALL extract the configured PPL metric(s) and associate them with `(slug, task_model)`

#### Scenario: Parse per-sample result layout
- **WHEN** PPL outputs are stored as `ppl/result/<run_ts>/<slug>/<sample_idx>/result.json`
- **THEN** the system SHALL aggregate metrics across samples into a single per-slug value using a configurable reducer (default: median)

#### Scenario: Ingest both O and IO metrics
- **WHEN** both O and IO PPL metrics are present in the source results
- **THEN** the system SHALL ingest and emit both metric definitions so that downstream routing and evaluation can be executed under each definition

### Requirement: Cluster-Level Task Modeling Selection
The system SHALL select a preferred task modeling per cluster using the representatives’ aggregated PPL signals.

#### Scenario: Choose the model with lower representative PPL
- **WHEN** a cluster has representatives with valid PPL values for multiple task modelings
- **THEN** the system SHALL choose the task modeling with lower aggregated representative PPL

#### Scenario: Missing metrics fallback
- **WHEN** PPL metrics are missing for one task modeling
- **THEN** the system SHALL fall back to the other available task modeling
- **AND** the selection output SHALL record the reason for the fallback

### Requirement: Evaluation and Reporting
The system SHALL generate evaluation artifacts to assess cluster-guided task modeling selection against baselines.

#### Scenario: Compare routed strategy against baselines
- **WHEN** evaluation is executed for a selected clustering cut level
- **THEN** the system SHALL report overall PPL for each configured PPL metric definition (e.g. O and IO), covering:
  - routed-by-cluster strategy
  - always-model-A baseline
  - always-model-B baseline
  - per-bug oracle baseline (min PPL across models)
- **AND** the system SHALL export a human-readable report (e.g. Markdown) with per-cluster summaries
