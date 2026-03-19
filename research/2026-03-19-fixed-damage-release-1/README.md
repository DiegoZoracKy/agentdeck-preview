# FixedDamage Release 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-19-fixed-damage-release-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 144/144
- Game: FixedDamageGame
- Players: local:AttackBot, local:PotionAt80Bot, openai:gpt-4o-mini, anthropic:claude-haiku-4-5-20251001, google:gemini-2.5-flash-lite, google:gemini-2.5-flash
- Seed Base: 4242
- Topline Winner: none; no cadence comparison was significant at `N=24`
- Avg Turns: 18.47
- Avg Duration (s): 16.96
- Total Cost: 0.66768
<!-- AUTO_FACTS:END -->

## Why This Exists
- This is the first release-facing research package meant to demonstrate AgentDeck's product value through a small, validated, replayable behavioral study.
- The goal is not to rank providers. The goal is to show that AgentDeck can make a subtle behavioral question visible through fairness controls, structured artifacts, and replay evidence.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Calibration bots: `AttackBot`, `PotionAt80Bot`
- Provider models: `gpt-4o-mini`, `claude-haiku-4-5-20251001`, `gemini-2.5-flash-lite`, `gemini-2.5-flash`
- Controller: `ActionOnlyController`
- Google runtime setting: `thinking_budget=0` for the Gemini 2.5 Flash-family cells, using Vertex AI's documented control for lower-latency runs on Gemini 2.5 models
- Prompt cadence conditions:
  - `handshake_only`: handshake uses the game default template, turns show `{game_view}`
  - `turn_reinforced`: same handshake, turns show `{game_view}\n\n{controller_format}`
- Matches planned:
  - Phase 0 calibration: 48
  - Phase 1 cadence pilot: 96

## Execution Plan
- `P0` calibration:
  - `AttackBot` vs `AttackBot`
  - `AttackBot` vs `PotionAt80Bot`
- `P1` cadence pilot:
  - `gpt-4o-mini` handshake-only vs turn-reinforced
  - `claude-haiku-4-5-20251001` handshake-only vs turn-reinforced
  - `gemini-2.5-flash-lite` handshake-only vs turn-reinforced
  - `gemini-2.5-flash` handshake-only vs turn-reinforced
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Conclusion phase: disabled
- Runtime artifacts:
  - local sessions live under `agentdeck_runs/` inside this experiment folder
  - raw recordings remain uncommitted and are referenced later from `recordings/`

## Results
- Phase 0 calibration exports are committed under `artifacts/`.
- Across all four provider cadence cells, no within-model handshake-only vs turn-reinforced comparison was significant at `N=24`. Mini and Haiku both split `12-12`; Flash-Lite landed `13-11`; Flash landed `10-14`.
- Turn reinforcement increased spend in every provider cell without producing a decisive win-rate shift:
  - `Mini-TR` `0.03274` vs `Mini-HO` `0.02754`
  - `Haiku-TR` `0.25034` vs `Haiku-HO` `0.21101`
  - `Gemini-TR` `0.01362` vs `Gemini-HO` `0.01196`
  - `GeminiFlash-TR` `0.06471` vs `GeminiFlash-HO` `0.05575`
- The headline finding is positional and behavioral, not cadence-based:
  - calibration and Mini stayed fully first-player dominated (`24/24` first-player wins)
  - Haiku inverted the game completely (`24/24` second-player wins)
  - Flash-Lite was near-balanced with a slight second-player lean (`13/24` second-player wins)
  - Flash returned to strong first-player dominance (`22/24` first-player wins)
- The second headline finding is contract quality, not parse failure. Every provider finished with `0` parse failures, but strict ActionOnly compliance ranged from `18.2%` for Flash-Lite to `90.2%` for Flash and `100%` for Mini/Haiku.
- Mini and Haiku stayed fully deterministic in trajectory length, while both Gemini cells showed wider turn-count spread. That makes the package useful both for representative replays and for showing how AgentDeck captures policy variance.
- Top-level `results.json` and `results.csv` are present for package validation and bookkeeping, but the analytic units for this study remain the per-cell exports under `artifacts/`.

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
