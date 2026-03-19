# Phase 1 Pilot Notes

## Purpose
- Run the first cadence-sensitive provider cells at pilot scale.

## Cells
- `p1_c01_mini_ho_vs_tr`
- `p1_c02_haiku_ho_vs_tr`

## Session Notes
- Session IDs:
- `p1_c01_mini_ho_vs_tr`: `session_20260319_133047_8ba9d0`
- `p1_c02_haiku_ho_vs_tr`: `session_20260319_134251_8a7b63`
- Any provider/API issues:
- no provider outages during the release-facing rerun
- the earlier Haiku handshake abort is intentionally excluded from this package; the final rerun used the stricter `Reply with exactly 'OK' and nothing else` handshake contract and completed cleanly
- Early replay-visible mechanisms:
- Mini stays in the expected first-player-dominant regime. `Mini-HO` and `Mini-TR` split `12-12`, but the actual first player wins `24/24`.
- Haiku also shows no cadence delta in topline wins, but it lands in a different policy regime: `Haiku-HO` and `Haiku-TR` split `12-12` while the second player wins `24/24`.
- In both provider cells, turn reinforcement increases token cost without changing the outcome split.
- Export/validation notes:
- both provider cells exported cleanly
- `research_validate.py` passed after export
- strict ActionOnly contract rate was `100%` for both cells with `0` parse failures

## Decision
- Expand any cell to `N=80`: no
- Reason:
- the cadence question is already answered cleanly enough for Release 1: no provider showed a win-rate delta at pilot scale
- further spend should go to a different causal question, not more cadence runs of the same design
