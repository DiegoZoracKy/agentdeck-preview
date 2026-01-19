# Research Directory

This directory hosts standardized, objective experiment results for AgentDeck.
Each experiment follows the Experiment Package layout defined in `SCHEMA.md`.

## Start Here
- `SCHEMA.md` - manifest/results schema and required fields
- `INDEX.md` - registry of experiments with status and topline results
- `_templates/` - boilerplate files for new experiments

## Experiment Package (Required)

```
research/<experiment-id>/
├── README.md          # Experiment card (short summary)
├── manifest.yaml      # Repro metadata (required)
├── results.json       # Objective results (generated)
├── results.csv        # Match-level results (generated)
├── analysis.md        # Interpretation (optional)
├── artifacts/         # Plots/tables (optional)
├── logs/              # Narrative logs (optional)
├── recordings/        # External pointers only (no raw JSON)
└── scripts/           # Experiment scripts (optional)
```

## Creating a New Experiment

1) Copy templates:
```
cp -R research/_templates research/YYYY-MM-DD-your-experiment
```

2) Fill out `manifest.yaml` and `README.md`.

3) Run experiments (recordings should be stored externally).

4) Export results:
```
python scripts/research_export.py \
  --recordings-dir recordings \
  --output-dir research/YYYY-MM-DD-your-experiment
```

5) Update the index:
```
python scripts/research_index.py
```

## Recordings Policy

Raw match recordings should not be committed to this repo. Store them in
external storage (S3, Hugging Face, etc.) and link them from
`research/<experiment-id>/recordings/README.md`.
