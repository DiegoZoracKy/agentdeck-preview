# FixedDamage AO: gpt-4o-mini vs Claude Haiku 4.5

**Status**: complete  
**Research Question**: In FixedDamage (AO, side-swapped), does gpt-4o-mini outperform claude-haiku-4.5?  
**Experiment ID**: `fixed-damage-mini-vs-haiku-ao__20260225_233925_d4fc1e`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 24/24
- Game: FixedDamageGame
- Players: A=openai:gpt-4o-mini, B=anthropic:claude-haiku-4-5-20251001
- Seed Base: 426000
- Topline Winner: claude-haiku-4-5-20251001-B (58.3%)
- Avg Turns: 18.416666666666668
- Avg Duration (s): 16.850005567073822
- Total Cost: $0.259715
<!-- AUTO_FACTS:END -->

## Why This Exists
- Establish a clean weak-model baseline in FixedDamage using AO only.
- Compare OpenAI mini vs Anthropic Haiku under paired side-swap before testing richer strategies.

## Design Snapshot
- Game + information level: `FixedDamageGame` (`partial`)
- Models / providers: `openai:gpt-4o-mini` vs `anthropic:claude-haiku-4-5-20251001`
- Configs: `AO` vs `AO` (`ActionOnlyController`)
- Matches Planned: `24` (paired side-swap)
- Seed Base: `426000`

## Execution Plan
- Single-cell pilot run (`24` matches) with side-swap enabled.
- Two 12-match batches (AB + BA) executed in one session.
- Next expansion gate: increase to `N=100` only if we keep this game setup.

## Results
- Winner by win-rate: `claude-haiku-4-5-20251001-B` (`58.3%`, 14/24).
- First-player wins: `22/24` (`91.7%`) indicating strong structural first-move advantage.
- Full data: `results.json` and `results.csv`.

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
