# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): `96` total matches across `2` cells
- Decisive matches: `96`
- Draws: `0`
- Baseline: `GPT5Mini-AO` finished `29-19` over `GPT4oMini-AO`
- Baseline statistics: `p=0.193`, small effect, not significant at `alpha=0.05`
- RC-only: `GPT5Mini-AO` finished `40-8` over `GPT4oMini-RC`
- RC-only statistics: `p=3.31e-06`, medium effect, significant at `alpha=0.05`
- Position read:
  - baseline first player won `41/48`
  - RC cell first player won `32/48`
  - `GPT4oMini-RC` won `0/24` as second player
- Artifact validation: all exported matches passed
- Total cost: `1.57631`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: plain `gpt-4o-mini` was only directionally behind plain `gpt-5-mini`, but `ReasoningController` alone made `gpt-4o-mini` much worse rather than more competitive.
- Statistical finding:
  - baseline `GPT5Mini-AO` vs `GPT4oMini-AO` finished `29-19`, `p=0.193`, not significant
  - RC-only `GPT5Mini-AO` vs `GPT4oMini-RC` finished `40-8`, `p=3.31e-06`, significant with medium effect
- Mechanism finding:
  - RC did reduce the worst high-HP early-heal behavior
  - but it replaced it with a more damaging pattern of low-HP indecision, all-attack/no-heal collapses, and much weaker recovery after missed defensive opportunities
- Practical read:
  - `gpt-4o-mini` plus RC-only is not a viable parity path against plain `gpt-5-mini` in FixedDamage
  - if this OpenAI ladder continues, it should skip any more RC-only expansion and move to heavier overlays or stop

## Outcome Readout
- Baseline cell:
  - `GPT5Mini-AO` beat `GPT4oMini-AO` `29-19`
  - exact binomial `p=0.193`
  - effect size `0.210` (`small`)
- RC-only cell:
  - `GPT5Mini-AO` beat `GPT4oMini-RC` `40-8`
  - exact binomial `p=3.31e-06`
  - effect size `0.730` (`medium`)
- So the plain-model gap was directionally real but still underpowered in this seed family, while the RC-only intervention clearly moved the matchup in the wrong direction.

## Position-Controlled Results
- Baseline remained very first-player heavy:
  - first player won `41/48`
  - `GPT4oMini-AO` won `18/24` as first player and only `1/24` as second
  - `GPT5Mini-AO` won `23/24` as first player and `6/24` as second
- RC-only reduced overall first-player dominance but did not help `gpt-4o-mini` in the harder seat:
  - first player won `32/48`
  - `GPT4oMini-RC` won `8/24` as first player and `0/24` as second
  - `GPT5Mini-AO` won `24/24` as first player and `16/24` as second
- That means RC did not just fail to fix the second-player problem.
  - it failed to create even a single second-player win across `24` attempts

## Behavioral Endpoints
- Plain `gpt-4o-mini` showed the expected early-heal pathology:
  - `first_potion_profile.median_first_potion_hp = 60`
  - `position_policy_delta = 0.324`
  - `state_action_consistency = 0.984`
  - `critical_potion_response_rate = 0.550`
  - `error_recovery_rate = 0.531`
- RC-only moved the policy, but not toward a better one:
  - `first_potion_profile.median_first_potion_hp = 40`
  - `position_policy_delta = 0.149`
  - `state_action_consistency = 0.863`
  - `critical_potion_response_rate = 0.363`
  - `error_recovery_rate = 0.336`
- The damaging RC regressions are especially clear in the loss-side metrics:
  - `all_attack_match_rate`: `0.0%` -> `18.75%`
  - `never_used_rate`: `0.0%` -> `18.75%`
  - `unused_potions_on_loss_rate`: `17.2%` -> `60.0%`
- So RC did not simply make `gpt-4o-mini` more cautious or more aggressive.
  - it made it less coherent
  - less consistent
  - and much worse at surviving critical states

