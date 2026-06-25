# SPEC-GAMEPLAY-EVENT-DATA: Canonical Gameplay Payload

> Status: Final
> Version: 2.0.0
> Last Updated: 2026-05-31
> Implementation: ✅ Implemented in `EventFactory.turn`, `MatchRuntime.record_turn`, `Recorder`, `ReplayEngine`, and parity tests
> Review State: consensus-approved
> Audience: Core contributors, spectator authors, recorder/replay implementers, research tooling maintainers

## 1. Purpose

Define the canonical `GAMEPLAY` event payload that live play, in-memory replay, disk recording, and disk replay all expose to spectators.

This spec exists to remove the historical split where live events, recorded JSON, and replayed events carried equivalent information in different shapes. After this contract is implemented, spectators should not need defensive code for "live shape" vs "recorded shape".

## 2. Scope & Philosophy Alignment

- Upholds `SPEC.md` separation: games define rules, mechanics emit gameplay, spectators observe.
- Upholds `SPEC-REPLAY.md` parity: the same match must expose equivalent gameplay payloads in live and replay paths.
- Extends `SPEC-OBSERVABILITY.md`: `GAMEPLAY` is the framework-owned structural event; this file is the source of truth for its `event.data` shape.
- Non-goals: lifecycle event payloads, domain event payloads, presentation markers, research findings, and frontend artifacts.

## 3. Responsibilities

- Define the canonical `event.data` structure for `EventType.GAMEPLAY`.
- Define field ownership so action data, LLM interaction data, state snapshots, and phase context do not duplicate each other.
- Define serialization rules for Recorder v2.0 and ReplayEngine v2.0.
- Define the parity test obligation that prevents live/replay drift from returning.

## 4. Data Structures

### 4.1 GameplayEventData

```python
GameplayEventData = {
    "mechanic": "turn_based",
    "phase_index": 0,
    "player": "Alice",
    "state_before": {...},
    "state_after": {...},
    "turn_context": {...},
    "action": {
        "value": "ATTACK",
        "reasoning": "Opponent is low; attack is lethal.",
        "metadata": {...},
    },
    "interaction": {
        "prompt_text": "...",
        "prompt_blocks": [...],
        "response_text": "ACTION: ATTACK\nREASONING: ...",
        "usage_info": {...},
        "renderer_output": {...},
        "controller_format": "...",
        "controller_metadata": {...},
    },
}
```

### 4.2 Required Fields

| Field | Type | Required | Owner | Notes |
|-------|------|----------|-------|-------|
| `mechanic` | str | yes | Mechanic/runtime | Mechanic slug such as `turn_based`. |
| `phase_index` | int | yes | Mechanic/runtime | Zero-based canonical phase counter. |
| `player` | str | mechanic-dependent | Mechanic/runtime | Required for sequential single-actor mechanics; optional for simultaneous mechanics. |
| `state_before` | object | yes | Mechanic/runtime | JSON-safe state snapshot before the action. |
| `state_after` | object | yes | Mechanic/runtime | JSON-safe state snapshot after the action. |
| `turn_context` | object | yes | Mechanic/runtime | Mechanic metadata, including human turn number when available. |
| `action` | object | yes | Controller/player result | Parsed decision. See §4.3. |
| `interaction` | object | yes | Player/controller/renderer | LLM I/O and prompt metadata. See §4.4. |

### 4.3 Action

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `value` | JSON scalar/object | yes | Parsed action value. Use `value`, not `action.action`, to avoid stutter. |
| `reasoning` | str or null | yes | Parsed or extracted reasoning, null when unavailable. |
| `metadata` | object | yes | Controller/action metadata that is not LLM I/O. Defaults to `{}`. |

`action.raw_response` MUST NOT be serialized. The raw model output belongs only in `interaction.response_text`.

### 4.4 Interaction

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `prompt_text` | str or null | yes | Exact prompt text sent to the model when available. |
| `prompt_blocks` | list | yes | PromptBuilder block metadata. Defaults to `[]`. |
| `response_text` | str or null | yes | Raw model response before controller parsing. |
| `usage_info` | object or null | yes | Token, cost, and latency metadata when available. |
| `renderer_output` | object or null | yes | Renderer metadata used to construct the prompt. |
| `controller_format` | str or null | yes | Format instruction shown to the model. |
| `controller_metadata` | object or null | yes | Parse/validation metadata from the controller. |

Implementations MAY include additive JSON-safe keys under `interaction` when a player/provider exposes them, but they MUST NOT duplicate the required keys elsewhere in the gameplay payload.

### 4.5 State Snapshots

`state_before` and `state_after` are public gameplay snapshots, not full engine
runtime snapshots. Framework-owned private keys whose names begin with `_`, such
as `_turn_count` and `_first_player_idx`, MUST NOT appear in gameplay event state
snapshots. When those values are needed for replay, scoring, or reproducibility,
they belong in lifecycle metadata, match metadata, final state, or
`turn_context`, not in the public game-domain state.

## 5. Public API

This spec does not define a standalone public class. It constrains the payload emitted by:

- `EventFactory.turn(...)`
- `MatchRuntime.record_turn(...)`
- `Recorder.on_gameplay(...)`
- `ReplayEngine.replay(...)`
- spectators that consume `on_gameplay(event)`

## 6. Invariants & Guarantees

1. **GP1 Canonical Shape**: Every live `GAMEPLAY` event MUST use the shape in §4.
2. **GP2 No Alias Phase Key**: `phase_index` is the only structural phase key. `turn_index` MUST NOT be emitted as an alias. Human-facing turn numbers belong in `turn_context`.
3. **GP3 No Raw Response Duplication**: Raw model output MUST appear only at `interaction.response_text`.
4. **GP4 Recorder Verbatim Rule**: Recorder v2.0 MUST serialize the canonical gameplay payload without flattening `action`, nesting prompt fields, or moving fields between containers. JSON safety and private state sanitization are allowed.
5. **GP5 Replay Verbatim Rule**: ReplayEngine v2.0 MUST re-emit the recorded canonical gameplay payload without legacy-shape normalization.
6. **GP6 Spectator Parity**: A spectator attached to `.play()`, `.replay(match=...)`, and `.replay(path=...)` for the same match MUST observe equivalent `GAMEPLAY` event data.
7. **GP7 Marker Exclusion**: Presentation markers, behavioral scores, and research findings MUST NOT be stored in `GameplayEventData`. They belong in projection/scoring layers with explicit provenance.
8. **GP8 JSON Safety**: Every value in the serialized payload MUST be JSON-safe after recorder serialization.

## 7. Data Flow & Interaction

```text
TurnLoop -> MatchRuntime.record_turn()
  -> EventFactory.turn() builds GameplayEventData
  -> EventBus emits EventType.GAMEPLAY
  -> Recorder serializes canonical payload verbatim
  -> ReplayEngine re-emits canonical payload verbatim
  -> Spectators consume one shape
```

## 8. Error Handling & Edge Cases

- Missing required gameplay fields in live emission is a framework bug and SHOULD fail fast in tests.
- Missing optional provider metadata is represented by `null` or an empty container, not by moving fields elsewhere.
- Mechanics that are not sequential MAY omit `player` and use mechanic-specific fields such as `actions` inside `turn_context` or an additive field approved by a mechanic spec.
- Runtime code MUST NOT accept old v1.3 gameplay shapes as compatibility input after the v2.0 break.

## 9. Examples

### 9.1 Turn-Based Attack

```python
{
    "mechanic": "turn_based",
    "phase_index": 3,
    "player": "FlashLite-S1-RC",
    "state_before": {"players": {"FlashLite-S1-RC": {"hp": 20}}},
    "state_after": {"players": {"FlashLite-S1-RC": {"hp": 50}}},
    "turn_context": {"turn_number": 4, "rng_label": "turn_3"},
    "action": {
        "value": "POTION",
        "reasoning": "At 20 HP I can die next turn; healing is safer.",
        "metadata": {"validated": True},
    },
    "interaction": {
        "prompt_text": "Current game state...",
        "prompt_blocks": [{"key": "state", "chars": 420}],
        "response_text": "REASONING: ...\nACTION: POTION",
        "usage_info": {"prompt_tokens": 312, "completion_tokens": 44, "cost": 0.0001},
        "renderer_output": {"information_level": "partial"},
        "controller_format": "Reply with REASONING then ACTION.",
        "controller_metadata": {"allowed_actions": ["ATTACK", "POTION"]},
    },
}
```

## 10. Testing Strategy

- Unit-test `EventFactory.turn()` against the exact §4 shape.
- Unit-test `MatchRuntime.record_turn()` delegates to the same builder and emits no duplicate shape.
- Integration-test `.play()` vs `.replay(match=...)` vs `.replay(path=...)` with a deep structural comparison of gameplay event payloads.
- Unit-test Recorder v2.0 writes canonical gameplay payloads without reshaping.
- Unit-test ReplayEngine v2.0 re-emits canonical gameplay payloads without reshaping.
- Regression-test that no runtime path accepts old flat `action` + nested `prompt` gameplay shapes.

## 11. Design Rationale

- `interaction` is broader than `prompt`: it contains prompt, response, usage, renderer, and controller metadata.
- `phase_index` is mechanic-agnostic. `turn_index` was a turn-based alias that leaked into the framework contract.
- `action.value` names the parsed decision without repeating `action.action`.
- Markers are excluded so raw engine evidence remains separate from presentation and scoring layers.

## 12. Open Questions / Future Work

- If simultaneous or real-time mechanics need additional canonical fields, define them in the mechanic spec and add them here only when the need is proven.

## 13. References

- [SPEC.md](SPEC.md)
- [SPEC-OBSERVABILITY.md](SPEC-OBSERVABILITY.md)
- [SPEC-MATCH-RUNTIME.md](SPEC-MATCH-RUNTIME.md)
- [SPEC-RECORDER.md](SPEC-RECORDER.md)
- [SPEC-REPLAY.md](SPEC-REPLAY.md)
- [SPEC-MATCH-SURFACE-PROJECTION.md](SPEC-MATCH-SURFACE-PROJECTION.md)
