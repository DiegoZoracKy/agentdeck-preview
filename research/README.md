# Research Directory

This directory hosts standardized, objective experiment results for AgentDeck.
Each experiment follows the Experiment Package layout defined in `SCHEMA.md`.

Core framework documentation remains in the repository root (`README.md`,
`CONTRIBUTING.md`, and `specs/`). This `research/` area is intentionally
experiment-specific.

The baseline branch intentionally ships the **research contract and templates**
without committed benchmark packages. Use `_templates/` or
`scripts/research_package.py` to start new experiments.

## Start Here
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

3) Run experiments (recordings should be stored externally).

4) Export results:
```
python scripts/research_export.py \
  --recordings-dir recordings \
  --output-dir research/YYYY-MM-DD-your-experiment
```

Repeat `--recordings-dir` to aggregate multiple checkpoint/session directories
into one export. Add `--no-generated-at` when you need deterministic diffs.

5) Update the index:
```
python scripts/research_index.py
```

## Create Package From Session

If you already have a completed session under `agentdeck_runs/`, promote it to a
research package in one step:
```
python scripts/research_package.py \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here"
```

For checkpoint aggregation across multiple compatible sessions:
```
python scripts/research_package.py \
  --session-ids session_A session_B \
  --question "Your research question here"
```

For benchmark grids, opt in to matrix scaffold generation:
```
python scripts/research_package.py \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here" \
  --include-matrix
```

## Validation

Validate manifests and the index before committing research changes:
```
python scripts/research_validate.py --research-dir research
```

To regenerate the index if out of date:
```
python scripts/research_validate.py --research-dir research --write-index
```

## Recordings Policy

Raw match recordings should not be committed to this repo. Store them in
external storage (S3, Hugging Face, etc.) and link them from
`research/<experiment-id>/recordings/README.md`.
