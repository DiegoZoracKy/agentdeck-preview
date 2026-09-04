# Research Experiment Schema

> **Historical `0.2` contract:** this schema documents the Research package
> format used by the archived Studies in this repository. It is not the active
> `0.4` package contract, and the `agentdeck-research-*` commands referenced
> below are available only from the `agentic-edge-research` tag. Do not use this
> file as the template for new Studies while `SPEC-RESEARCH` and its child specs
> remain in draft.

This schema defines the standard, objective artifacts for research experiments.
Every experiment folder should follow the same structure and use these fields.

## Experiment Package Layout

```
research/<experiment-id>/
├── README.md          # Experiment card (short summary)
├── manifest.yaml      # Repro metadata (required)
├── matrix.yaml        # Benchmark grid definition (optional)
├── results.json       # Objective results (generated)
├── results.csv        # Match-level results (generated)
├── results.md         # Human-readable factual report (generated)
├── analysis/          # Authored human/AI interpretation workspace (optional)
├── artifacts/         # Plots/tables (optional)
├── notes/             # Human run notes (optional)
├── recordings/        # External pointers only (no raw JSON)
└── scripts/           # Experiment scripts (optional)
```

## Path Naming Idiom

AgentDeck uses a shared timestamp core for instanced artifacts:

```text
YYYYMMDD_HHMMSS
```

Examples:

```text
agentdeck_runs/session_20260423_174802_d5ae44/
analysis/analysis_20260428_143001_codex_results_review/
analysis/analysis_20260428_144215_claude_seat_effects/
```

Runtime sessions use `session_YYYYMMDD_HHMMSS_<suffix>`. Authored analysis
directories use `analysis_YYYYMMDD_HHMMSS_<author>_<topic_slug>`. Process-created
research packages MUST use the `research_` prefix. The explicit prefixes are
intentionally redundant with their parent directories because they make grep,
glob, and AI-assisted search easier.

Research package folders remain long-lived public study identifiers and SHOULD
use a prefixed date-slug when named directly by a human:

```text
research/research_YYYY-MM-DD-<kebab-slug>/
```

Examples:

```text
research/research_2026-04-27-agentic-edge-strategy-stack/
research/research_20260423_174802_d5ae44/
```

When a research package is created from a session without an explicit
experiment ID, the packager rewrites `session_YYYYMMDD_HHMMSS_<suffix>` to
`research_YYYYMMDD_HHMMSS_<suffix>`. Human-authored slugs SHOULD be lowercase
ASCII. Use kebab-case for public research package slugs and snake_case for
timestamped analysis topic slugs.

## Status-Based Completeness Rules

Packages are validated differently depending on `manifest.status`:

- `planned`: placeholders are allowed in `README.md`; generated outputs may be absent.
- `running`: partial factual updates are allowed; interpretive sections may remain placeholders.
- `complete` with `run.matches_completed > 0`: factual blocks in `README.md` MUST
  be populated (no placeholder values). If a legacy `analysis.md` exists, its
  factual block is also validated. Packages declaring `artifacts.results_md`
  MUST have generated `results.md`.
- `archived`: treated like `complete` for validation purposes.

`results.md` is generated and deterministic. Interpretive documents under
`analysis/` are human/AI-authored and are not canonical factual artifacts.

## manifest.yaml (Required)

### Required Fields
- `schema_version` (int)
- `experiment_id` (string, folder name)
- `status` (planned|running|complete|archived)
- `question` (string)
- `game.name` (string)
- `players[].provider` (string)
- `players[].model` (string)
- `run.matches_planned` (int)
- `run.seed_base` (int)

### Recommended Fields
- `title` (string)
- `started_at`, `completed_at` (ISO-8601)
- `game.config` (dict)
- `players[].controller`, `players[].renderer`
- `variants` (models/controllers used across matchups)
- `run.matches_completed`, `run.concurrency`, `run.max_turns`
- `run.source_sessions` (ordered session id list used for checkpoint aggregation)
- `run.matrix_source` (path to matrix definition when present)
- `analysis_plan` (ci_method, alpha, effect_size)
- `artifacts` (paths for results.json/results.csv/plots)
- `storage` (where raw recordings and derived artifacts live)
- `notes`

