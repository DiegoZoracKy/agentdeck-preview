# Phase 1 Run Notes

## Purpose
- Run the dedicated fresh-seed `N=48` cross-provider baseline package:
  - `FlashLite-AO` vs `Mini-AO`
- Primary diagnostic:
  - whether plain Flash-Lite already beats Mini, or whether Mini Parity 1's `41-7` result depends mainly on Flash-Lite tuning

## Execution
- Phase: `P1`
- Cell: `p1_c01_flash_lite_ao_vs_mini_ao`
- Seed base: `13242`
- Session:
  - `session_20260320_224226_9145c9`

## Outcome
- Completed matches: `48`
- Result: `Mini-AO` `44-4` over `FlashLite-AO`
- Statistical read: `p=1.51e-09`, large effect, significant at `alpha=0.05`

## Position Diagnostic
- first player won `28/48`
- `FlashLite-AO` won `4/24` as first player and `0/24` as second
- `Mini-AO` won `24/24` as first player and `20/24` as second

## Mechanism Notes
- Plain Flash-Lite attacked through critical states instead of healing:
  - at shared `20 HP / 3 potions`, `FlashLite-AO` attacked `19/20` as first player and `6/10` as second
  - at shared `20 HP / 1 potion`, `FlashLite-AO` attacked `2/2` as first player and `14/16` as second
- Mini retained its early-heal baseline:
  - at shared `80 HP / 3 potions`, `Mini-AO` healed `14/28` as first player and `24/24` as second
- Compared with Mini Parity 1, the tuned stack clearly reversed Flash-Lite's own critical-state policy.
