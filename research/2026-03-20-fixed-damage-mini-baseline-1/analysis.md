# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches in one cell
- Decisive matches: 48
- Draws: 0
- Win rates: `Mini-AO` finished `44-4` over `FlashLite-AO`
- Statistical read: `p=1.51e-09`, large effect, significant at `alpha=0.05`
- Position read: first player won `28/48`; `FlashLite-AO` won `0/24` as second player vs `Mini-AO` `20/24`
- First player in first recorded match: `FlashLite-AO`
- Strict contract rate: `1.0000` overall
- Artifact validation: all exported matches passed
- Average turns: `18.17`
- Average duration (s): `13.47`
- Total cost: `0.06281`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: the missing Mini control is decisive. Plain Flash-Lite lost to plain Mini `44-4`, while the tuned Flash-Lite stack in Mini Parity 1 won `41-7` against the same baseline opponent.
- Causal finding: the Mini `41-7` result was not just “Mini is weak.” The strategy stack flipped the matchup.
- Mechanism finding: plain Flash-Lite attacked through critical states and frequently died holding unused potions, while tuned Flash-Lite healed much later but much more coherently.
- Practical read: this is the cleanest evidence in the FixedDamage arc that the strategy stack, not just the base model, was the main cause of the cross-provider reversal.

## Outcome Readout
- `Mini-AO` beat `FlashLite-AO` `44-4` at `N=48`.
- The outcome read is strong and statistically clean.
  - exact binomial `p=1.51e-09`
  - effect size `0.985` (`large`)
- This is the exact opposite of Mini Parity 1:
  - baseline: `FlashLite-AO` lost `4-44`
  - tuned: `FlashLite-RC-TR-HP` won `41-7`
- That is a `37`-win swing and a `77.1`-point win-rate swing for Flash-Lite across two otherwise comparable cross-provider packages.

## Position-Controlled Results
- Position was present but not the deciding story.
  - first player won `28/48`
  - upset rate: `20/48`
- Plain Flash-Lite was weak from both seats and completely failed from second:
  - `4/24` as first player
  - `0/24` as second player
- Mini was strong from both seats:
  - `24/24` as first player
  - `20/24` as second player
- Compared with Mini Parity 1:
  - tuned Flash-Lite improved from `0/24` to `19/24` as second player
  - that seat-level change is too large to explain away as seed noise

## Behavioral Endpoints
- Both players were perfectly strict and parseable, so the gap is entirely policy-level.
- Plain Flash-Lite's policy was the problem:
  - `all_attack_match_rate`: `45.8%`
  - `never_used_rate`: `45.8%`
  - `unused_potions_on_loss_rate`: `93.2%`
  - `state_action_consistency`: `0.907`
  - `position_policy_delta`: `0.169`
  - `critical_potion_response_rate`: `0.203`
  - `error_recovery_rate`: `0.259`
- Mini's baseline still had the recognizable early-heal pattern:
  - median first potion `80 HP`
  - `position_policy_delta`: `0.438`
  - `critical_potion_response_rate`: `0.657`
- The tuned comparison is the important one:
  - Flash-Lite `all_attack_match_rate`: `45.8% -> 12.5%`
  - `never_used_rate`: `45.8% -> 12.5%`
  - `critical_potion_response_rate`: `0.203 -> 0.513`
  - `error_recovery_rate`: `0.259 -> 0.730`
  - `position_policy_delta`: `0.169 -> 0.044`

## Threshold-State Evidence
- The baseline failure mode is visible at critical HP.
  - at shared `20 HP / 3 potions`, `FlashLite-AO` attacked `19/20` as first player and `6/10` as second
  - at shared `20 HP / 1 potion`, `FlashLite-AO` attacked `2/2` as first player and `14/16` as second
- So plain Flash-Lite did not merely “heal a bit too late.”
  - it often refused to heal in states where survival depended on it
- Mini still showed the same early-heal baseline that made Mini Parity 1 interpretable:
  - at shared `80 HP / 3 potions`, `Mini-AO` healed `14/28` as first player and `24/24` as second
- Compared with Mini Parity 1:
  - tuned Flash-Lite attacked `48/48` at `80 HP / 3 potions` as first player and `46/47` as second
  - tuned Flash-Lite healed `17/20` to `19/23` at `20 HP / 3 potions`
  - tuned Flash-Lite healed `17/17` to `17/20` at `20 HP / 1 potion`
- That is the mechanism of the reversal.
  - the stack did not just add generic quality
  - it repaired the exact states where plain Flash-Lite was self-sabotaging

## Cost, Latency, and Reliability
- Cost:
  - `FlashLite-AO`: `$0.02266` total, `$0.000472` per player-match
  - `Mini-AO`: `$0.04014` total, `$0.000836` per player-match
  - plain Flash-Lite was cheaper than plain Mini
- Latency:
  - package average duration: `13.47s` per match
  - much lower than the tuned package because both players remained action-only
- Reliability:
  - both players were `100%` strict with `0` parse failures
- So the tuned stack's win reversal came with a real cost increase for Flash-Lite:
  - `$0.000472 -> $0.002263` per player-match
  - about `4.8x` higher than plain Flash-Lite

## Interpretation
- This package settles the main ambiguity from Mini Parity 1.
- The sentence we can now defend is:
  - the Flash-Lite strategy stack, not merely Mini's weak default policy, was the main cause of the `41-7` cross-provider win
- Plain Flash-Lite was not close to parity with Mini.
  - it was dominated
- Tuned Flash-Lite then dominated that same opponent.
- That makes this one of the cleanest demonstrations so far of the broader AgentDeck thesis:
  - the strategy stack can matter more than the base model choice for a given task class
- The cost story also becomes clearer:
  - the win reversal was real
  - and it required materially more inference-time budget

## Limitations
- The package is still a single-cell study on one fresh seed family.
- FixedDamage remains a local sequential decision task, so the result transfers most directly to similar task classes.
- Position will need explicit reporting in any cross-provider interpretation.
- This baseline exists specifically to interpret Mini Parity 1; it is not a new tuning experiment.

## Next Steps
- The FixedDamage Mini story is now causally clean enough to stop.
- If the next goal is breadth, move to a new game class rather than more Mini variants in FixedDamage.
- Variable-damage uncertainty is the most natural next candidate once the FixedDamage arc is closed.
