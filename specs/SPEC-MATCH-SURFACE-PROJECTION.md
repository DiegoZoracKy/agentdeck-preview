# SPEC-MATCH-SURFACE-PROJECTION: Match Surface Projector

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-05-30
> Implementation: ⬜ Planned
> Review State: consensus-approved
> Audience: Core contributors, agentdeck.tv implementers, spectator authors, artifact pipeline maintainers

## 1. Purpose

Define the Core-owned projection layer that turns AgentDeck match events into a stable Match Surface protocol for viewers such as agentdeck.tv.

The projector is not a replay engine and not a research scorer. It is a read-only spectator that consumes canonical Core events from live play or replay and emits viewer-ready surface data through pluggable sinks.

## 2. Scope & Philosophy Alignment

- Upholds `SPEC.md` separation: Core produces evidence; viewers present it.
- Builds on `SPEC-SPECTATOR.md`: `MatchSurfaceProjector` is an observer, not a game participant.
- Builds on `SPEC-GAMEPLAY-EVENT-DATA.md`: the projector consumes one canonical gameplay shape.
- Preserves replay parity: the same match through live play or replay must produce equivalent Match Surface output.
- Non-goals: frontend routing, web UI layout, publishing policy, social sharing, research findings, game runtime logic, and live human input.

## 3. Responsibilities

- Consume lifecycle and gameplay events as a read-only spectator.
- Project canonical `GAMEPLAY` events into frame objects suitable for inspection.
- Preserve enough raw state, action, reasoning, interaction, cost, and timing data for a viewer to explain each decision.
- Expose sinks for static JSON artifacts and in-memory tests.
- Provide a redaction hook so callers can remove private fields before writing artifacts.
- Avoid computing research findings or editorial claims.

## 4. Data Structures

### 4.1 MatchSurfaceDocument

```python
MatchSurfaceDocument = {
    "schema_type": "match_surface",
    "schema_version": "0.1",
    "source": {
        "record_schema_version": "2.0",
        "match_id": "match_123",
        "provenance": {...},
    },
    "match": {
        "match_id": "match_123",
        "game": "FixedDamageGame",
        "seed": 2026047710,
        "winner": "Alice",
        "turns": 23,
        "metadata": {...},
    },
    "players": [...],
    "frames": [...],
    "markers": [],
    "economics": {...},
}
```

### 4.2 MatchSurfaceFrame

```python
MatchSurfaceFrame = {
    "phase_index": 0,
    "mechanic": "turn_based",
    "player": "Alice",
    "state_before": {...},
    "state_after": {...},
    "state_delta": {...},
    "action": {
        "value": "ATTACK",
        "reasoning": "...",
        "metadata": {...},
    },
    "interaction": {...},
    "economics": {
        "usage_info": {...},
        "cost": 0.0001,
        "latency_ms": 1234,
    },
    "markers": [],
    "source_event": {
        "type": "gameplay",
        "timestamp": 1700000000.0,
        "context": {...},
    },
}
```

`state_delta` is a deterministic convenience projection. It MUST be derived mechanically from `state_before` and `state_after` and MUST NOT contain interpretive labels.

### 4.3 Markers

Markers are optional projection annotations, not raw gameplay data.

```python
{
    "id": "invalid_action",
    "phase_index": 7,
    "source": "projector" | "upstream",
    "rule": "deterministic rule or upstream scorer id",
    "label": "Invalid action",
    "severity": "info" | "warning" | "critical",
    "data": {...},
}
```

The projector MAY attach mechanical markers from explicit marker providers. It MUST NOT invent behavioral findings such as "panicked" or "underreacted" unless those findings are imported from an upstream scorer with provenance.

## 5. Public API

### 5.1 MatchSurfaceProjector

```python
class MatchSurfaceProjector(Spectator):
    def __init__(
        self,
        *,
        sink: MatchSurfaceSink,
        redactor: Optional[Callable[[dict], dict]] = None,
        marker_providers: Optional[list[MarkerProvider]] = None,
    ) -> None: ...

    def on_match_start(self, game, players, match_id=None, context=None, **kwargs) -> None: ...
    def on_gameplay(self, event: Event) -> None: ...
    def on_match_end(self, result, context=None) -> None: ...
```

### 5.2 MatchSurfaceSink

```python
class MatchSurfaceSink(Protocol):
    def start(self, document: dict) -> None: ...
    def frame(self, frame: dict) -> None: ...
    def finish(self, document: dict) -> None: ...
```

### 5.3 InMemorySink

- Stores the latest completed `MatchSurfaceDocument` in memory.
- Used by parity and projection tests.
- MUST preserve deterministic ordering.

