## 1. Multi-View Bug Artifacts

- [x] 0.1 Create a new self-contained module folder for this pipeline (no edits to existing modules), organized with `src/` (code) and `data/` (outputs)
- [x] 1.1 Define view schema and mapping from `prompt_list/<slug>/` files to views (report/test/code/obfuscated/mixed)
- [x] 1.2 Implement optional buggy-code obfuscation/anonymization pipeline for the "obfuscated" view
- [x] 1.3 Extend embedding generation to embed each (slug, view) item with stable IDs and rich metadata

## 2. Agglomerative Hierarchical Clustering

- [x] 2.0 Prepare clustering input export (vectors.npy, id_mapping.pkl, metadata.pkl) from embeddings.jsonl
- [x] 2.1 Implement agglomerative clustering runner (cosine + average as default; configurable)
- [x] 2.2 Export merge tree/dendrogram data for explainability
- [x] 2.3 Export multiple cut levels (e.g. k=10/20/50) as nested cluster assignments

## 3. Representative Selection (Diversity Sampling)

- [x] 3.1 Implement or adapt representative selection to guarantee per-cluster coverage and reproducibility
- [x] 3.2 Produce per-cluster exports with representative IDs and point metadata (compatible with downstream selectors)

## 4. PPL Ingestion and Cluster-Level Task Modeling Selection

- [x] 4.1 Implement PPL result reader for `ppl/result/` (support both flat and per-sample directory layouts)
- [x] 4.2 Define per-bug PPL aggregation (e.g. median IO PPL across samples)
- [x] 4.3 Implement cluster-level task-modeling selector based on representatives’ PPL signals (with tie-breaks and fallbacks)

## 5. Evaluation and Reporting

- [x] 5.1 Compute and export cluster-level metrics (PPL distributions, deltas between task modelings)
- [x] 5.2 Compute and export overall metrics and baseline comparisons (always-A / always-B / oracle)
- [x] 5.3 Generate a human-readable report (Markdown) for explainability

## 6. Quality, Validation, and Docs

- [ ] 6.1 Add schema/consistency validation (missing views, missing PPL, duplicated assignments)
- [ ] 6.2 Add minimal tests for PPL parsing and clustering export schema
- [ ] 6.3 Document how to run the pipeline end-to-end and how to interpret outputs
