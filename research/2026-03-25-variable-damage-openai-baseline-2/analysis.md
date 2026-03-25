# VariableDamage OpenAI Baseline 2 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: the `15-9` GPT-5 Mini pilot did not survive expansion; `Flash-AO` edged the `N=48` cell `25-23` and the result stayed fully null
- Secondary finding: GPT-5 Mini still had the cleaner inventory-timing policy, but that policy edge did not convert into a larger win edge against Flash
- Practical recommendation: treat `Flash-AO` and `GPT5Mini-AO` as co-equal top-tier VariableDamage baselines and prefer Flash as the cheaper operational reference
<!-- AUTO_FACTS:END -->

## Status
- Complete single-cell VariableDamage baseline expansion with `48` matches.

## Question
- Does the pilot edge from `GPT5Mini-AO` over `Flash-AO` hold up at `N=48`, or are they effectively near-parity at the top of the current baseline graph?

## What This Package Is Designed To Answer
1. Whether the `15-9` pilot result from OpenAI Baseline 1 was early noise or the start of a real ordering.
2. Whether `GPT5Mini-AO`'s inventory-preservation advantage remains the main differentiator against Flash at larger `N`.
3. Whether future premium cross-provider work should treat `Flash-AO` or `GPT5Mini-AO` as the stronger top-tier baseline.

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
  - `unused_potions_on_loss_rate`
  - `high_roll_recovery_rate`

## Interpretation Guardrails
- This package is AO-only and single-cell.
- It should update the top of the baseline graph, not imply anything about controller usefulness.
- If the cell stays close, the behavioral split matters as much as the win count.

## Hypotheses
- `GPT5Mini-AO` should remain more inventory-efficient than `Flash-AO`.
- `Flash-AO` may still stay close enough on outcomes that the matchup remains functionally near-parity.
- The most informative metrics are likely to be first-lethal-entry inventory and second-player wins, not just raw aggression.

## Follow-On Rule
- If `GPT5Mini-AO` opens a clear edge, treat it as the current top VariableDamage baseline.
- If the cell stays null, treat both as top-tier baselines and prefer whichever is more useful for the next intervention question.

## Result
- `Flash-AO` beat `GPT5Mini-AO` `25-23` at `N=48`
- exact-binomial `p=0.8854`
- negligible effect
- first player won `37/48`
- `Flash-AO` won `19/24` as first player and `6/24` as second
- `GPT5Mini-AO` won `18/24` as first player and `5/24` as second

## Behavioral Read
- The pilot outcome reversed, but the policy differences stayed intact.
- `GPT5Mini-AO` remained the cleaner inventory-preservation policy:
  - first potion median `33.5 HP` vs `46.5 HP` for Flash
  - first lethal entry inventory median `2` vs `0`
  - first lethal entry `zero_potions_rate` `25.5%` vs `65.2%`
  - `safe_zone_potion_rate` `0.0` vs `10.2%`
  - `lethal_zone_potion_rate` `1.0` vs `0.739`
  - `unused_potions_on_loss_rate` `0.0` vs `0.043`
- `Flash-AO` remained the more pressure-oriented policy:
  - later first potion
  - much more healing in lower danger (`0.773` vs `0.488`)
  - slightly stronger conversion from both seats despite emptier lethal entry
- High-roll recovery and seat stability were close enough that they do not explain the outcome by themselves:
  - `high_roll_recovery_rate` `0.475` vs `0.442`
  - `position_policy_delta` `0.127` vs `0.160`

## Interpretation
- This package softens the earlier “GPT-5 Mini is above Flash” read.
- The stronger claim is now:
  - `Flash-AO` and `GPT5Mini-AO` are both top-tier VariableDamage baselines
  - `GPT5Mini-AO` is cleaner on inventory timing
  - `Flash-AO` is cheaper and still competitive enough to erase the pilot deficit at `N=48`
- That makes Flash the better practical reference baseline for future intervention work, even though GPT-5 Mini remains a very strong premium comparator.
