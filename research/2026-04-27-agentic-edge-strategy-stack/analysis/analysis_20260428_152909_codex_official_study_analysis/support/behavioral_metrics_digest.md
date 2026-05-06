# Behavioral Metrics Digest

Experiment: `2026-04-27-agentic-edge-strategy-stack`  
Scope: per-cell behavioral profiles from P2 plus the P3 S1 ladder-completion
cell

## Where These Metrics Live

The behavioral metrics are generated in each cell artifact under:

```text
artifacts/<cell_id>/results.json
```

The JSON path is:

```text
behavioral_profile.aggregate_metrics
behavioral_profile.per_player
behavioral_profile.state_metrics
```

The top-level package `results.json` has `behavioral_profile: null` because the
package aggregates both FixedDamage and VariableDamage cells. Mixed-game package
aggregation has no single behavioral profile. Use cell-level artifacts for
behavioral claims.

FixedDamage cells use:

```text
profile_id: fixed_damage_behavioral
profile_version: 0.2.0
game_id: fixed_damage
```

VariableDamage cells use:

```text
profile_id: variable_damage_behavioral
profile_version: 0.1.0
game_id: variable_damage
```

## Why These Metrics Matter

Win rate tells us who won. Behavioral metrics tell us why.

In this study, the important behavioral story is:

- S0 FlashLite often collapses into attacking and loses with unused potions.
- S1 reasoning reduces attack-only collapse and improves critical-state
  recovery.
- S3 grounding makes potion timing much more policy-aligned.
- In FixedDamage, S3 moves FlashLite toward the intended 20 HP survival
  threshold.
- In VariableDamage, S3-RISK moves FlashLite toward a risk-band policy instead
  of the fixed 20 HP rule.

## FixedDamage Metric Definitions

These are the core FixedDamage metrics used in prior FixedDamage work and in
this experiment:

| Metric | What it indicates |
| --- | --- |
| `all_attack_match_rate` | Fraction of matches where a player only attacked and never used potion. |
| `first_potion_profile` | Distribution and median HP of first potion use. |
| `unused_potions_on_loss_rate` | How often a player lost while still holding potions. |
| `state_action_consistency` | How consistently similar states produced similar actions. |
| `position_policy_delta` | How much policy changes by first/second seat. Lower is better. |
| `critical_potion_response_rate` | Potion use in critical low-HP states. |
| `error_recovery_rate` | Recovery after missed or risky critical states. |
| `wasted_full_health_potion_rate` | Potion use at full health. |

## FixedDamage: P2 and P3 Behavioral Readout

### S0 Tier Gap

Source:
[`p2_fd_tier_gap_s0/results.json`](../../../artifacts/p2_fd_tier_gap_s0/results.json)

| Player | All-attack | Median first potion HP | Never used potion | Unused potions on loss | Critical potion response | Error recovery | Position delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S0-AO | 70.83% | 20 | 70.83% | 100.00% | 13.04% | 21.43% | 8.82% |
| GPT4oMini-S0-AO | 0.00% | 80 | 0.00% | 0.00% | 69.49% | 100.00% | 48.14% |

Read: unscaffolded FlashLite often never used potions and lost with unused
resources. GPT4oMini used potions consistently and dominated the outcome.

### S1 Controller Effect

Source:
[`p2_fd_controller_effect_s1/results.json`](../../../artifacts/p2_fd_controller_effect_s1/results.json)

| Player | All-attack | Median first potion HP | Never used potion | Unused potions on loss | Critical potion response | Error recovery | Position delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S1-RC | 27.08% | 80 | 27.08% | 0.00% | 38.55% | 62.16% | 72.92% |
| FlashLite-S0-AO | 60.42% | 20 | 60.42% | 100.00% | 13.21% | 21.11% | 14.35% |

Read: reasoning alone substantially reduced all-attack collapse and improved
critical recovery, but this cell also showed high position-conditioned policy
delta for S1.

### S1 Frontier Follow-Up

Source:
[`p3_fd_frontier_s1/results.json`](../../../artifacts/p3_fd_frontier_s1/results.json)

Outcome: `FlashLite-S1-RC` beat `GPT4oMini-S0-AO` 34/48 matches (70.8%),
p=0.0055.

| Player | All-attack | Median first potion HP | Never used potion | Unused potions on loss | Critical potion response | Error recovery | Position delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S1-RC | 8.33% | 20 | 8.33% | 42.86% | 52.98% | 81.54% | 18.15% |
| GPT4oMini-S0-AO | 0.00% | 80 | 0.00% | 0.00% | N/A (0 support) | N/A (0 support) | 7.80% |

Read: the missing S1 frontier step shows that structured reasoning alone was
already enough to beat GPT4oMini-S0-AO in FixedDamage. The S3 story should now
be framed as strengthening and stabilizing the ladder, not as the only source of
the cross-tier inversion.

### S3 Full Stack vs FlashLite Baseline

Source:
[`p2_fd_full_stack_effect_s3/results.json`](../../../artifacts/p2_fd_full_stack_effect_s3/results.json)

