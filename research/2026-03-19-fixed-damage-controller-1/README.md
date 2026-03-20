# FixedDamage Controller 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-19-fixed-damage-controller-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 72/72
- Game: FixedDamageGame
- Players: google:gemini-2.5-flash-lite, google:gemini-2.5-flash
- Seed Base: 5242
- Topline Winner: FlashLite-RC is now significant at `37-11`; Flash-RC remains pilot-null at `13-11`
- Avg Turns: 17.97
- Avg Duration (s): 15.99
- Total Cost: 0.27348
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
  - Flash-Lite expanded from `24` to `48`
  - Flash stayed at `24`
  - `72` total

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
- `gemini-2.5-flash-lite`: `FlashLite-RC` finished `37-11` over `FlashLite-AO` after expansion to `N=48`.
- `gemini-2.5-flash`: `Flash-RC` finished `13-11` over `Flash-AO` at pilot scale.

### Confirmed Behavioral Findings
- `ReasoningController` clearly helped Flash-Lite and that claim now survives expansion.
  - Flash-Lite all-attack rate dropped from `45.8%` to `18.8%`.
  - Flash-Lite unused-potions-on-loss rate dropped from `94.6%` to `36.4%`.
  - Flash-Lite critical-potion response rose from `18.3%` to `50.8%`.
  - Flash-Lite recovery after missed critical defense rose from `0.259` to `0.596`.
  - the expanded named-player split is now significant: `37-11`, `p=0.00022`, medium effect
- Flash improved more modestly under reasoning.
  - all-attack rate fell from `20.8%` to `12.5%`
  - unused-potions-on-loss rate fell from `61.5%` to `54.5%`
  - recovery rose from `0.372` to `0.410`
- Position dependence remained important in both cells.
  - Flash-Lite stayed strongly first-player leaning (`33/48` first-player wins)
  - Flash stayed first-player leaning (`17/24` first-player wins)
- Minimal contract adherence stayed reliable overall.
  - `0` parse failures in both cells
  - Flash-Lite stayed `100%` strict for both controllers
  - Flash-RC stayed `100%` strict, while Flash-AO drifted to `95.1%` strict with `12` recoverable non-strict turns

### Directional Signals
- Flash-Lite no longer belongs in the purely directional bucket; the expanded cell is now statistically meaningful on outcomes as well as behavior.
- Flash stayed near outcome-null at `13-11` (`p=0.839`, negligible effect), so its controller delta is currently behavioral rather than competitive.
- Reasoning was expensive:
  - Flash-Lite cost `0.05828` for RC vs `0.02100` for AO (`2.78x`)
  - Flash cost `0.15008` for RC vs `0.04411` for AO (`3.40x`)

### What AgentDeck Made Visible
- The controller question would look weak on win rate alone, especially for Flash. The behavioral layer shows where reasoning actually moved policy quality and where it mostly added spend.
- Flash-Lite is the clearest example of outcome-mechanism separation in this package:
  - the pilot first surfaced the mechanism
  - the expansion then confirmed it with a significant `37-11` outcome split
  - RC still raised seat-conditioned policy divergence (`position_policy_delta` `0.204` vs AO `0.092`)
- The evidence layer makes the mechanism inspectable directly. In Flash-Lite RC, the same `70 HP / 2 potions` state split by seat:
  - as first player: `ATTACK` `3/3`
  - as second player: `ATTACK` `3/6`, `POTION` `3/6`
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
