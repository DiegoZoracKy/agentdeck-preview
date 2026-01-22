# SPEC-RESEARCH Implementation Compliance Report

**Spec Version**: 1.1.0
**Spec Status**: Final
**Review Date**: 2026-01-21
**Reviewer**: Codex (automated review)
**Implementation**: `src/agentdeck/research/analysis.py`, `src/agentdeck/research/comparison.py`, `src/agentdeck/research/statistical.py`, `src/agentdeck/research/statistical_analysis.py`, `src/agentdeck/research/performance_analysis.py`, `src/agentdeck/research/cost_analysis.py`, `src/agentdeck/research/multi_session.py`, `src/agentdeck/spectators/research_spectators.py`, `README.md`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 32 |
| Compliant | 25 |
| Partial | 7 |
| Non-Compliant | 0 |
| N/A | 0 |

**Overall Compliance**: 78.1% (25/32 fully compliant)

---

## Invariant Compliance Matrix

### Data Integrity (DI1-DI3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| DI1 | ResultsAnalyzer accepts MatchResults and does not mutate input | Yes | `analysis.py:11-41` | Uses input for read-only stats |
| DI2 | CSV export preserves winner, turns, duration, seed | Yes | `analysis.py:129-150` | Exports required fields |
| DI3 | Comparison functions track total matches and elapsed time | Partial | `comparison.py:140-216`, `comparison.py:354-379` | compare_models sets elapsed_time; progressive lacks elapsed_time |

### Statistical Rigor (SR1-SR4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| SR1 | Auto-select t-test/Mann-Whitney/bootstrap by sample size and normality | Yes | `statistical.py:170-182` | Uses n<30 bootstrap; Shapiro-Wilk for normality |
| SR2 | Report p-value, CI, test name, effect size | Yes | `comparison.py:175-231` | ComparisonResult populated with all fields |
| SR3 | Ensure fair player ordering via Console; avoid manual alternation | Partial | `comparison.py:150-152`, `comparison.py:209-216` | Relies on Console ordering, but metadata does not surface player_order_source |
| SR4 | Effect size uses Cohen's h (arcsine transform) | Yes | `statistical.py:104-136` | Implements arcsine difference |

### Progressive Testing (PT1-PT4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| PT1 | Run min_matches before significance checks | Yes | `comparison.py:290-324` | Checks only after min_matches |
| PT2 | Check significance at check_interval | Yes | `comparison.py:292-324` | Batch_size uses check_interval |
| PT3 | Record stopping decision in ProgressiveResult | Yes | `comparison.py:384-399` | stopped_early and significance_reached_at set |
| PT4 | Respect max_matches cap | Yes | `comparison.py:290-292` | Loop stops at max_matches |

### Reproducibility (RE1-RE3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| RE1 | Accept seed and derive per-match seeds deterministically | Yes | `comparison.py:133-138`, `comparison.py:270-275` | Passes seed into AgentDeckConfig |
| RE2 | Record seed, model configs, game config in metadata | Partial | `comparison.py:209-216` | Records seed only; model/game configs missing |
| RE3 | Benchmarks are versioned | Yes | `comparison.py:476-488` | benchmark_version stored in result |

### Metrics Aggregation (MA1-MA3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| MA1 | Collect win/draw rates, turns, costs, decision times | Yes | `comparison.py:142-177`, `comparison.py:209-213` | Tracks wins, draws, turns, costs, decision_times |
| MA2 | Compute confidence intervals for aggregated metrics | Partial | `comparison.py:209-216`, `statistical.py:344-358` | CI computed in aggregate_metrics, but comparison metadata has no CI for turns/cost/decision time |
| MA3 | Handle missing metrics gracefully | Yes | `comparison.py:166-172`, `statistical.py:318-329` | Guards missing cost/decision_times; returns None when no data |

### Dependency Handling (DH1-DH3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| DH1 | Missing scipy/statsmodels raises ImportError with install guidance | Partial | `statistical.py:31-36` | ImportError raised, but message lacks explicit install command |
| DH2 | compare_models falls back when libraries missing | Yes | `comparison.py:180-203` | Returns p_value=1.0, test_used=none, CI=(0,0) |
| DH3 | Optional dependencies documented | Yes | `README.md:167-168` | Research extra documented |

### Experiment Execution (EE1-EE2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| EE1 | Reuse provided player instances across matches | Yes | `comparison.py:150-152`, `comparison.py:300` | Uses same model instances in deck.play |
| EE2 | Use deck.play lifecycle; no explicit close required | Yes | `comparison.py:150-152`, `comparison.py:300` | Relies on AgentDeck.play |

