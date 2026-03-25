# VariableDamage OpenAI Parity 2 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `GPT4o-AO` and `GPT4o-RC` both edged `GPT5Mini-AO` `13-11`; neither cell was significant and RC created no outcome gain at all.
- Secondary finding: RC made `gpt-4o` somewhat cleaner on safe-zone healing, first lethal-entry inventory, and seat-conditioned policy spread, but those improvements were modest and came with a major cost increase.
- Practical recommendation: stop the RC branch here; if premium OpenAI baselines matter in VariableDamage, plain `gpt-4o AO` is already the useful comparison and RC is not worth the extra spend.
<!-- AUTO_FACTS:END -->

## Status
- Completed pilot-sized VariableDamage premium OpenAI parity package with `48` matches.

## Question
- Is premium `gpt-4o` already competitive with plain `gpt-5-mini` in VariableDamage, and does RC-only improve or worsen that comparison?

## What This Package Is Designed To Answer
1. How large the plain premium OpenAI gap is under VariableDamage uncertainty.
2. Whether `ReasoningController` alone improves `gpt-4o` against the same `gpt-5-mini` opponent.
3. Whether any premium OpenAI RC branch is justified, or whether plain capability already tells the more useful story.

## Primary Readout
- Outcome:
  - `GPT4o-AO` beat `GPT5Mini-AO` `13-11` (`p=0.8388`, negligible effect)
  - `GPT4o-RC` beat `GPT5Mini-AO` `13-11` (`p=0.8388`, negligible effect)
  - `GPT4o-AO` went `10/12` as first player and `3/12` as second
  - `GPT4o-RC` went `10/12` as first player and `3/12` as second
- Behavior:
  - `GPT4o-AO` was already a serious baseline:
    - first potion median `41 HP`
    - `safe_zone_potion_rate = 0.116`
    - `danger_zone_potion_rate = 0.545`
    - `lethal_zone_potion_rate = 1.0`
    - first lethal entry median `0` potions left
    - first lethal-entry `zero_potions_rate = 0.727`
  - `GPT4o-RC` cleaned some of that up:
    - first potion median `42.5 HP`
    - `safe_zone_potion_rate = 0.066`
    - `danger_zone_potion_rate = 0.448`
    - `lethal_zone_potion_rate = 1.0`
    - first lethal entry median `0` potions left
    - first lethal-entry `zero_potions_rate = 0.565`
    - `position_policy_delta` improved from `0.182` to `0.044`
  - `GPT5Mini-AO` stayed cleaner in both cells:
    - first potion median `33.0` / `32.5 HP`
    - `safe_zone_potion_rate = 0.012` / `0.0`
    - first lethal entry median `2` potions left in both cells
    - first lethal-entry `zero_potions_rate = 0.174` / `0.250`
    - lethal-zone healing stayed `1.0`
  - Cost:
    - AO cell total cost: `$0.7403`
    - RC cell total cost: `$1.0957`
    - RC raised cell cost by about `48%` without changing the scoreline

## Interpretation Guardrails
- This package is intentionally limited to AO baseline plus RC-only.
- It should not be used to infer that heavier overlays would behave the same way.
- Any follow-up should be justified by the exported VariableDamage behavior and the premium cost burden, not by a generic “larger model plus reasoning should win” prior.

## Interpretation
- This package did not reproduce the `gpt-4o-mini` story. Premium `gpt-4o` was already competitive with `gpt-5-mini` at pilot size before any controller overlay.
- RC did not improve wins, second-player conversion, or the aggregate outcome in any visible way. The scoreboard was identical.
- The main RC effect was policy cleanup:
  - less safe-zone healing
  - less empty-at-lethal entry
  - less seat-conditioned policy drift
- But the cleanup was modest, not transformative. `GPT4o-RC` still reached first lethal states with median `0` potions left, and `GPT5Mini-AO` still preserved more real endgame inventory.
- So the practical business read is simple:
  - if you want a premium OpenAI VariableDamage baseline, `GPT4o-AO` is already a fair comparison to `GPT5Mini-AO`
  - adding RC increases cost substantially without creating measurable benefit

## Follow-On Rule
- Stop the RC branch here.
- Do not spend the next package on expanding this exact AO/RC premium ladder.
- If premium OpenAI work continues in VariableDamage, use plain `gpt-4o AO` as the relevant baseline and spend the next research package on a genuinely open question instead.
