# VariableDamage Premium Final 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `GPT5Mini-AO` beat `FlashLite-RC-RISK` `13-11`, but the premium pilot stayed non-significant (`p=0.8388`, negligible effect).
- Secondary finding: the carried-forward Flash-Lite policy remained clean under premium pressure: `1.3%` safe-zone healing, `100%` lethal-zone healing, `0.0%` unused-potion losses, and `0.0` position-policy delta.
- Practical recommendation: stop the main VariableDamage experiment line here and move fully to synthesis; the final premium pilot is informative without justifying another tuning branch.
<!-- AUTO_FACTS:END -->

## Status
- Completed single-cell VariableDamage premium pilot with `24` matches.

## Question
- Can `FlashLite-RC-RISK` stay respectable against plain `GPT5Mini-AO`, or does the premium clean-policy baseline reopen a clear gap?

## What This Package Is Designed To Answer
1. Whether the carried-forward Flash-Lite treatment remains behaviorally clean against a premium baseline.
2. Whether the current remaining weakness, one-potion danger timing, is enough to create a clear premium gap.
3. Whether the VariableDamage main arc is ready to stop after this package and switch fully to synthesis.

## Primary Readout
- Outcome:
  - `GPT5Mini-AO` beat `FlashLite-RC-RISK` `13-11`
  - exact-binomial `p=0.8388`
  - effect size `h=-0.083`, negligible
  - first-player advantage stayed large overall (`19/24` first-player wins)
  - second-player wins were rare for both:
    - `FlashLite-RC-RISK`: `2/12`
    - `GPT5Mini-AO`: `3/12`
- Behavior:
  - `FlashLite-RC-RISK` stayed disciplined:
    - `safe_zone_potion_rate = 1.27%`
    - `danger_zone_potion_rate = 41.7%`
    - `lower_danger_zone_potion_rate = 65.4%`
    - `upper_danger_zone_potion_rate = 25.3%`
    - `lethal_zone_potion_rate = 100%`
    - first potion median `41.5 HP`
    - first lethal-entry median `1` potion left
    - first lethal-entry `zero_potions_rate = 34.8%`
    - `unused_potions_on_loss_rate = 0.0%`
    - `position_policy_delta = 0.0`
  - `GPT5Mini-AO` remained cleaner in the endgame:
    - `safe_zone_potion_rate = 1.32%`
    - `danger_zone_potion_rate = 30.4%`
    - `lower_danger_zone_potion_rate = 50.0%`
    - `upper_danger_zone_potion_rate = 11.6%`
    - `lethal_zone_potion_rate = 100%`
    - first potion median `39.0 HP`
    - first lethal-entry median `1` potion left
    - first lethal-entry `zero_potions_rate = 12.5%`
    - `unused_potions_on_loss_rate = 0.0%`
    - `position_policy_delta = 0.138`
  - Cost:
    - `FlashLite-RC-RISK`: `$0.0737` total, about `$0.00307` per player-match
    - `GPT5Mini-AO`: `$0.2344` total, about `$0.00977` per player-match
    - premium pilot total: `$0.3082`

## Interpretation Guardrails
- This is a ceiling check, not a new intervention branch.
- A close loss or null is still a successful final package if the carried-forward policy remains clean.
- The relevant comparison point is `VariableDamage Parity 1`, not the older RC-only or TR cells.

## Follow-On Rule
## Interpretation
- This package did what the final main-arc pilot needed to do.
- It did not show Flash-Lite overtaking the premium baseline, but it also did not show the treatment collapsing back into the old failure modes.
- The remaining difference is narrower than it was in earlier VariableDamage packages:
  - both models avoided safe-zone waste
  - both healed perfectly in lethal states
  - both avoided dying with unused potions
  - the premium edge came mostly from cleaner first-lethal inventory timing and more selective danger-zone healing
- The key contrast is now very specific:
  - `FlashLite-RC-RISK` still heals too often in danger when multiple potions remain and still arrives at first lethal empty too often
  - `GPT5Mini-AO` reaches similar outcomes with less danger-zone healing and much better preserved inventory
- That is a strong stopping signal. The main AgentDeck story is already proven:
  - the weak model was diagnosable
  - the intervention sequence improved it materially
  - the carried-forward condition remained respectable against both the practical baseline and the premium baseline

## Follow-On Rule
- Stop the main VariableDamage experiment line here.
- Move to synthesis:
  - `VariableDamage Arc 1`
  - cross-game comparison
  - release-facing `v0.1.0` docs
