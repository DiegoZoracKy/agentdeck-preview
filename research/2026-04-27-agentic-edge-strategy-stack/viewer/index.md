# Viewer Curation — Selected Match Examples

Experiment: `2026-04-27-agentic-edge-strategy-stack`  
Selected: 2026-05-02  
Purpose: representative match examples for demos, screenshots, NotebookLM, and public storytelling.

Each example has a one-sentence reason for inclusion. Full turn narratives are in the per-match sidecar files.

---

## Selected Examples

| # | Slot | Cell | Match ID | Winner | Story |
|---|---|---|---|---|---|
| 1 | S0 failure | `p2_fd_tier_gap_s0` | `match_0316b96b` | GPT4oMini-S0-AO | All-attack collapse: FlashLite attacks 8 times, never uses 3 potions, dies at HP=20 with full potion inventory |
| 2 | S1 pivot | `p3_fd_frontier_s1` | `match_0430d46c` | FlashLite-S1-RC | Reasoning pivot: FlashLite recognizes lethal threshold, uses all 3 potions at HP=20/10/20, survives and wins |
| 3 | S3 FD policy | `p2_fd_frontier_s3` | `match_2d1955c8` | FlashLite-S3-HP | Policy execution: every FlashLite turn shows explicit HP arithmetic ("80-20=60>0"), fires POTION at exactly HP=60, 50, 20 |
| 4 | VD risk policy | `p2_vd_full_stack_effect_s3` | `match_63fd5bc4` | FlashLite-S3-RISK | Risk-band reasoning: correctly skips POTION above 55, triggers at 54 ("not above 55, in range 26–40"), again at 39 and 16 |
| 5 | VD caveat | `p2_vd_frontier_s3` | `match_c2fe0872` | GPT4oMini-S0-AO | Seat-driven loss: FlashLite follows risk policy correctly throughout, loses by 2 HP because GPT4oMini went first |

---

## Sidecar Files

- [match_0316b96b.md](match_0316b96b.md) — S0 failure (p2_fd_tier_gap_s0)
- [match_0430d46c.md](match_0430d46c.md) — S1 pivot (p3_fd_frontier_s1)
- [match_2d1955c8.md](match_2d1955c8.md) — S3 FD policy execution (p2_fd_frontier_s3)
- [match_63fd5bc4.md](match_63fd5bc4.md) — VD risk policy (p2_vd_full_stack_effect_s3)
- [match_c2fe0872.md](match_c2fe0872.md) — VD caveat (p2_vd_frontier_s3)

---

## Recording Paths

Raw recordings are in `agentdeck_runs/<cell_id>/session_*/records/match_<id>.json` locally,
and in the Hugging Face dataset under the corresponding phase folder:

```text
https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study
p2_main/         → cells 1, 3, 4, 5
p3_supplemental/ → cell 2
```
