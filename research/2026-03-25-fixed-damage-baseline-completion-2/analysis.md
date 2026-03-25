# FixedDamage Baseline Completion 2 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `GPT5Mini-AO` is the clear strongest plain FixedDamage baseline, beating `Flash-AO` `36-12` and `Haiku-AO` `46-2`
- Secondary finding: `Haiku-AO` stayed seat-distorted and behaviorally strange in FixedDamage, but `GPT5Mini-AO` was strong enough to overwhelm that pathology almost completely
- Practical recommendation: treat the broad FixedDamage AO graph as closed and use it for cross-game comparison only, not for new FixedDamage intervention work
<!-- AUTO_FACTS:END -->

## Status
- Complete AO-only FixedDamage baseline completion package with `96` matches.

## Question
- How do the last missing plain-model FixedDamage matchups against `GPT5Mini-AO` resolve head-to-head, and does that fully close the FixedDamage AO baseline graph?

## What This Package Is Designed To Answer
1. Whether `Flash-AO` can stay competitive with plain `GPT5Mini-AO` in the same FixedDamage environment where tuned Flash-Lite could not overtake it.
2. Whether `Haiku-AO`'s bizarre FixedDamage seat distortion still converts into direct competitiveness against `GPT5Mini-AO`.
3. Whether the full FixedDamage plain-model graph is complete enough afterward to support symmetric cross-game comparisons without any remaining inferred edges.

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
- It should close the remaining FixedDamage plain-model graph edges, not create new intervention branches.
- Any comparison to the Flash-Lite strategy stack should stay explicit about the difference between plain baselines and tuned conditions.

## Hypotheses
- `GPT5Mini-AO` should beat both `Flash-AO` and `Haiku-AO` on plain outcome.
- `Flash-AO` should have the better chance to stay competitive.
- `Haiku-AO` should keep its FixedDamage seat-conditioned policy reversals.

## Follow-On Rule
- If these two cells execute cleanly, treat the FixedDamage plain-model AO graph as complete.
- Use the finished graph only for retrospective cross-game comparison and arc summary updates.

## Result
- `GPT5Mini-AO` beat `Flash-AO` `36-12` (`p=7.17e-04`, medium effect).
- `GPT5Mini-AO` beat `Haiku-AO` `46-2` (`p=8.36e-12`, large effect).

## Interpretation
- These two cells close the remaining broad FixedDamage AO edges cleanly.
- The completed plain-model FixedDamage ordering is:
  - `GPT5Mini-AO > Flash-AO ≈ Haiku-AO > Mini-AO > FlashLite-AO`
- The stronger conclusion is not just that `gpt-5-mini` wins, but that it wins in two different ways:
  - against `Flash-AO`, it keeps a clear survival-policy edge while still respecting the normal first-player script
  - against `Haiku-AO`, it largely erases Haiku's FixedDamage seat weirdness by simply being stronger from both seats

## Behavioral Read
- `Flash-AO` vs `GPT5Mini-AO`
  - `Flash-AO` remained the stronger non-OpenAI plain baseline, but `GPT5Mini-AO` was materially better in the critical states that matter most:
    - `critical_potion_response_rate`: `0.701` vs `0.497`
    - `error_recovery_rate`: `0.741` vs `0.432`
    - `unused_potions_on_loss_rate`: `0.0` vs `0.417`
  - `Flash-AO` still had the healthier non-pathological policy profile than Haiku, but it could not match `GPT5Mini-AO`'s survival discipline.
- `Haiku-AO` vs `GPT5Mini-AO`
  - `Haiku-AO` stayed unmistakably strange in FixedDamage even while losing badly:
    - `first_potion_profile.median_first_potion_hp = 70`
    - `critical_potion_response_rate = 1.0`
    - `position_policy_delta = 1.0`
    - `state_action_consistency = 0.984`
  - That combination means Haiku is coherent on its own terms, but its FixedDamage policy is still seat-conditioned in a way that does not survive contact with a stronger baseline.
  - `GPT5Mini-AO` won `23/24` as first player and `23/24` as second, so Haiku's old inversion no longer translates into meaningful competitive leverage.

## Cross-Game Read
- This package closes the last broad FixedDamage AO edges needed for symmetric comparison against the later VariableDamage baseline graph.
- The important cross-game asymmetry now looks even sharper:
  - in `FixedDamage`, `Haiku-AO` is bizarre and brittle
  - in `VariableDamage`, `Haiku-AO` is strong and much more coherent
- `GPT5Mini-AO` now also sets a clear upper bound among the plain FixedDamage baselines:
  - tuned weaker models can beat some stronger plain baselines
  - but plain `gpt-5-mini` is still the strongest untuned model we tested in this deterministic game

## Run Integrity
- `p1_c01_flash_ao_vs_gpt5mini_ao` completed cleanly in a single session.
- `p1_c02_haiku_ao_vs_gpt5mini_ao` completed cleanly in the manually launched standalone session `session_20260325_004346_8ab395`.
- After `p1_c01` completed, the original `--phase P1` runner rolled into `p1_c02` and wrote one completed duplicate match before it was interrupted.
- That duplicate session was moved to `notes/discarded_sessions/` before export so canonical results only include the clean standalone c02 session.
