# VariableDamage Release 1 Analysis Plan

## Status
- Planned baseline package. No recordings or exported results exist yet.

## Question
- How does seeded damage uncertainty change baseline behavior in a FixedDamage-like game before any transferred strategy stack is introduced?

## What This Package Must Answer
1. Does paired side-swap still make position effects legible under stochastic damage?
2. Is a clearly weak calibration policy (`PotionAt80Bot`) still measurably weak when exact damage is no longer fixed?
3. How do plain `FlashLite-AO` and plain `Flash-AO` behave in VariableDamage before any reasoning or turn-time reinforcement is added?

## Primary Readout
- Calibration:
  - decisive win rate
  - first-player win rate
  - average turns
- Behavioral baseline:
  - `all_attack_match_rate`
  - `unused_potions_on_loss_rate`
  - `state_action_consistency`
  - `position_policy_delta`
  - `action_by_risk_band`
  - `lethal_zone_potion_rate`
  - `danger_zone_potion_rate`
  - `risk_band_policy_delta`

## Interpretation Guardrails
- This package is baseline only.
- It must not be used to claim that the FixedDamage carry-forward stack transfers.
- If the new risk-band metrics are unclear or unsupported, scorer implementation must be fixed before any transfer or intervention package is run.
- The execution cap should stay above the FixedDamage default because VariableDamage can legitimately produce longer low-roll, full-potion matches without indicating a stuck engine.

## Planned Comparisons
- `AttackBot` vs `AttackBot`
  - expectation: stochastic damage weakens, but does not necessarily erase, position advantage
- `AttackBot` vs `PotionAt80Bot`
  - expectation: the early-heal policy remains behaviorally inferior
- `FlashLite-AO` vs `Flash-AO`
  - expectation: plain Flash remains the stronger Gemini baseline, but outcome and behavior may shift relative to FixedDamage because exact threshold play is no longer available

## Follow-On Rule
- If Release 1 exports cleanly and the baseline cells are behaviorally legible, the next package should be `VariableDamage Transfer 1` rather than another broader baseline sweep.
