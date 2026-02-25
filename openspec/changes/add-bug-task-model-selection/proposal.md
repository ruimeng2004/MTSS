# Change: Cluster-Guided Task Modeling Selection for Bug Repair

## Why
Different bug types may benefit from different task modeling formulations (e.g. “generate full refined code” vs “search/replace edit”, or different prompt compositions). However, a bug’s “type” is latent and difficult to hand-engineer from artifacts.

We want a systematic, data-driven method to:
- cluster bugs into interpretable groups using their artifacts (report, test info, buggy code, obfuscated code),
- sample representative bugs per group,
- use existing grey-box signals (e.g. O/IO PPL) from `ppl/result/` to pick the best task modeling for each group,
- evaluate the selection strategy at the cluster and global level.

## What Changes
- Add a multi-view bug representation pipeline (Report / Test Info / Buggy Code / Obfuscated Buggy Code / Mixed Code).
- Add an agglomerative (bottom-up) hierarchical clustering runner that outputs an explainable merge tree and multiple “cut” levels.
- Add representative selection (diversity sampling) per cluster for each cut level.
- Add PPL result ingestion from `ppl/result/` and a rule-based selector that assigns a preferred task modeling to each cluster based on representatives.
- Add evaluation report generation (cluster-level and overall metrics) to assess the effectiveness of the routing/selection.

## Impact
- **Affected specs:** new capability `bug-task-model-selection`
- **Affected code (expected):**
  - New code will be implemented in a new, self-contained folder to avoid modifying existing modules, organized with a clear `src/` and `data/` split (opt-in scripts).
- **Breaking changes:** None (new pipeline is opt-in)
