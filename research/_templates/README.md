# Experiment Title

**Status**: planned  
**Research Question**:  
**Experiment ID**: YYYY-MM-DD-slug

## Summary
- Objective statement of findings (or "Pending")

## Design Snapshot
- Game:
- Players / Models:
- Controllers:
- Matches Planned:
- Seed Base:

## Results
- See `results.json` and `results.csv`

## Artifacts
- `manifest.yaml` (repro metadata)
- `results.json` / `results.csv` (objective outputs)
- `analysis.md` (interpretation)
- `logs/` (narrative logs)
- `recordings/` (external pointers only)
- `scripts/` (execution scripts)

## Repro (if recordings available)
```bash
python scripts/research_export.py \
  --recordings-dir recordings \
  --output-dir .
```