| Player | All-attack | Median first potion HP | Never used potion | Unused potions on loss | Critical potion response | Error recovery | Position delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S3-HP | 0.00% | 20 | 0.00% | 0.00% | 53.15% | 100.00% | 9.12% |
| FlashLite-S0-AO | 20.83% | 20 | 20.83% | 100.00% | 19.81% | 30.65% | 13.71% |

Read: S3 nearly eliminated the behavioral failures that defined S0: no
all-attack collapse, no never-used-potion collapse, no losses with unused
potions, and much stronger critical-state behavior.

### S3 Frontier

Source:
[`p2_fd_frontier_s3/results.json`](../../../artifacts/p2_fd_frontier_s3/results.json)

| Player | All-attack | Median first potion HP | Never used potion | Unused potions on loss | Critical potion response | Error recovery | Position delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S3-HP | 2.08% | 20 | 2.08% | 10.00% | 56.08% | 81.71% | 7.23% |
| GPT4oMini-S0-AO | 0.00% | 80 | 0.00% | 0.00% | 60.00% | 50.00% | 9.35% |

Read: S3-HP retained the intended 20 HP threshold behavior against GPT4oMini.
GPT4oMini used a much earlier median first potion at 80 HP. The difference is a
policy difference, not just a win-rate difference.

## VariableDamage Behavioral Readout

VariableDamage uses a different scorer because damage is stochastic. The most
important analogues are risk-band potion rates:

| Metric | What it indicates |
| --- | --- |
| `safe_zone_potion_rate` | Potion use when HP is safely above the danger range. Lower is usually better. |
| `danger_zone_potion_rate` | Potion use in the risk band. |
| `lethal_zone_potion_rate` | Potion use when entering the likely lethal range. |
| `high_roll_recovery_rate` | Recovery after high-damage shock events. |
| `risk_band_policy_delta` | How much risk-band policy changes by position/context. |

### S1 Controller Effect

Source:
[`p2_vd_controller_effect_s1/results.json`](../../../artifacts/p2_vd_controller_effect_s1/results.json)

| Player | All-attack | Median first potion HP | Unused potions on loss | Safe potion | Danger potion | Lethal potion | High-roll recovery | Risk-band delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S0-AO | 8.33% | 18 | 94.74% | 0.00% | 5.77% | 35.37% | 24.79% | 5.75% |
| FlashLite-S1-RC | 4.17% | 43.5 | 20.00% | 17.68% | 50.00% | 80.56% | 49.19% | 9.64% |

Read: S1 shifted FlashLite from late/underused potion behavior toward earlier
risk-sensitive healing, improving lethal-zone potion use and high-roll recovery.

### S3 Risk Stack vs FlashLite Baseline

Source:
[`p2_vd_full_stack_effect_s3/results.json`](../../../artifacts/p2_vd_full_stack_effect_s3/results.json)

| Player | All-attack | Median first potion HP | Unused potions on loss | Safe potion | Danger potion | Lethal potion | High-roll recovery | Risk-band delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S3-RISK | 0.00% | 41 | 0.00% | 0.00% | 52.15% | 100.00% | 53.05% | 2.11% |
| FlashLite-S0-AO | 6.25% | 20 | 97.56% | 0.00% | 7.73% | 30.32% | 16.22% | 4.43% |

Read: S3-RISK is the cleanest behavioral transfer result. It used no safe-zone
potions, always healed in lethal-zone opportunities, and avoided losing with
unused potions.

### S3 Risk Frontier

Source:
[`p2_vd_frontier_s3/results.json`](../../../artifacts/p2_vd_frontier_s3/results.json)

| Player | All-attack | Median first potion HP | Unused potions on loss | Safe potion | Danger potion | Lethal potion | High-roll recovery | Risk-band delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FlashLite-S3-RISK | 0.00% | 39 | 0.00% | 0.00% | 47.44% | 100.00% | 48.33% | 4.47% |
| GPT4oMini-S0-AO | 0.00% | 79 | 0.00% | 42.56% | 97.62% | 0.00% | 29.25% | 11.57% |

Read: behaviorally, the models used different risk policies. FlashLite-S3-RISK
avoided safe-zone potion waste and healed in lethal-zone states; GPT4oMini-S0-AO
used many safe-zone potions and had no observed lethal-zone potion opportunities
under this scorer. The outcome claim remains weak because the VD frontier cell
was seat-confounded and not statistically significant.

## Condensed Story

The behavioral layer supports a stronger narrative than win rate alone:

1. **S0 failure mode:** FlashLite often attacked through danger and lost with
   unused potions.
2. **S1 repair:** structured reasoning reduced attack-only collapse and improved
   critical recovery.
3. **S3 FixedDamage policy:** HP grounding moved FlashLite toward the intended
   20 HP survival threshold.
4. **S3 VariableDamage policy:** risk-band grounding moved FlashLite toward
   stochastic risk management instead of a fixed threshold.
5. **Frontier nuance:** FixedDamage supports the cross-tier claim; VariableDamage
   shows strong behavioral repair but weak cross-tier outcome evidence due to
   seat effects.

## Product Gap

AgentDeck generates these metrics, but the current deterministic `results.md`
does not yet include a compact behavioral profile section. For presentation and
research handoff, a future `results.md` section should automatically render
per-cell behavioral-profile summaries when `behavioral_profile` is present.
