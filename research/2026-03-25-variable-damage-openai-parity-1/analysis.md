# VariableDamage OpenAI Parity 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `GPT5Mini-AO` beat `GPT4oMini-AO` `16-8` and `GPT4oMini-RC` `15-9`; both pilot cells stayed non-significant.
- Secondary finding: RC repaired `gpt-4o-mini`'s extreme early-heal / empty-at-lethal pattern, but over-corrected into under-healing danger states and leaving potions unused on losses.
- Practical recommendation: stop the RC-only OpenAI branch here; if `gpt-4o-mini` is revisited, it should be with a more targeted survival prompt rather than generic RC.
<!-- AUTO_FACTS:END -->

## Status
- Completed pilot-sized VariableDamage OpenAI parity package with `48` matches.

## Question
- Is plain `gpt-4o-mini` already close to plain `gpt-5-mini` in VariableDamage, and does RC-only improve or worsen that gap?

## What This Package Is Designed To Answer
1. How large the plain OpenAI mini gap is under VariableDamage uncertainty.
2. Whether `ReasoningController` alone improves `gpt-4o-mini` against the same `gpt-5-mini` opponent.
3. Whether any OpenAI controller branch is justified after baseline placement, or whether RC-only should be stopped immediately.

## Primary Readout
- Outcome:
  - `GPT5Mini-AO` beat `GPT4oMini-AO` `16-8` (`p=0.1516`, small effect)
  - `GPT5Mini-AO` beat `GPT4oMini-RC` `15-9` (`p=0.3075`, small effect)
  - `GPT4oMini-AO` went `6/12` as first player and `2/12` as second
  - `GPT4oMini-RC` went `6/12` as first player and `3/12` as second
- Behavior:
  - `GPT4oMini-AO` stayed extremely conservative:
    - first potion median `78 HP`
    - `safe_zone_potion_rate = 0.466`
    - first lethal entry median `0` potions left
    - `zero_potions_on_first_lethal_entry_rate = 1.0`
  - `GPT4oMini-RC` materially changed that policy:
    - first potion median `39 HP`
    - `safe_zone_potion_rate = 0.143`
    - first lethal entry median `1` potion left
    - `zero_potions_on_first_lethal_entry_rate = 0.375`
  - But RC also over-corrected:
    - `danger_zone_potion_rate` fell from `0.810` to `0.292`
    - `lethal_zone_potion_rate` reached only `0.581`
    - `unused_potions_on_loss_rate` rose from `0.0` to `0.40`
  - `GPT5Mini-AO` stayed cleaner in both cells:
    - `safe_zone_potion_rate` ~ `0.0`
    - `lethal_zone_potion_rate = 1.0`
    - first lethal entry median `1-2` potions left
    - `wins_as_second = 6/12` in both cells

## Interpretation Guardrails
- This package is intentionally limited to AO baseline plus RC-only.
- It should not be used to infer that heavier overlays would behave the same way.
- Any follow-up should be justified by the exported VariableDamage behavior, not by a generic “reasoning should help” prior.

## Interpretation
- The plain-model gap under VariableDamage is real but not enormous at pilot size: `8-16` is clearly behind, but much less catastrophic than the old FixedDamage RC collapse.
- RC did not create a clean outcome improvement. It only moved `gpt-4o-mini` from `8-16` to `9-15`.
- The mechanism read is mixed:
  - RC fixed the obvious over-conservatism
  - but then pushed the model too far toward late healing and attack-through-risk play
- That makes this package a direct counter-example to the idea that generic reasoning scaffolding should help by default. Here it reorganized the policy, but not into the shape that beats `gpt-5-mini`.
- The stronger model remained better calibrated:
  - it almost never healed in the safe zone
  - it always healed in the lethal zone
  - it kept more potions in reserve for the true endgame
  - it converted second-player starts much better than either `gpt-4o-mini` variant

## Follow-On Rule
- Stop the RC-only branch here.
- Do not spend the next package on `N=48` expansion for this exact AO/RC ladder.
- If `gpt-4o-mini` is revisited in VariableDamage, it should be with a narrow survival/risk instruction that targets the residual danger-zone calibration problem directly, not with a generic “reason more” controller.
