# SPEC-BEHAVIORAL-METRICS: FixedDamage Behavioral Profile

> Status: Draft v0.2.0
> Version: 0.2.0
> Last Updated: 2026-03-19
> Implementation: ✅ Existing component (`src/agentdeck/games/examples/fixed_damage/behavioral.py`)
> Authors: Codex (draft)
> Audience: Research engineers, experiment authors, contributors

## 1. Purpose
- Define the first concrete AgentDeck behavioral scorer profile using `FixedDamageGame`.
- Turn FixedDamage recordings into measurable policy questions instead of relying on manual replay inspection alone.
- Provide the reference example of how a game-specific behavioral profile extends the global contract in `SPEC-RESEARCH-BEHAVIORAL`.

## 2. Scope & Philosophy Alignment
- Extends the global behavioral scorer contract in [`SPEC-RESEARCH-BEHAVIORAL`](../../specs/SPEC-RESEARCH-BEHAVIORAL.md).
- Uses the rules and visibility contract defined by [`SPEC-GAME-FIXED-DAMAGE`](../../src/agentdeck/games/examples/fixed_damage/SPEC-GAME-FIXED-DAMAGE.md).
- Keeps the profile simple and recorder-driven: no model-side instrumentation, no custom match annotations, no hand-read labeling.
- Separates descriptive metrics from heuristic quality judgments.
- Non-goals:
  - claiming broad reasoning, memory, or theory-of-mind measurements
  - replacing the outcome layer (`win_rate`, cost, latency)
  - defining a general optimal-play oracle for all FixedDamage states

## 3. Responsibilities
- Define the normalized state buckets this profile uses.
- Define which FixedDamage behavioral metrics are required for the first scorer implementation.
- Define which FixedDamage metrics are heuristic extensions and therefore optional in v0.2.0.
- Keep every metric grounded in recorder payloads and the published FixedDamage rules.

## 4. Data Structures

### 4.1 Profile Identity
- `game_id = "fixed_damage"`
- `profile_id = "fixed_damage_behavioral"`
- `profile_version = "0.2.0"`

### 4.2 Normalized Turn Record
The scorer derives one normalized turn record per `gameplay` event.

Minimum fields:
- `match_id: str`
- `player: str`
- `position: "first" | "second"`
- `turn_number: int`
- `action: "ATTACK" | "POTION"`
- `own_hp: int`
- `own_potions: int`
- `last_action_self: str | None`
- `last_action_opponent: str | None`

These fields MUST be derived from the acting player's visible state at decision time, not from hidden opponent state.

### 4.3 State Buckets
- **Coarse state bucket**
  - `(position, own_hp, own_potions)`
  - Used for action-by-state summaries and position-policy comparison.
- **Decision-equivalence key**
  - `(position, own_hp, own_potions, last_action_self, last_action_opponent)`
  - Used for state-action consistency.

The scorer MUST document which metrics use coarse state and which use the decision-equivalence key.

### 4.4 Profile Constants
- `CONSISTENCY_MIN_SUPPORT = 2`
  - Minimum support for a decision-equivalence key to contribute to `state_action_consistency`.
- `POSITION_DELTA_MIN_SUPPORT_PER_POSITION = 2`
  - Minimum support per position for a coarse state bucket to contribute to `position_policy_delta`.
- `SCARCITY_BUCKETS = [0, 1, 2, 3]`
  - Per-count buckets keyed by `own_potions` at decision time.
- `CRITICAL_POTION_HP_MULTIPLIER = 2`
  - Used by heuristic defensive-response metrics.
- `EVIDENCE_MAX_EXAMPLES = 3`
  - Maximum number of deterministic evidence examples emitted per metric and player.

If a future FixedDamage profile revision changes these values, it MUST bump `profile_version`.

## 5. Public API

### 5.1 `FixedDamageBehavioralScorer.score(*, players, match_payloads, config=None) -> BehavioralProfileResult`

