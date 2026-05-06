# Results Report

> Generated deterministically from `results.json`. Authored interpretation belongs under `analysis/`.

## Scope
- Experiment ID: `2026-04-27-agentic-edge-strategy-stack`
- Schema version: `3`
- Aggregation scope: `study_phases`
- Phases included: `P2`, `P3`
- Cells included: `p2_fd_tier_gap_s0`, `p2_fd_controller_effect_s1`, `p2_fd_full_stack_effect_s3`, `p2_fd_frontier_s3`, `p2_vd_tier_gap_s0`, `p2_vd_controller_effect_s1`, `p2_vd_full_stack_effect_s3`, `p2_vd_frontier_s3`, `p3_fd_frontier_s1`
- Primary recordings source: `/home/diegozoracky/dev/agentdeck/research/2026-04-27-agentic-edge-strategy-stack/agentdeck_runs/p2_fd_tier_gap_s0/session_20260427_224646_81f317/records`
- Recordings source count: 9

## Warnings
- Package aggregate spans multiple cells; use cell-level rows for outcome claims.
- Cell `p2_vd_tier_gap_s0` has high first-player skew (77.1%); interpret aggregate win rates with seat splits.
- Cell `p2_vd_frontier_s3` has high first-player skew (87.5%); interpret aggregate win rates with seat splits.
- Cell `p2_vd_tier_gap_s0` direct result is not statistically significant (p=0.059, alpha=0.05); avoid strong dominance claims.
- Cell `p2_vd_frontier_s3` direct result is not statistically significant (p=0.312, alpha=0.05); avoid strong dominance claims.

## Summary
| Metric | Value |
| --- | --- |
| Total matches | 432 |
| Decisive matches | 432 |
| Draws | 0 |
| Average turns | 19.903 |
| Average duration seconds | 17.788 |
| Total cost | $1.128308 |
| Average cost per match | $0.002612 |

## Cell Overview
| Cell | n | Winner | Direct Result | p-value | Effect | First-Player WR | Cost | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [p2_fd_tier_gap_s0](artifacts/p2_fd_tier_gap_s0/results.json) | 48 | GPT4oMini-S0-AO (100.0%) | FlashLite-S0-AO 0/48 (0.0%) vs GPT4oMini-S0-AO 48/48 (100.0%) | 0.000 | large | 50.0% | $0.069183 | True |
| [p2_fd_controller_effect_s1](artifacts/p2_fd_controller_effect_s1/results.json) | 48 | FlashLite-S1-RC (77.1%) | FlashLite-S1-RC 37/48 (77.1%) vs FlashLite-S0-AO 11/48 (22.9%) | 0.000 | medium | 72.9% | $0.073344 | True |
| [p2_fd_full_stack_effect_s3](artifacts/p2_fd_full_stack_effect_s3/results.json) | 48 | FlashLite-S3-HP (85.4%) | FlashLite-S3-HP 41/48 (85.4%) vs FlashLite-S0-AO 7/48 (14.6%) | 0.000 | medium | 64.6% | $0.128578 | True |
| [p2_fd_frontier_s3](artifacts/p2_fd_frontier_s3/results.json) | 48 | FlashLite-S3-HP (79.2%) | FlashLite-S3-HP 38/48 (79.2%) vs GPT4oMini-S0-AO 10/48 (20.8%) | 0.000 | medium | 66.7% | $0.189441 | True |
| [p2_vd_tier_gap_s0](artifacts/p2_vd_tier_gap_s0/results.json) | 48 | GPT4oMini-S0-AO (64.6%) | FlashLite-S0-AO 17/48 (35.4%) vs GPT4oMini-S0-AO 31/48 (64.6%) | 0.059 | small | 77.1% | $0.083213 | True |
| [p2_vd_controller_effect_s1](artifacts/p2_vd_controller_effect_s1/results.json) | 48 | FlashLite-S1-RC (79.2%) | FlashLite-S0-AO 10/48 (20.8%) vs FlashLite-S1-RC 38/48 (79.2%) | 0.000 | medium | 66.7% | $0.098737 | True |
| [p2_vd_full_stack_effect_s3](artifacts/p2_vd_full_stack_effect_s3/results.json) | 48 | FlashLite-S3-RISK (85.4%) | FlashLite-S3-RISK 41/48 (85.4%) vs FlashLite-S0-AO 7/48 (14.6%) | 0.000 | medium | 60.4% | $0.139141 | True |
| [p2_vd_frontier_s3](artifacts/p2_vd_frontier_s3/results.json) | 48 | FlashLite-S3-RISK (58.3%) | GPT4oMini-S0-AO 20/48 (41.7%) vs FlashLite-S3-RISK 28/48 (58.3%) | 0.312 | negligible | 87.5% | $0.200966 | True |
| [p3_fd_frontier_s1](artifacts/p3_fd_frontier_s1/results.json) | 48 | FlashLite-S1-RC (70.8%) | FlashLite-S1-RC 34/48 (70.8%) vs GPT4oMini-S0-AO 14/48 (29.2%) | 0.006 | small | 66.7% | $0.145705 | True |

