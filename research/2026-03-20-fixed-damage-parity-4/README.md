# FixedDamage Parity 4

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-parity-4`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: completed
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `google:gemini-2.5-flash`
- Seed Base: `11242`
- Topline Winner: `FlashLite-RC-TR-HP` by `28-20`
- Statistical Read: `p=0.312`, negligible effect, not significant at `alpha=0.05`
- Position Read: first player won `42/48`; `FlashLite-RC-TR-HP` went `23/24` as first player and `5/24` as second
- Avg Turns: `22.54`
- Avg Duration (s): `19.30`
- Total Cost: `0.21126`
<!-- AUTO_FACTS:END -->

## Why This Exists
- Parity 3 showed that the full Flash-Lite strategy stack could beat plain Flash `31-17`, but still stopped just short of formal significance.
- The mechanism question is already answered well enough to keep this package single-cell.
- This package asks only the replication question:
  - does the same full Flash-Lite stack reproduce that near-parity result on a fresh seed family?
- The key diagnostic is not only total wins, but whether Flash-Lite can sustain its improved **second-player** win rate.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC-TR-HP` vs `Flash-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini 2.5 models
- Matches planned:
  - `48`
- Seed base:
  - `11242` to keep this package on a fresh schedule family

## Primary Endpoints
- second-player win split
- `position_policy_delta`
- state-level evidence at `80 HP / 3 potions`, `20 HP / 3 potions`, and `20 HP / 1 potion`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`

## Secondary Endpoints
- total win rate
- cost
- latency
- strict contract rate

## Hypothesis
- If the Parity 3 result was real rather than schedule-specific, the full Flash-Lite stack should stay competitive here too.
- The main diagnostic is whether second-player wins remain high enough to support a stronger competitive claim.

## Results
- `FlashLite-RC-TR-HP` beat `Flash-AO` `28-20` at `N=48`.
- The direction matched Parity 3, but the replication was weaker:
  - exact binomial `p=0.312`
  - effect size `0.167` (`negligible`)
- The key diagnostic improved in the right direction but not enough for a formal competitive claim:
  - `FlashLite-RC-TR-HP` won `5/24` as second player
  - `Flash-AO` won only `1/24` as second player
- Position was even more dominant here than in Parity 3:
  - first player won `42/48`
  - upset rate: `6/48`

### Confirmed Findings
- The full Flash-Lite stack remained behaviorally stronger than plain Flash on the fresh seed family:
  - `state_action_consistency`: `0.962` vs `0.897`
  - `position_policy_delta`: `0.032` vs `0.160`
  - `all_attack_match_rate`: `4.2%` vs `14.6%`
  - `unused_potions_on_loss_rate`: `15.0%` vs `42.9%`
  - `error_recovery_rate`: `0.569` vs `0.368`
- The healthy-state second-player bug stayed fixed:
  - at shared `80 HP / 3 potions`, `FlashLite-RC-TR-HP` attacked `24/24` as second player and `29/29` as first
- The critical-state second-player hesitation stayed much smaller than before, but it did not disappear:
  - at shared `20 HP / 3 potions`, second-player `FlashLite-RC-TR-HP` healed `20/24` and attacked `4/24`
  - at shared `20 HP / 1 potion`, second-player `FlashLite-RC-TR-HP` healed `19/21` and attacked `2/21`
- `Flash-AO` showed the sharper seat instability in this package:
  - at shared `20 HP / 3 potions`, first-player `Flash-AO` attacked `15/17` while second-player `Flash-AO` healed `8/10`
  - at shared `20 HP / 1 potion`, first-player `Flash-AO` healed `10/10` while second-player `Flash-AO` attacked `17/27`

### Cost and Reliability
- Cost was effectively equal:
  - `FlashLite-RC-TR-HP`: `$0.10577` total, `$0.002204` per player-match
  - `Flash-AO`: `$0.10548` total, `$0.002198` per player-match
- Reliability stayed cleaner on the Flash-Lite stack:
  - `FlashLite-RC-TR-HP`: `100%` strict, `0` parse failures
  - `Flash-AO`: `97.59%` strict, `13` recoverable non-strict turns, `0` parse failures

### What AgentDeck Made Visible
- The headline `28-20` result alone would read like a soft replication and little else.
- The behavioral layer shows something more specific:
  - the full Flash-Lite stack stayed clearly more coherent by seat and by state
  - the old healthy-state panic-heal bug did not return
  - the remaining barrier to a stronger competitive claim is still position, not the original threshold pathology