Compute the FixedDamage behavioral profile from recorder match payloads.

**Contract**:
- MUST follow the global scorer contract in `SPEC-RESEARCH-BEHAVIORAL`.
- MUST emit the required metrics in §6 unless a metric is explicitly listed in `unsupported_metrics`.
- MUST use only recorder payloads and the FixedDamage rules published in `SPEC-GAME-FIXED-DAMAGE`.
- MUST treat partial-information visibility honestly: metrics about policy grounding and state equivalence use only the acting player's visible state.

## 6. Metric Definitions

### 6.1 Required Descriptive Metrics
These metrics are required for the first scorer implementation.

#### `action_by_state`
- Scope:
  - `state_metrics`
- Definition:
  - For each coarse state bucket, count `ATTACK` and `POTION` actions.
  - Emit both counts and rates.
- Purpose:
  - Make state-conditioned policy directly inspectable.

#### `all_attack_match_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Fraction of matches in which the player takes `ATTACK` on every gameplay turn and never uses `POTION`.
- Purpose:
  - Detect policy-lock into the simplest possible FixedDamage policy.

#### `first_potion_profile`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - For each player, record the acting HP on the first successful `POTION` in each match.
  - Also record `never_used_rate`: fraction of matches in which the player never uses `POTION`.
- Required fields:
  - `median_first_potion_hp`
  - `first_potion_hp_values`
  - `never_used_rate`
- Purpose:
  - Describe resource timing without collapsing all no-potion matches into a misleading median.

#### `unused_potions_on_loss_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Among decisive losses, fraction where the player ends the match with potion count greater than `0`.
- Purpose:
  - Capture a simple, objective form of failed resource use without claiming global optimality.

#### `state_action_consistency`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - For each decision-equivalence key with support >= `CONSISTENCY_MIN_SUPPORT`, compute:
    - `max(action_count) / total_count`
  - Aggregate per player as the support-weighted mean across eligible keys.
- Range:
  - `0.0` to `1.0`
- Purpose:
  - Distinguish stable state-conditioned policy from regime-switching behavior.

#### `position_policy_delta`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - For each coarse state bucket observed in both positions with support >= `POSITION_DELTA_MIN_SUPPORT_PER_POSITION` per side, compute:
    - `abs(P(ATTACK | first, state) - P(ATTACK | second, state))`
  - Aggregate as the support-weighted mean across shared buckets.
- Range:
  - `0.0` to `1.0`
- Purpose:
  - Measure whether the policy itself changes by position, not only whether win rate changes.
- Evidence requirement:
  - MUST emit `evidence.per_player.<player>.position_policy_delta.examples`
  - Each example MUST compare one shared coarse state bucket across `first` and `second`
  - Each example MUST include:
    - `shared_state_key`
    - `delta`
    - `support_turns`
    - `first.bucket_key`
    - `first.attack_rate`
    - `first.potion_rate`
    - `first.support_turns`
    - `first.source_path`
    - `second.bucket_key`
    - `second.attack_rate`
    - `second.potion_rate`
    - `second.support_turns`
    - `second.source_path`
  - Examples MUST be sorted by descending `delta`, then descending `support_turns`, then ascending `shared_state_key`
  - The scorer MUST emit at most `EVIDENCE_MAX_EXAMPLES`

#### `scarcity_action_profile`
- Scope:
  - `per_player`
  - `state_metrics`
- Definition:
  - Group turns by the per-count scarcity buckets in `SCARCITY_BUCKETS` and report `ATTACK` / `POTION` rates for each bucket.
- Purpose:
  - Show whether policy changes as resources become scarce.

#### `state_action_consistency` evidence
- Scope:
  - `evidence.per_player`
- Definition:
  - For supported decision-equivalence keys, emit up to `EVIDENCE_MAX_EXAMPLES` examples showing where consistency is weakest.
