# Phase 1 Pilot Notes

## Purpose
- Test controller as a competitive equalizer by comparing:
  - `FlashLite-AO` vs `Flash-AO`
  - `FlashLite-RC` vs `Flash-AO`

## Sessions
- `p1_c01_flash_lite_ao_vs_flash_ao`
  - `session_20260320_122027_80aade`
- `p1_c02_flash_lite_rc_vs_flash_ao`
  - `session_20260320_122526_fafeef`

## Run Notes
- Provider/API issues:
  - none
- Seed family:
  - fresh package seed base `6242`
  - cell seeds `6242` and `6342`
- Export notes:
  - package-local exporters worked unchanged for the first pilot
  - no multi-session aggregation was needed in this package

## Results
- Baseline gap:
  - `Flash-AO` beat `FlashLite-AO` `21-3`
  - exact-binomial `p=0.00028`
  - large effect size
- Equalizer cell:
  - `Flash-AO` beat `FlashLite-RC` `14-10`
  - exact-binomial `p=0.541`
  - negligible effect size

## Interpretation
- `ReasoningController` clearly improved Flash-Lite's behavior and closed most of the plain-model gap.
- The remaining failure mode is not crude aggression. It is seat-conditioned reasoning policy, especially over-healing when second player.

## Decision
- Immediate expansion: no
- Reason:
  - the pilot already answers the causal question cleanly enough for this task
  - the better next move is to target the remaining failure mode, not spend more on a parity rerun with the same contract
