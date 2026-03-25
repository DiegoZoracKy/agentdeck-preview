## Phase P1 Run Notes

- `p1_c01_flash_ao_vs_gpt5mini_ao`
  - Completed cleanly in `session_20260325_003744_45161b`.
  - Flash used the carried retry profile (`max_retries=12`, `retry_delay=4.0`) from the start.

- `p1_c02_haiku_ao_vs_gpt5mini_ao`
  - Started manually in parallel as `session_20260325_004346_8ab395` because both remaining missing FixedDamage edges were gated on the slower `gpt-5-mini` baseline.
  - Completed cleanly with `48/48` matches and is the canonical c02 run.

- Duplicate-session recovery
  - After `p1_c01` completed, the original `--phase P1` runner rolled into `p1_c02` before it could be stopped.
  - The duplicate session `session_20260325_020958_5c1623` was interrupted, but it had already written one completed match (`match_673e6122.json`).
  - That duplicate session was moved to `notes/discarded_sessions/` before export so the canonical scan path only included the clean standalone c02 session.

- Package-level execution decision
  - Canonical exports use:
    - `p1_c01_flash_ao_vs_gpt5mini_ao/session_20260325_003744_45161b`
    - `p1_c02_haiku_ao_vs_gpt5mini_ao/session_20260325_004346_8ab395`
