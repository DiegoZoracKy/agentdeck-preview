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
- Avg Turns: 17.64
- Avg Duration (s): 13.46
- Total Cost: 0.63699
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

### Confirmed Behavioral Findings
- Turn reinforcement increased spend in every provider cell without producing a decisive win-rate shift:
  - `Mini-TR` `0.03274` vs `Mini-HO` `0.02754`
  - `Haiku-TR` `0.25034` vs `Haiku-HO` `0.21101`
  - `Gemini-TR` `0.00981` vs `Gemini-HO` `0.00849`
  - `GeminiFlash-TR` `0.05276` vs `GeminiFlash-HO` `0.04430`
- Policy stability differed sharply by model family:
  - Mini and Haiku were fully deterministic in turn count (`23` and `24` turns in every match)
  - Flash-Lite ranged from `9` to `22` turns
  - Flash ranged from `14` to `25` turns
- Minimal contract adherence was clean on the final audited codebase:
  - every provider cell finished with `0` parse failures
  - every provider cell finished with `100%` strict ActionOnly compliance
- Position dependence varied strongly by model:
  - calibration and Mini stayed fully first-player dominated (`24/24` first-player wins)
  - Haiku inverted the game completely (`24/24` second-player wins)
  - Flash-Lite kept a strong first-player lean (`20/24` first-player wins)
  - Flash kept a moderate first-player lean (`16/24` first-player wins)

### Directional Signals
- No cadence comparison was significant at `N=24`. Mini, Haiku, and Flash-Lite all split `12-12`; Flash landed `10-14`. This is a strong baseline against large effects, but not enough to rule out moderate ones.
- Flash still showed the largest cadence lean: `GeminiFlash-TR` finished `14-10` over `GeminiFlash-HO`, but the intervals overlap and the effect size remains negligible at pilot scale.

### What AgentDeck Made Visible
- Side-swap fairness metadata separated position effects from model identity, which is why the Haiku inversion and the weaker Gemini first-player leans are visible instead of being flattened into named-player splits.
- The same experiment could be rerun on a corrected Gemini integration path without changing the matrix design, which let the package replace an adapter-confounded result set with final audited artifacts.
- Replay and trajectory artifacts made policy mechanisms inspectable:
  - `AttackBot` vs `PotionAt80Bot` shows suboptimal healing as a longer match shape, not just as a loss
  - the Mini/Haiku/Gemini cells make deterministic vs variable policy regimes visible through turn-count distributions and representative recordings
- Cost, latency, fairness, and behavior live in the same validated package, so the tradeoff between contract reinforcement and spend is measurable rather than anecdotal.
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
