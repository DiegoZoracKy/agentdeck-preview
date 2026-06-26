# SPEC-MATCH-SURFACE-PROJECTION: Match Surface Projector

> Status: Final
> Version: 0.2.0
> Last Updated: 2026-06-26
> Implementation: ✅ Implemented in `agentdeck.spectators.match_surface`
> Review State: consensus-approved
> Audience: Core contributors, spectator authors, artifact pipeline maintainers

## 1. Purpose

Define the Core-owned projection layer that turns AgentDeck match events into a stable Match Surface protocol for viewer-facing consumers.

The projector is not a replay engine and not a research scorer. It is a read-only spectator that consumes canonical Core events from live play or replay and emits surface data through pluggable sinks.

## 2. Scope & Philosophy Alignment

- Upholds `SPEC.md` separation: Core produces evidence; viewers present it.
- Builds on `SPEC-SPECTATOR.md`: `MatchSurfaceProjector` is an observer, not a game participant.
- Builds on `SPEC-GAMEPLAY-EVENT-DATA.md`: the projector consumes one canonical gameplay shape.
- Preserves replay parity: the same match through live play or replay must produce equivalent Match Surface output.
- Non-goals: frontend routing, UI layout, external distribution policy, research findings, game runtime logic, and interactive human input.

## 3. Responsibilities

- Consume lifecycle and gameplay events as a read-only spectator.
- Project canonical `GAMEPLAY` events into frame objects suitable for inspection.
- Preserve enough raw state, action, reasoning, interaction, cost, and timing data for downstream inspection of each decision.
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
    "curation": {...},  # optional, only when a curation sidecar is imported
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

### 4.4 Static Curation Metadata

Static artifact export MAY import a `MatchCurator` sidecar for the same record.

```python
MatchSurfaceCuration = {
    "version": 1,
    "subtitle": "Short replay subtitle",
    "synopsis": "Replay synopsis for viewer selection and context.",
    "source": {
        "type": "curation_sidecar",
        "artifact": "match_123.meta.json",
    },
}
```

Imported `highlights` become normal Match Surface markers:

```python
{
    "id": "curation-highlight-7-1",
    "phase_index": 6,
    "turn": 7,
    "source": "upstream",
    "rule": "curation_sidecar.highlight",
    "label": "Critical missed heal",
    "severity": "info",
    "data": {
        "kind": "mistake",
        "sidecar_version": 1,
        "sidecar_artifact": "match_123.meta.json",
    },
}
```

Sidecar `turn` values are 1-based viewer turns. The imported marker `phase_index` MUST be `turn - 1`. Sidecar `transcript`, when present, remains in the sidecar and MUST NOT be embedded in the Match Surface artifact.

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
- Receives the document after `MatchSurfaceProjector` has applied any configured redactor.
- v0 JSON artifact export is intended for replay-from-record inputs, not live `play()` runs, so source timestamps come from the record rather than wall-clock playback.

### 5.5 Static Export Utility

`scripts/match_surface_export.py` is the thin CLI wrapper for static artifacts.

- Input: Recorder v2.0 match records.
- Output: one Match Surface JSON artifact per record.
- Optional sidecar input: a directory containing `<record-stem>.meta.json` curation sidecars.
- The utility MUST NOT contain viewer/product routing, frontend code, or external distribution policy.

## 6. Invariants & Guarantees

1. **MSP1 Read-Only**: The projector MUST NOT mutate game state, event payloads, players, or match results.
2. **MSP2 Core Event Input**: The projector consumes Core events only. It MUST NOT parse raw recorder files directly.
3. **MSP3 Gameplay Canonicality**: The projector assumes `SPEC-GAMEPLAY-EVENT-DATA.md` canonical gameplay data and MUST NOT normalize old v1.3 gameplay shapes.
4. **MSP4 Live/Replay Equivalence**: The same match through `.play()`, `.replay(match=...)`, and `.replay(path=...)` MUST produce equivalent Match Surface documents, ignoring explicitly allowed source timestamps.
5. **MSP5 Presentation, Not Research**: The projector MAY compute mechanical convenience data, such as state deltas and costs, but MUST NOT compute research findings.
6. **MSP6 Marker Provenance**: Every marker MUST declare whether it was computed by projection or imported from upstream.
7. **MSP7 Redaction Mechanism**: Core provides a redaction-capable projection/sink mechanism. Redaction rules are owned by the caller. The JSON artifact implementation applies redaction to the completed document before `finish`; future streaming sinks MUST apply the same policy before every externally emitted `start`, `frame`, or `finish` payload.
8. **MSP8 Sink Isolation**: Sink failures MUST be isolated like spectator failures: logged and surfaced without corrupting playback or game execution.
9. **MSP9 Source Provenance**: Static artifact export MUST propagate record-level `migration_provenance` into `MatchSurfaceDocument.source.provenance` when present.
10. **MSP10 Curation Import**: Static artifact export MAY import `MatchCurator` sidecars. Imported subtitle/synopsis MUST remain presentation metadata, imported highlights MUST become upstream markers, and sidecar transcripts MUST NOT be embedded.

## 7. Data Flow & Interaction

```text
Live:
  AgentDeck.play() -> EventBus -> MatchSurfaceProjector -> future streaming sink

Replay:
  AgentDeck.replay() / ReplayEngine -> EventBus -> MatchSurfaceProjector -> JsonArtifactSink

Tests:
  ReplayEngine(speed=0) -> MatchSurfaceProjector -> InMemorySink
```

## 8. Error Handling & Edge Cases

- Missing canonical gameplay fields SHOULD fail the projection test suite rather than silently producing partial frames.
- Redactor exceptions MUST fail artifact writing for that match; emitting unredacted data is worse than no artifact.
- Streaming sinks MUST NOT emit unredacted per-frame payloads; per-frame redaction is deferred with the streaming sink work and is not implemented by the v0 `JsonArtifactSink` path.
- Marker provider exceptions MUST be isolated and recorded in projector diagnostics; they MUST NOT prevent base frames from being emitted unless configured as strict.
- Projector output MUST remain useful for partial-information games; it must not require hidden state or omniscient game logic.
- Missing adjacent sidecars are tolerated when no sidecar directory is configured.
- When a sidecar directory is explicitly configured, a missing or invalid matching sidecar MUST fail export for that record.

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
- Unit-test static artifact post-processing before disk write.
- Unit-test sink failure isolation.
- Unit-test marker provenance rules.
- Unit-test static export propagation of `migration_provenance`.
- Unit-test static export sidecar import for curation metadata and highlight markers.

## 11. Design Rationale

- Core owns the projection seam because it already owns play/replay parity and spectators.
- Viewer-facing consumers should consume a stable Match Surface protocol rather than parse Core recorder internals.
- A sink interface keeps static artifacts and future streaming on the same projection contract without building streaming features now.
- Static export imports sidecars at the artifact boundary so `MatchSurfaceProjector` remains a Core event spectator and never parses recorder or sidecar files directly.

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
