# Phase 1 Run Notes

- Phase P1 was launched as three direct parallel cell runs using the repo `.env` plus `VERTEX_LOCATION=global`.
- The completed canonical sessions are:
  - `p1_c01_gpt5mini_ao_vs_flash_ao/session_20260325_091223_3e12c7`
  - `p1_c02_gpt5mini_ao_vs_haiku_ao/session_20260325_091223_6cc584`
  - `p1_c03_gpt5mini_ao_vs_mini_ao/session_20260325_091223_9a846a`
- All three cells exported from single completed sessions. No duplicate-session cleanup or segmented seed repair was needed.
- `GPT5Mini-AO` incurred repeated long-latency OpenAI turns, including several ~`600s` outliers and shorter `30-170s` spikes.
- Those latency spikes materially increased package wall-clock time, especially in `p1_c01_gpt5mini_ao_vs_flash_ao`, but did not create incomplete `match_*.json` files or contract failures.
