# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 96 total matches across 4 cells
- Decisive matches: 96
- Draws: 0
- Win rates: every paired cell split 12-12 under side-swap
- Topline winner: none; the signal is positional and behavioral, not name-based
- First player in first recorded match: Attack-B
- Strict contract rate: 1.0 across all exported cells
- Artifact validation: all exported cells passed
- Average turns: 17.75 overall
- Average duration (s): 14.76 overall
- Total cost: 0.52164
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: prompt cadence did not change topline outcomes for either provider at pilot scale. Both `gpt-4o-mini` and `claude-haiku-4-5-20251001` split `12-12` between handshake-only and turn-reinforced conditions with `0` parse failures and `100%` strict contract rate.
- Secondary finding: the more interesting behavioral difference was model-specific policy shape. Mini preserved the calibration-style first-player dominance (`24/24` first-player wins), while Haiku inverted the game and the second player won `24/24`.
- Practical recommendation: use this package to show AgentDeck's ability to make behavioral mechanisms legible through fairness metadata, replay, and validated artifacts. Do not frame Release 1 as evidence that cadence changes win rate in FixedDamage.

## Phase 0 Calibration
- `AttackBot` vs `AttackBot`: calibration rerun confirms pure position dominance under paired side-swap. Named bots split `12-12`, but the actual first player wins `24/24` and every match ends in 9 turns.
- `AttackBot` vs `PotionAt80Bot`: topline wins still split `12-12` because the first player wins `24/24`, but the weaker policy is clearly visible in trajectory shape. Every match extends to 15 turns because `PotionAt80Bot` burns potions at 80 HP.

## Phase 1 Cadence Pilot
- `gpt-4o-mini`: no cadence delta at `N=24`. `Mini-HO` and `Mini-TR` split `12-12`, stayed perfectly strict on the ActionOnly contract, and preserved the game's expected first-player dominance (`24/24` first-player wins).
- `claude-haiku-4-5-20251001`: no cadence delta at `N=24`. `Haiku-HO` and `Haiku-TR` also split `12-12` with `0` parse failures and `100%` strict contract rate, but unlike Mini they inverted the game and the second player won `24/24`.
- Reinforcement increased spend without changing results. `Mini-TR` cost `0.03274` vs `Mini-HO` `0.02754`, and `Haiku-TR` cost `0.25034` vs `Haiku-HO` `0.21101`.
- The earlier aborted Haiku pilot is no longer part of the result set. After tightening the handshake contract to require exactly `OK`, the rerun completed cleanly and is the only release-facing Haiku data.

## Statistical Summary
- Sample size (`n`): 24 decisive matches per provider cadence cell; 96 decisive matches overall across the package.
- Win rates + 95% CI: both provider cadence cells landed at `0.5` win rate per condition with exact-binomial `95%` intervals of `[0.314, 0.686]`.
- Effect size: `0.0` (`negligible`) for `Mini-TR` vs `Mini-HO` and `Haiku-TR` vs `Haiku-HO`.
- Significance notes: no cadence comparison was statistically significant. The actionable pilot signal is the absence of a cadence delta, not a marginal effect.

## Cost & Reliability
- Total cost: `0.52164` across the whole package, with provider spend concentrated in Phase 1 (`0.06028` Mini, `0.46136` Haiku).
- Cost per match: `0.00251` for the Mini cell, `0.01922` for the Haiku cell, `0.00543` overall across all 96 matches.
- Forfeit / parse-failure rates: `0` across every exported cell after the strict `OK` handshake contract fix.
- Latency notes: local calibration cells complete in fractions of a second per match; provider cells averaged about `30.04s` per Mini match and `28.72s` per Haiku match.

## Viewer Highlights
- Calibration highlights: `AttackBot` vs `AttackBot` is the clean fairness clip; `AttackBot` vs `PotionAt80Bot` is the clean policy-deviation clip.
- Cadence highlights: `Mini-HO` vs `Mini-TR` is the clean negative-result replay because the trajectories stay symmetric while the reinforcement path still costs more.
- Mechanism evidence: `Haiku-HO` vs `Haiku-TR` is the strongest replay pair for Release 1 because it shows cadence-insensitive outcomes alongside a fully inverted position effect.

## Limitations
- FixedDamage is a behavioral microscope, not a broad benchmark.
- Position effects remain important even with paired side-swap.

## Next Steps
- `P0` is complete on the final audited codebase.
- `P1` is complete on the final audited codebase.
- Expand cells only if the pilot supports a clean causal story.
- Do not expand the cadence matrix for Release 1. Treat the next experiment as a separate question, likely controller type or reasoning-contract differences rather than cadence.
- Keep the public release narrative behavior-first rather than leaderboard-first.
