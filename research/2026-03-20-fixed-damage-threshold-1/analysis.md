# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches across 2 cells
- Decisive matches: 48
- Draws: 0
- Win rates: `Flash-AO` finished `15-9` over `FlashLite-RC-TR`; `FlashLite-RC-TR-HP` finished `13-11` over `Flash-AO`
- Topline winner: HP-threshold grounding sharply improved Flash-Lite's behavioral coherence and narrowed the parity gap, but the competitive claim stayed null at `N=24` per cell
- First player in first recorded match: Flash-AO
- Strict contract rate: `0.9990` overall across both exported cells
- Artifact validation: all exported cells passed
- Average turns: 20.38 overall
- Average duration (s): 17.37 overall
- Total cost: 0.17316
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: HP-threshold grounding fixed the residual second-player threshold bug much more cleanly than reinforced reasoning alone.
- Secondary finding: the outcome gap narrowed from `15-9` against Flash to `13-11` in Flash-Lite's favor, but the cell remained statistically null.
- Practical recommendation: treat `RC + TR + HP-grounding` as the correct full-stack Flash-Lite condition for any future parity expansion. This package answered the mechanism question more clearly than the competitive one.

## Threshold Mechanism Pilot
- `p1_c01_flash_lite_rc_tr_vs_flash_ao`:
  - the reinforced baseline on a fresh seed family again fell short of parity: `Flash-AO` beat `FlashLite-RC-TR` `15-9` (`p=0.307`, small effect)
  - the mechanism still looked like the Parity 2 failure mode:
    - first-potion median `50 HP`
    - `position_policy_delta = 0.231`
    - critical-potion response `0.412`
    - unused-potions-on-loss `0.400`
    - first player won `21/24`
- `p1_c02_flash_lite_rc_tr_hp_vs_flash_ao`:
  - the HP-grounded cell narrowed the gap to a near draw: `FlashLite-RC-TR-HP` beat `Flash-AO` `13-11`
  - the cell is still pilot-null (`p=0.839`, negligible effect), so this is not a parity proof
  - the behavioral mechanism moved sharply in the expected direction:
    - all-attack rate `0.167 -> 0.042`
    - first-potion median `50 HP -> 20 HP`
    - unused-potions-on-loss `0.400 -> 0.182`
    - state-action consistency `0.868 -> 0.984`
    - `position_policy_delta 0.231 -> 0.023`
    - critical-potion response `0.412 -> 0.421`
    - recovery `0.516 -> 0.568`

## Behavioral Endpoints
- `all_attack_match_rate`:
  - FlashLite-RC-TR baseline: `0.167`
  - FlashLite-RC-TR-HP: `0.042`
  - Flash-AO baseline cell: `0.250`
  - Flash-AO HP-grounded cell: `0.208`
- `first_potion_profile`:
  - FlashLite-RC-TR baseline median first potion: `50 HP`
  - FlashLite-RC-TR-HP median first potion: `20 HP`
  - Flash-AO baseline median: `40 HP`
  - Flash-AO HP-grounded-cell median: `40 HP`
- `unused_potions_on_loss_rate`:
  - FlashLite-RC-TR baseline: `0.400`
  - FlashLite-RC-TR-HP: `0.182`
  - Flash-AO baseline cell: `0.333`
  - Flash-AO HP-grounded cell: `0.538`
- `state_action_consistency`:
  - FlashLite-RC-TR baseline: `0.868`
  - FlashLite-RC-TR-HP: `0.984`
  - Flash-AO baseline cell: `0.878`
  - Flash-AO HP-grounded cell: `0.905`
- `position_policy_delta`:
  - FlashLite-RC-TR baseline: `0.231`
  - FlashLite-RC-TR-HP: `0.023`
  - Flash-AO baseline cell: `0.197`
  - Flash-AO HP-grounded cell: `0.174`
- `error_recovery_rate`:
  - FlashLite-RC-TR baseline: `0.516`
  - FlashLite-RC-TR-HP: `0.568`
  - Flash-AO baseline cell: `0.483`
  - Flash-AO HP-grounded cell: `0.333`

## Threshold-State Evidence
- The strongest baseline failure state remained `80 HP / 3 potions`.
  - `FlashLite-RC-TR` as first player attacked `13/13`
  - `FlashLite-RC-TR` as second player attacked only `5/12` and used `POTION` `7/12`
  - that is the same healthy-state defensive error Parity 2 was built around
- HP-threshold grounding removed that exact error.
  - `FlashLite-RC-TR-HP` as first player attacked `13/13`
  - `FlashLite-RC-TR-HP` as second player attacked `12/12`
  - so the intervention fully restored healthy-state seat symmetry in the most important bucket
