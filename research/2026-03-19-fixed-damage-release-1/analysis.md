# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 0
- Decisive matches: 0
- Draws: 0
- Win rates: {}
- Topline winner: TBD
- First player in first recorded match: TBD
- Strict contract rate: TBD
- Artifact validation: TBD
- Average turns: TBD
- Average duration (s): TBD
- Total cost: TBD
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding:
- Secondary finding:
- Practical recommendation:

## Phase 0 Calibration
- `AttackBot` vs `AttackBot`: paired side-swap worked as intended; each named bot finished 12-12 overall, but the first player won 24/24 matches and every match ended in 9 turns.
- `AttackBot` vs `PotionAt80Bot`: paired side-swap again produced a 24/24 first-player win rate, so the weaker policy does not show up in topline wins; it shows up in trajectory length instead, with every match stretching to 15 turns because `PotionAt80Bot` heals at 80 HP.

## Phase 1 Cadence Pilot
- `gpt-4o-mini`:
- `claude-haiku-4-5-20251001`:

## Statistical Summary
- Sample size (`n`):
- Win rates + 95% CI:
- Effect size:
- Significance notes:

## Cost & Reliability
- Total cost:
- Cost per match:
- Forfeit / parse-failure rates:
- Latency notes:

## Viewer Highlights
- Calibration highlights:
- Cadence highlights:
- Mechanism evidence:

## Limitations
- FixedDamage is a behavioral microscope, not a broad benchmark.
- Position effects remain important even with paired side-swap.

## Next Steps
- Expand cells only if the pilot supports a clean causal story.
- Keep the public release narrative behavior-first rather than leaderboard-first.
