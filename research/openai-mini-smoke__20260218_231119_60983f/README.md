# Experiment Title

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: use folder name (must match `manifest.yaml.experiment_id`)

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 1/1
- Game: FixedDamageGame
- Players: A=openai:gpt-4o-mini, B=openai:gpt-4o-mini
- Seed Base: 420000
- Topline Winner: gpt-4o-mini-B (100.0%)
- Avg Turns: 19.0
- Avg Duration (s): 65.42419028282166
- Total Cost: $0.006163
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
- `logs/` (narrative logs)
- `recordings/` (external pointers only)
- `scripts/` (execution scripts)

## Storage
- Raw recordings: external store (HF/S3/R2) + pointer docs in `recordings/`
- Repo keeps summaries and lightweight derived artifacts only

## Repro (if recordings are available)
```bash
python scripts/research_export.py \
  --recordings-dir recordings \
  --output-dir .
```
