# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches across 2 cells
- Decisive matches: 48
- Draws: 0
- Win rates: `Flash-AO` finished `14-10` over `FlashLite-RC-HO`; `FlashLite-RC-TR` finished `15-9` over `Flash-AO`
- Topline winner: turn reinforcement improves Flash-Lite behavior substantially and flips the parity pilot outcome direction, but the reinforced cell stays underpowered
- First player in first recorded match: FlashLite-RC-HO
- Strict contract rate: `0.9733` overall across both exported cells
- Artifact validation: all exported cells passed
- Average turns: 20.27 overall
- Average duration (s): 18.66 overall
- Total cost: 0.16166
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: turn reinforcement improved `FlashLite-RC`'s behavioral profile enough to flip the parity pilot from `10-14` loss direction under handshake-only to `15-9` win direction against plain Flash on the same package design.
- Secondary finding: the healthy-state second-player misfire shrank dramatically under reinforcement, but the second-player policy still hesitates too often at critical HP.
- Practical recommendation: reinforcement is now a credible equalizer candidate for Flash-Lite, but the competitive claim is still underpowered at `N=24` per cell.

## Reinforced Parity Pilot
- `p1_c01_flash_lite_rc_ho_vs_flash_ao`:
  - the handshake-only control on a fresh seed family remained close but did not achieve parity: `Flash-AO` beat `FlashLite-RC-HO` `14-10` (`p=0.541`, negligible effect)
  - the mechanism still looked like the Parity 1 failure mode:
    - first-potion median `60 HP`
    - `position_policy_delta = 0.246`
    - critical-potion response `0.353`
    - unused-potions-on-loss `0.429`
- `p1_c02_flash_lite_rc_tr_vs_flash_ao`:
  - the reinforced cell flipped the raw outcome: `FlashLite-RC-TR` beat `Flash-AO` `15-9`
  - the cell is still pilot-null (`p=0.307`, small effect), so this is not yet a competitive proof
  - the behavioral mechanism moved in the expected direction:
    - all-attack rate `0.083 -> 0.042`
    - first-potion median `60 HP -> 20 HP`
    - unused-potions-on-loss `0.429 -> 0.222`
    - state-action consistency `0.896 -> 0.926`
    - `position_policy_delta 0.246 -> 0.206`
    - critical-potion response `0.353 -> 0.437`
    - recovery `0.486 -> 0.580`

## Behavioral Endpoints
- `all_attack_match_rate`:
  - FlashLite-RC-HO: `0.083`
  - FlashLite-RC-TR: `0.042`
  - Flash-AO control cell: `0.125`
  - Flash-AO reinforced cell: `0.167`
- `first_potion_profile`:
  - FlashLite-RC-HO median first potion: `60 HP`
  - FlashLite-RC-TR median first potion: `20 HP`
  - Flash-AO control median: `40 HP`
  - Flash-AO reinforced-cell median: `50 HP`
- `unused_potions_on_loss_rate`:
  - FlashLite-RC-HO: `0.429`
  - FlashLite-RC-TR: `0.222`
  - Flash-AO control cell: `0.400`
  - Flash-AO reinforced cell: `0.533`
- `state_action_consistency`:
  - FlashLite-RC-HO: `0.896`
  - FlashLite-RC-TR: `0.926`
  - Flash-AO control cell: `0.868`
  - Flash-AO reinforced cell: `0.851`
- `position_policy_delta`:
  - FlashLite-RC-HO: `0.246`
  - FlashLite-RC-TR: `0.206`
  - Flash-AO control cell: `0.158`
  - Flash-AO reinforced cell: `0.088`
- `error_recovery_rate`:
  - FlashLite-RC-HO: `0.486`
  - FlashLite-RC-TR: `0.580`
  - Flash-AO control cell: `0.536`
  - Flash-AO reinforced cell: `0.229`

## Threshold-State Evidence
- The strongest handshake-only failure state remained `80 HP / 3 potions`.
  - `FlashLite-RC-HO` as first player attacked `14/15`
  - `FlashLite-RC-HO` as second player used `POTION` `9/12`
  - that is the same healthy-state defensive inversion seen in Parity 1
- Reinforcement narrowed that exact error.
  - `FlashLite-RC-TR` as first player attacked `15/15`
  - `FlashLite-RC-TR` as second player attacked `9/12` and used `POTION` `3/12`
  - so reinforcement substantially reduced healthy-state over-healing in the second-player seat
