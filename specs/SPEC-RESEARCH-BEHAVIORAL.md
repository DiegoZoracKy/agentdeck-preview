# SPEC-RESEARCH-BEHAVIORAL: Behavioral Scoring Contract

> Status: Final
> Version: 0.2.0
> Last Updated: 2026-03-26
> Implementation: ✅ Complete (`src/agentdeck/research/behavioral.py`, game-specific scorer modules)
> Audience: Research engineers, game authors, contributors

## 1. Purpose
- Define a shared behavioral scoring layer for AgentDeck research packages so experiments can report not only who won, but how players behaved.
- Separate the outcome layer from the mechanism layer: outcomes answer comparative performance; behavioral scoring answers policy shape, consistency, and intervention response.
- Give future games a single extension contract so game-specific behavioral profiles plug into the same research pipeline instead of becoming one-off scripts.

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC.md` research-first framing: games are behavioral environments, not only score generators.
- Aligns with `SPEC.md` separation principles: live execution, recording, and post-hoc scoring remain separate concerns.
- Aligns with `SPEC.md` reproducibility guarantees: scorer output must be deterministic from recorder artifacts alone.
- Follows `CONTRIBUTING.md`: this spec defines the contract used by the current scorer stack.
- Non-goals:
  - defining what counts as a good move for every game
  - replacing `SPEC-RESEARCH-EXPERIMENT.md` ownership of package schema
  - requiring every game to expose the same semantic metrics

This spec defines the scorer contract and payload shape. `results.json` integration remains owned by `SPEC-RESEARCH-EXPERIMENT.md`, but the behavioral payload is now wired through that optional extension.

## 3. Responsibilities
- Define the minimum contract for any behavioral scorer AgentDeck recognizes.
- Distinguish the game-agnostic behavioral baseline from game-specific profile metrics.
- Define a deterministic, JSON-serializable scorer payload shape.
- Require scorers to surface unsupported metrics explicitly rather than omitting them silently.
- Require scorers to expose deterministic evidence for profile-defined derived metrics so readers can trace "why this score happened" back to concrete states or events.
- Keep metric semantics profile-owned: the global contract defines shape and guarantees, while each game profile defines meaning.

## 4. Data Structures

### 4.1 Behavioral Layers
- **Universal behavioral baseline**
  - Derived from recorder artifacts without game-specific semantics.
  - Includes surfaces already covered elsewhere in the research stack, such as parseability, strict contract adherence, position dependence, and cost/latency summaries.
- **Behavioral profile**
  - Game-specific scorer output built on top of the same recorder artifacts.
  - Defines state-aware policy metrics such as resource timing, policy consistency, or role-conditioned behavior.

### 4.2 BehavioralProfileResult
Any scorer MUST return a JSON-serializable mapping with this minimum shape:

```json
{
  "schema_version": 2,
  "game_id": "fixed_damage",
  "profile_id": "fixed_damage_behavioral",
  "profile_version": "0.2.0",
  "coverage": {
    "matches_total": 24,
    "matches_evaluable": 24,
    "turns_total": 344,
    "turns_evaluable": 344
  },
  "aggregate_metrics": {},
  "per_player": {},
  "state_metrics": {},
  "evidence": {
    "aggregate_metrics": {},
    "per_player": {},
    "state_metrics": {}
  },
  "quality_flags": {
    "complete": true,
    "unsupported_metrics": []
  }
}
```

Required fields:
- `schema_version: int`
- `game_id: str`
- `profile_id: str`
- `profile_version: str`
- `coverage.matches_total: int`
- `coverage.matches_evaluable: int`
- `coverage.turns_total: int`
- `coverage.turns_evaluable: int`
- `aggregate_metrics: mapping`
- `per_player: mapping`
- `state_metrics: mapping`
- `evidence.aggregate_metrics: mapping`
- `evidence.per_player: mapping`
- `evidence.state_metrics: mapping`
- `quality_flags.complete: bool`
- `quality_flags.unsupported_metrics: list[str]`

### 4.3 Metric Namespaces
- `aggregate_metrics`
  - Dataset-level or cell-level metrics.
  - Examples: average policy-lock rate, aggregate position-policy delta, cross-match stability.
- `per_player`
  - Metrics keyed by player name or player id.
  - Used when the same scorer profile compares multiple named players or prompt conditions.
- `state_metrics`
  - Metrics keyed by scorer-defined state buckets.
  - Used for action-by-state tables, resource-trigger profiles, or other policy maps.

The global contract does not define the contents of these mappings beyond requiring them to be JSON-serializable. Their semantics belong to the profile spec.

### 4.4 Evidence Namespace
- `evidence.aggregate_metrics`
  - Profile-owned evidence for aggregate derived metrics.
- `evidence.per_player`
  - Profile-owned evidence keyed by player name and metric name.
- `evidence.state_metrics`
  - Optional evidence keyed by state-derived namespaces when a profile needs extra traceability beyond `state_metrics`.

Evidence entries MUST be deterministic, JSON-serializable, and derived from the same recorder inputs as the metric they support. Profiles MAY choose any internal evidence shape, but they MUST document it explicitly.
Evidence entries MUST be interpretable from the entry itself. Optional helper pointers or source references MAY be included, but they MUST NOT be the primary way a reader understands the evidence.

### 4.5 Coverage Semantics
- `matches_total`
  - Total matches provided to the scorer.
- `matches_evaluable`
  - Matches actually used for profile metrics after any scorer-defined exclusions.
- `turns_total`
  - Total gameplay turn attempts observed in the supplied payloads.
- `turns_evaluable`
  - Turn attempts actually used for profile metrics after any scorer-defined exclusions.

Coverage makes missing or unsupported behavior explicit instead of letting scorers silently undercount.

### 4.6 Player Metadata Input
`BehavioralScorer.score(...)` receives `players` as an ordered list of mappings.

Minimum required field per entry:
- `name: str`

Common optional fields:
- `provider: str`
- `model: str`
- `controller: str`
- `renderer: str`
- `type: str`

Scorers MUST treat this list as the canonical ordered player roster for the supplied payload set. Profile specs MAY require additional optional fields, but they MUST document them explicitly.

### 4.7 Canonical Serialization
The scorer contract is defined over JSON-compatible mappings, but auditability also requires stable persisted bytes.

AgentDeck canonical behavioral-profile serialization is:
- UTF-8 encoded JSON
- `sort_keys=true`
- `separators=(",", ":")`
- `ensure_ascii=true`
- `allow_nan=false`

When serialized with these settings, scorer output MUST be byte-identical for identical normalized inputs.

## 5. Public API

### 5.1 `BehavioralScorer.score(*, players, match_payloads, config=None) -> BehavioralProfileResult`

Compute a game-specific behavioral profile from recorder match payloads.

**Contract**:
- `players`
  - Ordered list of player metadata entries following §4.5.
- `match_payloads`
  - Recorder-derived match payloads.
  - The scorer MUST treat these as read-only.
- `config`
  - Optional scorer-specific configuration.
  - MUST affect output only through explicit deterministic rules.
- Return value
  - MUST follow `BehavioralProfileResult` in §4.2.
- The scorer MUST fail fast if required recorder fields are missing or malformed.
- The scorer MUST NOT perform network I/O, filesystem writes, or live match execution.

### 5.2 `BehavioralScorer` metadata
A recognized scorer MUST expose stable profile metadata:
- `game_id: str`
- `profile_id: str`
- `profile_version: str`

These identifiers allow experiment tooling to label the profile unambiguously and compare future revisions of the same scorer.

## 6. Invariants & Guarantees
- **BR1**: Behavioral scorers MUST be deterministic. Given identical normalized recording inputs and the canonical serialization settings in §4.7, they MUST produce byte-identical output.
- **BR2**: Behavioral scorers MUST NOT mutate `players`, `match_payloads`, or nested payload objects.
- **BR3**: Behavioral scorers MUST read from recorder artifacts only. They MUST NOT depend on live provider calls, current time, or external mutable state.
- **BR4**: Behavioral scorers MUST surface unsupported metrics by name in `quality_flags.unsupported_metrics`. Silent omission is prohibited.
- **BR5**: `quality_flags.complete` MUST be `true` only when the scorer produced every metric promised by its profile spec for the supplied inputs.
- **BR6**: Scorer outputs MUST be JSON-serializable without custom encoders.
- **BR7**: Game-specific metric semantics MUST live in the profile spec, not in this global contract.
- **BR8**: Universal behavioral metrics already owned by `SPEC-RESEARCH-EXPERIMENT.md` remain game-agnostic and MUST NOT be redefined with game-specific meaning here.
- **BR9**: If a scorer cannot evaluate a metric because the recording payload lacks required support, that metric MUST be either:
  - omitted and listed in `unsupported_metrics`, or
  - emitted with explicit zero coverage in the profile-defined shape.
- **BR10**: If a profile spec marks a metric as evidence-bearing, the scorer MUST emit deterministic supporting evidence for that metric under `evidence`.
- **BR11**: Evidence MUST be recorder-derived. It MUST NOT depend on external models, human-written annotations, or non-deterministic summaries.
- **BR12**: Evidence MUST remain self-explanatory. Helper pointers such as `source_path` MAY be emitted, but a reader MUST be able to understand the behavioral contrast from the evidence entry itself.

## 7. Data Flow & Interaction
- Live execution:
  - `Console -> Recorder -> match payloads`
- Universal research export:
  - `match payloads -> recording_metrics.py -> results.json baseline metrics`
- Behavioral profile scoring:
  - `match payloads + player metadata -> BehavioralScorer.score(...) -> BehavioralProfileResult`
- Future package integration:
  - `BehavioralProfileResult -> research export / package artifacts`

Adjacent ownership:
- Recorder payload ownership: `SPEC-RECORDER.md`
- Experiment package schema ownership: `SPEC-RESEARCH-EXPERIMENT.md`
- Game-specific metric meaning: profile-local spec (for example a FixedDamage behavioral profile)
- Archivist Choice score, completion, and post-hoc action-fit semantics: [SPEC-BEHAVIORAL-ARCHIVIST-CHOICE-v0.1.0.md](SPEC-BEHAVIORAL-ARCHIVIST-CHOICE-v0.1.0.md)

## 8. Error Handling & Edge Cases
- Missing required recorder fields MUST raise clear `ValueError` or `KeyError` with the missing field names.
- Empty input sets MUST return a valid `BehavioralProfileResult` with zero coverage rather than crashing.
- Mixed-game payloads MUST be rejected unless the scorer profile explicitly supports them.
- Unknown player identities in match payloads MUST fail fast rather than being merged implicitly.
- Unsupported metrics MUST be declared in `unsupported_metrics`, not inferred by downstream tooling.

## 9. Examples

### 9.1 Minimal Complete Result
```json
{
  "schema_version": 2,
  "game_id": "fixed_damage",
  "profile_id": "fixed_damage_behavioral",
  "profile_version": "0.2.0",
  "coverage": {
    "matches_total": 24,
    "matches_evaluable": 24,
    "turns_total": 344,
    "turns_evaluable": 344
  },
  "aggregate_metrics": {
    "position_policy_delta": 0.12
  },
  "per_player": {
    "Gemini-HO": {
      "all_attack_match_rate": 0.25
    }
  },
  "state_metrics": {
    "action_by_state": {}
  },
  "evidence": {
    "aggregate_metrics": {},
    "per_player": {
      "Gemini-HO": {
        "position_policy_delta": {
          "examples": []
        }
      }
    },
    "state_metrics": {}
  },
  "quality_flags": {
    "complete": true,
    "unsupported_metrics": []
  }
}
```

### 9.2 Partial Result With Explicit Unsupported Metrics
```json
{
  "quality_flags": {
    "complete": false,
    "unsupported_metrics": [
      "error_recovery_rate",
      "opponent_adaptation"
    ]
  }
}
```

### 9.3 Global vs Profile-Owned Semantics
- Global contract:
  - guarantees deterministic scorer output shape
  - requires explicit unsupported metric names
  - requires explicit evidence namespaces for profile-defined derived metrics
- Profile spec:
  - defines what `position_policy_delta` means for one game
  - defines which state buckets exist
  - defines whether a metric is descriptive or heuristic
  - defines which metrics require evidence and what that evidence contains

## 10. Testing Strategy
- Verify scorer determinism with identical payloads and canonical JSON serialization.
- Verify scorers reject malformed payloads with field-specific errors.
- Verify scorers preserve zero-coverage and empty-input behavior without crashing.
- Verify unsupported metrics are surfaced by name and affect `quality_flags.complete`.
- Verify evidence-bearing metrics emit deterministic evidence in the documented namespace.
- Verify profile-specific scorers only emit metrics documented by their profile spec.

## 11. Design Rationale
- The global contract is intentionally shape-only. Metric semantics are too game-dependent to centralize without overfitting the platform to one game.
- Explicit `unsupported_metrics` prevents silent gaps and makes partial scorers self-documenting.
- Determinism is a hard guarantee because behavioral rescoring must remain audit-friendly and reproducible from committed artifacts.
- The universal baseline and the profile layer stay separate so AgentDeck can reuse existing game-agnostic metrics without pretending every game exposes the same decision semantics.

## 12. Open Questions / Future Work
- Should the behavioral profile live inside `results.json` or as a sidecar artifact once the export integration lands?
- Should cross-cell comparative deltas be computed inside scorers or in a higher-level post-hoc comparison layer?

## 13. References
- `SPEC.md`
- `CONTRIBUTING.md`
- `SPEC-RESEARCH.md`
- `SPEC-RESEARCH-EXPERIMENT.md`
- `SPEC-RECORDER.md`
- `src/agentdeck/research/recording_metrics.py`