When `matrix.yaml` is present, it should be the source of truth for:
- benchmark cells/phases
- sampling policy (pilot/expansion)
- expansion rules and overrides
- package aggregation phase scope

If an experiment is single-run or smoke-test oriented, `matrix.yaml` may be omitted.
In that case, `run.matrix_source` and `artifacts.matrix_yaml` SHOULD be omitted as well.

### Example
```yaml
schema_version: 1
experiment_id: research_2025-11-08-openai-benchmarks
title: OpenAI Strategic Benchmarks
status: running
question: How do OpenAI model configs compare in strategic gameplay?
game:
  name: FixedDamageGame
  config: {}
players:
  - id: A
    provider: openai
    model: gpt-4o-mini
    controller: ReasoningController
  - id: B
    provider: openai
    model: gpt-4o-mini
    controller: ActionOnlyController
run:
  seed_base: 42
  matches_planned: 200
  matches_completed: 120
  concurrency: 10
analysis_plan:
  ci_method: wilson
  alpha: 0.05
  effect_size: cohens_h
artifacts:
  results_json: results.json
  results_csv: results.csv
  results_md: results.md
  analysis_dir: analysis/
notes: ""
```

## results.json (Generated)

### Required Fields
- `schema_version` (int)
- `experiment_id` (string)
- `source.recordings_dir` (string; primary source pointer)
- `summary` (object)
- `players` (array of player metadata)
- `matches` (array of match summaries)

Optional source extension:
- `source.recordings_dirs` (array of strings) for multi-session checkpoint aggregation.
- `source.aggregation_scope` (`cell|study_phases|explicit_phase|explicit_cells|all_phases`)
- `source.phase` and `source.cell_id` for cell exports.
- `source.phases_included` and `source.cells_included` for matrix package exports.
- `generated_at` (ISO-8601) unless the export intentionally omitted it via `--no-generated-at`.
- `behavioral_profile` (object; optional game-specific behavioral scorer output)

For `results.json.schema_version >= 2`, the following are additionally required:
- `statistics` (object; inferential metrics)
- `format_strictness` (object; contract compliance metrics)
- `position_effect` (object; first-player and upset metrics)

For `results.json.schema_version >= 3`, the following is additionally required:
- `artifact_validation` (object; game-agnostic recording invariant summary)

### Summary Fields
- `total_matches`
- `decisive_matches`
- `draws`
- `win_rates` (per player)
- `total_cost`
- `avg_turns`, `avg_duration`, `avg_cost`

### statistics Fields (Minimum)
- `method`, `confidence_level`, `alpha`, `null_win_rate`
- `n_total`, `n_decisive`
- `players` (map)

Per-player:
- `wins`, `win_rate`
- `ci` (`[lower, upper]`)
- `p_value`
- `effect_size`
- `effect_label` (`negligible|small|medium|large`)

Optional `pairwise_comparisons` entries are direct head-to-head only. A pairwise
entry must be derived only from matches where both `player_a` and `player_b`
appear in the same `matches[*].players` array; package-level aggregate wins from
unrelated cells must not be used as pairwise evidence.

Per-pair fields:
- `player_a`, `player_b`
- `comparison_scope: direct_head_to_head`
- `wins_a`, `wins_b`
- `head_to_head_matches`
- `head_to_head_decisive`
- `win_rate_a`
- `ci_a`
- `p_value`
- `effect_size`
- `effect_label`
- `is_significant`

### format_strictness Fields (Minimum)
- `overall` and `by_player`

