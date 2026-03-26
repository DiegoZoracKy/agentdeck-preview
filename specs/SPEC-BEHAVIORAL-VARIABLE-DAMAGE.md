# SPEC-BEHAVIORAL-VARIABLE-DAMAGE: VariableDamage Behavioral Profile

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-03-26
> Implementation: ✅ Complete (`src/agentdeck/games/examples/variable_damage/behavioral.py`)
> Audience: Research engineers, experiment authors, contributors

## 1. Purpose
- Define the first VariableDamage behavioral profile on top of the global scorer contract in `SPEC-RESEARCH-BEHAVIORAL`.
- Turn VariableDamage recordings into inspectable policy questions about risk handling, survival margin, and stochastic response quality.
- Preserve as much continuity with the FixedDamage behavioral layer as possible while replacing exact-damage thresholds with deterministic risk bands.

## 2. Scope & Philosophy Alignment
- Extends [`SPEC-RESEARCH-BEHAVIORAL`](./SPEC-RESEARCH-BEHAVIORAL.md).
- Uses the rules and visibility contract defined by [SPEC-GAME-VARIABLE-DAMAGE](../src/agentdeck/games/examples/variable_damage/SPEC-GAME-VARIABLE-DAMAGE.md).
- Keeps the profile recorder-driven:
  - no model-side instrumentation
  - no hidden prompt annotations
  - no hand-labeled “good move” data
- Separates descriptive metrics from heuristic quality metrics.
- Non-goals:
  - defining a universal optimal policy for stochastic combat
  - proving whether a move is globally correct in expectation
  - replacing the outcome layer (`win_rate`, cost, latency, strictness)

## 3. Responsibilities
- Define the normalized turn record for VariableDamage scoring.
- Define deterministic risk bands derived from config, not from hand-picked thresholds.
- Define which metrics remain required because they generalize well from FixedDamage.
- Define new VariableDamage-specific risk metrics for the first scorer implementation.
- Surface early-heal conservatism and mid-risk calibration as first-class metrics rather than forcing readers to derive them from raw state buckets.
- Require evidence for derived metrics whose meaning is not self-evident from a single scalar.

## 4. Data Structures

### 4.1 Profile Identity
- `game_id = "variable_damage"`
- `profile_id = "variable_damage_behavioral"`
- `profile_version = "0.1.0"`

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

Config-derived fields:
- `min_attack_damage: int`
- `max_attack_damage: int`
- `potion_heal: int`
- `max_health: int`

Recorder-derived optional helper fields:
- `damage_dealt: int | null`
  - computed from HP delta when an `ATTACK` resolves

Visibility rule:
- Grounding and consistency metrics MUST use only the acting player’s visible state at decision time.

### 4.3 Risk Bands
The profile defines three deterministic HP risk bands from config:

- **Lethal zone**
  - `own_hp <= max_attack_damage`
  - one opponent `ATTACK` can end the game immediately
- **Danger zone**
  - `max_attack_damage < own_hp <= max_attack_damage + potion_heal`
  - one opponent `ATTACK` cannot kill immediately, but can push the player into or through the lethal band after a greedy exchange
- **Safe zone**
  - `own_hp > max_attack_damage + potion_heal`
  - one opponent `ATTACK` still leaves a full-heal buffer

These band boundaries MUST be config-driven and deterministic.

For finer-grained danger analysis, the profile also defines a config-derived danger split:

- `danger_split_hp = min(max_attack_damage + potion_heal, min_attack_damage + max_attack_damage)`

This yields two sub-bands inside danger:

- **Lower danger**
  - `max_attack_damage < own_hp <= danger_split_hp`
  - even a minimum-damage opponent `ATTACK` moves the player into the lethal zone
- **Upper danger**
  - `danger_split_hp < own_hp <= max_attack_damage + potion_heal`
  - a low roll still leaves the player in danger, but not yet lethal

With the default config (`15..25` damage, `30` heal), the split is:

- lower danger: `26..40`
- upper danger: `41..55`

### 4.4 State Buckets
- **Coarse state bucket**
  - `(position, own_hp, own_potions)`
  - used for action-by-state summaries and position-policy comparison
- **Risk bucket**
  - `(position, risk_band, own_potions)`
  - used for VariableDamage-specific risk metrics
- **Risk scarcity bucket**
  - `(risk_band, scarcity_bucket)`
  - where `scarcity_bucket in {"one", "multiple"}`
  - used for promoted summaries of whether the policy changes when only one potion remains
- **Decision-equivalence key**
  - `(position, own_hp, own_potions, last_action_self, last_action_opponent)`
  - used for state-action consistency

