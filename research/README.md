# Research Directory

This directory hosts standardized, objective experiment results for AgentDeck.
Each experiment follows the Experiment Package layout defined in `SCHEMA.md`.

Core framework documentation remains in the repository root (`README.md`,
`CONTRIBUTING.md`, and `specs/`). This `research/` area is intentionally
experiment-specific.

This preview repo now ships both the **research contract/tooling** and a
committed set of release-facing benchmark packages, including arc summaries and
cross-game synthesis.

Preferred commands use the installed `agentdeck-research-*` entry points. If
those are not yet available in your shell, use the equivalent `python scripts/...`
wrapper from the repo root.

For matrix packages, the shared template and runner use `player_registry` and
per-cell `player_ref` keys. Older drafts that still say `model_registry` /
`model_ref` should be updated.

## Start Here
- `../docs/how-to-run-a-study.md` - supported end-to-end study workflow
- `2026-03-23-fixed-damage-arc-1/README.md` - FixedDamage arc summary
- `2026-03-26-variable-damage-arc-1/README.md` - VariableDamage arc summary
- `2026-03-26-cross-game-comparison-1/README.md` - cross-game findings
- `SCHEMA.md` - manifest/results schema and required fields
- `INDEX.md` - registry of experiments with status and topline results
- `_templates/` - boilerplate files for new experiments

## Experiment Package (Required)

```
research/<experiment-id>/
├── README.md          # Experiment card (short summary)
├── manifest.yaml      # Repro metadata (required)
├── matrix.yaml        # Benchmark grid definition (optional)
├── results.json       # Objective results (generated)
├── results.csv        # Match-level results (generated)
├── analysis.md        # Interpretation (optional)
├── artifacts/         # Plots/tables (optional)
├── notes/             # Human run notes (optional)
├── recordings/        # External pointers only (no raw JSON)
└── scripts/           # Experiment scripts (optional)
```

## Creating a New Experiment

1) Copy templates:
```
cp -R research/_templates research/YYYY-MM-DD-your-experiment
```

2) Fill out `manifest.yaml` and `README.md`.
   - If applicable, define benchmark cells/phases in `matrix.yaml`.
   - If `matrix.yaml` exists, use it as source of truth for sampling + cells.
   - For matrix packages, use `player_registry` plus per-cell `player_ref`.
   - Keep the `AUTO_FACTS` marker blocks in `README.md` and `analysis.md`.

3) Run experiments (recordings should be stored externally).

4) Export results:
```
agentdeck-research-export \
  --recordings-dir recordings \
  --output-dir research/YYYY-MM-DD-your-experiment
```

Repeat `--recordings-dir` to aggregate multiple checkpoint/session directories
into one export. Add `--no-generated-at` when you need deterministic diffs.

For matrix-based benchmark packages, use the shared matrix workflow:

```
agentdeck-research-export \
  --experiment-dir research/YYYY-MM-DD-your-experiment \
  --phase P1 \
  --no-generated-at

agentdeck-research-export \
  --experiment-dir research/YYYY-MM-DD-your-experiment \
  --package \
  --no-generated-at
```

Top-level package export refreshes `results.json` / `results.csv` and also
hydrates the `AUTO_FACTS` blocks in `README.md` and `analysis.md`.

5) Update the index:
```
agentdeck-research-index
```

## Create Package From Session

If you already have a completed session under `agentdeck_runs/`, promote it to a
research package in one step:
```
agentdeck-research-package \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here"
```

For checkpoint aggregation across multiple compatible sessions:
```
agentdeck-research-package \
  --session-ids session_A session_B \
  --question "Your research question here"
```

For benchmark grids, opt in to matrix scaffold generation:
```
agentdeck-research-package \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here" \
  --include-matrix
```

## Validation

Validate manifests and the index before committing research changes:
```
agentdeck-research-validate --research-dir research
```

Completed packages with recorded matches must have real values inside the
`AUTO_FACTS` blocks. Placeholder `TBD` values will cause validation to fail.

To regenerate the index if out of date:
```
agentdeck-research-validate --research-dir research --write-index
```

## Recordings Policy

Raw match recordings should not be committed to this repo. Store them in
external storage (S3, Hugging Face, etc.) and link them from
`research/<experiment-id>/recordings/README.md`.
