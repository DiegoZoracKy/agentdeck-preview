# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches in one cell
- Decisive matches: 48
- Draws: 0
- Win rates: `GPT5Mini-AO` finished `28-20` over `FlashLite-RC-TR-HP`
- Statistical read: `p=0.312`, negligible effect, not significant at `alpha=0.05`
- Position read: first player won `44/48`; `FlashLite-RC-TR-HP` won `20/24` as first player and `0/24` as second
- First player in first recorded match: `FlashLite-RC-TR-HP`
- Strict contract rate: `1.0000` overall
- Artifact validation: all exported matches passed
- Average turns: `22.42`
- Average duration (s): `105.82`
- Total cost: `0.80113`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: the full Flash-Lite stack lost directionally to plain `gpt-5-mini`, finishing `20-28` at `N=48`.
- Statistical finding: this is not a formal performance gap claim. The edge stayed non-significant because the package was extremely first-player dominated.
- Mechanism finding: Flash-Lite remained the cleaner and lower-drift policy, but `gpt-5-mini` was the stronger survival policy. It healed more effectively in critical states, recovered better after misses, and converted the few second-player upsets that determined the gap.
- Practical read: this is a useful negative result. The current Flash-Lite stack is enough to beat `gpt-4o-mini` and stay competitive with plain Flash, but it does not fully close the gap to plain `gpt-5-mini` in FixedDamage.

## Outcome Readout
- `GPT5Mini-AO` beat `FlashLite-RC-TR-HP` `28-20` at `N=48`.
- The outcome read is directional only.
  - exact binomial `p=0.312`
  - effect size `0.167` (`negligible`)
- This is weaker than the Mini result and weaker than the near-significant Flash parity package.

## Position-Controlled Results
- Position was overwhelmingly dominant here.
  - first player won `44/48`
  - upset rate: `4/48`
- `FlashLite-RC-TR-HP` was strong only when it moved first:
  - `20/24` as first player
  - `0/24` as second player
- `GPT5Mini-AO` was perfect as first player and still stole a small number of second-player games:
  - `24/24` as first player
  - `4/24` as second player
- So the entire outcome gap comes from upset conversion.
  - Flash-Lite converted none
  - GPT-5 Mini converted four

## Behavioral Endpoints
- Flash-Lite remained the cleaner, lower-drift policy:
  - `state_action_consistency`: `0.9680`
  - `position_policy_delta`: `0.0159`
- GPT-5 Mini was much noisier and more seat-sensitive:
  - `state_action_consistency`: `0.8677`
  - `position_policy_delta`: `0.1403`
- But GPT-5 Mini still won because its survival policy was better:
  - `critical_potion_response_rate`: `0.5571` vs Flash-Lite `0.3958`
  - `error_recovery_rate`: `0.6304` vs Flash-Lite `0.5122`
  - `all_attack_match_rate`: `6.25%` vs Flash-Lite `20.83%`
- The loss-side resource metrics tell the same story:
  - `unused_potions_on_loss_rate`: `0.0%` for `GPT5Mini-AO`
  - `35.7%` for Flash-Lite on its `28` losses
- So the gap was not formatting or parseability.
  - both players were `100%` strict with `0` parse failures
  - the gap was better survival timing from the more expensive plain model

## Threshold-State Evidence
- The old `gpt-4o-mini` pathology does not transfer to `gpt-5-mini`.
  - at shared `80 HP / 3 potions`, `GPT5Mini-AO` attacked `24/24` as first player and `23/24` as second
  - this is a sane opening policy, not an early-heal giveaway
- GPT-5 Mini's biggest seat effect appears later, at medium HP:
  - at shared `40 HP / 3 potions`, `GPT5Mini-AO`:
    - first player: `ATTACK` `29/38`, `POTION` `9/38`
    - second player: `ATTACK` `7/21`, `POTION` `14/21`
  - that is the clearest evidence that it becomes much more defensive from the harder seat
- Flash-Lite's threshold repair mostly held:
  - at shared `80 HP / 3 potions`, it attacked `27/27` as first player and `24/24` as second
  - at shared `20 HP / 1 potion`, it healed `20/20` as first player and `18/19` as second
- The remaining Flash-Lite weakness is at critical states with more resources available:
  - at shared `20 HP / 3 potions`, Flash-Lite still attacked `10/30` as first player and `10/28` as second
  - that is not a giant seat inversion, but it is still too aggressive against an opponent that survives well

## Cost, Latency, and Reliability
- Cost:
  - `FlashLite-RC-TR-HP`: `$0.11202` total, `$0.002334` per player-match
  - `GPT5Mini-AO`: `$0.68911` total, `$0.014356` per player-match
  - plain `gpt-5-mini` cost about `6.15x` as much as the tuned Flash-Lite stack in this package
- Latency:
  - package average duration: `105.82s` per match
  - this is far slower than the earlier weak-tier baselines and reflects the heavier OpenAI mini runtime
- Reliability:
  - both players were `100%` strict with `0` parse failures
- So the pricing story is still meaningful even though Flash-Lite lost:
  - the cheaper stack stayed competitive enough to keep the result non-significant
  - but it did not overturn the stronger baseline

## Interpretation
- This package does justify the sentence “plain `gpt-5-mini` was stronger than the current best Flash-Lite stack in FixedDamage.”
- It also clarifies why:
  - not because Flash-Lite collapsed into the old threshold bug
  - but because `gpt-5-mini` had the better survival and recovery policy in a very position-heavy package
- That makes this a useful boundary marker for the current arc:
  - tuned Flash-Lite is enough to beat plain `gpt-4o-mini`
  - tuned Flash-Lite is enough to stay competitive with plain Flash
  - tuned Flash-Lite is not enough to beat plain `gpt-5-mini`

## Limitations
- The package is still a single-cell study on one seed family.
- First-player dominance was extreme (`44/48`), which weakens any broad performance claim from the headline score alone.
- FixedDamage remains a local sequential decision task, so the result transfers most directly to similar task classes.
- Because `gpt-5-mini` does not share the `gpt-4o-mini` early-heal bug, the intervention question is now different from the earlier Mini arc.

## Next Steps
- If the next FixedDamage question is still model-vs-strategy, the clean follow-up is a mirror test:
  - `GPT5Mini-RC-TR-HP` vs `GPT5Mini-AO`
- If the goal is breadth rather than more FixedDamage tuning, this is a good stopping point for the current game:
  - the stack's strengths and its boundary against a stronger plain mini model are now both visible
- That makes moving to the next game class more defensible than another narrow FixedDamage ablation.

