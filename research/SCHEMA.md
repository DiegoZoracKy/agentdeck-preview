# Research Experiment Schema

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
├── analysis.md        # Interpretation (optional)
├── artifacts/         # Plots/tables (optional)
├── logs/              # Narrative logs (optional)
├── recordings/        # External pointers only (no raw JSON)
└── scripts/           # Experiment scripts (optional)
```

## Status-Based Completeness Rules

Packages are validated differently depending on `manifest.status`:

- `planned`: placeholders are allowed in `README.md` and `analysis.md`.
- `running`: partial factual updates are allowed; interpretive sections may remain placeholders.
- `complete` with `run.matches_completed > 0`: factual blocks in `README.md` and
  `analysis.md` MUST be populated (no placeholder values).
- `archived`: treated like `complete` for validation purposes.

Interpretive sections (conclusions/limitations/next steps) are always human-owned.
Automation should only write factual content.

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

If an experiment is single-run or smoke-test oriented, `matrix.yaml` may be omitted.
In that case, `run.matrix_source` and `artifacts.matrix_yaml` SHOULD be omitted as well.

### Example
```yaml
schema_version: 1
experiment_id: 2025-11-08-openai-benchmarks
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
notes: ""
```

## results.json (Generated)

### Required Fields
- `schema_version` (int)
- `experiment_id` (string)
- `generated_at` (ISO-8601)
- `source.recordings_dir` (string; canonical source pointer)
- `summary` (object)
- `players` (array of player metadata)
- `matches` (array of match summaries)

Optional source extension:
- `source.recordings_dirs` (array of strings) for multi-session checkpoint aggregation.

For `results.json.schema_version >= 2`, the following are additionally required:
- `statistics` (object; inferential metrics)
- `format_strictness` (object; contract compliance metrics)
- `position_effect` (object; first-player and upset metrics)

### Summary Fields
- `total_matches`
- `decisive_matches`
- `draws`
- `win_rates` (per player)
- `forfeit_rate` (recommended)
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

## matrix.yaml (Optional, Recommended for Benchmark Grids)

Suggested top-level sections:
- `frozen_inputs` (git tag/commit, template version, pricing snapshot)
- `model_registry`
- `config_registry`
- `sampling_policy`
- `execution_plan`
- `cells`

### config_registry.prompt_builder

Recommended fields for reproducible cadence tests:
- `turn_template_mode` (`default` | `custom`)
- `turn_template` (rendered template string used for turn prompts)

### execution_plan.preflight

Recommended fields:
- `cell_ids` (list of benchmark cell IDs to run in reduced scale preflight)
- `matches_per_cell`

If `cell_ids` is empty, preflight is treated as intentionally skipped.

## Markdown Factual Blocks (README.md / analysis.md)

To keep automation deterministic and interpretation human-owned, templates SHOULD
include a fenced factual block with markers:

- `<!-- AUTO_FACTS:BEGIN -->`
- `<!-- AUTO_FACTS:END -->`

Packager tools may rewrite only content between those markers.
Anything outside those markers is considered human-authored narrative.

## results.csv (Generated)

Columns (minimum):
- match_id, winner, turns, outcome, seed, duration, cost,
  player_order_source, first_player, players, player_costs

## INDEX.md (Generated)

`research/INDEX.md` is a registry of all experiments. It should be generated
from manifest.yaml files and updated whenever experiments change.

## Scripts

- `scripts/research_export.py` generates results.json/results.csv from recordings.
- `scripts/research_index.py` generates research/INDEX.md from manifests.
- `scripts/research_package.py` creates a research package from one or more session directories.