## Cell Seat Splits
| Cell | Player | As First | As Second |
| --- | --- | --- | --- |
| p2_fd_tier_gap_s0 | FlashLite-S0-AO | 0/24 (0.0%) | 0/24 (0.0%) |
| p2_fd_tier_gap_s0 | GPT4oMini-S0-AO | 24/24 (100.0%) | 24/24 (100.0%) |
| p2_fd_controller_effect_s1 | FlashLite-S0-AO | 11/24 (45.8%) | 0/24 (0.0%) |
| p2_fd_controller_effect_s1 | FlashLite-S1-RC | 24/24 (100.0%) | 13/24 (54.2%) |
| p2_fd_full_stack_effect_s3 | FlashLite-S0-AO | 7/24 (29.2%) | 0/24 (0.0%) |
| p2_fd_full_stack_effect_s3 | FlashLite-S3-HP | 24/24 (100.0%) | 17/24 (70.8%) |
| p2_fd_frontier_s3 | FlashLite-S3-HP | 23/24 (95.8%) | 15/24 (62.5%) |
| p2_fd_frontier_s3 | GPT4oMini-S0-AO | 9/24 (37.5%) | 1/24 (4.2%) |
| p2_vd_tier_gap_s0 | FlashLite-S0-AO | 15/24 (62.5%) | 2/24 (8.3%) |
| p2_vd_tier_gap_s0 | GPT4oMini-S0-AO | 22/24 (91.7%) | 9/24 (37.5%) |
| p2_vd_controller_effect_s1 | FlashLite-S0-AO | 9/24 (37.5%) | 1/24 (4.2%) |
| p2_vd_controller_effect_s1 | FlashLite-S1-RC | 23/24 (95.8%) | 15/24 (62.5%) |
| p2_vd_full_stack_effect_s3 | FlashLite-S0-AO | 6/24 (25.0%) | 1/24 (4.2%) |
| p2_vd_full_stack_effect_s3 | FlashLite-S3-RISK | 23/24 (95.8%) | 18/24 (75.0%) |
| p2_vd_frontier_s3 | FlashLite-S3-RISK | 23/24 (95.8%) | 5/24 (20.8%) |
| p2_vd_frontier_s3 | GPT4oMini-S0-AO | 19/24 (79.2%) | 1/24 (4.2%) |
| p3_fd_frontier_s1 | FlashLite-S1-RC | 21/24 (87.5%) | 13/24 (54.2%) |
| p3_fd_frontier_s1 | GPT4oMini-S0-AO | 11/24 (45.8%) | 3/24 (12.5%) |

## Package Aggregate Player Exposure

_These rows pool all included package matches and are not cell-level toplines._

| Player | Wins | Win Rate | 95% CI | p-value | Effect Size | Effect |
| --- | --- | --- | --- | --- | --- | --- |
| FlashLite-S0-AO | 52 | 12.0% | 9.3%-15.4% | 0.000 | -0.862 | large |
| FlashLite-S1-RC | 109 | 25.2% | 21.4%-29.5% | 0.000 | -0.518 | medium |
| FlashLite-S3-HP | 79 | 18.3% | 14.9%-22.2% | 0.000 | -0.687 | medium |
| FlashLite-S3-RISK | 69 | 16.0% | 12.8%-19.7% | 0.000 | -0.749 | medium |
| GPT4oMini-S0-AO | 123 | 28.5% | 24.4%-32.9% | 0.000 | -0.445 | small |

## Package Aggregate Direct Head-to-Head

_These comparisons pool direct matches across included cells. Use Cell Overview for study claims._

