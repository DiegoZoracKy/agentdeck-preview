# Phase 1 Run Notes

## Purpose
- Run the dedicated fresh-seed `N=48` cross-provider parity package for the full Flash-Lite stack:
  - `FlashLite-RC-TR-HP` vs `Mini-AO`
- Primary diagnostic:
  - whether the stronger threshold-grounded policy keeps its behavioral advantages against a stable Mini baseline

## Execution
- Phase: `P1`
- Cell: `p1_c01_flash_lite_rc_tr_hp_vs_mini_ao`
- Seed base: `12242`
- Session:
  - `session_20260320_220849_582a93`

## Outcome
- Completed matches: `48`
- Result: `FlashLite-RC-TR-HP` `41-7` over `Mini-AO`
- Statistical read: `p=6.24e-07`, medium effect, significant at `alpha=0.05`

## Position Diagnostic
- first player won `27/48`
- `FlashLite-RC-TR-HP` won `22/24` as first player and `19/24` as second
- `Mini-AO` won `5/24` as first player and `2/24` as second

## Mechanism Notes
- `Mini-AO` used `POTION` at shared `80 HP / 3 potions` in `24/24` turns from both seats.
- `FlashLite-RC-TR-HP` attacked at shared `80 HP / 3 potions` in `48/48` turns as first player and `46/47` as second.
- Flash-Lite kept a strong late-heal threshold at `20 HP / 3 potions` and `20 HP / 1 potion`; Mini almost never reached those states with potions remaining.
