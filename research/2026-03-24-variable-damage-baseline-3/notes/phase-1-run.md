# Phase 1 Run Notes

- `p1_c02_haiku_ao_vs_flash_ao` and `p1_c03_mini_ao_vs_haiku_ao` completed in single sessions and exported normally.
- `p1_c01_mini_ao_vs_flash_ao` hit the same Vertex/Flash post-`429` hang twice:
  - first live attempt stalled after producing only an incomplete partial session and was excluded from analysis
  - second live attempt produced `23` completed matches plus one incomplete `match_8dfc2bf8.json`
- To preserve the intended exact `N=48` cell without re-running from scratch, the remaining valid matches were reconstructed deterministically from seed structure:
  - continuation batch: `24` matches at seed `25254` covering original paired-side-swap indices `24-47`
  - repair batch: `2` matches at seed `25253`; only the second, side-swapped match was kept to recover the missing original index `23`
- Canonical `p1_c01` export was built from:
  - `session_20260324_133436_1f7c2c` completed matches only
  - `session_20260324_141508_9cde66`
  - `session_20260324_144253_17d637/match_dd60753e.json`
- The incomplete `match_8dfc2bf8.json` was intentionally excluded from the staged export because it lacked `ended_at` and `duration_seconds`.
