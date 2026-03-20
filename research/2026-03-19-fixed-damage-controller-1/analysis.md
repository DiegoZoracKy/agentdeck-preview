# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 72 total matches across 2 cells
- Decisive matches: 72
- Draws: 0
- Win rates: FlashLite-RC finished `37-11` over FlashLite-AO after expansion; Flash-RC finished `13-11` over Flash-AO
- Topline winner: ReasoningController is now significant for Flash-Lite and still near-null for Flash
- First player in first recorded match: FlashLite-AO
- Strict contract rate: `0.9907` overall across both exported cells
- Artifact validation: all exported cells passed
- Average turns: 17.97 overall
- Average duration (s): 15.99 overall
- Total cost: 0.27348
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the
actor who actually took the first turn.

## Executive Summary
- Primary finding: `ReasoningController` now has a statistically significant competitive effect on Flash-Lite at `N=48`, and the behavioral mechanism remains the same one surfaced in the pilot.
- Secondary finding: Flash already behaved closer to a reasonable state-grounded policy, so reasoning mostly added cost and a small amount of extra polish.
- Practical recommendation: use `ReasoningController` selectively for weak unstable policies like Flash-Lite; do not treat it as a default upgrade for every weak model.

## Controller Pilot
- `gemini-2.5-flash-lite`:
  - `FlashLite-RC` was expanded from `24` to `48` matches and now finished `37-11` over `FlashLite-AO` (`p=0.00022`, medium effect).
  - The behavioral mechanism remained strong after expansion:
    - all-attack rate fell from `45.8%` to `18.8%`
    - never-used-potion rate fell from `45.8%` to `18.8%`
    - unused-potions-on-loss rate fell from `94.6%` to `36.4%`
    - critical-potion response rose from `18.3%` to `50.8%`
    - recovery after missed critical defense rose from `0.259` to `0.596`
  - One pilot detail did not survive expansion: first-potion median converged to `40 HP` for both AO and RC, so the durable story is better defensive timing under pressure, not a stable earlier first-heal threshold.
  - The tradeoff is still real. `FlashLite-RC` remained less state-consistent than `FlashLite-AO` (`0.821` vs `0.897`) and more seat-conditioned (`position_policy_delta` `0.204` vs `0.092`).
  - Concrete evidence from the exported artifact:
    - at shared `80 HP / 3 potions`, `FlashLite-RC` attacked `25/25` as first player but split `14/24` attack vs `10/24` potion as second player
    - at shared `60 HP / 1 potion`, `FlashLite-RC` attacked `6/6` as first player but split `3/6` attack vs `3/6` potion as second player
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
  - Flash-Lite: `0.458` AO vs `0.188` RC
  - Flash: `0.208` AO vs `0.125` RC
- `first_potion_profile`:
  - Flash-Lite first-potion median: `40 HP` AO vs `40 HP` RC
  - Flash first-potion median: `40 HP` AO vs `40 HP` RC
  - never-used-potion rate improved in both cells
- `unused_potions_on_loss_rate`:
  - Flash-Lite: `0.946` AO vs `0.364` RC
  - Flash: `0.615` AO vs `0.545` RC
- `state_action_consistency`:
  - Flash-Lite: `0.897` AO vs `0.821` RC
  - Flash: `0.888` AO vs `0.897` RC
- `position_policy_delta`:
  - Flash-Lite: `0.092` AO vs `0.204` RC
  - Flash: `0.071` AO vs `0.100` RC
- `error_recovery_rate`:
  - Flash-Lite: `0.259` AO vs `0.596` RC
  - Flash: `0.372` AO vs `0.410` RC

## Outcome, Cost, and Reliability
- Win rates:
  - Flash-Lite: `11-37` AO vs RC
  - Flash: `11-13` AO vs RC
- Cost per match:
  - Flash-Lite cell: `0.00165`
  - Flash cell: `0.00809`
  - controller-level totals:
    - FlashLite-AO `0.02100`
    - FlashLite-RC `0.05828`
    - Flash-AO `0.04411`
    - Flash-RC `0.15008`
- Latency notes:
  - Flash-Lite cell average duration: `14.87s` per match
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
- The Flash-Lite expansion reused the same cell scheduling seed as the pilot. It adds another stochastic replicate under the same fairness schedule rather than a different schedule family.
- `ReasoningController` changes both output contract and verbosity, so part of the cost increase is structural rather than model-specific.

## Next Steps
- Freeze Flash-Lite as the current positive controller case unless we specifically want schedule-diversity replication.
- Do not expand Flash yet; the current behavioral gains are still too small for the cost multiplier.
- The next product-facing task is no longer more Flash-Lite matches; it is turning multi-session matrix aggregation into a first-class research CLI feature.
