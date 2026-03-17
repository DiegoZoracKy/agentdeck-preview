# Experiment Title

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: use folder name (must match `manifest.yaml.experiment_id`)

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 24/24
- Game: FixedDamageGame
- Players: A=anthropic:claude-haiku-4-5-20251001, B=google:gemini-2.5-flash
- Seed Base: 427000
- Topline Winner: gemini-2.5-flash-A (50.0%)
- Avg Turns: 18.666666666666668
- Avg Duration (s): 238.68723268310228
- Total Cost: $0.307087
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