| Comparison | Scope | Player A Result | Player B Result | Matches | p-value | Effect |
| --- | --- | --- | --- | --- | --- | --- |
| FlashLite-S0-AO_vs_FlashLite-S1-RC | direct_head_to_head | FlashLite-S0-AO: 21/96 (21.9%) | FlashLite-S1-RC: 75/96 (78.1%) | 96 | 0.000 | medium |
| FlashLite-S0-AO_vs_FlashLite-S3-HP | direct_head_to_head | FlashLite-S0-AO: 7/48 (14.6%) | FlashLite-S3-HP: 41/48 (85.4%) | 48 | 0.000 | medium |
| FlashLite-S0-AO_vs_FlashLite-S3-RISK | direct_head_to_head | FlashLite-S0-AO: 7/48 (14.6%) | FlashLite-S3-RISK: 41/48 (85.4%) | 48 | 0.000 | medium |
| FlashLite-S0-AO_vs_GPT4oMini-S0-AO | direct_head_to_head | FlashLite-S0-AO: 17/96 (17.7%) | GPT4oMini-S0-AO: 79/96 (82.3%) | 96 | 0.000 | medium |
| GPT4oMini-S0-AO_vs_FlashLite-S1-RC | direct_head_to_head | GPT4oMini-S0-AO: 14/48 (29.2%) | FlashLite-S1-RC: 34/48 (70.8%) | 48 | 0.006 | small |
| GPT4oMini-S0-AO_vs_FlashLite-S3-HP | direct_head_to_head | GPT4oMini-S0-AO: 10/48 (20.8%) | FlashLite-S3-HP: 38/48 (79.2%) | 48 | 0.000 | medium |
| GPT4oMini-S0-AO_vs_FlashLite-S3-RISK | direct_head_to_head | GPT4oMini-S0-AO: 20/48 (41.7%) | FlashLite-S3-RISK: 28/48 (58.3%) | 48 | 0.312 | negligible |

## Position Effects
| Metric | Value |
| --- | --- |
| First-player wins | 294 |
| First-player win rate | 68.1% |
| Second-player wins | 138 |
| Second-player win rate | 31.9% |

### Seat Split By Player
| Player | As First | As Second |
| --- | --- | --- |
| FlashLite-S0-AO | 48/144 (33.3%) | 4/144 (2.8%) |
| FlashLite-S1-RC | 68/72 (94.4%) | 41/72 (56.9%) |
| FlashLite-S3-HP | 47/48 (97.9%) | 32/48 (66.7%) |
| FlashLite-S3-RISK | 46/48 (95.8%) | 23/48 (47.9%) |
| GPT4oMini-S0-AO | 85/120 (70.8%) | 38/120 (31.7%) |

## Format Strictness
| Metric | Value |
| --- | --- |
| Turn attempts | 8598 |
| Parse failure rate | 0.0% |
| Strict contract rate | 100.0% |
| Action-line rate | 100.0% |
| Reasoning-line rate | 40.3% |

### Strictness By Player
| Player | Attempts | Parse Failure Rate | Strict Contract Rate | Action-Line Rate | Reasoning-Line Rate |
| --- | --- | --- | --- | --- | --- |
| FlashLite-S0-AO | 2610 | 0.0% | 100.0% | 100.0% | 0.0% |
| FlashLite-S1-RC | 1379 | 0.0% | 100.0% | 100.0% | 100.0% |
| FlashLite-S3-HP | 1035 | 0.0% | 100.0% | 100.0% | 100.0% |
| FlashLite-S3-RISK | 1051 | 0.0% | 100.0% | 100.0% | 100.0% |
| GPT4oMini-S0-AO | 2523 | 0.0% | 100.0% | 100.0% | 0.0% |

## Player Costs
| Player | Player-Matches | Total Cost | Avg Cost |
| --- | --- | --- | --- |
| FlashLite-S0-AO | 288 | $0.176449 | $0.000613 |
| FlashLite-S1-RC | 144 | $0.203304 | $0.001412 |
| FlashLite-S3-HP | 96 | $0.222475 | $0.002317 |
| FlashLite-S3-RISK | 96 | $0.240076 | $0.002501 |
| GPT4oMini-S0-AO | 240 | $0.286004 | $0.001192 |

## Artifact Validation
| Metric | Value |
| --- | --- |
| Matches checked | 432 |
| All passed | True |
| Failure count | 0 |
