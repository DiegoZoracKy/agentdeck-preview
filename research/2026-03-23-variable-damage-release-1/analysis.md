# VariableDamage Release 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: stochastic damage materially changed the calibration story; `PotionAt80Bot` beat `AttackBot` `18-6` instead of looking obviously weak.
- Secondary finding: plain `Flash-AO` still beat plain `FlashLite-AO` clearly in VariableDamage, `19-5` at `N=24`.
- Practical recommendation: move next to `VariableDamage Transfer 1`, but rewrite any carried-forward HP prompt for stochastic damage rather than copying the FixedDamage text verbatim.
<!-- AUTO_FACTS:END -->

## Status
- Complete baseline package with `72` recorded matches and clean behavioral export.

## Question
- How does seeded damage uncertainty change baseline behavior in a FixedDamage-like game before any transferred strategy stack is introduced?

## What This Package Answered
1. Paired side-swap still makes position legible, but the first-player effect is weaker than in FixedDamage once damage is stochastic.
2. `PotionAt80Bot` is no longer a clearly weak calibration policy. Under variable damage it decisively beat `AttackBot`.
3. Plain `Flash-AO` remained the stronger Gemini baseline and beat plain `FlashLite-AO` clearly even without a large seat confound.

## Results
- `AttackBot` vs `AttackBot`
  - `12-12`
  - first-player wins: `16/24`
  - average turns: `9.67`
  - reading: pure attack remains seat-sensitive, but much less deterministic than FixedDamage
- `PotionAt80Bot` vs `AttackBot`
  - `18-6` for `PotionAt80Bot`
  - exact-binomial `p=0.0227`, medium effect
  - first-player wins: `14/24`
  - average turns: `16.17`
  - reading: uncertainty makes early healing strategically viable enough to beat the all-attack baseline
- `FlashLite-AO` vs `Flash-AO`
  - `19-5` for `Flash-AO`
  - exact-binomial `p=0.00661`, medium effect
  - first-player wins: `13/24`
  - average turns: `19.21`
  - total cell cost: `$0.0534`
  - reading: the model gap is real and no longer explainable as a near-forced first-player script

## Behavioral Readout
- The scorer exported cleanly across all three cells and made the new uncertainty boundary legible.
- In calibration, `PotionAt80Bot` still never healed in lethal or danger because its trigger is fixed at high HP, but its median first potion at `77 HP` was enough to outperform the reckless all-attack policy.
- In the Gemini baseline, the model difference was concentrated exactly where VariableDamage should matter:
  - `Flash-AO` first potion median: `45 HP`
  - `FlashLite-AO` first potion median: `18.5 HP`
  - `Flash-AO` danger-zone potion rate: `54.7%`
  - `FlashLite-AO` danger-zone potion rate: `6.3%`
  - `Flash-AO` lethal-zone potion rate: `83.3%`
  - `FlashLite-AO` lethal-zone potion rate: `37.1%`
  - `Flash-AO` unused-potion losses: `20.0%`
  - `FlashLite-AO` unused-potion losses: `89.5%`
- Flash-Lite stayed slightly more state-consistent (`0.963` vs `0.897`), but that consistency was attached to a bad policy: it attacked through danger far too often and still lost holding resources.

## Interpretation
- VariableDamage successfully changed the game class. The first-player advantage is no longer load-bearing enough to hide policy quality.
- The most important calibration finding is that variance made “heal early” less obviously wrong. That is a useful warning for the transfer phase: a FixedDamage-optimized stack should not be assumed to carry over unchanged.
- The Gemini baseline result is still favorable to plain Flash, but for a different reason than in FixedDamage. Flash was not just more reliable; it was materially better at preserving survival margin once high rolls became possible.
- The new risk-band metrics are clear enough to support intervention work. This package does not need another baseline sweep.

## Follow-On Rule
- The next package should be `VariableDamage Transfer 1`.
- It should carry forward the best FixedDamage Flash-Lite stack conceptually, but not copy the old HP instruction literally because `20 damage` is no longer a guaranteed next-hit assumption.