- Critical-state behavior improved, but not all the way.
  - at shared `20 HP / 3 potions`, `FlashLite-RC-TR` as first player used `POTION` `9/9`
  - in the same state as second player it split `4` attacks / `4` potions
  - that remaining split is exactly why the package still cannot claim the threshold inversion is solved
- The residual second-player hesitation also shows up at intermediate states.
  - at shared `50 HP / 2 potions`, first-player `FlashLite-RC-TR` attacked `3/3`
  - second-player `FlashLite-RC-TR` split `2` attacks / `2` potions
  - reinforcement reduced the pathological healthy-state potion burn, but it did not make second-player policy fully coherent

## Outcome, Cost, and Reliability
- Win rates:
  - control cell: `Flash-AO` `14-10` over `FlashLite-RC-HO`
  - reinforced cell: `FlashLite-RC-TR` `15-9` over `Flash-AO`
- Position-controlled results:
  - control cell first-player wins: `18/24`
  - reinforced cell first-player wins: `21/24`
  - `FlashLite-RC-TR` won `12/12` as first player and `3/12` as second
  - `Flash-AO` won `9/12` as first player and `0/12` as second in the reinforced cell
  - so the reinforced `15-9` result reflects both Flash-Lite improvement and a much more position-dominated cell; position advantage explains a substantial share of the win split independent of model or strategy
- Cost per match:
  - control cell: `0.00319`
  - reinforced cell: `0.00355`
  - reinforcement raised the parity cell cost modestly while keeping Flash-Lite still cheaper than plain Flash on a per-player basis
- Parse / strictness notes:
  - `0` parse failures in both cells
  - `FlashLite-RC-HO` and `FlashLite-RC-TR` stayed `100%` strict
  - `Flash-AO` drifted to `89.5%` strict in the reinforced cell with `26` recoverable non-strict turns
  - that is a mild candidate confound in the reinforced cell, not just a formatting footnote, and future follow-ups should check whether the regression correlates with turn count or specific HP / potion states
- Latency notes:
  - control cell average duration: `18.14s` per match
  - reinforced cell average duration: `19.18s` per match
  - reinforcement added cost modestly and latency only slightly relative to the parity baseline

## Interpretation Notes
- Cell artifacts are the primary inferential unit in this package. Top-level pooled player win rates mix two different strategy conditions and should not be read as a single matchup.
- The reinforced pilot is meaningful because it pairs a fresh within-package control (`RC-HO`) with the reinforced condition against the same opponent family.
- The parity story is therefore not “reinforcement proved Flash-Lite is better than Flash.” It is “reinforcement made Flash-Lite look more competitive and more behaviorally coherent, but the sample is still too small for a strong outcome claim.”

## Evidence Highlights
- Reinforcement clearly fixed the worst healthy-state seat error.
  - `FlashLite-RC-HO` at shared `80 HP / 3 potions`: first `ATTACK` `14/15`, second `POTION` `9/12`
  - `FlashLite-RC-TR` in the same state: first `ATTACK` `15/15`, second `ATTACK` `9/12`
- Reinforcement did not fully fix critical-state seat symmetry.
  - `FlashLite-RC-TR` at shared `20 HP / 3 potions`: first `POTION` `9/9`, second split `4` `ATTACK` / `4` `POTION`
- That combination explains the package outcome:
  - reinforcement removes much of the waste at healthy HP
  - but residual second-player indecision keeps the parity result from becoming a clean competitive claim

## Limitations
- FixedDamage remains a local-decision game.
- The control cell and reinforced cell both stop at `N=24`, so this package is still a pilot on the competitive question.
- Reinforcement changed the cell direction, but because both cells remain underpowered it does not yet justify a final parity claim.

## Next Steps
- If the next question is competitive parity, expand both `RC-HO` and `RC-TR` to `N=48` so the reinforcement effect stays interpretable against an equally sized control.
- If the next question is mechanism, keep the current result and design a tighter reinforcement or reasoning contract aimed specifically at second-player critical-state hesitation.
- That follow-up should anchor to HP-survival thresholds, not to `POTION` directly, so it targets the inverted threshold instead of simply nudging the model toward more healing.
- Do not frame the current package as “Lite beats Flash with reinforcement.” The honest conclusion is narrower: reinforcement is a promising equalizer that materially improves behavior and may be moving outcomes in the right direction.