- Critical-state behavior also improved sharply.
  - at shared `20 HP / 3 potions`, baseline `FlashLite-RC-TR`:
    - first player `POTION` `6/9`
    - second player split `2` attacks / `2` potions
  - at shared `20 HP / 3 potions`, HP-grounded `FlashLite-RC-TR-HP`:
    - first player `POTION` `11/12`
    - second player `POTION` `12/13`
  - that is the clearest mechanism win in the package
- The low-resource critical state improved too.
  - at shared `20 HP / 1 potion`, baseline `FlashLite-RC-TR` split `2` attacks / `2` potions in both seats
  - under HP-grounding, second-player `FlashLite-RC-TR-HP` used `POTION` `12/12`
  - first-player `FlashLite-RC-TR-HP` still showed some residual risk-taking (`2` attacks / `5` potions), but the old second-player hesitation was essentially gone
- Intermediate states became more coherent as well.
  - at shared `30 HP / 2 potions`, baseline `FlashLite-RC-TR` still split by seat (`0.5/0.5` first, `0.8/0.2` second attack/potion)
  - under HP-grounding, `FlashLite-RC-TR-HP` attacked `13/13` as first player and `22/22` as second

## Outcome, Cost, and Reliability
- Win rates:
  - baseline cell: `Flash-AO` `15-9` over `FlashLite-RC-TR`
  - HP-grounded cell: `FlashLite-RC-TR-HP` `13-11` over `Flash-AO`
- Position-controlled results:
  - baseline cell first-player wins: `21/24`
  - HP-grounded cell first-player wins: `19/24`
  - `FlashLite-RC-TR` won `9/12` as first player and `0/12` as second
  - `FlashLite-RC-TR-HP` won `10/12` as first player and `3/12` as second
  - `Flash-AO` went from `12/12` first-player wins and `3/12` second-player wins in the baseline cell to `9/12` first-player wins and `2/12` second-player wins in the HP-grounded cell
- Cost per match:
  - baseline cell: `0.00320`
  - HP-grounded cell: `0.00401`
  - HP-grounding raised total cell cost by about `25%`
  - even so, Flash-Lite stayed slightly cheaper than Flash on a per-player basis inside the HP-grounded cell
- Parse / strictness notes:
  - `0` parse failures in both cells
  - HP-grounded cell: both players `100%` strict
  - baseline cell: only one recoverable non-strict turn overall, from `Flash-AO`
  - unlike Parity 2, there is no meaningful strictness confound here
- Latency notes:
  - baseline cell average duration: `16.32s` per match
  - HP-grounded cell average duration: `18.41s` per match
  - the mechanism fix cost some latency, but not a full model-tier jump

## Interpretation Notes
- Cell artifacts are the primary inferential unit in this package. Top-level pooled player win rates mix two different prompt strategies and should not be read as a single matchup.
- This is a mechanism package, not a final parity package.
- The right reading is not “Flash-Lite now beats Flash.” It is “the HP-grounded overlay fixed the residual threshold pathology and made the outcome gap much smaller.”

## Evidence Highlights
- The healthy-state seat bug was fully removed.
  - baseline `FlashLite-RC-TR` at shared `80 HP / 3 potions`: first `ATTACK` `13/13`, second `POTION` `7/12`
  - HP-grounded `FlashLite-RC-TR-HP` in the same state: first `ATTACK` `13/13`, second `ATTACK` `12/12`
- The critical-state seat bug was almost fully removed.
  - baseline `FlashLite-RC-TR` at shared `20 HP / 3 potions`: second split `2` `ATTACK` / `2` `POTION`
  - HP-grounded `FlashLite-RC-TR-HP`: second `POTION` `12/13`
- The aggregate metric confirms the same story.
  - `position_policy_delta` collapsed from `0.231` to `0.023`
  - that is a much stronger signal than the small change in raw win count

## Limitations
- FixedDamage remains a local-decision game.
- Both cells stop at `N=24`, so this package is still a pilot on the competitive question.
- The HP-grounded cell won `13-11`, but the effect is negligible and statistically null.
- The first-player advantage remained strong even after the mechanism fix, so a clean parity claim still needs a larger run.

## Next Steps
- If the next question is competitive parity, run a full-stack parity package with `FlashLite-RC-TR-HP` vs `Flash-AO` at `N=48`.
- If the next question is transferability, carry the same HP-threshold overlay into another sequential decision task class and see whether the mechanism generalizes.
- Do not frame the current package as “Lite beats Flash.” The honest conclusion is narrower and stronger: an explicit survival calculation fixed the residual threshold bug and made the cheaper model substantially more coherent.
