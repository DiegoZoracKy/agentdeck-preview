# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
Pending — regenerate after P1/P2 provider-backed results are exported with
`agentdeck-research-export --package --no-generated-at`.
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Preregistered Readout
- H1 Strategy stack effect:
- H2 Controller effect:
- H3 Grounding effect:
- H4 Seat drift reduction:
- H5 Cost-quality frontier:
- H6 Transfer limitation:

Each hypothesis should be marked as one of: confirmed, falsified, inconclusive,
or post-hoc observation.

## Pilot Gates
- Runner/list-cells status: PASS — 10 cells list cleanly (2 P0, 8 P1).
- Provider/model verification: PENDING — fill credentials and verify live model IDs before P1.
- Max-turn truncation: not observed in P0 (max_turns=40; avg turns 15.9 in smoke cells).
- Export validation: PASS — schema_version 3, artifact_validation all_passed=True for both P0 cells and package.
- Built-in scorer coverage: per-cell behavioral profiles ARE present in P0 exports (p0_fd_bot_smoke: game_id=fixed_damage; p0_vd_bot_smoke: game_id=variable_damage). Package-level behavioral_profile is absent because the package aggregates both FixedDamage and VariableDamage matches — mixed-game aggregation has no single homogeneous scorer. This is expected behaviour; per-cell scoring is the reliable surface.
- Cost projection: $0.00 for P0 (bots). Requires P1 pilot cost telemetry to project main-run budget.
- Main-run pruning decision: PENDING — requires P1 pilot review.

## FixedDamage
- Replication target:
  - Primary candidate: `research/2026-04-08-fixed-damage-rc-replication-1/`
  - Arc context: `research/2026-03-23-fixed-damage-arc-1/`
- Outcome layer:
- Behavioral layer:
- Position/fairness layer:
- Cost layer:

## VariableDamage
- Transfer question:
- Outcome layer:
- Risk-band behavioral layer:
- Position/fairness layer:
- Cost layer:

## Cost-Quality Frontier
- S0 cost multiplier:
- S1 cost multiplier:
- S3 FixedDamage cost multiplier:
- S3 VariableDamage cost multiplier:
- Cost per successful critical response:

## Limitations
- LLM nondeterminism:
- Provider-side model drift:
- Prompt sensitivity:
- Synthetic-game scope:
- Model roster scope:

## Next Steps
- Main-run cell list:
- S2 controller decision, if S2 is added:
- Custom scorer decision:
- Viewer curation candidates:
