# FixedDamage Parity 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-parity-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: FixedDamageGame
- Players: google:gemini-2.5-flash-lite, google:gemini-2.5-flash
- Seed Base: 6242
- Topline Winner: Flash-AO dominated FlashLite-AO `21-3`; FlashLite-RC narrowed the gap to `10-14` but did not reach parity
- Avg Turns: 18.69
- Avg Duration (s): 15.97
- Total Cost: 0.12093
<!-- AUTO_FACTS:END -->

## Why This Exists
- FixedDamage Controller 1 showed that `ReasoningController` materially improved Flash-Lite's behavior and outcomes against its own ActionOnly baseline.
- This follow-up asks the broader strategy question: can a weaker, cheaper model with a stronger reasoning strategy match or beat a stronger plain model?

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-AO` vs `Flash-AO`
  - `FlashLite-RC` vs `Flash-AO`
- Turn cadence:
  - `handshake_only` for both cells; turns show `{game_view}` only
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini 2.5 models
- Matches planned:
  - `24` per cell, `48` total
- Seed base:
  - `6242` to keep this package on a fresh schedule family

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
- position-controlled win splits

## Execution Plan
- `P1` cross-model parity pilot:
  - `FlashLite-AO` vs `Flash-AO`
  - `FlashLite-RC` vs `Flash-AO`
- Expansion rule:
  - expand only if the parity gap is directionally interesting and the behavioral story is legible

## Results
- `gemini-2.5-flash-lite` vs `gemini-2.5-flash` under `ActionOnlyController`: `Flash-AO` finished `21-3` over `FlashLite-AO`.
- `gemini-2.5-flash-lite` with `ReasoningController` vs plain `Flash-AO`: `Flash-AO` finished `14-10` over `FlashLite-RC`.

### Confirmed Behavioral Findings
- Plain Flash is decisively stronger than plain Flash-Lite in this game.
  - `FlashLite-AO` locked into all-attack matches `45.8%` of the time.
  - `FlashLite-AO` first healed very late, median `20 HP`, and died with unused potions in `100%` of its losses.
  - the baseline cell was decisive: `21-3`, `p=0.00028`, large effect
- `ReasoningController` substantially improved Flash-Lite's policy quality.
  - all-attack rate fell from `45.8%` to `12.5%`
  - first-potion median shifted from `20 HP` to `60 HP`
  - unused-potions-on-loss rate fell from `100.0%` to `28.6%`
  - critical-potion response rose from `14.4%` to `49.1%`
  - recovery after missed critical defense rose from `0.200` to `0.478`
- The equalizer effect was real but incomplete.
  - `FlashLite-RC` closed the raw gap from `3-21` to `10-14`
  - `FlashLite-RC` stayed cheaper than `Flash-AO` at about `$0.00138` vs `$0.00193` per player-match
  - but the parity cell stayed outcome-null at pilot scale (`p=0.541`, negligible effect)
- Position remained load-bearing in the equalizer cell.
  - first player won `20/24` matches in `FlashLite-RC` vs `Flash-AO`
  - `FlashLite-RC` won `9/12` as first player but only `1/12` as second
  - `Flash-AO` won `11/12` as first player and `3/12` as second
- Contract adherence stayed reliable.
  - `0` parse failures in both cells
  - the parity cell stayed `100%` strict
  - the plain baseline cell ended at `97.9%` strict because `FlashLite-AO` produced `8` recoverable non-strict turns

### Directional Signals
- `ReasoningController` does not yet make Flash-Lite fully competitive with plain Flash in FixedDamage.
- The remaining gap is no longer primarily “dumb all-attack policy”; it is now a seat-conditioned defensive threshold that flips the wrong way under pressure.
- A broader parity claim needs either:
  - a second task class, or
  - a cheaper/tighter reasoning contract that preserves the behavioral gains without increasing position sensitivity

### What AgentDeck Made Visible
- The parity question would look binary on win rate alone. The behavioral layer shows the real story:
  - plain Flash-Lite is clearly too weak
  - reasoning materially improves Flash-Lite
  - but the improved policy is still brittle by seat, specifically because its defensive threshold inverts between healthy and critical states
- The evidence layer makes that mechanism explicit. In `FlashLite-RC`:
  - at shared `80 HP / 3 potions`, first player attacked `16/17` while second player used `POTION` `8/12`, so the second-player policy heals while still healthy
  - at shared `20 HP / 1 potion`, first player used `POTION` `3/3` while second player always `ATTACK`ed `2/2`, so the second-player policy then refuses to heal when survival depends on it
- Plain Flash is not perfectly invariant across studies either.
  - in this fresh seed family and against a different opponent, `Flash-AO` stayed clearly stronger than Flash-Lite but shifted slightly on metrics like all-attack rate and unused-potion losses, so behavioral profiles should be read in context rather than as fixed universal traits
- So the package does answer the product question:
  - strategic reasoning can move a weaker model much closer to a stronger one
  - but in this game it did not fully erase the performance gap

## Artifacts
- `matrix.yaml` defines the cross-model cells
- `manifest.yaml` tracks package status and reproducibility metadata
- `results.json` / `results.csv` carry the objective and behavioral outputs
- `analysis.md` is the human interpretation layer
- `notes/` tracks human run notes
- `recordings/` stores recording pointers only
- `scripts/` contains the package-local runner plus export helpers

## Repro
Run the pilot:

```bash
.venv/bin/python research/2026-03-20-fixed-damage-parity-1/scripts/run_experiment.py --phase P1
```

Export per-cell and package results:

```bash
.venv/bin/python research/2026-03-20-fixed-damage-parity-1/scripts/export_cell_results.py --phase P1
.venv/bin/python research/2026-03-20-fixed-damage-parity-1/scripts/export_package_results.py
```