## Threshold-State Evidence
- Baseline high-HP failure mode:
  - at shared `80 HP / 3 potions`, `GPT4oMini-AO`:
    - first player: `ATTACK` `24/24`
    - second player: `POTION` `24/24`
  - this is a maximal seat-conditioned threshold bug, and it is the clearest explanation for the baseline second-player collapse
- RC-only partially fixed that exact state:
  - at shared `80 HP / 3 potions`, `GPT4oMini-RC`:
    - first player: `ATTACK` `24/25`
    - second player: `ATTACK` `15/24`, `POTION` `9/24`
  - so the high-HP error was reduced, not removed
- The replacement failure mode shows up at lower HP:
  - evidence example `hp=10|potions=2`:
    - first player: `POTION` `7/7`
    - second player: `ATTACK` `3/6`, `POTION` `3/6`
  - state bucket `position=second|hp=30|potions=1`:
    - `ATTACK` `7/10`
    - `POTION` `3/10`
  - state bucket `position=second|hp=20|potions=2`:
    - `ATTACK` `2/3`
    - `POTION` `1/3`
- That is why the RC cell got worse:
  - it softened the obvious `80 HP` mistake
  - but still attacked too often in the states where survival mattered most

## Cost, Latency, and Reliability
- Baseline cost:
  - `GPT4oMini-AO`: `$0.06009` total, `$0.001252` per player-match
  - `GPT5Mini-AO`: `$0.70033` total, `$0.014590` per player-match
  - plain `gpt-5-mini` cost about `11.7x` as much as plain `gpt-4o-mini`
- RC-only cost:
  - `GPT4oMini-RC`: `$0.09907` total, `$0.002064` per player-match
  - `GPT5Mini-AO`: `$0.71682` total, `$0.014934` per player-match
  - plain `gpt-5-mini` still cost about `7.2x` as much as RC-only `gpt-4o-mini`
  - RC increased `gpt-4o-mini` cost by about `65%` relative to the AO baseline
- Latency:
  - baseline average duration: `95.41s` per match
  - RC-only average duration: `125.14s` per match
  - one `gpt-5-mini` turn in the RC cell took about `606s`, so the runtime tail was very real
- Reliability:
  - baseline overall strict contract rate: `1.0000`
  - RC-only overall strict contract rate: `0.9990`
  - both cells stayed essentially fully parseable and artifact validation passed
- So the package does not support a formatting explanation for the RC failure.
  - the problem is decision quality, not contract compliance

## Interpretation
- This package answers the OpenAI ladder question cleanly:
  - plain `gpt-4o-mini` is directionally weaker than plain `gpt-5-mini`
  - `ReasoningController` alone does not close that gap
  - in this game, it widens it dramatically
- The behavioral read is the important part:
  - RC helped on the obvious opening-seat threshold bug
  - but it degraded the model's low-HP defensive policy enough to swamp that benefit
- That makes this a useful negative result:
  - “add CoT” is not a generic improvement recipe
  - the intervention has to match the actual failure mode
- In FixedDamage, RC alone is the wrong intervention for `gpt-4o-mini`.

## Limitations
- This package covers one seed family only.
- The baseline AO cell stayed non-significant, so it should be read as directional rather than definitive.
- The RC cell had a very long `gpt-5-mini` latency outlier, which affects runtime but not the exported outcome logic.
- FixedDamage remains a local sequential decision task, so these findings transfer most directly to similar task classes.
- The package isolates RC-only on purpose; it does not test whether heavier overlays like TR or HP-grounding could rescue `gpt-4o-mini`.

## Next Steps
- Do not expand the RC-only branch. The package already answered that question.
- If the FixedDamage OpenAI ladder continues, the honest next step is a different intervention stack:
  - `GPT4oMini-RC-TR-HP` vs `GPT5Mini-AO`
  - or stop the ladder here and move to the next game once the current FixedDamage arc is complete
- What this package clearly rules out is the simplest story:
  - RC alone is not enough to make the cheaper OpenAI mini competitive with plain `gpt-5-mini`
