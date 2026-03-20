# Phase 1 Pilot Notes

## Purpose
- Test whether turn reinforcement on top of `ReasoningController` can close the remaining parity gap between Flash-Lite and plain Flash.

## Sessions
- `p1_c01_flash_lite_rc_ho_vs_flash_ao`
  - `session_20260320_133855_81128d`
- `p1_c02_flash_lite_rc_tr_vs_flash_ao`
  - `session_20260320_134613_21bd90`

## Run Notes
- Provider/API issues:
  - none
- Seed family:
  - fresh package seed base `7242`
  - cell seeds `7242` and `7342`
- Export notes:
  - per-cell export completed cleanly
  - package export succeeded on rerun after cell artifacts landed

## Results
- control cell:
  - `Flash-AO` beat `FlashLite-RC-HO` `14-10`
  - exact-binomial `p=0.541`
  - negligible effect size
- reinforced cell:
  - `FlashLite-RC-TR` beat `Flash-AO` `15-9`
  - exact-binomial `p=0.307`
  - small effect size

## Interpretation
- Handshake-only control reproduced the same broad parity picture as Parity 1: Flash-Lite reasoning is competitive enough to stay close, but not enough to win cleanly.
- Turn reinforcement improved Flash-Lite's behavior materially and flipped the raw outcome direction.
- The strongest healthy-state second-player error shrank sharply under reinforcement, but second-player critical-state choices still split too often.

## Decision
- Immediate expansion: not yet
- Reason:
  - if the next goal is competitive parity, both cells should expand together to `N=48`
  - if the next goal is mechanism, the current package already isolates the remaining failure mode clearly enough to design a tighter follow-up
