# Spec Delta: Bug Task Model Selection

## MODIFIED Requirements

### Requirement: Evaluation and Reporting
The system SHALL generate evaluation artifacts to assess cluster-guided task modeling selection against baselines using both PPL metrics and actual bug fix outcomes.

#### Scenario: Compare routed strategy against baselines using PPL
- **WHEN** evaluation is executed for a selected clustering cut level
- **THEN** the system SHALL report overall PPL for each configured PPL metric definition (e.g. O and IO), covering:
  - routed-by-cluster strategy
  - always-model-A baseline
  - always-model-B baseline
  - per-bug oracle baseline (min PPL across models)
- **AND** the system SHALL export a human-readable report (e.g. Markdown) with per-cluster summaries

#### Scenario: Execute actual bug fix attempts using routed task modelings
- **WHEN** fix evaluation is executed for a routing strategy
- **THEN** the system SHALL execute bug fix attempts using the routed task modeling for each bug
- **AND** the system SHALL respect the configured sampling budget (number of attempts per bug)
- **AND** the system SHALL stop early on first successful fix if early stopping is enabled

#### Scenario: Collect bugfix statistics
- **WHEN** fix attempts complete for a set of bugs
- **THEN** the system SHALL collect per-bug statistics including: total attempts, first success index, success status
- **AND** the system SHALL aggregate statistics at cluster level and overall level
- **AND** the system SHALL persist statistics in structured format (JSON/CSV)

#### Scenario: Calculate Loss metrics on fix outcomes
- **WHEN** bugfix results are available
- **THEN** the system SHALL calculate Loss metric as `(bugfix_multi - bugfix_router) / bugfix_multi`
- **AND** the system SHALL report bugfix_multi (multi-budget baseline fixed count)
- **AND** the system SHALL report bugfix_router (router strategy fixed count)
- **AND** the system SHALL export loss value with interpretation

