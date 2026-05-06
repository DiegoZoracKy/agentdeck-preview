# Results Report

> Generated deterministically from `results.json`. Authored interpretation belongs under `analysis/`.

## Scope
- Experiment ID: `2026-04-27-agentic-edge-strategy-stack::p3_fd_frontier_s1`
- Schema version: `3`
- Aggregation scope: `cell`
- Phase: `P3`
- Cell: `p3_fd_frontier_s1`
- Primary recordings source: `/home/diegozoracky/dev/agentdeck/research/2026-04-27-agentic-edge-strategy-stack/agentdeck_runs/p3_fd_frontier_s1/session_20260428_230412_dc36c6/records`

## Summary
| Metric | Value |
| --- | --- |
| Total matches | 48 |
| Decisive matches | 48 |
| Draws | 0 |
| Average turns | 22 |
| Average duration seconds | 23.108 |
| Total cost | $0.145705 |
| Average cost per match | $0.003036 |

## Player Results
| Player | Wins | Win Rate | 95% CI | p-value | Effect Size | Effect |
| --- | --- | --- | --- | --- | --- | --- |
| FlashLite-S1-RC | 34 | 70.8% | 56.8%-81.8% | 0.006 | 0.430 | small |
| GPT4oMini-S0-AO | 14 | 29.2% | 18.2%-43.2% | 0.006 | -0.430 | small |

## Direct Head-to-Head
| Comparison | Scope | Player A Result | Player B Result | Matches | p-value | Effect |
| --- | --- | --- | --- | --- | --- | --- |
| FlashLite-S1-RC_vs_GPT4oMini-S0-AO | direct_head_to_head | FlashLite-S1-RC: 34/48 (70.8%) | GPT4oMini-S0-AO: 14/48 (29.2%) | 48 | 0.006 | small |

## Position Effects
| Metric | Value |
| --- | --- |
| First-player wins | 32 |
| First-player win rate | 66.7% |
| Second-player wins | 16 |
| Second-player win rate | 33.3% |

### Seat Split By Player
| Player | As First | As Second |
| --- | --- | --- |
| FlashLite-S1-RC | 21/24 (87.5%) | 13/24 (54.2%) |
| GPT4oMini-S0-AO | 11/24 (45.8%) | 3/24 (12.5%) |

## Format Strictness
| Metric | Value |
| --- | --- |
| Turn attempts | 1056 |
| Parse failure rate | 0.0% |
| Strict contract rate | 100.0% |
| Action-line rate | 100.0% |
| Reasoning-line rate | 50.5% |

### Strictness By Player
| Player | Attempts | Parse Failure Rate | Strict Contract Rate | Action-Line Rate | Reasoning-Line Rate |
| --- | --- | --- | --- | --- | --- |
| FlashLite-S1-RC | 533 | 0.0% | 100.0% | 100.0% | 100.0% |
| GPT4oMini-S0-AO | 523 | 0.0% | 100.0% | 100.0% | 0.0% |

## Player Costs
| Player | Player-Matches | Total Cost | Avg Cost |
| --- | --- | --- | --- |
| FlashLite-S1-RC | 48 | $0.085401 | $0.001779 |
| GPT4oMini-S0-AO | 48 | $0.060304 | $0.001256 |

## Behavioral Profile
| Field | Value |
| --- | --- |
| Profile | fixed_damage_behavioral |
| Game | fixed_damage |
| Version | 0.2.0 |

### Aggregate Behavioral Metrics
_No rows._

## Artifact Validation
| Metric | Value |
| --- | --- |
| Matches checked | 48 |
| All passed | True |
| Failure count | 0 |
