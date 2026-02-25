# MTSS: Multi-Task Strategy Selection for LLM-based APR

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **MTSS (Multi-Task Strategy Selection)** is a routing framework for LLM-based automated program repair (APR).
> It dynamically selects between two repair strategies — **Edit** (targeted local patch) and **REW** (full file rewrite) — for each bug instance, validated on **Defects4J** (Java) and **SWE-bench Verified** (Python).

## Overview

**MTSS** is a routing framework that dynamically selects the optimal repair strategy for each bug instance.

### Two Repair Strategies

| Strategy | Description | Output Format |
|----------|-------------|---------------|
| **Edit (SR)** | Targeted local modification using SEARCH/REPLACE blocks | `unified diff` |
| **REW (Gen)** | Full file rewrite from context | `unified diff` |

### Core Insight: Strategy Selection Matters

| Setting | Edit | REW | Routing (MTSS) |
|---------|------|-----|----------------|
| Defects4J (Java) | **78.9%** | 72.2% | 74.64% |
| SWE-bench Verified (Python) | TBD | TBD | TBD |

The optimal strategy is **benchmark-dependent**. MTSS learns to route each bug instance to the better-suited repair mode based on structural features (change scope, repo history, cluster assignment).

---

## Routing Mechanism

MTSS uses a **Hybrid Metric** to decide which repair strategy to use for each bug:

### Routing Signals

| Signal | Description | Weight |
|--------|-------------|--------|
| **PPL Gap** | Perplexity difference between Edit and REW outputs | 0.4 |
| **Vote Consistency** | Majority vote across cluster representatives | 0.4 |
| **Cluster Size** | Reliability factor based on cluster population | 0.2 |

### Routing Formula

```python
# Step 1: Compute individual signals
ppl_ratio = sigmoid(-(mean_edit_ppl - mean_rew_ppl) / temperature)
vote_ratio = edit_votes / total_votes
size_factor = min(cluster_size / normalization, 1.0)

# Step 2: Compute confidence
confidence = (
    ppl_confidence * 0.4 +
    vote_confidence * 0.4 +
    size_factor * 0.2
)

# Step 3: Weighted routing decision
edit_ratio = 0.5 + (weighted_ratio - 0.5) * confidence
```

**Key intuition**: Strong signals (large PPL gap, unanimous vote, large cluster) → high confidence → aggressive routing. Weak signals (small gap, split vote, tiny cluster) → low confidence → conservative fallback to 50:50.

**Example scenarios**:
- Large cluster (N=50) + strong Edit preference (PPL gap = -5.0, 9/10 vote) → **84.9% Edit**
- Tiny cluster (N=2) + weak signal (PPL gap = -0.5, 3/5 vote) → **51.5% Edit** (nearly neutral)

See [`docs/BTMS_ARCHITECTURE.md`](docs/BTMS_ARCHITECTURE.md) and [`../btms-budget-allocation/HYBRID_METRIC_DESIGN.md`](../btms-budget-allocation/HYBRID_METRIC_DESIGN.md) for full details.

---

## Repository Structure

