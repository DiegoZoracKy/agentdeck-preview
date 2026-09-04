# FixedDamage RC Replication — Flash-Lite RC vs GPT-4o-mini RC

> **Historical Study package:** results and commands below document the `0.2`
> Research workflow. Historical `agentdeck-research-*` commands are available
> only from the `agentic-edge-research` tag, not current `main`.

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: 2026-04-08-fixed-damage-rc-replication-1

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 20/20
- Game: FixedDamageGame (information_level=full)
- Players: gemini-2.5-flash-lite (RC) vs gpt-4o-mini (RC)
- Seed Base: 42
- Topline Winner: TBD
- Avg Turns: TBD
- Avg Duration (s): TBD
- Total Cost: TBD
<!-- AUTO_FACTS:END -->

## Why This Exists
Gemini's Round 6 QA experiment (round-06-20260407-171442) used ReasoningController
for both players and produced 11-9 in favor of Gemini (p=0.82) — the opposite
directional signal from the 20-0 ActionOnlyController result. This package is an
independent replication with the identical config to determine whether that result
is reproducible.

## Design Snapshot
- Game + information level: FixedDamageGame, information_level=full
- Models / providers: gemini-2.5-flash-lite (Google), gpt-4o-mini (OpenAI)
- Configs: ReasoningController for both players
- Matches Planned: 20
- Seed Base: 42

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
```
