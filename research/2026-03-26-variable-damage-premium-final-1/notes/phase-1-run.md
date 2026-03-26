# Phase 1 Run Notes

- Ran `P1` end-to-end in a single live session:
  - `p1_c01_flash_lite_rc_risk_vs_gpt5mini_ao`
- Session path:
  - `research/2026-03-26-variable-damage-premium-final-1/agentdeck_runs/p1_c01_flash_lite_rc_risk_vs_gpt5mini_ao/session_20260326_100052_d4e562`
- Result:
  - `24/24` valid completed matches
  - no match-level recovery batches required
- Runtime notes:
  - the OpenAI premium cell ran more slowly than the Gemini-only parity package, but remained stable throughout
  - no parse failures, no contract failures, and no manual seed-range recovery was needed
- Export note:
  - cell export succeeded on the first pass
  - package export failed once immediately after cell export because the canonical cell `results.json` was not yet visible to the package-export script
  - rerunning package export succeeded without changing any match artifacts
