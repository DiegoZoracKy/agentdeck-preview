# VariableDamage OpenAI Baseline 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `GPT5Mini-AO` landed above all three current VariableDamage baselines directionally, but none of the `N=24` pilot cells reached significance.
- Secondary finding: the more important separation was behavioral: `GPT5Mini-AO` avoided safe-zone healing, preserved inventory into lethal states, and still held `lethal_zone_potion_rate = 1.0` in every cell.
- Practical recommendation: treat `GPT5Mini-AO` as a top-tier VariableDamage baseline, do not infer an OpenAI RC branch from this package alone, and expand `GPT5Mini-AO vs Flash-AO` first if one follow-up cell is warranted.
<!-- AUTO_FACTS:END -->

## Status
- Completed pilot-sized VariableDamage OpenAI baseline package with `72` decisive matches.

## Question
- Where does plain `GPT5Mini-AO` land relative to the existing `Flash-AO`, `Haiku-AO`, and `Mini-AO` VariableDamage baselines?

## What This Package Is Designed To Answer
1. Whether plain `gpt-5-mini` is materially stronger than the current best VariableDamage baselines (`Flash-AO` and `Haiku-AO`) or only near-parity with them.
2. Whether the plain OpenAI gap under uncertainty (`GPT5Mini-AO` vs `Mini-AO`) is large enough to justify any VariableDamage OpenAI controller branch at all.
3. Whether the new VariableDamage metrics make `gpt-5-mini`'s style legible at pilot size without immediately paying for full `N=48` package expansion.

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
  - `lethal_zone_potion_rate`
  - `risk_band_potion_rate_by_scarcity`
  - `first_lethal_entry_inventory`
  - `unused_potions_on_loss_rate`
  - `high_roll_recovery_rate`

## Interpretation Guardrails
- This package is AO-only.
- It should place `gpt-5-mini` into the VariableDamage baseline graph, not imply that RC should help `gpt-4o-mini` by default.
- Any OpenAI controller follow-up should be justified by specific behavior in these exports, not by a generic “reasoning models are better” prior.

## Hypotheses
- `GPT5Mini-AO` should at least beat `Mini-AO` cleanly if the VariableDamage OpenAI gap resembles the FixedDamage ladder at all.
- `Flash-AO` and `Haiku-AO` are strong enough that one or both cells may come back near-parity at pilot size.
- The most informative differences are likely to show up in resource timing and first lethal-entry inventory, not in raw aggression alone.

## Follow-On Rule
- If a cell is clearly separated on both outcome and behavior at `N=24`, stop there.
- If a cell comes back near-parity or behaviorally novel, expand only that cell to `N=48`.
- Only consider `GPT4oMini-RC` after the plain `GPT5Mini-AO` placement is known.

## Result
- `GPT5Mini-AO` beat `Flash-AO` `15-9` (`p=0.307`, small directional edge)
- `GPT5Mini-AO` beat `Haiku-AO` `14-10` (`p=0.541`, negligible)
- `GPT5Mini-AO` beat `Mini-AO` `14-10` (`p=0.541`, negligible)

## Interpretation
- The pilot does **not** show `gpt-5-mini` opening a dominant new VariableDamage tier. At `N=24`, it was directionally ahead of every current baseline, but only by modest margins.
- What *does* look clearly different is policy shape:
  - vs `Flash-AO`, `GPT5Mini-AO` was more inventory-efficient
    - first potion median `36 HP` vs `43 HP`
    - first lethal-entry median `2` potions vs `0`
    - zero-potions on first lethal entry `13.0%` vs `61.9%`
    - second-player wins `4/12` vs `1/12`
  - vs `Haiku-AO`, `GPT5Mini-AO` was much less conservative early while staying perfectly safe in lethal states
    - safe-zone potion rate `0.0%` vs `23.8%`
    - first potion median `36 HP` vs `72.5 HP`
    - first lethal-entry median `2` potions vs `0`
    - zero-potions on first lethal entry `25.0%` vs `91.7%`
  - vs `Mini-AO`, `GPT5Mini-AO` was both cleaner and more position-stable
    - safe-zone potion rate `0.0%` vs `33.3%`
    - upper-danger potion rate `9.8%` vs `64.7%`
    - first lethal-entry median `2` potions vs `0`
    - zero-potions on first lethal entry `21.7%` vs `95.8%`
    - position-policy delta `0.0` vs `0.333`
- The through-line is consistent across all three cells:
  - `GPT5Mini-AO` spends almost nothing in the safe zone
  - heals perfectly in the lethal zone
  - and carries more optionality into dangerous endgames than the current baselines
- That is a cleaner read of `gpt-5-mini` under uncertainty than the FixedDamage ladder gave us. It looks like a strong, efficient VariableDamage baseline, but not one that obviously makes the rest of the field irrelevant.

## Operational Note
- Phase P1 was launched as three parallel direct cell runs using the repo `.env` plus `VERTEX_LOCATION=global`.
- All three cells completed in single canonical sessions:
  - `p1_c01_gpt5mini_ao_vs_flash_ao/session_20260325_091223_3e12c7`
  - `p1_c02_gpt5mini_ao_vs_haiku_ao/session_20260325_091223_6cc584`
  - `p1_c03_gpt5mini_ao_vs_mini_ao/session_20260325_091223_9a846a`
- `GPT5Mini-AO` incurred repeated long-latency OpenAI turns, including several ~`600s` outliers and shorter `30-170s` spikes.
- Those delays increased wall-clock runtime materially but did not produce parse failures, incomplete matches, or segmented-recovery needs.
