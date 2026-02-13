# Out-of-the-Box Requirements

Goal: run this benchmark using only AgentDeck-native capabilities (no custom
metrics code, no custom post-hoc calculators, no custom reporting pipelines).

## P0 Required Before Running Cells

1. Match execution API
- Requirement: run matches only with `AgentDeck(...).play(...)`.
- Status: `ready` (native API).

2. Controllers and prompt cadence
- Requirement: use only built-in controllers (`ActionOnlyController`, `ReasoningController`) and PromptBuilder templates configured in `matrix.yaml`.
- Status: `ready` (defined in `config_registry`).

3. Reproducibility and turn budget
- Requirement: deterministic seeds, `max_turns`, and frozen `git/pricing/prompt` inputs.
- Status: `ready` (manifest + matrix freeze fields + `turn_budget.py` helper).

4. Runtime observability
- Requirement: rely on built-in spectators only.
- Required spectators: `ProgressDisplay`, `StatsTracker`, `TokenUsageTracker`.
- Optional spectator: `StatisticalAnalysisSpectator` (batch summary).
- Status: `ready`.

5. Artifact generation
- Requirement: use AgentDeck recorder outputs as source of truth (session records/logs).
- Status: `ready` (recorder is automatic in AgentDeck sessions).

6. Provider/model pricing availability
- Requirement: exact model ids used in matrix must resolve in `pricing.yaml`.
- Status: `ready` for current v2 matrix models.

## P1 Strongly Recommended Before Full Campaign

1. Matrix orchestration runner
- Requirement: execute by `phase_id` and `cell_id` directly from `matrix.yaml` with no custom analytics.
- Status: `gap` (planned script: `run_matrix_phase.py`).

2. Resume/checkpoint ergonomics
- Requirement: restart long runs safely from cell/match progress.
- Status: `partial` (session artifacts exist; matrix-level resume helper not yet implemented).

3. Highlight export from recordings
- Requirement: generate `clutch/comeback/chaos/dumb_decision/cost_upset` tags from built-in artifacts only.
- Status: `gap` (planned script: `export_highlights.py`).

## Working Rule for This Benchmark

1. Do not add custom win-rate/cost/significance calculators outside AgentDeck research modules and built-in spectators.
2. Do not add custom print-based summaries as execution source of truth.
3. If a needed capability is missing, implement it as a reusable AgentDeck feature or official script before running full phases.