### 5.4 JsonArtifactSink

- Writes one deterministic JSON artifact per match.
- MUST use atomic write semantics.
- MUST sort object keys where practical and avoid nondeterministic generated timestamps unless supplied by caller/source metadata.
- MUST apply the redactor before writing.

## 6. Invariants & Guarantees

1. **MSP1 Read-Only**: The projector MUST NOT mutate game state, event payloads, players, or match results.
2. **MSP2 Core Event Input**: The projector consumes Core events only. It MUST NOT parse raw recorder files directly.
3. **MSP3 Gameplay Canonicality**: The projector assumes `SPEC-GAMEPLAY-EVENT-DATA.md` canonical gameplay data and MUST NOT normalize old v1.3 gameplay shapes.
4. **MSP4 Live/Replay Equivalence**: The same match through `.play()`, `.replay(match=...)`, and `.replay(path=...)` MUST produce equivalent Match Surface documents, ignoring explicitly allowed source timestamps.
5. **MSP5 Presentation, Not Research**: The projector MAY compute mechanical convenience data, such as state deltas and costs, but MUST NOT compute research findings.
6. **MSP6 Marker Provenance**: Every marker MUST declare whether it was computed by projection or imported from upstream.
7. **MSP7 Redaction Mechanism**: Core provides a redaction-capable sink mechanism. Publishing policy and redaction rules are owned by the caller, such as agentdeck.tv.
8. **MSP8 Sink Isolation**: Sink failures MUST be isolated like spectator failures: logged and surfaced without corrupting playback or game execution.

## 7. Data Flow & Interaction

```text
Live:
  AgentDeck.play() -> EventBus -> MatchSurfaceProjector -> JsonArtifactSink

Replay:
  AgentDeck.replay() / ReplayEngine -> EventBus -> MatchSurfaceProjector -> JsonArtifactSink

Tests:
  ReplayEngine(speed=0) -> MatchSurfaceProjector -> InMemorySink
```

## 8. Error Handling & Edge Cases

- Missing canonical gameplay fields SHOULD fail the projection test suite rather than silently producing partial frames.
- Redactor exceptions MUST fail artifact writing for that match; publishing unredacted data is worse than no artifact.
- Marker provider exceptions MUST be isolated and recorded in projector diagnostics; they MUST NOT prevent base frames from being emitted unless configured as strict.
- Projector output MUST remain useful for partial-information games; it must not require hidden state or omniscient game logic.

## 9. Examples

### 9.1 Static Artifact Export

```python
from agentdeck.core.recorder import Recorder
from agentdeck.core.replay import ReplayEngine
from agentdeck.spectators.match_surface import JsonArtifactSink, MatchSurfaceProjector

record = Recorder.load_match("records/match_123.json")
sink = JsonArtifactSink(output_dir="artifacts/match_surface")
projector = MatchSurfaceProjector(sink=sink, redactor=public_redactor)

ReplayEngine(record).replay(spectators=[projector], speed=0)
```

### 9.2 Test Projection

```python
sink = InMemorySink()
projector = MatchSurfaceProjector(sink=sink)

deck.replay(match=match_result, spectators=[projector], speed=0)

assert sink.document["schema_type"] == "match_surface"
assert sink.document["frames"][0]["action"]["value"] == "ATTACK"
```

## 10. Testing Strategy

- Unit-test the projector with synthetic canonical `GAMEPLAY` events.
- Integration-test projector output equivalence for `.play()`, `.replay(match=...)`, and `.replay(path=...)`.
- Unit-test deterministic JSON output for identical input.
- Unit-test redactor application before disk write.
- Unit-test sink failure isolation.
- Unit-test marker provenance rules.

## 11. Design Rationale

- Core owns the projection seam because it already owns play/replay parity and spectators.
- agentdeck.tv should consume a stable Match Surface protocol rather than parse Core recorder internals.
- A sink interface keeps static v0 artifacts and future live streaming on the same projection contract without building live features now.

## 12. Open Questions / Future Work

- SSE/WebSocket sinks for live viewing.
- Web human input bridge and seat model.
- Challenge recipes and mid-match branching.
- Cartridge-specific scene projections beyond the universal decision surface.

## 13. References

- [SPEC.md](SPEC.md)
- [SPEC-GAMEPLAY-EVENT-DATA.md](SPEC-GAMEPLAY-EVENT-DATA.md)
- [SPEC-SPECTATOR.md](SPEC-SPECTATOR.md)
- [SPEC-RECORDER.md](SPEC-RECORDER.md)
- [SPEC-REPLAY.md](SPEC-REPLAY.md)
- `docs/planning/ROADMAP-MATCH-SURFACE.md`
