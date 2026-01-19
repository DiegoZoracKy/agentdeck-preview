# Multi-Provider Benchmarks (2025-11-19)

**Status**: running  
**Research Question**: How do Gemini variants compare to GPT-4o-mini in strategic gameplay?

## Summary (Topline)
- Gemini-2.5-Flash underperforms GPT-4o-mini while costing more per match.
- Gemini-2.5-Pro is statistically tied to GPT-4o-mini with higher cost.

## Design Snapshot
- Game: FixedDamageGame
- Models: gpt-4o-mini, gemini-2.5-flash, gemini-2.5-pro
- Controller: ReasoningController
- Matches Planned: 100
- Matches Completed: 93 (recordings present in repo)
- Seed Base: 42

## Results
- `results.json` and `results.csv` contain objective outputs generated from recordings.
- `analysis.md` contains interpretation and narrative conclusions.

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
  --output-dir research/2025-11-19-multi-provider-benchmarks
```
