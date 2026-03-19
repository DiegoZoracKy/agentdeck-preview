# Phase 1 Pilot Notes

## Purpose
- Run the first cadence-sensitive provider cells at pilot scale.

## Cells
- `p1_c01_mini_ho_vs_tr`
- `p1_c02_haiku_ho_vs_tr`
- `p1_c03_gemini_ho_vs_tr`
- `p1_c04_gemini_flash_ho_vs_tr`

## Session Notes
- Session IDs:
- `p1_c01_mini_ho_vs_tr`: `session_20260319_133047_8ba9d0`
- `p1_c02_haiku_ho_vs_tr`: `session_20260319_134251_8a7b63`
- `p1_c03_gemini_ho_vs_tr`: `session_20260319_150524_5e9cfe`
- `p1_c04_gemini_flash_ho_vs_tr`: `session_20260319_151139_d2f1fd`
- Google cells ran with `thinking_budget=0` after the initial default-Flash path proved too slow for the benchmark. The Flash cell also used stronger retry/backoff (`max_retries=8`, `retry_delay=2.0`) because Vertex returned occasional `429` throttling on the faster path.
- Any provider/API issues:
- no provider outages during the release-facing rerun
- the earlier Haiku handshake abort is intentionally excluded from this package; the final rerun used the stricter `Reply with exactly 'OK' and nothing else` handshake contract and completed cleanly
- Early replay-visible mechanisms:
- Mini stays in the expected first-player-dominant regime. `Mini-HO` and `Mini-TR` split `12-12`, but the actual first player wins `24/24`.
- Haiku also shows no cadence delta in topline wins, but it lands in a different policy regime: `Haiku-HO` and `Haiku-TR` split `12-12` while the second player wins `24/24`.
- Flash-Lite also shows no cadence delta in topline wins (`13-11`), but it differs from both Mini and Haiku in contract quality: `0` parse failures with only `18.2%` strict ActionOnly compliance.
- Flash remains cadence-insensitive in win rate (`10-14`) while returning to strong first-player dominance (`22/24` first-player wins) and much higher strictness (`90.2%`).
- In all four provider cells, turn reinforcement increases token cost without changing the causal readout.
- Export/validation notes:
- all four provider cells exported cleanly
- `research_validate.py` passed after export
- strict ActionOnly contract rate was `100%` for Mini and Haiku, `90.2%` for Flash, and `18.2%` for Flash-Lite, all with `0` parse failures

## Decision
- Expand any cell to `N=80`: no
- Reason:
- the cadence question is already answered cleanly enough for Release 1: no provider showed a statistically meaningful win-rate delta at pilot scale
- the richer release story is behavioral and contractual: position dependence and strictness diverge sharply by model family even when cadence does not
