# Phase 1 Expansion Notes

## Purpose
- Expand only the Flash-Lite controller cell after the pilot showed a strong behavioral signal.

## Cell
- `p1_c01_flash_lite_ao_vs_rc`

## Session Notes
- Session ID:
  - `session_20260320_113943_ef180e`
- Expansion size:
  - `24` additional matches
  - aggregated cell total now `48`
- Provider/API issues:
  - none after exporting the repo `.env` into the launching shell
- Method note:
  - the expansion reused the original cell scheduling seed (`5242`)
  - this adds a second stochastic replicate under the same fairness schedule rather than a different schedule family
- Export/validation notes:
  - package-local exporters were patched so the cell and package exports now honor plural `source.recordings_dirs`
  - re-export after the expansion confirmed `p1_c01` now aggregates both retained sessions

## Result
- Expanded Flash-Lite cell outcome:
  - `FlashLite-RC` `37`
  - `FlashLite-AO` `11`
  - exact-binomial `p=0.00022`
  - medium effect size
- Stable behavioral gains after expansion:
  - all-attack rate: `45.8%` AO vs `18.8%` RC
  - unused-potions-on-loss: `94.6%` AO vs `36.4%` RC
  - critical-potion response: `18.3%` AO vs `50.8%` RC
  - error recovery: `0.259` AO vs `0.596` RC
- Persistent tradeoffs:
  - lower state consistency for RC
  - higher seat-conditioned policy divergence for RC
  - `2.78x` RC cost multiplier

## Decision
- Further expand Flash-Lite immediately: no
- Reason:
  - the behavioral story is now stable enough for this experiment
  - the more valuable next move is productizing matrix-aware multi-session aggregation
