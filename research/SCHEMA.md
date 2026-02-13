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
- `run.matrix_source` (path to matrix definition when present)
- `analysis_plan` (ci_method, alpha, effect_size)
- `artifacts` (paths for results.json/results.csv/plots)
- `storage` (where raw recordings and derived artifacts live)
- `notes`

When `matrix.yaml` is present, it should be the source of truth for:
- benchmark cells/phases
- sampling policy (pilot/expansion)
- expansion rules and overrides

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
- `source.recordings_dir` (string)
- `summary` (object)
- `players` (array of player metadata)
- `matches` (array of match summaries)

### Summary Fields
- `total_matches`
- `decisive_matches`
- `draws`
- `win_rates` (per player)
- `forfeit_rate` (recommended)
- `total_cost`
- `avg_turns`, `avg_duration`, `avg_cost`

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
- `scripts/research_package.py` creates a research package from a session directory.