### 4.5 Profile Constants
- `CONSISTENCY_MIN_SUPPORT = 2`
- `POSITION_DELTA_MIN_SUPPORT_PER_POSITION = 2`
- `RISK_BAND_MIN_SUPPORT = 2`
- `EVIDENCE_MAX_EXAMPLES = 3`

If a future profile revision changes these values, it MUST bump `profile_version`.

### 4.6 Recorder Dependency Note
The scorer will often need realized HP deltas to explain stochastic outcomes.

Therefore:
- if recorder events expose both `state_before` and `state_after` for each gameplay event, the scorer SHOULD compute `damage_dealt` from those paired states
- if `state_after` is unavailable in a future payload shape, the scorer MUST reconstruct realized damage from adjacent canonical state observations or mark the affected metrics unsupported

This dependency belongs to scorer implementation, not the game contract, but it must be acknowledged up front because VariableDamage quality metrics depend on realized transitions rather than a single fixed constant.

## 5. Public API

### 5.1 `VariableDamageBehavioralScorer.score(*, players, match_payloads, config=None) -> BehavioralProfileResult`

Compute the VariableDamage behavioral profile from recorder match payloads.

**Contract**:
- MUST follow the global scorer contract in `SPEC-RESEARCH-BEHAVIORAL`
- MUST emit the required metrics in §6 unless a metric is explicitly listed in `unsupported_metrics`
- MUST use only recorder payloads and the published VariableDamage rules
- MUST treat partial-information visibility honestly: descriptive policy metrics use only the acting player’s visible state

## 6. Metric Definitions

### 6.1 Required Descriptive Metrics

#### `action_by_state`
- Scope:
  - `state_metrics`
- Definition:
  - For each coarse state bucket, count `ATTACK` and `POTION` actions and emit both counts and rates.
- Purpose:
  - Preserve direct policy inspection continuity with FixedDamage.

#### `action_by_risk_band`
- Scope:
  - `state_metrics`
- Definition:
  - For each risk bucket `(position, risk_band, own_potions)`, count `ATTACK` and `POTION` actions and emit both counts and rates.
- Purpose:
  - Make the stochastic risk policy inspectable without relying only on exact HP buckets.

#### `all_attack_match_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Fraction of matches in which the player takes `ATTACK` on every gameplay turn and never uses `POTION`.
- Purpose:
  - Detect policy lock into the simplest possible policy under uncertainty.

#### `first_potion_profile`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Record the acting HP on the first successful `POTION` in each match.
  - Also record `never_used_rate`.
- Required fields:
  - `median_first_potion_hp`
  - `first_potion_hp_values`
  - `never_used_rate`
- Purpose:
  - Preserve comparison continuity with FixedDamage.

#### `unused_potions_on_loss_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Among decisive losses, fraction where the player ends the match with potion count greater than `0`.
- Purpose:
  - Detect objective resource underuse without claiming perfect play.

#### `first_lethal_entry_inventory`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - For each match, identify the first acting turn where:
    - `own_hp <= max_attack_damage`
  - Record `own_potions` on that turn.
  - Also record matches where the player never enters the lethal zone.
- Required fields:
  - `median_potions_on_first_lethal_entry`
  - `first_lethal_entry_potion_values`
  - `zero_potions_rate`
  - `never_entered_rate`
- Purpose:
  - Describe how much inventory the player still has when it first faces a truly lethal decision.
  - This is descriptive only; reaching the lethal zone with `0` potions is not automatically a policy error.

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
  - Measure whether stochastic outcomes produce regime-switching or stable state-grounded policy.
- Evidence requirement:
  - MUST emit `evidence.per_player.<player>.state_action_consistency.examples`
  - each example MUST include:
    - `decision_key`
    - `consistency`
    - `support_turns`
    - `attack_count`
    - `potion_count`
    - `attack_rate`
    - `potion_rate`
    - `dominant_action`

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
  - Measure whether the policy itself changes by seat.
- Evidence requirement:
  - MUST emit `evidence.per_player.<player>.position_policy_delta.examples`
  - each example MUST compare one shared coarse state bucket across `first` and `second`

### 6.2 Required VariableDamage Risk Metrics

#### `lethal_zone_potion_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Among turns where:
    - `own_potions > 0`
    - `own_hp <= max_attack_damage`
  - compute the fraction of actions that are `POTION`
- Purpose:
  - Track immediate defensive response in the truly lethal band.

#### `safe_zone_potion_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Among turns where:
    - `own_potions > 0`
    - `own_hp > max_attack_damage + potion_heal`
  - compute the fraction of actions that are `POTION`
