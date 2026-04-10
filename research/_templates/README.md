# Experiment Title

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: use folder name (must match `manifest.yaml.experiment_id`)

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
- See `results.json` and `results.csv`

## Artifacts
- `matrix.yaml` (optional; benchmark grid definition)
- `manifest.yaml` (repro metadata)
- `results.json` / `results.csv` (objective outputs)
- `analysis.md` (interpretation)
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
agentdeck-research-score \
  --experiment-dir .
```
