# Phase 1 Run Notes

- Execution command used the repo `.env` plus `VERTEX_LOCATION=global`.
- An initial startup attempt failed before any match completed because the shell had not loaded the Vertex env. That empty session under `p1_c01` was ignored for export and interpretation because it contains no `match_*.json` files.
- The completed phase used:
  - `p1_c01_flash_lite_rc_vs_flash_ao/session_20260324_094743_01fb81`
  - `p1_c02_flash_lite_rc_tr_vs_flash_ao/session_20260324_102245_0bfcc8`
- `Flash-AO` hit several recoverable Vertex `429 RESOURCE_EXHAUSTED` retries during the live run.
- Those retries increased latency on some turns but did not produce parse failures or incomplete matches.