- Purpose:
  - Surface conservative or front-loaded healing directly.
  - This metric is broader than `wasted_full_health_potion_rate`, which is too narrow for VariableDamage.

#### `danger_zone_potion_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Among turns where:
    - `own_potions > 0`
    - `max_attack_damage < own_hp <= max_attack_damage + potion_heal`
  - compute the fraction of actions that are `POTION`
- Purpose:
  - Detect whether the player preserves margin or over-pressures before entering the lethal band.

#### `lower_danger_zone_potion_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Among turns where:
    - `own_potions > 0`
    - `max_attack_damage < own_hp <= danger_split_hp`
  - compute the fraction of actions that are `POTION`
- Purpose:
  - Measure whether the player heals when even a minimum-damage hit would push it into the lethal zone.

#### `upper_danger_zone_potion_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Among turns where:
    - `own_potions > 0`
    - `danger_split_hp < own_hp <= max_attack_damage + potion_heal`
  - compute the fraction of actions that are `POTION`
- Purpose:
  - Separate high-danger pressure from lower-urgency buffer preservation.

#### `lethal_zone_attack_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Same support set as `lethal_zone_potion_rate`, but measure `ATTACK` frequency.
- Purpose:
  - Make self-destructive aggression explicit.

#### `danger_zone_attack_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - Same support set as `danger_zone_potion_rate`, but measure `ATTACK` frequency.
- Purpose:
  - Capture risk-seeking behavior in the forward-projection band.

#### `risk_band_potion_rate_by_scarcity`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - For each `risk_band in {"lethal", "danger", "safe"}`, group turns with `own_potions > 0` into:
    - `one`: `own_potions == 1`
    - `multiple`: `own_potions >= 2`
  - Emit a `(risk_band, scarcity_bucket)` entry only when support for that entry is at least `RISK_BAND_MIN_SUPPORT`.
  - Emit potion rates and support counts for each `(risk_band, scarcity_bucket)` pair.
- Purpose:
  - Surface whether the policy changes when the player is down to its last potion.
  - This is a promoted summary of information that would otherwise be buried in `action_by_risk_band`.

#### `risk_band_policy_delta`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - For each shared risk bucket `(risk_band, own_potions)` observed in both positions with support >= `RISK_BAND_MIN_SUPPORT` per side, compute:
    - `abs(P(ATTACK | first, band, potions) - P(ATTACK | second, band, potions))`
  - Aggregate as the support-weighted mean across eligible buckets.
- Purpose:
  - Compare seat sensitivity at a more meaningful abstraction than exact HP.
- Evidence requirement:
  - MUST emit `evidence.per_player.<player>.risk_band_policy_delta.examples`
  - each example MUST include:
    - `shared_risk_key`
    - `delta`
    - `support_turns`
    - `first.attack_rate`
    - `first.potion_rate`
    - `second.attack_rate`
    - `second.potion_rate`

#### `high_roll_recovery_rate`
- Scope:
  - `per_player`
  - `aggregate_metrics`
- Definition:
  - A high-roll shock event is a gameplay transition where the player survives an opponent `ATTACK` and the realized damage is in the top half of the configured range.
  - Recovery is counted when the player's next turn in the same match that still begins in either the lethal zone or the danger zone uses `POTION`.
  - If the player reaches a later turn that begins in the safe zone before using `POTION`, that shock event does not count as recovered.
  - `high_roll_recovery_rate` is the fraction of supported shock events that recover on that next eligible turn.
- Purpose:
  - Measure whether the policy stabilizes after an unusually bad sampled outcome.
- Dependency note:
  - This metric requires reliable reconstruction of realized damage from recorder state transitions.
  - If realized damage cannot be reconstructed, the metric MUST be listed in `unsupported_metrics`.

### 6.3 Optional Heuristic Metrics
These MAY remain unsupported in `v0.1.0` if declared explicitly.

#### `wasted_full_health_potion_rate`
- Definition:
  - Fraction of `POTION` actions taken at `own_hp == max_health`.
- Purpose:
  - Same hard-waste metric carried forward from FixedDamage.

## 7. Invariants & Guarantees
- `VD-B1`: State-grounded descriptive metrics MUST use only the acting player's visible state.
- `VD-B2`: Risk bands MUST be derived solely from `max_attack_damage` and `potion_heal`, not hand-tuned package thresholds.
- `VD-B2a`: The danger sub-band split MUST be derived solely from `min_attack_damage`, `max_attack_damage`, and `potion_heal`.
- `VD-B3`: Required metrics in §6.1 and §6.2 MUST be emitted unless explicitly listed in `unsupported_metrics`.
- `VD-B4`: All rates MUST be reported in `[0.0, 1.0]`.
- `VD-B5`: Support thresholds MUST be deterministic and documented.
- `VD-B6`: Evidence-bearing metrics MUST emit deterministic evidence payloads.
- `VD-B7`: Metrics that depend on realized stochastic transitions MUST fail loudly or declare themselves unsupported when recorder support is insufficient.