```
MTSS/
├── README.md
├── requirements.txt
├── config.yaml                  # Main config (API key, model settings)
├── btms_config.yaml             # BTMS routing experiment config
│
├── scripts/                     # Experiment entry points
│   ├── run_btms_routing_eval.py     # BTMS routing evaluation (main)
│   ├── run_btms_enhanced_eval.py    # Enhanced routing with probabilistic mode
│   ├── run_probabilistic_routing_eval.sh
│   ├── run_edit_batch_evaluation.py # Edit-only baseline
│   ├── run_gen_batch_evaluation.py  # REW-only baseline
│   ├── run_parallel_evaluation.py
│   ├── run_evaluation.sh
│   ├── run_btms_best_config.sh
│   ├── run_control_evals.sh
│   └── batch.sh                     # D4C original patch generation
│
├── tools/                       # Utility scripts
│   ├── checkout.py                  # Checkout Defects4J bug repos
│   ├── evaluate.py                  # Patch validation
│   ├── compare_results.py           # Compare routing strategies
│   ├── extract_results.py           # Extract evaluation metrics
│   ├── result_refiner.py
│   ├── show_progress.py
│   ├── pre_checkout_bugs.py
│   └── sample_bugs_by_project.py
│
├── docs/                        # Architecture & design documents
│   ├── BTMS_ARCHITECTURE.md
│   ├── BTMS_QUICKSTART.md
│   ├── BTMS_IMPLEMENTATION_SUMMARY.md
│   ├── PROBABILISTIC_ROUTING_IMPLEMENTATION.md
│   └── BTMS_ENHANCED_README.md
│
├── bug_task_model_selection/    # BTMS core routing framework
│   └── src/btms/
│       ├── clustering/              # HAC / K-means / bisecting clustering
│       ├── sampling/                # DPP / farthest-first sampling
│       ├── selection/               # Routing selector & budget allocator
│       └── experiment/              # Experiment runner & config
│
├── embedding/                   # Issue embedding & vector clustering
│   ├── embedder.py
│   ├── vector_store.py
│   └── hierarchical_clustering.py
│
├── ppl/                         # Perplexity scoring (routing signal)
│   ├── perplexity.py
│   ├── d4j_api_ppl_edit.py
│   └── d4j_api_ppl_gen.py
│
├── generator/                   # Patch generation for D4J / SWE-bench
│   ├── d4j.py                       # D4J Edit mode (SR)
│   ├── d4j_SR_v3_multi.py
│   ├── d4j_Rew_muliti.py            # D4J REW mode
│   └── SWE_bench.py                 # SWE-bench adapter
│
├── evaluation/                  # Evaluation framework
│   └── core/                        # Patch applicator, evaluator, reporter
│
├── prompt/                      # Prompt templates
├── analysis/                    # Result analysis scripts
└── btms_budget_experiments/     # Budget allocation experiments
```

---

## Setup

### Prerequisites

- Python 3.10+
- Linux (macOS not recommended for Defects4J evaluation)

```bash
pip install -r requirements.txt
```

### Configure API / Model

Edit `config.yaml`:

```yaml
api_key: "sk-xxxxx"          # OpenAI API key
remote_model: "gpt-4o"       # Remote model
local_model: "..."           # Local model path (optional)
```

### Setup Defects4J (for Java experiments)

1. Clone [Defects4J](https://github.com/rjust/defects4j) and install dependencies (Java 11, Perl ≥ 5.0.12, svn ≥ 1.8)
2. Initialize:
   ```bash
   cd defects4j && cpanm --installdeps . && ./init.sh
   export PATH=$PATH:/path/to/defects4j/framework/bin
   ```
3. Checkout bug repos:
   ```bash
   python tools/checkout.py
   ```

---

## Running Experiments

### D4J Baseline (Edit / REW)

```bash
# Edit mode (SR) — Defects4J
bash scripts/batch.sh

# Or run Edit / REW evaluations separately
python scripts/run_edit_batch_evaluation.py
python scripts/run_gen_batch_evaluation.py
```

### BTMS Routing (main experiment)

```bash
# Probabilistic routing with BTMS
python scripts/run_btms_routing_eval.py --config btms_config.yaml

# Best config sweep
bash scripts/run_btms_best_config.sh
```

### Patch Validation

```bash
python tools/evaluate.py \
  --test True \
  --data defects4j \
  --pred result/defects4j/pred_full_1shot_gpt-4_10try_temp=1.0.csv \
  --eval result/defects4j/eval_full_1shot_gpt-4_10try_temp=1.0.csv
```

---

## SWE-bench Extension (in progress)

Active development for validating MTSS routing on **SWE-bench Verified (500 instances)**:

- Edit mode → `Agentless repair.py` (SEARCH/REPLACE output)
- REW mode → `Agentless repair_rew.py` (full file rewrite)
- Routing signals: `changed_lines`, `repo`, `cluster_id`, FSI-aware rerank

See design document in `../mtss_swebench/design.md` for full experimental plan.

---

## License

MIT License

