# Phase 0 Calibration Notes

## Purpose
- Verify environment behavior, fairness controls, and replay artifacts before provider runs.

## Cells
- `p0_c01_attack_vs_attack`
- `p0_c02_attack_vs_potion80`

## Session Notes
- Session IDs:
- `p0_c01_attack_vs_attack`: `session_20260319_132932_3fd3d3`
- `p0_c02_attack_vs_potion80`: `session_20260319_132935_4f5581`
- Any blockers:
- none
- Replay observations:
- `AttackBot` vs `AttackBot` remains a clean fairness baseline: deterministic mirror policy, 9 turns every match, first player wins every match.
- `AttackBot` vs `PotionAt80Bot` shows why FixedDamage is a behavioral microscope and not a leaderboard. The named bots split `12-12` only because side-swap cancels the position effect; the real signal is the trajectory stretch to 15 turns caused by potion use at 80 HP.
- Export/validation notes:
- cell-level exports were regenerated from the reset package and both passed artifact validation with no failures.

## Decision
- Ready to proceed to `P1`: yes
- Reason:
- fairness metadata, strict contract metrics, and artifact validation are clean on the final audited codebase
- the calibration cells still show the two intended proofs: pure position effect and replay-visible suboptimal policy
