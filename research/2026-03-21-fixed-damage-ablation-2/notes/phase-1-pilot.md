# Phase 1 Pilot Notes

## Run Summary
- Phase: `P1`
- Date: `2026-03-21`
- Cells:
  - `p1_c01_flash_lite_ao_hp_vs_flash_ao`
  - `p1_c02_flash_lite_ao_tr_hp_vs_flash_ao`

## Sessions
- `p1_c01_flash_lite_ao_hp_vs_flash_ao`
  - session: `session_20260321_092226_0af577`
  - result: `Flash-AO` beat `FlashLite-AO-HP` `24-0`
- `p1_c02_flash_lite_ao_tr_hp_vs_flash_ao`
  - session: `session_20260321_092727_a59369`
  - result: `Flash-AO` beat `FlashLite-AO-TR-HP` `18-6`

## Immediate Read
- HP-threshold grounding by itself failed completely.
- Adding turn-time ActionOnly reinforcement recovered some low-HP behavior and reduced healthy-state waste, but it did not solve the second-player problem.
- Both cheap ActionOnly overlays stayed far below the full Flash-Lite stack from Parity 3.

## Why This Matters
- This closes the main cheap-ablation question for FixedDamage:
  - `ReasoningController` is not just formatting overhead
  - it is carrying real decision-quality value in the best known Flash-Lite strategy
