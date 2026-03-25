# VariableDamage Threshold 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: the risk-grounded prompt moved Flash-Lite from an `8-16` loss to a `12-12` tie against plain Flash at `N=24`
- Secondary finding: the mechanism shift was large and clean, especially on first-lethal-entry inventory, safe-zone suppression, and seat stability
- Practical recommendation: keep the risk-grounded prompt as the live Flash-Lite VariableDamage line and stop plain RC-only branching here
<!-- AUTO_FACTS:END -->

## Status
- Complete pilot-sized VariableDamage prompt-layer package with `48` matches.

## Question
- Can a risk-band-aware HP instruction improve Flash-Lite RC against plain Flash by reducing empty-at-lethal entries and seat-conditioned threshold errors?

## What This Package Is Designed To Answer
1. Whether the Flash-Lite RC control arm reproduces the same lower-danger / lethal inventory problem on a fresh seed family.
2. Whether an explicit VariableDamage risk instruction improves first-lethal-entry inventory, second-player conversion, and lower-danger healing.
3. Whether the Flash-Lite line should expand to a larger parity package or stop after the prompt layer.

## Primary Readout
- Outcome:
  - decisive win rate
  - exact-binomial significance
  - first-player win rate
  - position-controlled split
- Behavior:
  - `first_lethal_entry_inventory`
  - `safe_zone_potion_rate`
  - `lower_danger_zone_potion_rate`
  - `upper_danger_zone_potion_rate`
  - `lethal_zone_potion_rate`
  - `risk_band_potion_rate_by_scarcity`
  - `unused_potions_on_loss_rate`
  - `position_policy_delta`

## Interpretation Guardrails
- This package is RC baseline plus one prompt-layer treatment only.
- It should not be used to infer anything about broader transfer or multi-layer stacks.
- The main question is whether the treatment fixes the specific VariableDamage resource-timing failure, not whether any extra instruction always helps.

## Hypotheses
- `FlashLite-RC` should again lose to plain Flash but remain much better than the old AO baseline.
- `FlashLite-RC-RISK` should:
  - reduce `safe_zone_potion_rate`
  - raise lower-danger and lethal healing
  - reduce first-lethal-entry `zero_potions_rate`
  - improve second-player wins
- A failure mode worth watching is over-correction:
  - the treatment could suppress safe healing
  - but also push Flash-Lite back toward attacking too late or too rigidly

## Follow-On Rule
- If the risk instruction improves both behavior and competitiveness, expand that line.
- If it improves behavior but not outcome, keep the result as a mechanism finding and stop before more VariableDamage prompt branching.
- If it degrades either inventory timing or safe/lower-danger calibration, stop the Flash-Lite prompt branch here.

## Result
- Control cell:
  - `Flash-AO` beat `FlashLite-RC` `16-8` at `N=24`
  - exact-binomial `p=0.1516`
  - small effect
- Treatment cell:
  - `FlashLite-RC-RISK` tied `Flash-AO` `12-12` at `N=24`
  - exact-binomial `p=1.0`
  - negligible effect

## Behavioral Read
- The treatment fixed the exact failure mode we targeted.
- Against the RC control, `FlashLite-RC-RISK`:
  - moved first potion earlier from median `55.5 HP` to `41 HP`
  - improved first-lethal-entry inventory from median `0` to `1`
  - cut first-lethal-entry `zero_potions_rate` from `58.3%` to `26.1%`
  - eliminated safe-zone healing (`23.0% -> 0.0%`)
  - raised lower-danger healing sharply (`22.2% -> 74.5%`)
  - raised lethal-zone healing to `100%` (`76.7% -> 100%`)
  - improved high-roll recovery (`0.343 -> 0.479`)
  - eliminated unused-potion losses (`18.8% -> 0.0%`)
  - collapsed seat-conditioned policy spread (`position_policy_delta 0.333 -> 0.051`)
- The outcome moved in the same direction:
  - `FlashLite-RC` won `2/12` as second player
  - `FlashLite-RC-RISK` won `4/12` as second player

## Interpretation
- This is the strongest VariableDamage Flash-Lite result so far.
- `RC` alone repaired the old under-healing collapse but left Flash-Lite too empty when entering lethal states.
- The risk-grounded prompt corrected that inventory-timing problem without reintroducing the old all-attack failure.
- The remaining limit is cost and efficiency rather than obvious tactical failure:
  - treatment average match cost rose to about `$0.005419`
  - control average match cost was about `$0.003833`

## Recommendation
- Treat `FlashLite-RC-RISK` as the current best Flash-Lite VariableDamage condition.
- If the line continues, expand this treatment rather than revisiting plain RC or turn reinforcement.