- Required fields per example:
  - `decision_key`
  - `consistency`
  - `support_turns`
  - `attack_count`
  - `potion_count`
- Ordering:
  - Sort by ascending `consistency`, then descending `support_turns`, then ascending `decision_key`
- Purpose:
  - Make low-consistency states inspectable without forcing readers to reconstruct them from aggregate rates alone.

### 6.2 Heuristic Quality Metrics
These metrics are allowed in the profile but MAY remain unsupported in v0.2.0 if they are declared explicitly in `unsupported_metrics`.

#### `critical_potion_response_rate`
- Definition:
  - Fraction of turns where the player chooses `POTION` when:
    - `own_potions > 0`
    - `own_hp <= CRITICAL_POTION_HP_MULTIPLIER * attack_damage`
- Interpretation:
  - A rule-based proxy for defensive urgency.
- Note:
  - This is heuristic, not an optimality proof.
  - `attack_damage` MUST be read from the FixedDamage game configuration present in the recording metadata or scorer config. If unavailable, the metric MUST be listed in `unsupported_metrics`.

#### `error_recovery_rate`
- Definition:
  - A missed defensive response is a turn where:
    - `own_potions > 0`
    - `own_hp <= CRITICAL_POTION_HP_MULTIPLIER * attack_damage`
    - `action == "ATTACK"`
  - Recovery is counted when the player's next eligible turn in the same critical condition uses `POTION`.
  - `error_recovery_rate` is the fraction of missed defensive responses that recover on that next eligible turn.
- Interpretation:
  - Measures whether a missed defensive opportunity compounds or self-corrects.
- Note:
  - This metric depends on the same `attack_damage` source requirement as `critical_potion_response_rate` and is therefore profile-heuristic.

#### `wasted_full_health_potion_rate`
- Definition:
  - Fraction of `POTION` actions taken at `own_hp == max_health`.
- Interpretation:
  - A hard-waste resource metric.
- Note:
  - `max_health` MUST be read from the FixedDamage game configuration present in the recording metadata or scorer config. If unavailable, the metric MUST be listed in `unsupported_metrics`.

## 7. Invariants & Guarantees
- **FD-B1**: This profile MUST score behavior from the acting player's visible state for grounding and consistency metrics.
- **FD-B2**: This profile MUST NOT use hidden opponent HP or potion count to define state buckets for descriptive policy metrics.
- **FD-B3**: Required descriptive metrics in §6.1 MUST be emitted unless declared unsupported by name.
- **FD-B4**: Heuristic metrics in §6.2 MUST be labeled as heuristic in any downstream presentation.
- **FD-B5**: The scorer MUST preserve `coverage` honestly when support thresholds exclude sparse states.
- **FD-B6**: All rates MUST be reported in `[0.0, 1.0]`.
- **FD-B7**: Support thresholds used by the profile MUST be deterministic and documented.
- **FD-B8**: Evidence-bearing metrics MUST emit deterministic evidence payloads following the ordering rules in this profile.
- **FD-B9**: Evidence examples MUST stay recorder-derived and MUST NOT introduce narrative or model-generated interpretation.

## 8. Data Flow & Interaction
- Recorder payloads:
  - `match_*.json -> gameplay events -> normalized turn records`
- Descriptive metrics:
  - `normalized turn records -> action_by_state / consistency / position delta / scarcity profile`
- Heuristic metrics:
  - `normalized turn records + FixedDamage rule thresholds -> recovery / critical response metrics`
- Research package use:
  - `FixedDamageBehavioralScorer -> behavioral profile artifact -> analysis / viewer narrative`

