# Phase 1 Pilot Notes

## Purpose
- Run the first cadence-sensitive provider cells at pilot scale.

## Cells
- `p1_c01_mini_ho_vs_tr`
- `p1_c02_haiku_ho_vs_tr`

## Session Notes
- Session IDs:
  - `p1_c01_mini_ho_vs_tr`: `session_20260319_095250_a59af7`
  - `p1_c02_haiku_ho_vs_tr`: `session_20260319_100413_d79ea7`
- Any provider/API issues:
  - none at the transport layer
  - `claude-haiku-4-5-20251001` failed before gameplay because the handshake contract requires a bare acknowledgement token and `Haiku-HO` responded with `OK` plus a longer explanation
- Early replay-visible mechanisms:
  - `gpt-4o-mini` is parse-clean in both cadence conditions but repeatedly chooses `POTION` instead of staying on the dominant always-attack policy
  - the exported `Mini-HO` vs `Mini-TR` cell shows no win-rate separation at `N=24`; both conditions finish `12-12` under paired side-swap and the first player wins `24/24`
- Export/validation notes:
  - `p1_c01_mini_ho_vs_tr` exported cleanly to `artifacts/p1_c01_mini_ho_vs_tr/`
  - `p1_c02_haiku_ho_vs_tr` has no match recordings because gameplay never began
  - package validation remains clean because cell-level results are kept under `artifacts/` while the study is still running

## Decision
- Expand any cell to `N=80`: no
- Reason:
  - `gpt-4o-mini` currently shows no cadence delta on wins at pilot scale
  - the second provider cell did not start, so the release-facing cross-model comparison is incomplete until we decide whether to keep the handshake failure as a finding or replace the cell
