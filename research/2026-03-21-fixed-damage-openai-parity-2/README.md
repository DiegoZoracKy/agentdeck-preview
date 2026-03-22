# FixedDamage OpenAI Parity 2

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-21-fixed-damage-openai-parity-2`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `openai:gpt-4o-mini`, `openai:gpt-5-mini`
- Seed Base: `17242`
- Topline Winner: `GPT5Mini-AO` by `27-21`
- Statistical Read: `p=0.471`, negligible effect, not significant at `alpha=0.05`
- Position Read: first player won `45/48`; `GPT4oMini-RC-TR-HP` went `21/24` as first player and `0/24` as second
- Avg Turns: `24.60`
- Avg Duration (s): `114.45`
- Total Cost: `0.92794`
<!-- AUTO_FACTS:END -->

## Why This Exists
- OpenAI Parity 1 established two things:
  - plain `gpt-4o-mini` was only directionally behind plain `gpt-5-mini`
  - `ReasoningController` alone made `gpt-4o-mini` much worse
- The remaining honest FixedDamage question for this ladder is:
  - does the full stack that worked for Flash-Lite also work for `gpt-4o-mini`?
- This package tests the full stack directly:
  - `ReasoningController`
  - turn-time controller-format reinforcement
  - HP-threshold grounding

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gpt-4o-mini`
  - `gpt-5-mini`
- Strategy conditions:
  - `GPT4oMini-RC-TR-HP` vs `GPT5Mini-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `48`
- Seed base:
  - `17242`

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
- If the failure in OpenAI Parity 1 was that RC-only changed the policy in the wrong direction, then the full stack should recover `gpt-4o-mini` and at least make the `gpt-5-mini` matchup look competitive again.

## Results
- `GPT5Mini-AO` beat `GPT4oMini-RC-TR-HP` `27-21` at `N=48`.
- This is not a significant result:
  - exact binomial `p=0.4709`
  - effect size `0.125` (`negligible`)
- So the full stack did not achieve parity or superiority.
- But it did recover almost all the ground lost in the RC-only failure:
  - AO baseline had `gpt-4o-mini` at `19-29`
  - RC-only dropped to `8-40`
  - full stack improved back to `21-27`

### Confirmed Findings
- The full stack fixed the obvious high-HP seat bug:
  - at `80 HP / 3 potions`, `GPT4oMini-RC-TR-HP` attacked `24/25` as first player and `24/24` as second
  - this is a major repair over:
    - plain `GPT4oMini-AO`, which healed `24/24` as second player in that same state
    - RC-only `GPT4oMini-RC`, which still healed `9/24` as second player there
- The full stack also restored much healthier low-HP defense than RC-only:
  - first potion median `20 HP`
  - `critical_potion_response_rate`: `0.444`
  - `error_recovery_rate`: `0.494`
  - `unused_potions_on_loss_rate`: `18.5%`
- Relative to the RC-only failure, the recovery is large:
  - wins: `8 -> 21`
  - `critical_potion_response_rate`: `0.363 -> 0.444`
  - `error_recovery_rate`: `0.336 -> 0.494`
  - `unused_potions_on_loss_rate`: `60.0% -> 18.5%`
  - `position_policy_delta`: `0.149 -> 0.060`
- But the full stack still failed completely in the harder seat:
  - `GPT4oMini-RC-TR-HP` won `21/24` as first player
  - `0/24` as second player
- The remaining failure mode is narrower than before:
  - at `20 HP / 1 potion` as second player, it still attacked `6/22`
  - at `30 HP / 2 potions` as second player, it attacked `41/49`
  - so the problem is no longer the obvious opening threshold bug; it is medium-to-low HP over-aggression in the harder seat

### Cost and Reliability
- Cost:
  - `GPT4oMini-RC-TR-HP`: `$0.17777` total, `$0.003703` per player-match
  - `GPT5Mini-AO`: `$0.75017` total, `$0.015629` per player-match
  - plain `gpt-5-mini` still cost about `4.2x` as much as the full `gpt-4o-mini` stack in this package
- Reliability:
  - both players were `100%` strict with `0` parse failures

### What AgentDeck Made Visible
- The simple score says the full stack still lost.
- The behavioral layer shows the more useful truth:
  - the stack clearly repaired the policy damage introduced by RC-only
  - it repaired the early threshold bug and the worst loss-side resource misuse
  - but it did not solve second-player conversion
- That is why this package matters:
  - it turns “the intervention didn’t win” into a much more actionable statement:
  - the full stack made `gpt-4o-mini` competitive again, but the remaining obstacle is seat-conditioned endgame aggression, not general confusion
