# VariableDamage Reinforcement 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: turn reinforcement did not improve Flash-Lite's VariableDamage outcome against plain Flash; both RC and RC-TR lost 10-14.
- Secondary finding: TR slightly improved lethal-state discipline and second-player wins, but worsened overall seat-conditioned policy spread.
- Practical recommendation: keep RC as the meaningful repair, but do not continue the TR branch; move to a targeted instruction layer if this line continues.
<!-- AUTO_FACTS:END -->

## Status
- Complete package with `48/48` scheduled matches finished and exported.

## Question
- Does turn-time instruction reinforcement on top of Flash-Lite reasoning stabilize the repaired VariableDamage policy enough to perform better against plain Flash?

## What This Package Is Designed To Answer
1. Whether the Flash-Lite RC gain from `VariableDamage Controller 1` remains legible against a stronger plain-model opponent on a fresh seed family.
2. Whether turn reinforcement reduces the new RC failure mode in VariableDamage:
   - safe-zone over-healing
   - wide spread in danger-zone thresholds
   - higher seat-conditioned risk-band drift
3. Whether reinforcement improves second-player conversion without reopening the old under-healing/resource-waste problem.

## Result
- `FlashLite-RC` vs `Flash-AO`: `10-14`, exact-binomial `p=0.541`, negligible effect.
- `FlashLite-RC-TR` vs `Flash-AO`: `10-14`, exact-binomial `p=0.541`, negligible effect.
- Both conditions were still materially better than the old `FlashLite-AO` baseline from `VariableDamage Release 1` (`5-19`), so the RC repair held.
- But TR did not close more ground against Flash than RC alone.

## Behavioral Readout
- `FlashLite-RC` remained the more aggressive-but-repaired condition:
  - first potion median `40 HP`
  - `danger_zone_potion_rate = 37.5%`
  - `lethal_zone_potion_rate = 75.0%`
  - `unused_potions_on_loss_rate = 21.4%`
  - second-player wins `1/12`
- `FlashLite-RC-TR` shifted that policy:
  - first potion median `49 HP`
  - `danger_zone_potion_rate = 33.3%`
  - `lethal_zone_potion_rate = 82.1%`
  - `unused_potions_on_loss_rate = 21.4%`
  - second-player wins `3/12`
- The useful gains from TR were:
  - slightly less safe-zone healing (`21.5% -> 19.0%`)
  - better lethal-zone healing (`75.0% -> 82.1%`)
  - better high-roll recovery (`0.394 -> 0.420`)
  - lower zero-potion first lethal entry rate (`58.3% -> 41.7%`)
- The important regressions were:
  - weaker first-player conversion (`9/12 -> 7/12`)
  - worse `position_policy_delta` (`0.333 -> 0.750`)
  - slightly weaker danger-zone healing (`37.5% -> 33.3%`)
- That combination explains the null outcome: TR made the policy more conservative in some useful low-HP places, but not in a way that translated into a stronger overall matchup against Flash.

## Interpretation Guardrails
- This package is reinforcement-on-top-of-RC only.
- It must not be used to claim that any guided HP instruction helps in VariableDamage; that is a later layer.
- The main question is not just whether `FlashLite-RC-TR` wins more matches. It is whether it becomes behaviorally better calibrated than `FlashLite-RC`.

## Primary Readout
- Outcome:
  - decisive win rate
  - exact-binomial significance
  - first-player win rate
  - position-controlled split
- Behavior:
  - `safe_zone_potion_rate`
  - `danger_zone_potion_rate`
  - `lower_danger_zone_potion_rate`
  - `upper_danger_zone_potion_rate`
  - `risk_band_potion_rate_by_scarcity`
  - `first_lethal_entry_inventory`
  - `unused_potions_on_loss_rate`
  - `risk_band_policy_delta`
  - `high_roll_recovery_rate`

## Hypotheses
- `FlashLite-RC` should still look materially better than `FlashLite-AO`, but may remain unstable in the safer and mid-risk bands.
- `FlashLite-RC-TR` should reduce `risk_band_policy_delta` relative to `FlashLite-RC`.
- If TR works in VariableDamage the same way it helped in FixedDamage, the cleanest gain should be:
  - less safe-zone healing
  - tighter lower-vs-upper danger separation
  - better last-potion behavior
  - stronger second-player win rate
- A failure mode worth watching is overcorrection:
  - reinforcement could suppress wasteful safe healing
  - but also push Flash-Lite back toward the old "heal too late" behavior

## Follow-On Rule
- TR was null on outcome and mixed on behavior.
- So the next move should not be more cadence work.
- If the Flash-Lite VariableDamage line continues, it should continue with a targeted instruction layer aimed at the remaining seat-conditioned threshold problem rather than another prompt-cadence variant.