Per entry:
- `turn_attempts`
- `parse_failures`, `parse_failure_rate`
- `contract_evaluable_attempts`
- `strict_contract_passes`, `strict_contract_rate`
- `recoverable_non_strict`, `recoverable_non_strict_rate`
- `action_line_rate`, `reasoning_line_rate`

These metrics MUST be game-agnostic and derived only from recorder events and
controller contracts.

### position_effect Fields (Minimum)
- `total_matches`
- `first_player_wins`, `first_player_win_rate`
- `second_player_wins`, `upset_rate`
- `by_player`

Per player:
- `first_count`, `second_count`
- `wins_as_first`, `wins_as_second`
- `win_rate_as_first`, `win_rate_as_second`

These metrics MUST be game-agnostic and derived only from `first_player` metadata
and `winner` fields in recorded matches.

### artifact_validation Fields (Minimum)
- `matches_checked`
- `all_passed`
- `checks`
- `failures`

Required checks:
- `monotonic_gameplay_timeline`
- `top_level_timing_consistency`
- `prompt_turn_number_coherence`
- `winner_final_state_consistency`

Each check entry should contain:
- `passed`
- `failed`

Exports SHOULD fail fast when any artifact invariant fails. Committed public
results should therefore have `all_passed: true` and `failures: []`.

### behavioral_profile Fields (Optional)
When present, `behavioral_profile` should follow `SPEC-RESEARCH-BEHAVIORAL.md`.

Minimum fields:
- `schema_version`
- `game_id`
- `profile_id`
- `profile_version`
- `coverage`
- `aggregate_metrics`
- `per_player`
- `state_metrics`
- `evidence`
- `quality_flags`

This extension is optional because behavioral scorers are game-specific. The
baseline research package contract remains game-agnostic.

### Match Fields (per entry)
- `match_id`
- `players` (ordered list)
- `winner`
- `turns`
- `outcome` (win|draw|forfeit|abort)
- `seed`
- `duration`
- `cost`
- `player_costs`
- `player_order_source`
- `first_player`

`first_player` should be an object containing:
- `name`
- `index` (original roster index)
- `ordered_index` (slot within the effective ordered player list)

## matrix.yaml (Optional, Recommended for Benchmark Grids)

### Minimum Supported Shared-Workflow Contract

The shared matrix export workflow assumes:
- `experiment_id`
- `cells`
- `execution_plan.phases` when phase-based export is used

Each cell SHOULD define at minimum:
- `id`
- `phase`

Suggested top-level sections:
- `frozen_inputs` (git tag/commit, template version, pricing snapshot)
- `phase_model` (default package aggregation scope)
- `player_registry`
- `config_registry`
- `sampling_policy`
- `execution_plan`
- `cells`

### phase_model

Multi-phase matrices SHOULD declare phase scope before top-level package export.

Recommended fields:
- `study_phases`: phases included in default `--package` aggregation.
- `preflight_phases`: smoke/setup phases excluded from default `--package` aggregation.
- `main_phases`: scaled study phases, when distinct from pilot phases.
- `excluded_phases`: phases intentionally excluded from default package aggregation.

If `study_phases` is missing and the matrix has multiple non-empty phases,
`agentdeck-research-export --package` fails fast unless `--phase` or `--cell`
is provided explicitly.

### config_registry.prompt_builder

Recommended fields for reproducible cadence tests:
- `handshake_template_mode` (`default` | `custom`)
- `handshake_template` (rendered handshake template string used for acknowledgements)
- `turn_template_mode` (`default` | `custom`)
- `turn_template` (rendered template string used for turn prompts)

Recommended session-fairness fields for benchmark grids:
- `pairing_policy` (`none` | `paired_side_swap`)
- `first_player_policy` (`random` | `fixed` | `alternating`)
- `fixed_first_player_index` (required when `first_player_policy: fixed`)

Recommended cell/preflight notes:
- keep handshake and turn templates explicit as separate concerns
- document controller asymmetry when the compared players use different controllers
- note any `information_level="partial"` assumptions about public `last_action`

