# Phase 1 Run Notes

## Purpose
- Run the no-turn-reinforcement ablation:
  - `FlashLite-RC-HP` vs `Flash-AO`
- Primary question:
  - does HP-grounding still carry the policy when `{controller_format}` is no longer repeated every turn?

## Execution
- Phase: `P1`
- Cell: `p1_c01_flash_lite_rc_hp_vs_flash_ao`
- Seed base: `10242`
- Session:
  - `research/2026-03-20-fixed-damage-ablation-1/agentdeck_runs/p1_c01_flash_lite_rc_hp_vs_flash_ao/session_20260320_181004_58e3d8/records/`

## Outcome
- Completed matches: `48`
- Result: `Flash-AO` finished `27-21` over `FlashLite-RC-HP`
- Statistical read:
  - exact binomial `p=0.471`
  - negligible effect

## Main Comparative Read
- Parity 3 full-stack result:
  - `FlashLite-RC-TR-HP` finished `31-17` over `Flash-AO`
- Ablation result:
  - `FlashLite-RC-HP` finished `21-27`
- The removal of turn-time reinforcement cost Flash-Lite `10` wins relative to the full stack.

## Position Diagnostic
- First player won `39/48`
- `FlashLite-RC-HP`:
  - `18/24` as first player
  - `3/24` as second player
- `Flash-AO`:
  - `21/24` as first player
  - `6/24` as second player

## Mechanism Notes
- Healthy-state `80 HP / 3 potions` stayed fixed:
  - second-player `FlashLite-RC-HP`: `28/28` `ATTACK`
- The main regression was critical-state commitment with potions still available:
  - second-player `20 HP / 3 potions`: `16/30` `POTION`, `14/30` `ATTACK`
- Strictness did not regress:
  - `FlashLite-RC-HP` stayed `100%` strict with `0` parse failures
- Conclusion:
  - turn-time reinforcement mattered for policy quality, not just formatting
