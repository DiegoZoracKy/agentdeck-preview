# Phase 1 Pilot Notes

## Purpose
- Test whether HP-threshold grounding on top of `ReasoningController + turn reinforcement` fixes Flash-Lite's residual second-player threshold bug against plain Flash.

## Sessions
- failed preflight launch:
  - `p1_c01_flash_lite_rc_tr_vs_flash_ao`
  - `session_20260320_144427_c2b24f`
  - failed before match start because the launching shell had not exported the repo `.env`
- canonical retained sessions:
  - `p1_c01_flash_lite_rc_tr_vs_flash_ao`
    - `session_20260320_144445_8184dd`
  - `p1_c02_flash_lite_rc_tr_hp_vs_flash_ao`
    - `session_20260320_145119_f19cd1`

## Run Notes
- Provider/API issues:
  - one initial Gemini launch failed before any matches because the shell did not export the repo `.env`
  - rerunning with the repo `.env` exported completed both canonical sessions cleanly
- Seed family:
  - fresh package seed base `8242`
  - cell seeds `8242` and `8342`
- Export notes:
  - per-cell export completed cleanly
  - package export completed cleanly

## Results
- reinforced baseline cell:
  - `Flash-AO` beat `FlashLite-RC-TR` `15-9`
  - exact-binomial `p=0.307`
  - small effect size
- HP-grounded cell:
  - `FlashLite-RC-TR-HP` beat `Flash-AO` `13-11`
  - exact-binomial `p=0.839`
  - negligible effect size

## Interpretation
- The baseline reproduced the same broad reinforced-parity picture as the prior package: Flash-Lite was close, but still visibly weaker by seat.
- The HP-grounded overlay fixed the mechanism much more clearly than it changed the outcome:
  - healthy-state second-player over-healing disappeared
  - critical-state second-player hesitation mostly disappeared
  - `position_policy_delta` collapsed from `0.231` to `0.023`
- The outcome narrowed to near parity, but the cell stayed inferentially null at `N=24`.

## Decision
- Immediate expansion: not yet
- Reason:
  - the mechanism question is answered well enough to promote `RC + TR + HP-grounding` as the full-stack Flash-Lite condition
  - the competitive question should be asked in a dedicated parity package at larger `N`
