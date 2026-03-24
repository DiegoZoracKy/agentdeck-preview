# VariableDamage Baseline 3 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `Flash-AO` and `Haiku-AO` are the two strong plain VariableDamage baselines; `Mini-AO` is clearly weaker against both.
- Secondary finding: `Flash-AO` vs `Haiku-AO` was effectively a draw (`26-22`, `p=0.665`), while both outperformed `Mini-AO`.
- Practical recommendation: treat `Flash-AO` as the default plain-model reference baseline, keep `Haiku-AO` as the closest comparison baseline, and stop any Mini/Haiku controller branch until a sharper failure mode appears.
<!-- AUTO_FACTS:END -->

## Status
- Completed stronger-model AO round-robin with `144` decisive matches.

## Question
- How do plain Flash, plain GPT-4o Mini, and plain Claude Haiku compare head-to-head in VariableDamage before any controller or prompt-stack intervention?

## What This Package Is Designed To Answer
1. Whether Mini's extremely conservative VariableDamage policy holds up against stronger plain-model opponents.
2. Whether Haiku's strong VariableDamage baseline remains strong when measured directly against Flash and Mini rather than only against Flash-Lite.
3. What the actual plain-model ordering is among the stronger VariableDamage baselines.
4. Whether any stronger plain model shows a coherent enough policy failure to justify an RC branch before any transfer work.

## Primary Readout
- Outcome:
  - decisive win rate
  - exact-binomial significance
  - first-player win rate
  - position-controlled split
- Behavior:
  - `safe_zone_potion_rate`
  - `lethal_zone_potion_rate`
  - `danger_zone_potion_rate`
  - `lower_danger_zone_potion_rate`
  - `upper_danger_zone_potion_rate`
  - `risk_band_potion_rate_by_scarcity`
  - `first_lethal_entry_inventory`
  - `unused_potions_on_loss_rate`
  - `high_roll_recovery_rate`

## Interpretation Guardrails
- This package is AO-only.
- It must not be used to infer that a stronger model needs controller work just because it loses one matchup.
- The main question is plain-model ordering plus legible policy differences, not intervention design.

## Hypotheses
- `Flash-AO` should be a tougher plain-model opponent than `FlashLite-AO`, so Mini and Haiku may lose more ground here than they did in the FlashLite-centered sweep.
- `Mini-AO` should still look the most conservative in the safe and danger bands.
- `Haiku-AO` should remain the most balanced plain model under uncertainty unless its earlier strength was mostly opponent-specific.
- The most important discriminator may be second-player conversion rather than raw first-player win rate, because VariableDamage still has a seat effect but not a deterministic one.

## Follow-On Rule
- If Haiku remains clearly strongest and behaviorally healthy, no Haiku RC branch is justified.
- If Mini remains coherent but overconservative even against stronger plain baselines, Mini can stay the only plausible stronger-model RC candidate.
- If Flash outperforms both, the Flash baseline becomes the practical reference point for future VariableDamage intervention work because it combines strong outcomes with the more pressure-oriented policy we are most likely to challenge with intervention.

## Result
- `Flash-AO` beat `Mini-AO` `34-14` (`p=0.0055`, small effect)
- `Flash-AO` beat `Haiku-AO` `26-22` (`p=0.665`, negligible)
- `Haiku-AO` beat `Mini-AO` `31-17` (`p=0.059`, small directional edge but not formally significant)

## Interpretation
- The stronger plain-model ordering is now legible:
  - `Flash-AO` is the best practical baseline
  - `Haiku-AO` is close enough to Flash to count as near-parity
  - `Mini-AO` is the clear laggard under uncertainty
- `Mini-AO`'s core weakness is not chaos. It is coherent overconservatism.
  - vs `Flash-AO`: first potion median `81 HP`, safe-zone potion rate `44.9%`, danger-zone potion rate `100%`, zero-potions on first lethal entry `100%`
  - vs `Haiku-AO`: first potion median `80 HP`, safe-zone potion rate `34.2%`, danger-zone potion rate `100%`, zero-potions on first lethal entry `100%`
  - In plain terms: Mini spends its inventory early and arrives at critical states already empty.
- `Flash-AO` and `Haiku-AO` solve that problem differently:
  - `Flash-AO` is later and more pressure-oriented
    - vs `Mini-AO`: first potion median `57 HP`, safe-zone potion rate `13.8%`, second-player win rate `50.0%`
  - `Haiku-AO` is earlier and safer, but still strong
    - vs `Flash-AO`: first potion median `72.5 HP`, lethal-zone potion rate `100%`, second-player win rate `37.5%`
    - vs `Mini-AO`: first potion median `72 HP`, safe-zone potion rate `17.9%`, second-player win rate `50.0%`
- The most important comparative result is not raw aggression. It is resource timing:
  - `Mini-AO` reaches lethal states with `0` potions almost every time
  - `Flash-AO` and `Haiku-AO` retain more optionality into the dangerous endgame

## Operational Note
- `p1_c01_mini_ao_vs_flash_ao` required segmented execution because `Flash-AO` twice hung after a Vertex `429` retry.
- The canonical cell artifact was rebuilt from exact-seed segments and excludes the incomplete partial match file.
- This changed execution logistics, not the game/policy contract.
