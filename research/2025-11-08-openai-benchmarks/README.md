# OpenAI Strategic Benchmarks (2025-11-08)

**Status**: running  
**Research Question**: How do OpenAI model configurations compare in strategic gameplay?

## Summary (Topline)
- Format instruction repetition dominates win rates in FixedDamageGame.
- ReasoningController yields a consistent advantage over ActionOnlyController.
- gpt-4o-mini is a strong cost-performance baseline.

## Design Snapshot
- Game: FixedDamageGame
- Models: gpt-4o-mini, gpt-5-nano, gpt-5-mini, gpt-5
- Controllers: ActionOnlyController, ReasoningController
- Matches Planned: 230
- Matches Completed: 185 (recordings present in repo)
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
  --output-dir research/2025-11-08-openai-benchmarks
```
