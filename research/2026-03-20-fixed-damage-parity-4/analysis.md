# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches in one cell
- Decisive matches: 48
- Draws: 0
- Win rates: `FlashLite-RC-TR-HP` finished `28-20` over `Flash-AO`
- Statistical read: `p=0.312`, negligible effect, not significant at `alpha=0.05`
- Position read: first player won `42/48`; `FlashLite-RC-TR-HP` won `5/24` as second player vs `Flash-AO` `1/24`
- First player in first recorded match: `Flash-AO`
- Strict contract rate: `0.9880` overall
- Artifact validation: all exported matches passed
- Average turns: `22.54`
- Average duration (s): `19.30`
- Total cost: `0.21126`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: the full Flash-Lite stack reproduced a positive outcome edge on a fresh seed family, finishing `28-20` over plain Flash, but the replication was weaker than Parity 3 and still far from formal significance.
- Competitive finding: Flash-Lite again outperformed Flash on raw wins, but the edge was small enough that the outcome still reads as compatible with chance at `N=48`.
- Mechanism finding: the improved Flash-Lite policy held up. It remained more consistent, less seat-sensitive, and far less likely to lose with unused potions than plain Flash.
- Practical read: the full stack still looks like the best known Flash-Lite condition for FixedDamage, but this package reinforces that position remains the load-bearing obstacle to a clean superiority claim.

## Outcome Readout
- `FlashLite-RC-TR-HP` beat `Flash-AO` `28-20` at `N=48`.
- This is a positive replication in direction, not a formal competitive proof.
  - exact binomial `p=0.312`
  - effect size `0.167` (`negligible`)
- Compared with Parity 3:
  - Parity 3 finished `31-17` with `p=0.059`
  - Parity 4 finished `28-20` with `p=0.312`
- So the current arc supports “the full Flash-Lite stack stays competitive across fresh seeds,” not “the full stack has now proven superiority over Flash.”

## Position-Controlled Results
- The primary diagnostic weakened relative to Parity 3.
  - `FlashLite-RC-TR-HP` won `23/24` as first player and `5/24` as second
  - `Flash-AO` won `19/24` as first player and `1/24` as second
- First player won `42/48`, so this schedule family was even more position-dominated than Parity 3.
- The good news is that Flash-Lite still held the better second-player record.
- The limiting fact is that `5/24` second-player wins is not enough to carry a robust parity claim on its own.

## Behavioral Endpoints
- `FlashLite-RC-TR-HP` remained the more coherent policy:
  - `state_action_consistency`: `0.962` vs `Flash-AO` `0.897`
  - `position_policy_delta`: `0.032` vs `0.160`
  - `all_attack_match_rate`: `4.2%` vs `14.6%`
  - `unused_potions_on_loss_rate`: `15.0%` vs `42.9%`
  - `error_recovery_rate`: `0.569` vs `0.368`
- Critical defense was similar in the aggregate:
  - `critical_potion_response_rate`: `0.444` for `FlashLite-RC-TR-HP`
  - `0.434` for `Flash-AO`
- Flash-Lite still healed later on first use:
  - median first potion `20 HP` for `FlashLite-RC-TR-HP`
  - median first potion `40 HP` for `Flash-AO`
- In this package, later healing again paired with better overall policy quality rather than worse survival.

## Threshold-State Evidence
- The healthy-state second-player bug stayed fully fixed.
  - at shared `80 HP / 3 potions`, `FlashLite-RC-TR-HP` attacked `29/29` as first player and `24/24` as second
  - the old panic-heal pattern did not return
- The critical-state second-player behavior stayed much better than in the pre-HP-grounding packages, though not perfectly symmetric.
  - at shared `20 HP / 3 potions`, `FlashLite-RC-TR-HP`:
    - first player: `POTION` `20/21`
    - second player: `POTION` `20/24`, `ATTACK` `4/24`
  - at shared `20 HP / 1 potion`, `FlashLite-RC-TR-HP`:
    - first player: `POTION` `20/21`
    - second player: `POTION` `19/21`, `ATTACK` `2/21`
- So the residual problem is no longer a broken threshold.
  - it is a smaller amount of second-player critical-state risk-taking
- `Flash-AO` showed the larger seat-conditioned threshold problem in this package.
  - at shared `20 HP / 3 potions`, `Flash-AO` attacked `15/17` as first player but only `2/10` as second
  - at shared `20 HP / 1 potion`, it healed `10/10` as first player but attacked `17/27` as second
  - that asymmetry helps explain why Flash won only `1/24` matches as second player

## Cost, Latency, and Reliability
- Cost:
  - `FlashLite-RC-TR-HP`: `$0.10577` total, `$0.002204` per player-match
  - `Flash-AO`: `$0.10548` total, `$0.002198` per player-match
  - cost was effectively equal in this package
- Latency:
  - package average duration: `19.30s` per match
- Reliability:
  - `FlashLite-RC-TR-HP`: `100%` strict, `0` parse failures
  - `Flash-AO`: `97.59%` strict, `13` recoverable non-strict turns, `0` parse failures
- So the full Flash-Lite stack stayed slightly cleaner on the contract layer as well as the behavioral layer.

## Interpretation
- This package does not justify the sentence “Flash-Lite is now proven better than Flash.”
- It does justify two narrower sentences:
  - the full Flash-Lite strategy stack remained competitively better on raw outcomes than plain Flash on a fresh seed family
  - the stronger policy shape held up, with lower seat drift and fewer costly healing mistakes than plain Flash
- The replication therefore strengthens the broader research story:
  - strategy stack matters
  - a weaker model can stay competitive with a stronger one once the prompting and reasoning structure are tuned
- What it does not settle is the formal competitive claim.
  - the remaining uncertainty is still position
  - this seed family was too first-player dominated for a `28-20` edge to mean very much statistically

## Limitations
- The package is still a single-cell study on one fresh seed family.
- The outcome edge is directionally positive but still statistically weak.
- FixedDamage remains a local sequential decision task, so the result transfers most directly to similar task classes.
- Position was extremely dominant in this schedule family, which compresses what outcome differences can prove.

## Next Steps
- Move on to the cross-provider test:
  - `FlashLite-RC-TR-HP` vs `Mini-AO`
- Keep the same behavioral endpoints for comparability.
- Do not change the Flash-Lite stack again before that matchup; Parity 4 reinforces that the current stack is already the right candidate to carry forward.
