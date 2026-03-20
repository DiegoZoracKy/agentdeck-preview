# Phase 1 Pilot Notes

## Purpose
- Run the first controller-intervention pilot on the Gemini Flash-family models.

## Cells
- `p1_c01_flash_lite_ao_vs_rc`
- `p1_c02_flash_ao_vs_rc`

## Session Notes
- Session IDs:
- `p1_c01_flash_lite_ao_vs_rc`: `session_20260319_231248_4b9e00`
- `p1_c02_flash_ao_vs_rc`: `session_20260319_231822_84cc1f`
- Provider/API issues:
- one initial Flash-Lite launch failed before any matches because the shell had not exported the repo `.env`; that empty session is intentionally excluded from the package
- after rerunning with the repo `.env` exported, both canonical sessions completed cleanly
- Early replay-visible mechanisms:
- FlashLite-RC heals much more readily than FlashLite-AO and no longer looks as close to the all-attack calibration floor
- FlashLite-RC is still not purely stable; the same visible state can split by seat or by repeated context
- Flash-RC looks cleaner than Flash-AO, but the lift is much smaller than the Flash-Lite change
- Export/validation notes:
- both cell exports completed cleanly from the canonical session directories
- package export completed cleanly
- research validation passed after doc refresh

## Decision
- Expand any cell beyond `N=24`: not yet
- Reason:
- Flash-Lite is the only cell with a clearly legible behavioral gain worth considering for expansion
- Flash remains too close to outcome-null and too expensive under reasoning to justify immediate expansion
- follow-up: Flash-Lite was later expanded; see `phase-1-expansion.md`
