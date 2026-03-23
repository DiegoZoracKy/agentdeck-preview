# Analysis — FixedDamage FlashLite Exit 1

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: the no-potion exit clause improved the best Flash-Lite stack materially; `FlashLite-RC-TR-HP-exit` beat `Flash-AO` `35-13` at `N=48`.
- Secondary finding: the prompt repair removed the pathological low-HP tail without reopening the old threshold bug.
- Practical recommendation: treat the exit-clause stack as the cleaned final Flash-Lite condition for FixedDamage and move next to `VariableDamageGame`.
<!-- AUTO_FACTS:END -->

## Outcome Layer
- The exit-clause stack beat plain Flash `35-13` at `N=48`.
- This is the strongest Flash parity result in the arc and it is now formally significant.
  - exact binomial `p=0.0021`
  - effect size `0.476` (`small`)
- Relative to Parity 3's `31-17`, the result improved by `4` wins on the same `N=48`.
- Position remains strong at the game level, but the repaired Flash-Lite stack kept the second-player edge that mattered most:
  - first player won `37/48`
  - `FlashLite-RC-TR-HP-exit` won `11/24` as second player
  - `Flash-AO` won `0/24` as second player

## Behavioral Layer
- The exit clause preserved the full-stack Flash-Lite behavior and improved several endpoints.
  - `all_attack_match_rate`: `2.1%` vs `Flash-AO` `10.4%`
  - `unused_potions_on_loss_rate`: `7.7%` vs `37.1%`
  - `state_action_consistency`: `0.981` vs `0.868`
  - `position_policy_delta`: `0.014` vs `0.114`
  - `critical_potion_response_rate`: `0.463` vs `0.408`
  - `error_recovery_rate`: `0.597` vs `0.326`
- The repaired stack also stayed cleaner than the old Parity 3 full stack:
  - `all_attack_match_rate`: `2.1%` vs `10.4%`
  - `unused_potions_on_loss_rate`: `7.7%` vs `35.3%`
  - `state_action_consistency`: `0.981` vs `0.947`
  - `position_policy_delta`: `0.014` vs `0.043`

## Cost Layer
- The prompt repair removed the pathological tail, but it did not reduce average spend.
- Flash-Lite cost:
  - Exit 1 mean: about `$0.002379` per player-match
  - Parity 3 mean: about `$0.002123`
- The average rose because the repaired stack won more and pushed more matches deeper.
  - package average turns: `22.31` vs Parity 3 `21.73`
- The important improvement is tail behavior.
  - Parity 3 Flash-Lite per-player-match cost:
    - `p99`: about `$0.003722`
    - max: about `$0.003722`
  - Exit 1 Flash-Lite per-player-match cost:
    - `p99`: about `$0.003184`
    - max: about `$0.003184`
- So the no-potion exit clause traded a slightly higher average for a cleaner, less pathological cost distribution.

## Contract and Confounds
- Planned execution should start on the global Vertex endpoint.
- The Flash retry/backoff profile remains the package-local Gemini setting used
  in the recent parity/cap work:
  - `max_retries=12`
  - `retry_delay=4.0`
- This is an infrastructure note, not a gameplay confound.
- Reliability stayed clean:
  - `FlashLite-RC-TR-HP-exit`: `100%` strict, `0` parse failures
  - `Flash-AO`: `100%` strict, `0` parse failures

## What This Proves
- The worst full-stack tail spike in FixedDamage was a prompt defect, not irreducibly hard reasoning.
- A one-line no-potion escape clause was enough to:
  - remove the `10 HP / 0 potions` deadlock
  - preserve the high-performing Flash-Lite policy
  - improve the Flash parity result from near-significant to significant
- This closes the Flash-Lite prompt stack for FixedDamage in a clean way.

## Tail Evidence
- The local bug really disappeared.
  - in Parity 3, Flash-Lite had `45` turns over `500` chars, including a `13,126`-char outlier at `10 HP / 0 potions`
  - in Exit 1, Flash-Lite had only `19` turns over `500` chars and the largest turn was `848` chars
- State-level length checks confirm the change in the target zone:
  - `10 HP / 0 potions`:
    - Parity 3 average `872` chars, max `13,126`
    - Exit 1 average `263` chars, max `358`
  - `20 HP / 3 potions`:
    - Parity 3 average `473` chars, max `1,635`
    - Exit 1 average `269` chars, max `436`
  - `20 HP / 1 potion`:
    - Parity 3 average `416` chars, max `2,168`
    - Exit 1 average `255` chars, max `452`

## Next Research Move
- Treat FixedDamage as closed.
- Carry `FlashLite-RC-TR-HP-exit` forward as the final Flash-Lite stack for this game.
- Move next to `VariableDamageGame`, where the key question becomes whether the strategy stack still helps under uncertainty instead of exact deterministic thresholds.
