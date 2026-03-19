# FixedDamage Release 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-19-fixed-damage-release-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: running
- Matches: 72/96
- Game: FixedDamageGame
- Players: local:AttackBot, local:PotionAt80Bot, openai:gpt-4o-mini, anthropic:claude-haiku-4-5-20251001
- Seed Base: 4242
- Topline Winner: TBD
- Avg Turns: TBD
- Avg Duration (s): TBD
- Total Cost: TBD
<!-- AUTO_FACTS:END -->

## Why This Exists
- This is the first release-facing research package meant to demonstrate AgentDeck's product value through a small, validated, replayable behavioral study.
- The goal is not to rank providers. The goal is to show that AgentDeck can make a subtle behavioral question visible through fairness controls, structured artifacts, and replay evidence.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Calibration bots: `AttackBot`, `PotionAt80Bot`
- Provider models: `gpt-4o-mini`, `claude-haiku-4-5-20251001`
- Controller: `ActionOnlyController`
- Prompt cadence conditions:
  - `handshake_only`: handshake uses the game default template, turns show `{game_view}`
  - `turn_reinforced`: same handshake, turns show `{game_view}\n\n{controller_format}`
- Matches planned:
  - Phase 0 calibration: 48
  - Phase 1 cadence pilot: 48

## Execution Plan
- `P0` calibration:
  - `AttackBot` vs `AttackBot`
  - `AttackBot` vs `PotionAt80Bot`
- `P1` cadence pilot:
  - `gpt-4o-mini` handshake-only vs turn-reinforced
  - `claude-haiku-4-5-20251001` handshake-only vs turn-reinforced
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Conclusion phase: disabled
- Runtime artifacts:
  - local sessions live under `agentdeck_runs/` inside this experiment folder
  - raw recordings remain uncommitted and are referenced later from `recordings/`

## Results
- Cell-level exports live under `artifacts/<cell-id>/results.json` and `results.csv` while the study is still in progress.
- A top-level `results.json` should only be generated once the package has a meaningful study-level synthesis rather than a misleading mixed-cell aggregate.

## Artifacts
- `matrix.yaml` defines cells, phases, and cadence conditions
- `manifest.yaml` tracks package status and reproducibility metadata
- `analysis.md` is the human-owned interpretation layer
- `notes/` tracks phase-by-phase execution notes
- `recordings/` stores external pointers and retention notes
- `scripts/` contains the package-local runner

## Repro
Run one phase:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/run_experiment.py --phase P0
```

Run one cell:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/run_experiment.py --cell p1_c01_mini_ho_vs_tr
```

Export package results once sessions exist:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/export_cell_results.py --phase P0
```
