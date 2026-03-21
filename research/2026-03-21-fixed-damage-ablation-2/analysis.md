# Analysis — FixedDamage Ablation 2

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: HP-threshold grounding without `ReasoningController` is not enough. `FlashLite-AO-HP` was swept `24-0` by plain Flash.
- Secondary finding: turn-time ActionOnly reinforcement plus HP-grounding recovered some of the missing behavior, but still lost `18-6`.
- Practical recommendation: keep `FlashLite-RC-TR-HP` as the best known Flash-Lite condition for FixedDamage. The cheap ActionOnly overlays are materially cheaper, but not competitive enough.
<!-- AUTO_FACTS:END -->

## Outcome Layer
- `Flash-AO` beat `FlashLite-AO-HP` `24-0` at `N=24`.
  - `p=1.19e-07`
  - effect size `1.571` (`large`)
- `Flash-AO` beat `FlashLite-AO-TR-HP` `18-6` at `N=24`.
  - `p=0.0227`
  - effect size `0.524` (`medium`)
- Seat read:
  - HP-only: `FlashLite-AO-HP` won `0/12` as first player and `0/12` as second
  - TR+HP: `FlashLite-AO-TR-HP` won `6/12` as first player and `0/12` as second
- So the reinforced ActionOnly variant improved only on the easier seat. It did not fix the second-player bottleneck at all.

## Behavioral Layer

### 1. HP-only collapsed into the wrong threshold
- `FlashLite-AO-HP` looked cheap, strict, and highly aggressive, but it was not survival-grounded.
  - `all_attack_match_rate`: `66.7%`
  - first potion median: `80 HP`
  - `never_used_rate`: `66.7%`
  - `unused_potions_on_loss_rate`: `87.5%`
  - `critical_potion_response_rate`: `0.082`
  - `error_recovery_rate`: `0.123`
- The state evidence explains why it lost every match:
  - at `80 HP / 3 potions`, second-player `FlashLite-AO-HP` still used `POTION` `5/12`
  - at `20 HP / 3 potions`, first-player `FlashLite-AO-HP` attacked `17/17`
  - at `20 HP / 1 potion`, second-player `FlashLite-AO-HP` attacked `4/5`
- That is not just “aggressive.” It is a broken threshold:
  - sometimes healing while healthy
  - often attacking when survival depends on healing

### 2. TR+HP recovered part of the policy, but not the hard part
- `FlashLite-AO-TR-HP` was a real improvement over HP-only.
  - `all_attack_match_rate`: `29.2%`
  - first potion median: `20 HP`
  - `position_policy_delta`: `0.079`
  - `critical_potion_response_rate`: `0.241`
  - `error_recovery_rate`: `0.392`
- The healthy-state correction improved:
  - at `80 HP / 3 potions`, second-player `FlashLite-AO-TR-HP` used `POTION` only `2/12`
  - HP-only had used `POTION` `5/12`
- But the critical-state threshold was still far too weak:
  - at `20 HP / 3 potions`, first-player `FlashLite-AO-TR-HP` split `7 ATTACK / 7 POTION`
  - at `20 HP / 3 potions`, second-player `FlashLite-AO-TR-HP` split `10 ATTACK / 5 POTION`
  - at `20 HP / 1 potion`, first-player `FlashLite-AO-TR-HP` attacked `9/9`
  - at `20 HP / 1 potion`, second-player `FlashLite-AO-TR-HP` attacked `6/8`
- So reinforcement kept the HP hint active enough to reduce the healthy-state bug, but it still did not make Flash-Lite reliably heal when the game hinged on it.

### 3. The full stack is still qualitatively different
- Compared with `FlashLite-RC-TR-HP` in Parity 3:
  - outcome: `31-17` win vs Flash instead of `18-6` loss
  - `all_attack_match_rate`: `10.4%` instead of `29.2%`
  - `unused_potions_on_loss_rate`: `35.3%` instead of `88.9%`
  - `critical_potion_response_rate`: `0.434` instead of `0.241`
  - `error_recovery_rate`: `0.563` instead of `0.392`
  - second-player wins: `10/24` instead of `0/12`
- State-level comparison makes the gap sharper:
  - full stack at `20 HP / 3 potions`: second-player `POTION` `18/26`
  - TR+HP at the same state: second-player `POTION` only `5/15`
  - full stack at `20 HP / 1 potion`: second-player `POTION` `17/19`
  - TR+HP at the same state: second-player `POTION` only `2/8`
- This is the key inference of the package:
  - `ReasoningController` is doing real decision-quality work
  - not just keeping the output format tidy

## Cost Layer
- Flash-Lite costs per player-match:
  - HP-only: `$0.000488`
  - TR+HP: `$0.000767`
  - full stack: `$0.002123`
- So:
  - HP-only is only about `23%` of the full-stack Flash-Lite cost
  - TR+HP is only about `36%` of the full-stack Flash-Lite cost
- But neither cheap ablation came close to the full-stack outcome or policy quality.
- The cost lesson is therefore not “remove RC.”
- It is:
  - `RC` is expensive
  - but in this task class, the cheap substitutes leave too much performance on the table

## Contract and Confounds
- Both Flash-Lite ablations were `100%` strict with `0` parse failures.
- `Flash-AO` remained fully parseable but stayed mildly non-strict:
  - `89.2%` strict in the HP-only cell
  - `89.9%` strict in the TR+HP cell
- That is the same kind of recoverable non-strictness seen in earlier Flash parity packages. It is a mild confound, but not enough to explain the size of the outcome gap here.

## What This Proves
- The HP survival hint is helpful only when paired with a stronger policy scaffold.
- Turn-time reinforcement helps preserve the hint.
- But neither HP-only nor TR+HP can substitute for the full reasoning stack in FixedDamage.
- The cheap-stack thesis did not survive this ablation:
  - cheaper prompting overlays alone are not enough
  - the strong Flash-Lite result still depends on `ReasoningController`

## Next Research Move
- Do not replace the full stack with either ActionOnly ablation.
- If cost reduction remains the goal, the next optimization should be a **cheaper reasoning contract**, not removing reasoning entirely.
- FixedDamage is now close to saturated on this question:
  - the best Flash-Lite stack is known
  - the cheapest plausible substitutes have been tested
  - and they do not recover enough of the policy quality to be viable replacements
