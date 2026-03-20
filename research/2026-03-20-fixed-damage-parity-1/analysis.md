# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches across 2 cells
- Decisive matches: 48
- Draws: 0
- Win rates: Flash-AO finished `21-3` over FlashLite-AO; Flash-AO finished `14-10` over FlashLite-RC
- Topline winner: Reasoning narrows the Flash-Lite gap sharply, but plain Flash still wins the parity pilot
- First player in first recorded match: FlashLite-AO
- Strict contract rate: `0.9911` overall across both exported cells
- Artifact validation: all exported cells passed
- Average turns: 18.69 overall
- Average duration (s): 15.97 overall
- Total cost: 0.12093
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: `ReasoningController` substantially improves Flash-Lite and closes most of the plain-model gap, but it does not achieve parity with plain Flash in FixedDamage at `N=24`.
- Secondary finding: the remaining gap is not mostly about crude aggression anymore; it is about a position-sensitive defensive threshold that flips the wrong way in the second-player seat, healing while healthy and attacking while critical.
- Practical recommendation: reasoning is a real equalizer strategy, but not yet a full substitute for plain Flash on this task. The next intervention should target the remaining position-conditioned failure mode.

## Cross-Model Parity Pilot
- `p1_c01_flash_lite_ao_vs_flash_ao`:
  - baseline parity question answered decisively: `Flash-AO` beat `FlashLite-AO` `21-3` (`p=0.00028`, large effect).
  - Flash-Lite's plain policy was weak in exactly the way the prior studies predicted:
    - all-attack rate `45.8%`
    - first-potion median `20 HP`
    - unused-potions-on-loss `1.0`
    - critical-potion response `0.144`
    - recovery `0.200`
- `p1_c02_flash_lite_rc_vs_flash_ao`:
  - equalizer question answered partially: `FlashLite-RC` narrowed the gap to `10-14`, but the cell stayed pilot-null (`p=0.541`, negligible effect).
  - reasoning changed the mechanism materially:
    - all-attack rate `45.8% -> 12.5%`
    - first-potion median `20 HP -> 60 HP`
    - unused-potions-on-loss `1.0 -> 0.286`
    - critical-potion response `0.144 -> 0.491`
    - recovery `0.200 -> 0.478`
  - the cost tradeoff remained favorable relative to plain Flash:
    - `FlashLite-RC` about `$0.00138` per player-match
    - `Flash-AO` about `$0.00193` per player-match

## Behavioral Endpoints
- `all_attack_match_rate`:
  - FlashLite-AO: `0.458`
  - FlashLite-RC: `0.125`
  - Flash-AO baseline cell: `0.125`
  - Flash-AO parity cell: `0.042`
- `first_potion_profile`:
  - FlashLite-AO median first potion: `20 HP`
  - FlashLite-RC median first potion: `60 HP`
  - Flash-AO median first potion: `40 HP` in both cells
- `unused_potions_on_loss_rate`:
  - FlashLite-AO: `1.000`
  - FlashLite-RC: `0.286`
  - Flash-AO baseline cell: `0.667`
  - Flash-AO parity cell: `0.200`
- `state_action_consistency`:
  - FlashLite-AO: `0.905`
  - FlashLite-RC: `0.898`
  - Flash-AO baseline cell: `0.856`
  - Flash-AO parity cell: `0.862`
- `position_policy_delta`:
  - FlashLite-AO: `0.093`
  - FlashLite-RC: `0.321`
  - Flash-AO baseline cell: `0.281`
  - Flash-AO parity cell: `0.218`
- `error_recovery_rate`:
  - FlashLite-AO: `0.200`
  - FlashLite-RC: `0.478`
  - Flash-AO baseline cell: `0.536`
  - Flash-AO parity cell: `0.481`

## Outcome, Cost, and Reliability
- Win rates:
  - baseline: `Flash-AO` `21-3` over `FlashLite-AO`
  - parity: `Flash-AO` `14-10` over `FlashLite-RC`
- Position-controlled results:
  - baseline cell first-player wins: `13/24`, so the model gap dominates seat in the plain-vs-plain comparison
  - parity cell first-player wins: `20/24`, so seat dominates much more strongly once `FlashLite-RC` becomes competitive
  - `FlashLite-RC` won `9/12` as first player and `1/12` as second
  - `Flash-AO` won `11/12` as first player and `3/12` as second in the parity cell
- Cost per match:
  - baseline cell: `0.00173`
  - parity cell: `0.00331`
  - per player-match:
    - FlashLite-AO `$0.00040`
    - FlashLite-RC `$0.00138`
    - Flash-AO baseline `$0.00132`
    - Flash-AO parity `$0.00193`
- Parse / strictness notes:
  - `0` parse failures in both cells
  - parity cell strictness: `100%`
  - baseline cell strictness: `97.9%` with `8` recoverable non-strict turns
- Latency notes:
  - baseline cell average duration: `12.37s` per match
  - parity cell average duration: `19.57s` per match
  - longer reasoning traces clearly increased wall-clock time

## Interpretation Notes
- Cross-model win rates must be paired with position-controlled summaries because position can bias raw named-player splits.
- Cell artifacts are the primary inferential unit in this package. Top-level pooled player win rates mix heterogeneous cells and should not be read as a single matchup.
- `Flash-AO`'s own behavioral profile shifts somewhat across packages and opponent contexts, so repeated values like all-attack rate or unused-potion losses should be read as context-dependent measurements rather than model invariants.
- The strategic claim is broader than FixedDamage, but the evidence here is specific to constrained sequential decision-making under partial information.

## Evidence Highlights
- `FlashLite-RC` develops an inverted defensive threshold in the second-player seat.
  - at shared `80 HP / 3 potions`, `FlashLite-RC` attacked `16/17` as first player but used `POTION` `8/12` as second player, so the second-player policy heals while still healthy
  - at shared `20 HP / 1 potion`, `FlashLite-RC` used `POTION` `3/3` as first player but `ATTACK` `2/2` as second player, so the second-player policy then attacks when healing is critical
- That reversal explains the `1/12` second-player win rate more precisely than generic “seat-conditioned instability”: reasoning improved the policy, but under second-player pressure it moved the defensive threshold in the wrong direction at both ends of the health range.

## Limitations
- FixedDamage remains a local-decision game.
- This package tests a cross-model parity question, not broad reasoning or business-logic claims.
- Any parity result here is evidence for strategy effects in this task class, not proof that the same intervention works universally.

## Next Steps
- Do not expand this parity package immediately. The answer is already clear at pilot scale:
  - reasoning is a strong equalizer
  - but it did not close the full gap here
- The next research move should target the remaining failure mode, for example:
  - a cheaper or tighter reasoning contract for Flash-Lite
  - a prompt-reinforced parity cell to test whether reinforcement reduces the inverted second-player defensive threshold
  - a second task class to test whether equalizer behavior transfers beyond FixedDamage