## 9. Error Handling & Edge Cases
- If a match lacks `gameplay` events, it contributes to `matches_total` but not `matches_evaluable`.
- If a player never appears in a position, `position_policy_delta` MUST use only shared supported buckets and coverage MUST reflect that.
- If a player never uses `POTION`, `first_potion_profile.median_first_potion_hp` MUST be `null` and `never_used_rate` MUST capture the behavior explicitly.
- If support for a state bucket is below the documented threshold, that bucket MUST be excluded from the derived rate and the scorer MUST keep aggregate coverage honest.
- If recording metadata does not expose `attack_damage`, heuristic defensive-response metrics MUST be listed in `unsupported_metrics` rather than inferred from hard-coded defaults.

## 10. Examples

### 10.1 `first_potion_profile`
```json
{
  "first_potion_profile": {
    "median_first_potion_hp": 40,
    "first_potion_hp_values": [40, 40, 60],
    "never_used_rate": 0.25
  }
}
```

### 10.2 `state_action_consistency`
```json
{
  "state_action_consistency": {
    "value": 0.94,
    "supported_state_keys": 18,
    "support_turns": 172
  }
}
```

### 10.3 `position_policy_delta`
```json
{
  "position_policy_delta": {
    "value": 0.61,
    "shared_state_buckets": 9,
    "support_turns": 144
  }
}
```

### 10.4 `position_policy_delta` evidence
```json
{
  "evidence": {
    "per_player": {
      "Haiku-TR": {
        "position_policy_delta": {
          "examples": [
            {
              "shared_state_key": "hp=80|potions=3",
              "delta": 1.0,
              "support_turns": 36,
              "first": {
                "bucket_key": "position=first|hp=80|potions=3",
                "attack_rate": 0.0,
                "potion_rate": 1.0,
                "support_turns": 12,
                "source_path": "state_metrics.action_by_state.Haiku-TR.position=first|hp=80|potions=3"
              },
              "second": {
                "bucket_key": "position=second|hp=80|potions=3",
                "attack_rate": 1.0,
                "potion_rate": 0.0,
                "support_turns": 24,
                "source_path": "state_metrics.action_by_state.Haiku-TR.position=second|hp=80|potions=3"
              }
            }
          ]
        }
      }
    }
  }
}
```

## 11. Testing Strategy
- Verify normalization uses visible-state fields only for descriptive metrics.
- Verify `all_attack_match_rate`, `first_potion_profile`, and `unused_potions_on_loss_rate` on hand-built match fixtures.
- Verify `state_action_consistency` and `position_policy_delta` on deterministic synthetic fixtures where the expected score is exact.
- Verify heuristic metrics remain absent only when listed in `unsupported_metrics`.
- Verify scorer determinism across repeated rescoring of the same FixedDamage recordings.

## 12. Design Rationale
- The first implementation prioritizes descriptive policy metrics over ambitious optimality claims. That keeps the profile useful without pretending FixedDamage measures more than it does.
- `first_potion_profile` is preferred over a single threshold metric because no-potion matches are a meaningful regime, not missing data.
- `position_policy_delta` is a load-bearing metric for this package because Haiku's inversion is about policy content, not just named-player outcome.
- Heuristic metrics are kept separate so the first scorer can ship objective policy descriptions before the project commits to a stronger quality oracle.

## 13. Open Questions / Future Work
- Should the profile add a stronger rule-based quality oracle once the descriptive layer is stable?
- Should `critical_potion_response_rate` use only HP and potion count, or should it incorporate visible last-action context?
- Should the profile expose a calibration-proximity score comparing model behavior to bundled bots, or should that remain an analysis-layer comparison?
  - Comparison to bundled bots can already be expressed in the analysis layer through existing metrics such as `all_attack_match_rate`; a new scorer metric may be unnecessary.

## 14. References
- [`SPEC-RESEARCH-BEHAVIORAL`](../../specs/SPEC-RESEARCH-BEHAVIORAL.md)
- [`SPEC-GAME-FIXED-DAMAGE`](../../src/agentdeck/games/examples/fixed_damage/SPEC-GAME-FIXED-DAMAGE.md)
- [`README.md`](./README.md)
- [`analysis.md`](./analysis.md)
