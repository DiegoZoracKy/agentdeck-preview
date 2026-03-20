# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches across 2 cells
- Decisive matches: 48
- Draws: 0
- Win rates: FlashLite-RC finished `16-8` over FlashLite-AO; Flash-RC finished `13-11` over Flash-AO
- Topline winner: ReasoningController led both Gemini cells, but only Flash-Lite showed a large behavioral shift
- First player in first recorded match: FlashLite-AO
- Strict contract rate: `0.9865` overall across both exported cells
- Artifact validation: all exported cells passed
- Average turns: 18.56 overall
- Average duration (s): 16.04 overall
- Total cost: 0.23293
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the
actor who actually took the first turn.

## Executive Summary
- Primary finding: `ReasoningController` materially improved Flash-Lite's decision quality, but the improvement was more behavioral than inferential at `N=24`.
- Secondary finding: Flash already behaved closer to a reasonable state-grounded policy, so reasoning mostly added cost and a small amount of extra polish.
- Practical recommendation: use `ReasoningController` selectively for weak unstable policies like Flash-Lite; do not treat it as a default upgrade for every weak model.

## Controller Pilot
- `gemini-2.5-flash-lite`:
  - `FlashLite-RC` finished `16-8` over `FlashLite-AO`, a directional but underpowered uplift (`p=0.152`, small effect).
  - The meaningful change was behavioral:
    - all-attack rate fell from `50.0%` to `16.7%`
    - never-used-potion rate fell from `50.0%` to `16.7%`
    - first-potion median moved earlier/safelier from `40 HP` to `60 HP`
    - unused-potions-on-loss rate fell from `93.8%` to `37.5%`
    - critical-potion response rose from `19.1%` to `53.8%`
    - recovery after missed critical defense rose from `0.259` to `0.529`
  - The tradeoff is not free. `FlashLite-RC` was less state-consistent than `FlashLite-AO` (`0.818` vs `0.891`) and more seat-conditioned (`position_policy_delta` `0.247` vs `0.117`).
  - Concrete evidence from the exported artifact:
    - at shared `70 HP / 2 potions`, `FlashLite-RC` attacked `3/3` as first player and healed `2/2` as second player
    - at decision key `position=second|hp=80|potions=3|self=NONE|opp=ATTACK`, `FlashLite-RC` split `50/50` between `ATTACK` and `POTION`
- `gemini-2.5-flash`:
  - `Flash-RC` finished `13-11` over `Flash-AO`, essentially outcome-null (`p=0.839`, negligible effect).
  - Behavioral movement existed, but it was smaller:
    - all-attack rate fell from `20.8%` to `12.5%`
    - never-used-potion rate fell from `20.8%` to `12.5%`
    - unused-potions-on-loss rate fell from `61.5%` to `54.5%`
    - critical-potion response rose from `44.3%` to `46.2%`
    - recovery rose from `0.372` to `0.410`
    - state-action consistency rose slightly from `0.888` to `0.897`
  - The stronger operational difference was contract and spend:
    - `Flash-RC` stayed `100%` strict
    - `Flash-AO` drifted to `95.1%` strict with `12` recoverable non-strict turns
    - `Flash-RC` cost `3.40x` as much as `Flash-AO`

## Behavioral Endpoints
- `all_attack_match_rate`:
  - Flash-Lite: `0.500` AO vs `0.167` RC
  - Flash: `0.208` AO vs `0.125` RC
- `first_potion_profile`:
  - Flash-Lite first-potion median: `40 HP` AO vs `60 HP` RC
  - Flash first-potion median: `40 HP` AO vs `40 HP` RC
  - never-used-potion rate improved in both cells
- `unused_potions_on_loss_rate`:
  - Flash-Lite: `0.938` AO vs `0.375` RC
  - Flash: `0.615` AO vs `0.545` RC
- `state_action_consistency`:
  - Flash-Lite: `0.891` AO vs `0.818` RC
  - Flash: `0.888` AO vs `0.897` RC
- `position_policy_delta`:
  - Flash-Lite: `0.117` AO vs `0.246` RC
  - Flash: `0.071` AO vs `0.100` RC
- `error_recovery_rate`:
  - Flash-Lite: `0.259` AO vs `0.529` RC
  - Flash: `0.372` AO vs `0.410` RC

## Outcome, Cost, and Reliability
- Win rates:
  - Flash-Lite: `8-16` AO vs RC
  - Flash: `11-13` AO vs RC
- Cost per match:
  - Flash-Lite cell: `0.00161`
  - Flash cell: `0.00809`
  - controller-level totals:
    - FlashLite-AO `0.01054`
    - FlashLite-RC `0.02819`
    - Flash-AO `0.04411`
    - Flash-RC `0.15008`
- Latency notes:
  - Flash-Lite cell average duration: `13.83s` per match
  - Flash cell average duration: `18.25s` per match
  - long reasoning traces clearly increased wall-clock time in both cells
- Parse / strictness notes:
  - `0` parse failures in both cells
  - Flash-Lite stayed `100%` strict for both controllers
  - Flash-RC stayed `100%` strict
  - Flash-AO recorded `12` recoverable non-strict turns and ended at `95.1%` strictness

## Limitations
- FixedDamage remains a local-decision game.
- This pilot isolates controller type only; it does not test broader reasoning or memory claims.
- The Flash-Lite uplift is still pilot-scale. `16-8` is directionally interesting, not yet a statistically secure competitive claim.
- `ReasoningController` changes both output contract and verbosity, so part of the cost increase is structural rather than model-specific.

## Next Steps
- Expand only the Flash-Lite controller cell if we want stronger causal evidence.
- Do not expand Flash yet; the current behavioral gains are too small for the cost multiplier.
- If Flash-Lite is rerun, keep behavioral endpoints primary and add one consumer-facing summary that pulls the evidence examples directly into the writeup.
