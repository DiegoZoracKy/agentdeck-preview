# Phase 0 Calibration Notes

## Purpose
- Verify environment behavior, fairness controls, and replay artifacts before provider runs.

## Cells
- `p0_c01_attack_vs_attack`
- `p0_c02_attack_vs_potion80`

## Session Notes
- Session IDs:
  - `p0_c01_attack_vs_attack`: `session_20260319_094732_487b35`
  - `p0_c02_attack_vs_potion80`: `session_20260319_094735_bb2df8`
- Any blockers:
  - none
- Replay observations:
  - `AttackBot` vs `AttackBot` behaves as a clean pure-position baseline: the first player wins every match in 9 turns.
  - `AttackBot` vs `PotionAt80Bot` surfaces the weaker policy in trajectory shape rather than topline wins: the first player still wins every match, but matches take 15 turns because `PotionAt80Bot` extends the game with healing.
- Export/validation notes:
  - study-level top-level export was intentionally not kept because mixed-cell aggregation flattened the matrix into a misleading single scoreboard.
  - cell-level exports should be generated under `artifacts/<cell-id>/`.

## Decision
- Ready to proceed to `P1`: yes
- Reason:
  - fairness metadata, recordings, and replay artifacts are clean
  - Phase 0 already demonstrated the position effect and a legible policy-quality difference in trajectory length/behavior
