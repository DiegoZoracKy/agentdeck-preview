# FixedDamage Threshold 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-threshold-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: FixedDamageGame
- Players: google:gemini-2.5-flash-lite, google:gemini-2.5-flash
- Seed Base: 8242
- Topline Winner: reinforced baseline cell `Flash-AO` finished `15-9` over `FlashLite-RC-TR`; HP-grounded cell `FlashLite-RC-TR-HP` finished `13-11` over `Flash-AO`
- Avg Turns: 20.38
- Avg Duration (s): 17.37
- Total Cost: 0.17316
<!-- AUTO_FACTS:END -->

## Why This Exists
- FixedDamage Parity 2 showed that turn-reinforced reasoning made Flash-Lite much more competitive with plain Flash, but left a residual second-player threshold bug.
- That remaining error was narrow and concrete:
  - as second player, Flash-Lite still sometimes healed while healthy
  - and still hesitated to heal in some critical low-HP states
- This package tests whether a pure prompt-surface intervention can fix that mechanism without changing the engine or the game.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC-TR` vs `Flash-AO`
  - `FlashLite-RC-TR-HP` vs `Flash-AO`
- Turn cadence:
  - both Flash-Lite cells repeat `{controller_format}` on every turn
  - the new HP-grounded cell adds:
    - `Before acting, calculate: does your current HP minus one ATTACK (20 damage) leave you alive? Let that determine your choice.`
  - `Flash-AO` remains handshake only
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini 2.5 models
- Matches planned:
  - `24` per cell, `48` total
- Seed base:
  - `8242` to keep this package on a fresh schedule family
- Intervention surface:
  - config only, via `prompt_builder.turn_template`
  - no engine changes, no game changes, no controller code changes

## Primary Endpoints
- `position_policy_delta`
- state-level evidence at `80 HP / 3 potions`, `20 HP / 3 potions`, and `20 HP / 1 potion`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`

## Secondary Endpoints
- win rate
- cost
- latency
- strict contract rate
- position-controlled win splits

## Hypothesis
- Turn-reinforced reasoning already removed most of Flash-Lite's broad policy weakness.
- The remaining failure mode is a threshold-calculation problem, not a generic need for more healing.
- If an explicit one-more-hit survival check fixes that threshold, Flash-Lite should become more coherent by seat and more competitive with plain Flash while staying slightly cheaper.

## Results
- `FlashLite-RC-TR` vs `Flash-AO`: `Flash-AO` finished `15-9` over `FlashLite-RC-TR`.
- `FlashLite-RC-TR-HP` vs `Flash-AO`: `FlashLite-RC-TR-HP` finished `13-11` over `Flash-AO`.

### Confirmed Behavioral Findings
- The within-package reinforced baseline reproduced the same broad parity picture as Parity 2.
  - `Flash-AO` finished `15-9` over `FlashLite-RC-TR`
  - the baseline cell stayed outcome-null at pilot scale (`p=0.307`, small effect)
  - first player won `21/24`
  - `FlashLite-RC-TR` still went `9/12` as first player and `0/12` as second
- HP-threshold grounding materially improved Flash-Lite's behavioral profile.
  - all-attack rate fell `16.7% -> 4.2%`
  - median first potion shifted `50 HP -> 20 HP`
  - unused-potions-on-loss fell `40.0% -> 18.2%`
  - state-action consistency rose `0.868 -> 0.984`
  - `position_policy_delta` fell `0.231 -> 0.023`
  - critical-potion response rose slightly `41.2% -> 42.1%`
  - recovery after missed critical defense rose `0.516 -> 0.568`
- HP-threshold grounding completely removed the healthy-state second-player misfire.
  - at shared `80 HP / 3 potions`, baseline second-player `FlashLite-RC-TR` attacked only `5/12` and used `POTION` `7/12`
  - under HP-grounding, second-player `FlashLite-RC-TR-HP` attacked `12/12`
- HP-threshold grounding also fixed the critical-state seat asymmetry much more cleanly than reinforcement alone.
  - at shared `20 HP / 3 potions`, baseline second-player `FlashLite-RC-TR` split `2` attacks / `2` potions
  - under HP-grounding, second-player `FlashLite-RC-TR-HP` used `POTION` `12/13`
  - at shared `20 HP / 1 potion`, baseline second-player `FlashLite-RC-TR` split `2` attacks / `2` potions
  - under HP-grounding, second-player `FlashLite-RC-TR-HP` used `POTION` `12/12`
- Position stayed load-bearing, but the cell became less position-dominated.
  - baseline cell: first player won `21/24`
  - HP-grounded cell: first player won `19/24`
  - `FlashLite-RC-TR-HP` improved from `0/12` second-player wins in the baseline cell to `3/12`
- The outcome gap narrowed, but the package still does not establish parity.
  - baseline cell: `Flash-AO` `15-9` over `FlashLite-RC-TR` (`p=0.307`, small effect)
  - HP-grounded cell: `FlashLite-RC-TR-HP` `13-11` over `Flash-AO` (`p=0.839`, negligible effect)
  - this is a mechanism success and a competitive near-null, not a final “Lite beats Flash” result
- HP-threshold grounding raised Flash-Lite cost modestly while preserving a slight per-player cost advantage over plain Flash.
  - baseline `FlashLite-RC-TR`: about `$0.00143` per player-match
  - HP-grounded `FlashLite-RC-TR-HP`: about `$0.00194` per player-match
  - HP-grounded `Flash-AO`: about `$0.00207` per player-match
- The strictness confound from Parity 2 disappeared in the HP-grounded cell.
  - both players stayed `100%` strict
  - both players had `0` parse failures

### Directional Signals
- The remaining gap between `FlashLite-RC-TR-HP` and `Flash-AO` now looks much smaller and much less mechanism-driven than the baseline gap.
- If a future parity package wants to test the full stack competitively, `RC + TR + HP-grounding` is the right Flash-Lite condition to expand.
- The strongest open question is no longer “does Flash-Lite understand when to heal?” but “does the cleaner threshold policy hold at larger `N` and across more schedule families?”

### What AgentDeck Made Visible
- This mechanism hypothesis was tested entirely through the public prompt surface.
  - a new `turn_template` in `matrix.yaml`
  - same game
  - same controllers
  - same engine
- Without the behavioral layer, this package would read as “a 15-9 loss became a 13-11 win, still null.”
- The state buckets show the more useful story:
  - the old `80 HP` second-player panic-heal disappeared
  - the old `20 HP` second-player hesitation mostly disappeared
  - seat-conditioned policy divergence collapsed from `0.231` to `0.023`
- That is exactly the kind of mechanism result AgentDeck is supposed to produce:
  - not only whether a strategy changed outcomes
  - but how it changed decisions
