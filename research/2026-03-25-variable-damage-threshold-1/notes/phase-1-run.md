# Phase 1 Run Notes

- `p1_c01_flash_lite_rc_vs_flash_ao` completed in a single session:
  - `session_20260325_144624_3cc2c5`
- `p1_c02_flash_lite_rc_risk_vs_flash_ao` did not finish cleanly in its original session:
  - `session_20260325_151803_d3f697`
  - this session produced `14` valid completed matches plus `1` incomplete partial record
  - the incomplete partial had no `seed`, `ended_at`, or `duration_seconds`
- Recovery was run from the next untouched seed bucket:
  - remaining intended seeds were `31349..31353` under paired side-swap
  - recovery session: `session_20260325_162432_e7a488`
  - recovery completed the remaining `10` matches
- Before export, the incomplete partial file was renamed out of the exporter’s `*.json` set so it would not contaminate cell totals.
- Exports then completed successfully for:
  - both per-cell artifacts
  - package-level `results.json`
  - package-level `results.csv`
