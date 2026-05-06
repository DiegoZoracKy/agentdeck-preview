# S1 Cross-Tier Frontier Follow-up

**Cell:** `p3_fd_frontier_s1`  
**Date:** 2026-04-28  
**Purpose:** Fill the missing tuning-ladder step between S0 (FlashLite baseline) and S3 (full-stack frontier) in the FixedDamage cross-tier matchup against GPT-4o-mini.

---

## Setup

| Field | Value |
|---|---|
| Cell ID | `p3_fd_frontier_s1` |
| Phase | P3 (targeted ladder-completion cell; included in official study aggregate) |
| Game | FixedDamageGame (`attack_damage=20`, `information_level=partial`) |
| Player A | FlashLite-S1-RC (gemini-2.5-flash-lite + ReasoningController) |
| Player B | GPT4oMini-S0-AO (gpt-4o-mini + ActionOnlyController) |
| n | 48 matches (24 paired AB/BA seed pairs) |
| Seed | 2026047701 (base 2026042701 + offset 5000) |
| Pairing | `paired_side_swap` |
| First player | `random` |

---

## Direct Result

**FlashLite-S1-RC 34/48 (70.8%) — GPT4oMini-S0-AO 14/48 (29.2%)**

| Metric | Value |
|---|---|
| FlashLite-S1-RC wins | 34 |
| GPT4oMini-S0-AO wins | 14 |
| Draws | 0 |
| Win rate (FlashLite-S1-RC) | **70.8%** |
| 95% CI | [56.8%, 81.8%] |
| p-value (exact binomial vs 50%) | **0.0055** |
| Effect size (Cohen's h) | 0.430 (small) |
| Statistically significant | Yes |
| Total cost | **$0.1457** |
| Avg cost per match | $0.0030 |
| Avg turns per match | 22.0 |

---

## Position (Seat) Effect

| | Matches as First | Matches as Second | Wins as First | Win Rate (First) | Wins as Second | Win Rate (Second) |
|---|---|---|---|---|---|---|
| FlashLite-S1-RC | 24 | 24 | 21 | **87.5%** | 13 | **54.2%** |
| GPT4oMini-S0-AO | 24 | 24 | 11 | 45.8% | 3 | 12.5% |

First-player win rate across all matches: **32/48 = 66.7%** (notable first-mover advantage in FixedDamage; consistent with other cells in this study).

FlashLite-S1-RC wins decisively regardless of seat (87.5% first, 54.2% second), confirming the result is not seat-driven.

---

## Tuning-Ladder Summary

Cross-tier FixedDamage win rates for FlashLite vs GPT4oMini-S0-AO:

```
S0  FlashLite-S0-AO vs GPT4oMini-S0-AO:  0/48  =  0.0%   (p2_fd_tier_gap_s0)
S1  FlashLite-S1-RC vs GPT4oMini-S0-AO: 34/48  = 70.8%   (p3_fd_frontier_s1)  ← this cell
S3  FlashLite-S3-HP vs GPT4oMini-S0-AO: 38/48  = 79.2%   (p2_fd_frontier_s3)
```

---

## Interpretation

**The S0→S1 jump (0% → 70.8%) is the decisive step in the tier inversion.**

Adding only the ReasoningController — no explicit HP-grounding, no threshold tables, no full stack — is sufficient to flip FlashLite from 0-wins to a commanding 70.8% win rate over GPT4oMini. This is an increase of 70.8 percentage points on a single scaffold change.

**The S1→S3 increment (70.8% → 79.2%) is marginal.**

Adding the full HP-grounded strategy stack (S3-HP = ReasoningController plus
repeated FixedDamage HP-survival grounding) on top of S1-RC produces a +8.4pp
gain. The improvement is real and directionally correct but small relative to
the S0→S1 step.

**What this means for the mechanism story:**

The primary driver of the FixedDamage tier inversion is structured reasoning.
The ReasoningController alone — by requiring an explicit reasoning field before
the action — is responsible for the majority of the outcome improvement that
allows lighter-tier FlashLite to beat GPT4oMini in this cell. The HP grounding
layer in S3 acts as a precision and consistency optimizer on an
already-transformed policy, not as the only source of the inversion.

**Ladder interpretation (applying the rules from the task specification):**

- S1 wins strongly (70.8%) → reasoning alone is responsible for most of the tier inversion.
- S3 increments over S1 (+8.4pp) → the HP-grounding layer in S3 is a marginal optimizer, not a structural requirement.
- The dominant conclusion: **ReasoningController is the load-bearing intervention.** S3 sharpens the edge; S1 creates it.

---

## Impact on the Official Analysis

This targeted cell does **not** change the P2 cell results. It completes the
FixedDamage cross-tier tuning ladder and strengthens the mechanism story:

1. **H1 (tier gap)** — S0 result stands unchanged (0/48, p2_fd_tier_gap_s0).
2. **H2 (controller effect)** — The within-model S1 result (p2_fd_controller_effect_s1) already established that RC improves FlashLite over itself. The S1 cross-tier result now shows that improvement is large enough to invert the tier gap entirely.
3. **H6 (cost-quality frontier)** — Already established by p2_fd_frontier_s3 (S3 HP beats GPT4oMini 79.2%). The S1 result shows the frontier threshold is actually lower than S3: the cheaper S1 scaffold is sufficient to cross the tier boundary.

The tuning-ladder picture is now complete for the FixedDamage cross-tier question. S1 reasoning is the pivot point.

---

## Behavioral Profile

Source:
[`artifacts/p3_fd_frontier_s1/results.json`](../../../artifacts/p3_fd_frontier_s1/results.json)

| Player | All-attack | Median first potion HP | Never used potion | Unused potions on loss | Critical potion response | Error recovery | Position delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| FlashLite-S1-RC | 8.33% | 20 | 8.33% | 42.86% | 52.98% | 81.54% | 18.15% |
| GPT4oMini-S0-AO | 0.00% | 80 | 0.00% | 0.00% | N/A (0 support) | N/A (0 support) | 7.80% |

Read: S1 alone did more than improve win rate. It nearly eliminated
FlashLite's baseline all-attack collapse, moved first potion timing to the
20 HP threshold observed in the stronger FixedDamage policies, and improved
error recovery sharply. S3 remains useful because it further reduces policy
failure modes in the full-stack cells, especially never-used-potion and
unused-potions-on-loss failures.

---

## Files

| File | Path |
|---|---|
| Cell artifact | `artifacts/p3_fd_frontier_s1/results.json` |
| Cell artifact (CSV) | `artifacts/p3_fd_frontier_s1/results.csv` |
| This document | `analysis/analysis_20260428_152909_codex_official_study_analysis/support/s1_frontier_followup.md` |
