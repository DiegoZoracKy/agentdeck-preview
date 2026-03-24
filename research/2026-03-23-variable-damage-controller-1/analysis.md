# VariableDamage Controller 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `FlashLite-RC` beat `FlashLite-AO` `17-7` in VariableDamage and showed a strong behavioral repair, but the pilot stopped just short of significance at `p=0.0639`.
- Secondary finding: `Mini-RC` only edged `Mini-AO` `13-11` and mostly traded Mini's conservative stability for a more aggressive but not clearly better policy.
- Practical recommendation: continue the VariableDamage intervention line with Flash-Lite, not Mini.
<!-- AUTO_FACTS:END -->

## Status
- Complete controller-intervention pilot with `48` recorded matches and clean behavioral export.

## Question
- Does requiring explicit reasoning improve VariableDamage decision quality for Flash-Lite or GPT-4o Mini relative to plain ActionOnly output?

## What This Package Answered
1. RC materially repaired Flash-Lite's under-healing in VariableDamage and made it competitively viable against its own AO baseline.
2. RC made Mini less conservative, but not in a clearly better way. The outcome stayed near-null and Mini lost one of its strongest baseline virtues: not dying with resources unused.
3. Flash-Lite is the only model from this package that clearly earned a next-stage VariableDamage follow-up.

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
- This package is controller-only.
- It must not be used to claim that turn reinforcement or guided prompts help in VariableDamage; it only decides whether RC alone is useful first.
- The key question is whether the AO failure is coherent enough that explicit reasoning actually improves the policy rather than just adding cost and latency.

## Results
- `FlashLite-AO` vs `FlashLite-RC`
  - `17-7` for `FlashLite-RC`
  - exact-binomial `p=0.0639`, small effect
  - first-player wins: `19/24`
  - average turns: `18.46`
  - total cell cost: `$0.0414`
  - reading: strong directional controller win with a legible behavioral repair, but still pilot-scale
- `Mini-AO` vs `Mini-RC`
  - `13-11` for `Mini-RC`
  - exact-binomial `p=0.8388`, negligible effect
  - first-player wins: `17/24`
  - average turns: `21.13`
  - total cell cost: `$0.0720`
  - reading: RC changed the policy, but not into a clearly better one

## Behavioral Readout
- Both cells exported cleanly with `100%` strict contract rate and `0` parse failures.
- `FlashLite-RC` repaired the exact VariableDamage risk-band failure we cared about:
  - first potion median: `46 HP` vs `16 HP` for `FlashLite-AO`
  - danger-zone potion rate: `36.1%` vs `8.7%`
  - lethal-zone potion rate: `90.0%` vs `34.8%`
  - unused-potion losses: `0%` vs `94.1%`
  - high-roll recovery: `37.5%` vs `29.4%`
  - wins as second player: `5/12` vs `0/12`
- The tradeoff for Flash-Lite is that RC did not become simply “better calibrated.” It also introduced a wider spread in healing thresholds:
  - some matches still opened with wasteful high-HP potion use
  - `state_action_consistency` dropped from `0.956` to `0.914`
  - `risk_band_policy_delta` rose from `0.036` to `0.256`
- `Mini-RC` made Mini much less overconservative:
  - first potion median: `37.5 HP` vs `77 HP`
  - danger-zone potion rate: `26.4%` vs `76.5%`
  - lethal-zone potion rate: `53.7%` vs `100%`
- But that shift did not read as a clean improvement:
  - unused-potion losses worsened to `63.6%` from `0%`
  - all-attack matches rose to `16.7%` from `0%`
  - the outcome stayed effectively null at `13-11`

## Follow-On Rule
- Flash-Lite earns the next VariableDamage follow-up.
- Mini does not.
- The next package should stay on Flash-Lite, either by expanding the RC baseline to `N=48` or by moving to the next intervention layer on top of the now-legible RC behavior.