## 8. Error Handling & Edge Cases
- Mixed-game payloads MUST be rejected.
- Missing required config (`max_attack_damage`, `potion_heal`) MUST fail fast or force dependent metrics into `unsupported_metrics`.
- Missing `min_attack_damage` MUST fail fast or force metrics that depend on `danger_split_hp` into `unsupported_metrics`, including:
  - `lower_danger_zone_potion_rate`
  - `upper_danger_zone_potion_rate`
- Empty input sets MUST still return a valid behavioral profile with zero coverage.
- If realized damage cannot be reconstructed, metrics depending on realized rolls MUST be declared unsupported rather than guessed.

## 9. Examples

### 9.1 Risk-Band Interpretation
- `own_hp = 18`, `max_attack_damage = 25`
  - lethal zone
- `own_hp = 40`, `max_attack_damage = 25`, `potion_heal = 30`
  - lower danger
- `own_hp = 50`, `min_attack_damage = 15`, `max_attack_damage = 25`, `potion_heal = 30`
  - upper danger
- `own_hp = 80`, `max_attack_damage = 25`, `potion_heal = 30`
  - safe zone

### 9.2 Example Evidence Shape
```json
{
  "shared_risk_key": "risk=danger|potions=2",
  "delta": 0.5,
  "support_turns": 20,
  "first": {
    "attack_rate": 0.75,
    "potion_rate": 0.25
  },
  "second": {
    "attack_rate": 0.25,
    "potion_rate": 0.75
  }
}
```

## 10. Testing Strategy
- Unit tests MUST cover:
  - correct risk-band assignment from config
  - correct lower/upper danger split assignment from config
  - support-threshold behavior
  - first lethal-entry inventory extraction
  - deterministic evidence ordering
  - unsupported-metric handling when realized damage cannot be reconstructed
  - reconstructed damage correctness when `state_before` and `state_after` are present
- Integration tests SHOULD cover:
  - scorer compatibility with real recorder payloads from VariableDamage matches
  - reproducibility across repeated exports of the same recordings

## 11. Design Rationale
- The FixedDamage `critical_hp_threshold = 2 * attack_damage` pattern does not transfer cleanly because VariableDamage has no single exact damage value.
- Risk bands preserve determinism while respecting uncertainty.
- VariableDamage experiments already showed that conservative healing behavior often lives in the safe zone rather than only at full health, so `safe_zone_potion_rate` is more useful than a full-health-only waste metric.
- The single danger bucket is too coarse for VariableDamage: lower danger and upper danger already show materially different behavior in the first baseline and controller packages.
- Keeping `all_attack_match_rate`, `first_potion_profile`, `state_action_consistency`, and `position_policy_delta` provides continuity with the FixedDamage arc.
- The paired `attack_rate` and `potion_rate` metrics inside each risk zone are redundant by design and should sum to `1.0`; both are emitted so readers do not need to infer the complement mentally.
- The promoted scarcity summary is not new raw information; it exists to make last-potion behavior legible without forcing readers to reconstruct it from fine-grained buckets.
- Adding realized-outcome metrics such as `high_roll_recovery_rate` lets the scorer measure response quality to stochastic shocks rather than only pre-action state policy.

## 12. Open Questions / Future Work
- Should later profile revisions add potion timing by match stage once VariableDamage packages have enough variation in match length?
- Should future versions add expected-value style metrics once a stronger baseline policy exists?
- Should later profile revisions add within-match damage adaptation metrics once longer trajectories provide enough support?
- Should the scorer emit explicit reconstructed `damage_dealt` samples under `state_metrics` for audit/debug workflows?

## 13. References
- [`SPEC-RESEARCH-BEHAVIORAL`](./SPEC-RESEARCH-BEHAVIORAL.md)
- [`SPEC-GAME-VARIABLE-DAMAGE`](../src/agentdeck/games/examples/variable_damage/SPEC-GAME-VARIABLE-DAMAGE.md)
- [`SPEC-GAME-FIXED-DAMAGE`](../src/agentdeck/games/examples/fixed_damage/SPEC-GAME-FIXED-DAMAGE.md)
- [`FixedDamage Arc 1`](../research/2026-03-23-fixed-damage-arc-1/README.md)
