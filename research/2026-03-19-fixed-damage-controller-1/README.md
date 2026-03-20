# FixedDamage Controller 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-19-fixed-damage-controller-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: FixedDamageGame
- Players: google:gemini-2.5-flash-lite, google:gemini-2.5-flash
- Seed Base: 5242
- Topline Winner: ReasoningController led both Gemini cells; FlashLite-RC finished `16-8`, Flash-RC finished `13-11`
- Avg Turns: 18.56
- Avg Duration (s): 16.04
- Total Cost: 0.23293
<!-- AUTO_FACTS:END -->

## Why This Exists
- FixedDamage Release 1 showed that prompt cadence was mostly outcome-null but that decision-level behavior varied sharply by model family.
- This follow-up asks a narrower intervention question: can requiring explicit reasoning improve the weak Gemini policies that still showed late healing, policy lock, and brittle recovery?

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Controller conditions:
  - `ActionOnlyController`
  - `ReasoningController`
- Turn cadence:
  - `handshake_only` for both cells; turns show `{game_view}` only
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini 2.5 models
- Matches planned:
  - `24` per cell, `48` total

## Primary Endpoints
- `all_attack_match_rate`
- `first_potion_profile`
- `unused_potions_on_loss_rate`
- `state_action_consistency`
- `position_policy_delta`
- `error_recovery_rate`

## Secondary Endpoints
- win rate
- cost
- latency
- strict contract rate

## Execution Plan
- `P1` controller pilot:
  - `gemini-2.5-flash-lite`: `ActionOnlyController` vs `ReasoningController`
  - `gemini-2.5-flash`: `ActionOnlyController` vs `ReasoningController`
- No calibration rerun in this package:
  - the audited FixedDamage substrate already exists in `fixed-damage-release-1`
  - this package changes only controller contract

## Results
- `gemini-2.5-flash-lite`: `FlashLite-RC` finished `16-8` over `FlashLite-AO`.
- `gemini-2.5-flash`: `Flash-RC` finished `13-11` over `Flash-AO`.

### Confirmed Behavioral Findings
- `ReasoningController` improved Flash-Lite much more than Flash.
  - Flash-Lite all-attack rate dropped from `50.0%` to `16.7%`.
  - Flash-Lite unused-potions-on-loss rate dropped from `93.8%` to `37.5%`.
  - Flash-Lite critical-potion response rose from `19.1%` to `53.8%`.
  - Flash-Lite recovery after missed critical defense rose from `0.259` to `0.529`.
- Flash improved more modestly under reasoning.
  - all-attack rate fell from `20.8%` to `12.5%`
  - unused-potions-on-loss rate fell from `61.5%` to `54.5%`
  - recovery rose from `0.372` to `0.410`
- Position dependence remained important in both cells.
  - Flash-Lite stayed strongly first-player leaning (`18/24` first-player wins)
  - Flash stayed first-player leaning (`17/24` first-player wins)
- Minimal contract adherence stayed reliable overall.
  - `0` parse failures in both cells
  - Flash-Lite stayed `100%` strict for both controllers
  - Flash-RC stayed `100%` strict, while Flash-AO drifted to `95.1%` strict with `12` recoverable non-strict turns

### Directional Signals
- Flash-Lite showed the clearest outcome movement, but the `16-8` split remained underpowered at `N=24` (`p=0.152`, small effect).
- Flash stayed near outcome-null at `13-11` (`p=0.839`, negligible effect), so its controller delta is currently behavioral rather than competitive.
- Reasoning was expensive:
  - Flash-Lite cost `0.02819` for RC vs `0.01054` for AO (`2.67x`)
  - Flash cost `0.15008` for RC vs `0.04411` for AO (`3.40x`)

### What AgentDeck Made Visible
- The controller question would look weak on win rate alone, especially for Flash. The behavioral layer shows where reasoning actually moved policy quality and where it mostly added spend.
- Flash-Lite is the clearest example of outcome-mechanism separation in this package:
  - RC improved healing behavior and recovery sharply
  - but RC also raised seat-conditioned policy divergence (`position_policy_delta` `0.247` vs AO `0.117`)
- The evidence layer makes the mechanism inspectable directly. In Flash-Lite RC, the same `70 HP / 2 potions` state split by seat:
  - as first player: `ATTACK` `3/3`
  - as second player: `POTION` `2/2`
- Flash showed a different story: smaller behavioral gains, better strictness under RC, and a much steeper cost multiplier.

## Artifacts
- `matrix.yaml` defines the controller-intervention cells
- `manifest.yaml` tracks package status and reproducibility metadata
- `results.json` / `results.csv` carry the objective and behavioral outputs
- `analysis.md` is the human interpretation layer
- `notes/` tracks human run notes
- `recordings/` stores recording pointers only
- `scripts/` contains the package-local runner plus export helpers

## Repro
Run the pilot:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/run_experiment.py --phase P1
```

Export per-cell and package results:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/export_cell_results.py --phase P1
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/export_package_results.py
```