### Cross-Player Comparison (CPC1-CPC5)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| CPC1 | 2-player direct comparison computed | Yes | `statistical_analysis.py:410-428` | Direct fields populated when two players |
| CPC2 | 3+ player pairwise matrix computed | Yes | `statistical_analysis.py:360-408` | Pairwise comparisons generated |
| CPC3 | Use binomial test for win rate significance | Yes | `statistical_analysis.py:372-377` | Calls statistical_significance |
| CPC4 | Matrix shows significance symbols (better/worse/none) | Yes | `statistical_analysis.py:452-463` | Uses check/cross/neutral symbols |
| CPC5 | Include effect sizes for significant comparisons | Yes | `statistical_analysis.py:380-405` | Effect sizes computed per pair |

### Post-Hoc Analysis (PH1-PH5)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| PH1 | Read recordings from agentdeck_runs/session_id/records | Yes | `statistical_analysis.py:101-139`, `performance_analysis.py:62-107`, `cost_analysis.py:61-103` | Uses records/ subdir |
| PH2 | Validate batch and match recordings exist | Partial | `statistical_analysis.py:149-167` | Checks batch file and match_refs, not individual match files |
| PH3 | Handle recorder schema versions gracefully | Partial | `statistical_analysis.py:156-176` | No schema version checks or compatibility branches |
| PH4 | Spectator wrappers do not duplicate analysis logic | Yes | `research_spectators.py:90-109`, `research_spectators.py:182-203`, `research_spectators.py:274-289` | Imports and calls standalone analysis classes |
| PH5 | Raise informative errors on analysis failures | Yes | `statistical_analysis.py:122-133`, `performance_analysis.py:90-103`, `cost_analysis.py:86-99` | FileNotFoundError messages include guidance |

---

## Drift Issues

1. **DI3**: Progressive comparisons lack elapsed_time tracking
   - **Description**: compare_models includes elapsed_time, but compare_models_progressive does not record it.
   - **Impact**: Progressive results lose timing transparency.
   - **Recommended Fix**: Record elapsed_time in ProgressiveResult metadata or add field.

2. **SR3**: player_order_source not surfaced in comparison metadata
   - **Description**: compare_models metadata does not include player_order_source from match metadata.
   - **Impact**: Post-hoc analysis cannot distinguish console vs game-controlled ordering.
   - **Recommended Fix**: Capture player_order_source (and player_order) in ComparisonResult.metadata.

3. **RE2**: Missing model/game config in comparison metadata
   - **Description**: compare_models metadata only includes seed and averages.
   - **Impact**: Reproducibility is incomplete without model/game config snapshots.
   - **Recommended Fix**: Attach model summaries and game configuration into metadata.

4. **MA2**: Confidence intervals not computed for all aggregated metrics in comparisons
   - **Description**: CI is only provided for win rate difference, not for turns/cost/decision time aggregates.
   - **Impact**: Metrics lack statistical bounds.
   - **Recommended Fix**: Compute CI for aggregated metrics (reuse aggregate_metrics for each metric).

5. **DH1**: ImportError lacks explicit install guidance
   - **Description**: ImportError message suggests verifying environment but does not include install command.
   - **Impact**: Users lack clear remediation.
   - **Recommended Fix**: Include `pip install agentdeck-ai[research]` in ImportError message.

6. **PH2**: Match recordings not validated
   - **Description**: Post-hoc tools check batch file but do not verify referenced match files exist.
   - **Impact**: Missing/corrupt matches can produce silent partial analyses.
   - **Recommended Fix**: Verify each match_ref points to an existing match file before analysis.

7. **PH3**: No recorder schema version handling
   - **Description**: Post-hoc analysis assumes current schema without version branching.
   - **Impact**: Older recorder payloads may break analysis.
   - **Recommended Fix**: Read schema_version and branch/normalize accordingly.

---

## Action Items

- [ ] Add elapsed_time tracking for progressive comparisons
- [ ] Include player_order_source and ordering metadata in comparison outputs
- [ ] Attach model and game config snapshots to comparison metadata
- [ ] Compute CIs for aggregated metrics beyond win rates
- [ ] Add explicit install guidance in dependency ImportErrors
- [ ] Validate match recording files before analysis
- [ ] Handle recorder schema version compatibility in post-hoc tools
