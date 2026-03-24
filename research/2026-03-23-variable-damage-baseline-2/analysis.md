# VariableDamage Baseline 2 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: plain Claude Haiku was decisively stronger than plain Flash-Lite in VariableDamage, `38-10` at `N=48`, while plain GPT-4o Mini only beat Flash-Lite directionally, `30-18`.
- Secondary finding: Mini and Haiku were both far more willing than Flash-Lite to spend potions in risky bands, but Mini did so with a much more conservative high-HP policy than Haiku.
- Practical recommendation: no Haiku RC branch is warranted; Mini is the only plausible RC-only candidate from this sweep, while the main line can still move next to Flash-Lite transfer testing.
<!-- AUTO_FACTS:END -->

## Status
- Complete cross-provider AO baseline sweep with `96` recorded matches and clean behavioral export.

## Question
- How do plain GPT-4o Mini and plain Claude Haiku compare to plain Flash-Lite in VariableDamage before any controller intervention?

## What This Package Answered
1. Plain `gpt-4o-mini` does not look weak in VariableDamage. It beat plain Flash-Lite directionally and did so with a stable, conservative policy.
2. Plain Claude Haiku no longer looks pathologically inverted under uncertainty. It was simply strong, well-calibrated, and robust across seats.
3. Flash-Lite's AO failure transferred cleanly across both matchups: it still under-healed in danger and lethal bands, then lost with potions unused.

## Primary Readout
- Outcome:
  - decisive win rate
  - exact-binomial significance
  - first-player win rate
  - position-controlled split
- Behavior:
  - `first_potion_profile`
  - `unused_potions_on_loss_rate`
  - `state_action_consistency`
  - `position_policy_delta`
  - `lethal_zone_potion_rate`
  - `danger_zone_potion_rate`
  - `risk_band_policy_delta`
  - `high_roll_recovery_rate`

## Interpretation Guardrails
- This package is baseline only.
- It must not be used to claim that RC helps Mini or Haiku; it only decides whether RC is worth testing next.
- The key question is not just who wins. It is whether the losing or unstable policy is coherent enough to target with a simple reasoning intervention.
- If a model is already strong and behaviorally calibrated in the lethal and danger bands, it should not automatically get an RC branch just because it lost a cross-provider matchup.

## Results
- `FlashLite-AO` vs `Mini-AO`
  - `30-18` for `Mini-AO`
  - exact-binomial `p=0.111`, small effect
  - first-player wins: `36/48`
  - average turns: `18.58`
  - total cell cost: `$0.0638`
  - reading: Mini beat Flash-Lite directionally, but the stronger finding is behavioral rather than inferential
- `FlashLite-AO` vs `Haiku-AO`
  - `38-10` for `Haiku-AO`
  - exact-binomial `p=6.17e-05`, medium effect
  - first-player wins: `28/48`
  - average turns: `20.13`
  - total cell cost: `$0.3641`
  - reading: Haiku was materially stronger than Flash-Lite and no longer dependent on a heavy seat bias

## Behavioral Readout
- The sweep exported cleanly in both cells with `100%` strict contract rate and `0` parse failures.
- Flash-Lite showed the same core VariableDamage weakness against both opponents:
  - vs `Mini-AO`
    - first potion median: `14 HP`
    - danger-zone potion rate: `6.8%`
    - lethal-zone potion rate: `40.2%`
    - unused-potion losses: `100%`
    - all-attack matches: `27.1%`
  - vs `Haiku-AO`
    - first potion median: `19 HP`
    - danger-zone potion rate: `9.6%`
    - lethal-zone potion rate: `37.8%`
    - unused-potion losses: `100%`
    - all-attack matches: `12.5%`
- Mini's policy was coherent but very conservative:
  - first potion median: `79 HP`
  - danger-zone potion rate: `96.8%`
  - no all-attack matches
  - zero losses with unused potions
- Haiku's policy looked stronger and better calibrated than Mini's:
  - first potion median: `72 HP`
  - danger-zone potion rate: `66.9%`
  - lethal-zone potion rate: `100%`
  - wins as second player: `17/24`
  - zero losses with unused potions

## Follow-On Rule
- Haiku does not justify an RC-only follow-up from this baseline.
- Mini is the only plausible RC candidate because its policy is stable and overconservative rather than noisy.
- If the main VariableDamage line remains focused on weaker-model equalization rather than Mini optimization, `VariableDamage Transfer 1` is still the better immediate next package.
