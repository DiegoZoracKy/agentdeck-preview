# Phase 1 Run Notes

## Purpose
- Run the dedicated fresh-seed `N=48` parity replication package for the full Flash-Lite stack:
  - `FlashLite-RC-TR-HP` vs `Flash-AO`
- Primary diagnostic:
  - whether the stronger threshold-grounded policy keeps second-player performance high enough to replicate the Parity 3 competitive result

## Execution
- Phase: `P1`
- Cell: `p1_c01_flash_lite_rc_tr_hp_vs_flash_ao`
- Seed base: `11242`
- Session:
  - `session_20260320_214554_6c9818`

## Outcome
- Completed matches: `48`
- Result: `FlashLite-RC-TR-HP` `28-20` over `Flash-AO`
- Statistical read: `p=0.312`, negligible effect, not significant at `alpha=0.05`

## Position Diagnostic
- first player won `42/48`
- `FlashLite-RC-TR-HP` won `23/24` as first player and `5/24` as second
- `Flash-AO` won `19/24` as first player and `1/24` as second

## Mechanism Notes
- The healthy-state second-player panic-heal stayed fixed:
  - `FlashLite-RC-TR-HP` attacked `24/24` at shared `80 HP / 3 potions` as second player
- The residual issue stayed narrow:
  - at shared `20 HP / 3 potions`, second-player `FlashLite-RC-TR-HP` still attacked `4/24`
  - at shared `20 HP / 1 potion`, second-player `FlashLite-RC-TR-HP` still attacked `2/21`
- `Flash-AO` showed the larger seat-conditioned threshold problem on the fresh seed family.
