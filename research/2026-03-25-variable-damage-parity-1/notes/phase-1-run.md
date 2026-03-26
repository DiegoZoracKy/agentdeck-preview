# Phase 1 Run Notes

- Ran `P1` end-to-end in a single live session:
  - `p1_c01_flash_lite_rc_risk_vs_flash_ao`
- Session path:
  - `research/2026-03-25-variable-damage-parity-1/agentdeck_runs/p1_c01_flash_lite_rc_risk_vs_flash_ao/session_20260325_223321_3b4a7c`
- Result:
  - `48/48` valid completed matches
  - no match-level recovery batches required
- Operational note:
  - Flash incurred normal intermittent Vertex `429 RESOURCE_EXHAUSTED` retries during the run, but the live session continued to complete matches without manual intervention
- Export note:
  - cell export succeeded on the first pass
  - package export failed once immediately after cell export because the canonical cell `results.json` was not yet visible to the package-export script
  - rerunning package export succeeded without changing any match artifacts
