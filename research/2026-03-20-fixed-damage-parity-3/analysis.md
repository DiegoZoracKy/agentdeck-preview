# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches in one cell
- Decisive matches: 48
- Draws: 0
- Win rates: `FlashLite-RC-TR-HP` finished `31-17` over `Flash-AO`
- Statistical read: `p=0.059`, small effect, not significant at `alpha=0.05`
- Position read: first player won `35/48`; `FlashLite-RC-TR-HP` won `10/24` as second player vs `Flash-AO` `3/24`
- First player in first recorded match: `FlashLite-RC-TR-HP`
- Strict contract rate: `0.9751` overall
- Artifact validation: all exported matches passed
- Average turns: `21.73`
- Average duration (s): `19.78`
- Total cost: `0.20162`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: the full Flash-Lite strategy stack produced the strongest competitive result in the FixedDamage arc so far, finishing `31-17` over plain Flash at `N=48`.
- Statistical finding: the outcome edge still stops just short of the formal cutoff (`p=0.059`, small effect), so this is not yet a clean superiority claim.
- Mechanism finding: the HP-threshold intervention held up at scale. The healthy-state second-player bug stayed fixed, the critical-state second-player hesitation shrank substantially, and Flash-Lite's second-player win rate rose to `10/24`.
- Practical recommendation: treat `FlashLite-RC-TR-HP` as the correct parity candidate stack for this task class. The remaining obstacle is position, not the original healing-threshold pathology.

## Outcome Readout
- `FlashLite-RC-TR-HP` beat `Flash-AO` `31-17` at `N=48`.
- The outcome read is strong but not formally significant under the package threshold.
  - exact binomial `p=0.059`
  - effect size `0.296` (`small`)
- This is a real upgrade from Threshold 1's HP-grounded pilot, where the same stack finished only `13-11`.
- The main reason the package is still short of a clean competitive claim is that first-player advantage remains strong:
  - first player won `35/48`
  - upset rate: `13/48`

## Position-Controlled Results
- The primary diagnostic improved materially.
  - `FlashLite-RC-TR-HP` won `21/24` as first player and `10/24` as second
  - `Flash-AO` won `14/24` as first player and only `3/24` as second
- That means the full-stack Lite condition did not merely farm first-player wins.
  - it gained a real second-player edge over plain Flash
  - but the second-player record is still below `50%`, so position remains load-bearing
- Compared with Threshold 1's HP-grounded pilot:
  - `FlashLite-RC-TR-HP` improved from `3/12` to `10/24` as second player
  - this is the most important competitive improvement in the package

## Behavioral Endpoints
- `FlashLite-RC-TR-HP` remained the more coherent policy:
  - `state_action_consistency`: `0.947` vs `Flash-AO` `0.875`
  - `position_policy_delta`: `0.043` vs `0.153`
  - `all_attack_match_rate`: `10.4%` vs `18.8%`
  - `unused_potions_on_loss_rate`: `35.3%` vs `41.9%`
  - `error_recovery_rate`: `0.563` vs `0.327`
- Critical defense was roughly comparable at the aggregate level:
  - `critical_potion_response_rate`: `0.434` for `FlashLite-RC-TR-HP`
  - `0.438` for `Flash-AO`
- First-potion timing stayed later for Flash-Lite:
  - median first potion `20 HP` for `FlashLite-RC-TR-HP`
  - median first potion `40 HP` for `Flash-AO`
  - in this package, later healing did not mean worse behavior; it came with fewer all-attack collapses and better recovery

## Threshold-State Evidence
- The healthy-state second-player bug stayed fixed.
  - at shared `80 HP / 3 potions`, `FlashLite-RC-TR-HP` attacked `28/28` as first player and `23/24` as second
  - the old second-player panic-heal from Parity 2 and the reinforced baseline did not return
- The critical-state second-player behavior improved but did not become perfectly symmetric.
  - at shared `20 HP / 3 potions`, `FlashLite-RC-TR-HP`:
    - first player: `POTION` `19/21`
    - second player: `POTION` `18/26`, `ATTACK` `8/26`
  - at shared `20 HP / 1 potion`, `FlashLite-RC-TR-HP`:
    - first player: `POTION` `19/20`
    - second player: `POTION` `17/19`, `ATTACK` `2/19`
- So the current residual problem is no longer an inverted threshold.
  - it is occasional second-player risk-taking in critical states
  - that residual still appears often enough to keep the package just short of a full competitive proof
- `Flash-AO` showed its own seat-sensitive thresholds in this package.
  - at shared `20 HP / 3 potions`, `Flash-AO` attacked `16/22` as first player but only `2/9` as second
  - at shared `30 HP / 2 potions`, it attacked `6/16` as first player and only `3/17` as second
  - this helps explain why Flash's second-player record fell to `3/24`

## Cost, Latency, and Reliability
- Cost:
  - `FlashLite-RC-TR-HP`: about `$0.1019` total, `$0.002123` per player-match
  - `Flash-AO`: about `$0.0997` total, `$0.002078` per player-match
  - the full Flash-Lite stack no longer preserved a cost advantage in this cell
- Latency:
  - package average duration: `19.78s` per match
  - some terminal no-potion states triggered long reasoning traces, which raised tail latency without changing the game outcome
- Reliability:
  - `FlashLite-RC-TR-HP`: `100%` strict, `0` parse failures
  - `Flash-AO`: `94.98%` strict, `26` recoverable non-strict turns, `0` parse failures
  - unlike earlier parity packages, the weaker model now looks cleaner on the contract layer as well

## Interpretation
- This package does not justify the sentence “Flash-Lite is now proven better than Flash.”
- It does justify a narrower and still important sentence:
  - the full strategy stack made the weaker model competitively better than plain Flash in this `N=48` package, while removing the original threshold pathology and materially improving second-player performance
- That is enough to support the broader research program:
  - model strength is not the only lever
  - the strategy stack can move a weaker model much closer to a stronger one, and sometimes ahead on raw outcomes
- The remaining uncertainty is not whether the intervention matters.
  - it clearly does
  - the uncertainty is whether the current `31-17` edge is stable enough across schedules to support a formal superiority claim

## Limitations
- The package is still a single-cell study on one fresh seed family.
- The outcome edge is just above the exact-binomial significance threshold.
- FixedDamage remains a local sequential decision task, so the result transfers most directly to similar task classes.
- Position is still strong enough that the remaining gap may be more about seat dynamics than generic reasoning quality.

## Next Steps
- If the goal is a formal competitive claim, run one more fresh-seed parity package with the same full stack and treat it as a schedule-diversity replication.
- If the goal is product framing, the current package is already enough to support the claim that strategic prompting can make a cheaper model competitive with a stronger one in this task class.
- Do not spend more effort on the old threshold bug. That mechanism question is resolved well enough.
