# FixedDamage Baseline Completion 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: the completed plain-model FixedDamage ordering is `Flash-AO ≈ Haiku-AO > Mini-AO > FlashLite-AO`
- Secondary finding: `Haiku-AO` is strong in FixedDamage, but it gets there through a much more seat-distorted policy than it shows in VariableDamage
- Practical recommendation: use this package to sharpen the FixedDamage-vs-VariableDamage comparison, not to reopen the FixedDamage intervention ladder
<!-- AUTO_FACTS:END -->

## Status
- Completed AO-only FixedDamage baseline completion package with `192` matches.

## Question
- How do the remaining plain-model FixedDamage matchups among Flash-Lite,
  Flash, Mini, and Haiku resolve head-to-head, and how does that complete the
  cross-game comparison against VariableDamage?

## What This Package Is Designed To Answer
1. Whether Haiku's known FixedDamage seat inversion converts into strong direct
   head-to-head performance or only into weird within-model behavior.
2. Whether Mini's early-heal FixedDamage policy holds up directly against Flash
   and Haiku.
3. What the actual plain-model ordering is among the four FixedDamage baseline
   models once the missing edges are filled.
4. Whether the cross-game claim that Haiku changed the most between FixedDamage
   and VariableDamage is supported by symmetric baseline evidence.

## Primary Readout
- Outcome:
  - decisive win rate
  - exact-binomial significance
  - first-player win rate
  - position-controlled split
- Behavior:
  - `all_attack_match_rate`
  - `first_potion_profile`
  - `unused_potions_on_loss_rate`
  - `critical_potion_response_rate`
  - `state_action_consistency`
  - `position_policy_delta`

## Interpretation Guardrails
- This package is AO-only.
- It should complete the FixedDamage plain-model graph, not reopen the
  intervention ladder.
- Any cross-game comparison should emphasize behavioral mechanism, not just raw
  win totals.

## Hypotheses
- `Haiku-AO` should remain the most position-sensitive FixedDamage baseline.
- `Mini-AO` should remain early-healing and stable.
- `Flash-AO` should remain the cleanest plain Gemini baseline.
- `FlashLite-AO` should still be the weakest untuned model in FixedDamage.

## Follow-On Rule
- Use the results to sharpen the FixedDamage-vs-VariableDamage comparison, not
  to create new FixedDamage intervention branches.
- Only refresh the FixedDamage arc summary if the completed baseline ordering
  materially changes the cross-game interpretation.

## Result
- `Haiku-AO` beat `FlashLite-AO` `44-4` (`p=1.51e-09`, large effect).
- `Flash-AO` beat `Mini-AO` `36-12` (`p=7.17e-04`, medium effect).
- `Flash-AO` vs `Haiku-AO` ended `26-22` for Flash (`p=0.665`, negligible effect).
- `Haiku-AO` beat `Mini-AO` `35-13` (`p=0.00209`, small effect).

## Interpretation
- The completed FixedDamage baseline ordering is:
  - `Flash-AO ≈ Haiku-AO > Mini-AO > FlashLite-AO`
- This closes the one real symmetry gap in the cross-game comparison.
- The result that matters most for that comparison is `Flash-AO` vs `Haiku-AO`:
  - the matchup is effectively null on outcome
  - but it is not null on mechanism
  - `Flash-AO` reached near parity with a much steadier policy
  - `Haiku-AO` stayed highly seat-conditioned and still disrupted the normal first-player script

## Behavioral Read
- `FlashLite-AO` remained the weakest untuned model in FixedDamage:
  - against `Haiku-AO`, it lost `44-4`
  - `unused_potions_on_loss_rate = 97.7%`
  - `critical_potion_response_rate = 0.221`
- `Mini-AO` remained stable and early-healing:
  - first potion median stayed `80 HP` against both stronger opponents
  - it still healed critically well, but the early spend made it materially weaker than both `Flash-AO` and `Haiku-AO`
- `Haiku-AO` remained the strangest FixedDamage baseline:
  - `position_policy_delta = 1.0` against `FlashLite-AO`
  - `position_policy_delta = 1.0` against `Mini-AO`
  - yet only `0.188` against `Flash-AO`
  - it won `23/24` as second player against `FlashLite-AO`, but only `15/24` as second player against `Flash-AO`
- `Flash-AO` again looked like the cleanest plain Gemini baseline:
  - decisive over `Mini-AO`
  - near parity with `Haiku-AO`
  - less pathological seat dependence than Haiku while keeping competitive outcomes

## Cross-Game Read
- The VariableDamage plain ordering was already `Flash-AO ≈ Haiku-AO > Mini-AO > FlashLite-AO`.
- This package shows the same broad ordering now also holds in FixedDamage once the missing edges are filled.
- The important difference is *how* the models get there:
  - in `FixedDamage`, `Haiku-AO` is strong but deeply seat-distorted
  - in `VariableDamage`, `Haiku-AO` is strong and much more coherent
- That makes `Haiku` the clearest model-level behavioral shift across the two games.

## Run Integrity
- `p1_c03_flash_ao_vs_haiku_ao` required a clean rerun after the original sequential phase-run session was intentionally interrupted to avoid duplicating `p1_c04`.
- The interrupted `p1_c03` session was moved to `notes/discarded_sessions/` because it contained `47` complete matches plus one partial record and was not export-safe.
- Canonical exports use the clean rerun plus the clean standalone `p1_c04` session.
