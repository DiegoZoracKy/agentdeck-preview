# Experiment Title

> **Historical template:** retained to explain `0.2` Study packages. Do not copy
> this template for new work on current `main`; the redesigned Study Package
> contract is not yet approved or implemented.

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: use folder name (must match `manifest.yaml.experiment_id`; process-created folders use `research_...`)

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: planned
- Matches: 0/0
- Game: FixedDamageGame
- Players: TBD
- Seed Base: TBD
- Topline Winner: TBD
- Avg Turns: TBD
- Avg Duration (s): TBD
- Total Cost: TBD
<!-- AUTO_FACTS:END -->

## Why This Exists
- One-paragraph motivation and intended audience.

## Design Snapshot
- Game + information level:
- Models / providers:
- Configs (AO / CoT-H / CoT-T or equivalent):
- Matches Planned:
- Seed Base:

## Execution Plan
- Preflight gate:
- Phase A:
- Phase B:
- Expansion rule:

## Results
- See `results.md`, `results.json`, and `results.csv`.

## Authored Analysis
`results.md` is the generated factual report. Independent human or AI-authored
interpretation belongs under `analysis/`.

To analyze this experiment, read `analysis/README.md` and create a new
timestamped `analysis_...` subdirectory under `analysis/`.

## Artifacts
- `matrix.yaml` (optional; benchmark grid definition)
- `manifest.yaml` (repro metadata)
- `results.json` / `results.csv` / `results.md` (generated outputs)
- `analysis/` (authored interpretation workspace)
- `artifacts/` (derived tables/plots/highlights)
- `notes/` (human run notes)
- `recordings/` (external pointers only)
- `scripts/` (execution scripts)
  - `scripts/behavioral_scorer.py` (optional package-local scorer for a formal
    `behavioral_profile`)

## Storage
- Raw recordings: external store (HF/S3/R2) + pointer docs in `recordings/`
- Repo keeps summaries and lightweight derived artifacts only

## Repro (if recordings are available)
```bash
python scripts/run_experiment.py --list-cells
python scripts/run_experiment.py --phase P1

agentdeck-research-export \
  --experiment-dir . \
  --phase P1 \
  --no-generated-at

agentdeck-research-export \
  --experiment-dir . \
  --package \
  --no-generated-at

# Optional: only when this package defines scripts/behavioral_scorer.py
# This template is matrix-based, so score one cell artifact at a time.
agentdeck-research-score \
  --experiment-dir . \
  --cell p1_c01_example
```

For matrix packages, rescoring writes the behavioral profile to:

```text
artifacts/<cell>/results.json
```

It does not update the top-level package `results.json`.
