## Phase P1 Run Notes

- `p1_c01_flash_lite_ao_vs_haiku_ao`
  - First startup attempt failed before match execution because the shell had not loaded the repo Vertex env.
  - Empty session `session_20260324_221006_6287f0` recorded `0` matches and is not interpreted.
  - Clean rerun `session_20260324_221022_0b695b` completed `48/48` matches and is the canonical run.

- `p1_c02_flash_ao_vs_mini_ao`
  - Completed cleanly in `session_20260324_223718_80d313`.
  - Flash used the carried retry profile (`max_retries=12`, `retry_delay=4.0`) from the start to avoid the VariableDamage-style `429` hang pattern.

- `p1_c03_flash_ao_vs_haiku_ao`
  - Initial sequential phase-run session `session_20260324_231901_b33b34` was interrupted after `p1_c04` had already been launched manually in parallel.
  - That left `47` complete matches plus one partial record (`match_75e44c9f.json` missing `ended_at` and `duration_seconds`), so the session was not export-safe.
  - The contaminated session was moved to `notes/discarded_sessions/` to keep the canonical scan path clean.
  - Canonical interpretation uses the clean rerun started as `session_20260324_235449_17174b`.

- `p1_c04_mini_ao_vs_haiku_ao`
  - Launched manually in parallel while `p1_c03` was still running, because it does not use Flash and therefore did not add Gemini Flash quota pressure.
  - Cleanly completed in `session_20260324_232231_b510e8`.

- Package-level execution decision
  - The original `--phase P1` runner was intentionally stopped once `p1_c04` already had its own valid standalone completion, to avoid a duplicate `Mini-AO vs Haiku-AO` cell execution.