#### Scenario: Compare fix outcomes against baselines
- **WHEN** fix evaluation includes baseline strategies
- **THEN** the system SHALL execute fix attempts for multi-budget baseline (primary), always-REW baseline, always-EDIT baseline, and optionally oracle baseline
- **AND** the system SHALL report success rates and Loss metrics for each strategy
- **AND** the system SHALL include statistical significance testing (e.g., McNemar's test) comparing router vs multi-budget baseline

## ADDED Requirements

### Requirement: Bug Fix Sampling
The system SHALL execute bug fix attempts using specified task modelings and collect repair outcomes.

#### Scenario: Execute fix attempt with routed task modeling
- **WHEN** a bug is assigned a task modeling by the routing strategy
- **THEN** the system SHALL invoke the appropriate patch generator (d4j_gen or d4j_edit)
- **AND** the system SHALL validate the generated patch using Defects4J validation infrastructure
- **AND** the system SHALL record the attempt result (success/failure) with metadata

#### Scenario: Respect sampling budget
- **WHEN** fix sampling is configured with budget k
- **THEN** the system SHALL execute at most k attempts per bug
- **AND** the system SHALL stop early if a successful patch is found and early stopping is enabled

#### Scenario: Handle validation failures gracefully
- **WHEN** patch validation times out or encounters errors
- **THEN** the system SHALL record the validation failure with error details
- **AND** the system SHALL continue with remaining attempts up to the budget
- **AND** the system SHALL report validation failure rates separately from fix failures

#### Scenario: Cache and resume fix experiments
- **WHEN** a fix evaluation experiment is interrupted
- **THEN** the system SHALL support resuming from the last completed bug
- **AND** the system SHALL reuse cached results for already-completed bugs

### Requirement: Loss Metric Calculation
The system SHALL calculate Loss metric based on budget allocation comparison to measure routing effectiveness against multi-budget baseline.

#### Scenario: Calculate router loss metric
- **WHEN** loss metric is calculated for a routing strategy
- **THEN** the system SHALL calculate `Loss = (bugfix_multi - bugfix_router) / bugfix_multi`
- **WHERE** bugfix_multi is the number of bugs fixed by splitting budget equally (5 for REW, 5 for EDIT)
- **AND** bugfix_router is the number of bugs fixed by allocating budget according to router-determined ratios
- **AND** router SHALL output budget allocation ratios (e.g., `{rew_ratio: 0.3, edit_ratio: 0.7}` for 3:7 split)
- **AND** router MAY choose any ratio: 0:10, 1:9, 2:8, 3:7, 4:6, 5:5, 6:4, 7:3, 8:2, 9:1, 10:0
- **AND** negative loss indicates routing improvement over multi-budget baseline

#### Scenario: Router outputs budget allocation ratios
- **WHEN** router makes a routing decision for a bug
- **THEN** the router SHALL output budget allocation ratios for REW and EDIT modelings
- **AND** the ratios SHALL sum to 1.0 (e.g., `{rew_ratio: 0.3, edit_ratio: 0.7}`)
- **AND** the system SHALL convert ratios to attempt counts based on total budget
- **AND** the system SHALL execute the specified number of attempts for each modeling

#### Scenario: Identify task modeling from PPL results
- **WHEN** PPL results are ingested from `ppl/result/<timestamp>/<slug>/<sample_idx>/result.json`
- **THEN** the system SHALL read the `task` field to identify the task modeling type
- **AND** the system SHALL map `task="d4j_gen"` to REW modeling
- **AND** the system SHALL map `task="d4j_edit"` to EDIT modeling
- **AND** the system SHALL use this mapping to associate PPL values with the correct task modeling

#### Scenario: Execute multi-budget baseline
- **WHEN** multi-budget baseline is executed with budget 10
- **THEN** the system SHALL execute 5 attempts using REW modeling for each bug
- **AND** the system SHALL execute 5 attempts using EDIT modeling for each bug
- **AND** the system SHALL count a bug as fixed if either modeling succeeds within its 5 attempts

#### Scenario: Execute router strategy with allocated budget
- **WHEN** router strategy is executed with budget 10
- **THEN** the system SHALL allocate attempts according to router-determined ratios for each bug
- **AND** the system SHALL execute the allocated number of attempts for REW modeling
- **AND** the system SHALL execute the allocated number of attempts for EDIT modeling
- **AND** the system SHALL count a bug as fixed if either modeling succeeds within its allocated attempts
- **AND** the system SHALL support any ratio allocation (e.g., 3:7, 2:8, 5:5, 7:3, 8:2)

#### Scenario: Handle zero bugfix_multi edge case
- **WHEN** bugfix_multi equals zero (no bugs fixed by multi-budget baseline)
- **THEN** the system SHALL handle division by zero gracefully
- **AND** the system SHALL report loss as 0.0 or undefined with appropriate warning

#### Scenario: Report loss interpretation
- **WHEN** loss metric is reported
- **THEN** the system SHALL include interpretation guidance:
  - Loss < 0: routing outperforms multi-budget baseline
  - Loss = 0: routing equivalent to multi-budget baseline
  - Loss > 0: routing underperforms multi-budget baseline

### Requirement: Baseline Strategy Execution
The system SHALL execute baseline strategies for comparison with the routed strategy.

#### Scenario: Execute multi-budget baseline
- **WHEN** multi-budget baseline is enabled
- **THEN** the system SHALL split the budget equally between REW and EDIT modelings
- **AND** the system SHALL execute fix attempts using both modelings with half budget each
- **AND** the system SHALL collect statistics for this baseline (primary baseline for Loss calculation)

#### Scenario: Execute always-REW baseline
- **WHEN** always-REW baseline is enabled
- **THEN** the system SHALL execute fix attempts using REW (d4j_gen) task modeling for all bugs with full budget (10:0 ratio)
- **AND** the system SHALL collect statistics and calculate losses for this baseline

#### Scenario: Execute always-EDIT baseline
- **WHEN** always-EDIT baseline is enabled
- **THEN** the system SHALL execute fix attempts using EDIT (d4j_SR) task modeling for all bugs with full budget (0:10 ratio)
- **AND** the system SHALL collect statistics and calculate losses for this baseline

#### Scenario: Execute fixed-ratio baselines
- **WHEN** fixed-ratio baseline is enabled with specified ratio (e.g., 3:7, 7:3)
- **THEN** the system SHALL execute fix attempts using the fixed ratio for all bugs
- **AND** the system SHALL collect statistics to compare against router's dynamic ratio selection
- **AND** the system SHALL support multiple fixed-ratio baselines (e.g., 2:8, 3:7, 7:3, 8:2)

#### Scenario: Execute oracle baseline
- **WHEN** oracle baseline is enabled
- **THEN** the system SHALL execute fix attempts using all possible ratios for each bug
- **AND** the system SHALL select the best ratio outcome (first success or fewest total attempts) per bug
- **AND** the system SHALL report oracle results as upper bound on routing effectiveness

#### Scenario: Reuse baseline results across experiments
- **WHEN** multiple routing experiments are evaluated
- **THEN** the system SHALL support caching baseline results (including all ratio attempts)
- **AND** the system SHALL reuse cached baseline results when configuration matches

### Requirement: Router Budget Allocation
The system SHALL support router-determined budget allocation ratios between task modelings.

#### Scenario: Router determines allocation ratios
- **WHEN** router makes a decision for a bug
- **THEN** the router SHALL output allocation ratios for REW and EDIT modelings
- **AND** the ratios SHALL be in range [0.0, 1.0] and sum to 1.0
- **AND** the router MAY use any ratio (e.g., 0.3:0.7, 0.5:0.5, 0.8:0.2)

#### Scenario: Convert ratios to attempt counts
- **WHEN** allocation ratios are applied to a budget
- **THEN** the system SHALL convert ratios to integer attempt counts
- **AND** the system SHALL handle rounding (e.g., 0.35 * 10 = 3.5 → 3 or 4 attempts)
- **AND** the total attempts SHALL not exceed the budget

#### Scenario: Learn optimal ratios from features
- **WHEN** router is trained or configured
- **THEN** the router MAY learn optimal ratios based on cluster features and PPL signals
- **AND** the router MAY use classification, regression, or rule-based methods
- **AND** the router MAY start with discrete ratio options (e.g., 2:8, 3:7, 5:5, 7:3, 8:2) for simplicity

### Requirement: Fix Evaluation Configuration
The system SHALL support configuration of fix evaluation experiments including sampling budgets, baselines, and loss metrics.

#### Scenario: Configure sampling parameters
- **WHEN** fix evaluation is configured
- **THEN** the system SHALL accept sampling_budget (number of attempts per bug)
- **AND** the system SHALL accept early_stop flag (stop on first success)
- **AND** the system SHALL accept timeout_per_attempt (validation timeout in seconds)

#### Scenario: Configure baseline strategies
- **WHEN** fix evaluation is configured
- **THEN** the system SHALL accept flags to enable/disable each baseline strategy
- **AND** the system SHALL support running routed strategy only, baselines only, or both

#### Scenario: Configure loss metrics
- **WHEN** fix evaluation is configured
- **THEN** the system SHALL accept a list of loss metric definitions to calculate
- **AND** the system SHALL support multiple loss metrics in a single experiment

#### Scenario: Configure experiment subset
- **WHEN** fix evaluation is configured
- **THEN** the system SHALL support specifying a subset of bugs to evaluate (e.g., first 100 bugs, specific projects)
- **AND** the system SHALL support random sampling of bugs with configurable seed

### Requirement: Fix Evaluation Reporting
The system SHALL generate comprehensive reports comparing routing strategy against baselines on actual repair outcomes.

#### Scenario: Generate fix evaluation report
- **WHEN** fix evaluation completes
- **THEN** the system SHALL generate a Markdown report including:
  - Overall success rates for routed strategy and baselines
  - Per-cluster success rate breakdown
  - Loss metric comparisons across strategies
  - Statistical significance test results
- **AND** the report SHALL include visualizations (tables, charts) where applicable

#### Scenario: Export structured results
- **WHEN** fix evaluation completes
- **THEN** the system SHALL export structured results in JSON format including:
  - Per-bug fix outcomes with attempt details
  - Aggregated statistics (cluster-level and overall)
  - Loss metric values for all strategies
  - Experiment configuration and metadata

#### Scenario: Generate cost analysis report
- **WHEN** fix evaluation completes and token tracking is enabled
- **THEN** the system SHALL report token costs for each strategy
- **AND** the system SHALL calculate cost-effectiveness metrics (cost per successful fix)

#### Scenario: Export comparison visualizations
- **WHEN** fix evaluation completes
- **THEN** the system SHALL generate comparison charts including:
  - Success rate bar charts (routed vs baselines)
  - Loss metric comparison charts
  - Per-cluster heatmaps showing routing decisions and outcomes

### Requirement: Adaptive Budget Allocation (Current Scope)
The system SHALL support router-determined budget allocation where router outputs optimal budget split ratios between task modelings based on bug characteristics.

#### Scenario: Router outputs budget allocation ratio
- **WHEN** router makes a routing decision
- **THEN** the router SHALL output budget allocation ratios (e.g., `{rew_ratio: 0.3, edit_ratio: 0.7}`)
- **AND** the system SHALL allocate attempts according to the specified ratios
- **AND** the router SHALL be able to choose any ratio from 0:10 to 10:0

#### Scenario: Evaluate router ratio selection against fixed ratios
- **WHEN** router evaluation is performed
- **THEN** the system SHALL compare router-determined ratios against fixed ratio baselines (1:1, 2:1, 1:2, 3:7, 7:3, etc.)
- **AND** the system SHALL report whether router's dynamic ratio selection outperforms fixed ratio strategies
- **AND** the system SHALL analyze which ratios router selects for different bug clusters