### execution_plan.preflight

Recommended fields:
- `phase_id` (for example, `P0`)
- `cell_ids` (list of benchmark cell IDs to run in reduced scale preflight)
- `matches_per_cell`
- `required_checks` (list of explicit causal / contract checks reviewed before scale-up)

If `cell_ids` is empty, preflight is treated as intentionally skipped.

## results.md (Generated)

`results.md` is the deterministic human-readable report generated from
`results.json` and, for matrix package exports, sibling cell artifacts under
`artifacts/<cell_id>/results.json`.

It SHOULD include:
- source scope and phase/cell membership
- aggregate summary metrics
- player results with confidence intervals when available
- direct head-to-head comparisons
- position/seat splits
- per-cell overview and per-cell seat splits for matrix package exports
- format strictness
- cost summaries
- behavioral profile summaries when present
- artifact validation status
- warnings for heterogeneous package aggregates, high position skew, or
  non-significant direct comparisons

`results.md` is generated factual content. It MUST NOT contain human or LLM
interpretation beyond deterministic warnings derived from exported metrics.

## Authored Analysis (`analysis/`)

`analysis/` is the authored interpretation namespace for humans and AI agents.
Each independent analysis SHOULD live in its own timestamped subdirectory using
the project timestamp core:

```text
analysis/analysis_YYYYMMDD_HHMMSS_<author>_<topic_slug>/
├── analysis.md
├── provenance.yaml
└── support/
```

`analysis/README.md` SHOULD document an agent quickstart, provenance rules,
artifact citation expectations, and the boundary between generated facts and
interpretation. Package root `README.md` SHOULD link to `analysis/README.md`
so a human or AI agent can discover the reporting workflow from the experiment
root. Quantitative claims in authored analyses SHOULD cite generated artifacts.

Legacy packages MAY still use `analysis.md`; validators treat it as an
authored legacy document and validate its `AUTO_FACTS` block only when it
exists or is declared in `manifest.artifacts.analysis_md`.

## Markdown Factual Blocks (README.md / legacy analysis.md)

To keep automation deterministic and interpretation human-owned, templates SHOULD
include a fenced factual block with markers:

- `<!-- AUTO_FACTS:BEGIN -->`
- `<!-- AUTO_FACTS:END -->`

Tooling may rewrite only content between those markers.
Anything outside those markers is considered human-authored narrative.

For completed or archived experiments with `run.matches_completed > 0`:
- `README.md` MUST contain these marker blocks
- legacy `analysis.md` MUST contain these marker blocks when present or declared
  in `manifest.artifacts.analysis_md`
- the factual block contents MUST contain real values, not placeholders like `TBD`
- `agentdeck-research-package` and `agentdeck-research-export --package` are the
  supported ways to refresh those blocks automatically

## results.csv (Generated)

Columns (minimum):
- match_id, winner, turns, outcome, seed, duration, cost,
  player_order_source, first_player, players, player_costs

## INDEX.md (Generated)

`research/INDEX.md` is a registry of all experiments. It should be generated
from manifest.yaml files and updated whenever experiments change.

## Scripts

- The shared export surface (`agentdeck-research-export`, `python -m agentdeck.research.export`, or compatibility `python scripts/research_export.py`) generates results.json/results.csv from recordings.
  - direct mode:
    - `--recordings-dir ... --output-dir ...`
  - shared matrix mode:
    - `--experiment-dir <path> --cell <id>`
    - `--experiment-dir <path> --phase <id>`
    - `--experiment-dir <path> --package`
    - `--experiment-dir <path> --package --phase <id>`
    - `--experiment-dir <path> --package --cell <id>`
- The shared index surface (`agentdeck-research-index`, `python -m agentdeck.research.index`, or compatibility `python scripts/research_index.py`) generates `research/INDEX.md` from manifests.
- `agentdeck-research-package` / `python scripts/research_package.py` creates a research package from one or more session directories.
