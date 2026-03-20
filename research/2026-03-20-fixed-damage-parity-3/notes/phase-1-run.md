# Phase 1 Run Notes

## Purpose
- Run the dedicated `N=48` parity package for the full Flash-Lite stack:
  - `FlashLite-RC-TR-HP` vs `Flash-AO`
- Primary diagnostic:
  - whether the stronger threshold-grounded policy lifts second-player performance enough to make the competitive claim plausible

## Execution
- Phase: `P1`
- Cell: `p1_c01_flash_lite_rc_tr_hp_vs_flash_ao`
- Seed base: `9242`
- Session:
  - `research/2026-03-20-fixed-damage-parity-3/agentdeck_runs/p1_c01_flash_lite_rc_tr_hp_vs_flash_ao/session_20260320_171412_3f4676/records/`

## Outcome
- Completed matches: `48`
- Result: `FlashLite-RC-TR-HP` finished `31-17` over `Flash-AO`
- Statistical read:
  - exact binomial `p=0.059`
  - small effect
  - not significant at `alpha=0.05`

## Position Diagnostic
- First player won `35/48`
- `FlashLite-RC-TR-HP`:
  - `21/24` as first player
  - `10/24` as second player
- `Flash-AO`:
  - `14/24` as first player
  - `3/24` as second player

## Mechanism Notes
- The healthy-state second-player bug stayed fixed:
  - `80 HP / 3 potions` second-player `FlashLite-RC-TR-HP`: `23/24` `ATTACK`
- The critical-state hesitation shrank but did not disappear:
  - `20 HP / 3 potions` second-player `FlashLite-RC-TR-HP`: `18/26` `POTION`, `8/26` `ATTACK`
- Conclusion:
  - this is a strong competitive showing and a clear mechanism hold
  - the remaining uncertainty is stability across schedules, not whether the intervention changed behavior
