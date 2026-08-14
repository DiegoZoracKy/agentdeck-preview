# ROADMAP: Match Surface Core Cleanup

> Status: Core cleanup merged; static artifact completeness in progress
> Date: 2026-06-26
> Repository: AgentDeck Core
> Workflow: Follows `CONTRIBUTING.md` Phase A/B/C. This is a temporary planning note, not an authoritative spec.

## 1. Purpose

Make live play, in-memory replay, disk recording, and disk replay expose one canonical gameplay event language.

The current Core architecture already routes both `play()` and `replay()` through `EventBus` and spectators. This cleanup removes payload drift between live events, recorded JSON, and replayed events before relying on projected match artifacts.

## 2. Scope

Core owns:

- `play()` and `replay()`
- recorder and replay artifacts
- EventBus event delivery
- spectator contracts
- canonical gameplay event data
- Match Surface projection

Out of scope for this branch:

- interactive browser input
- session orchestration outside Core
- streaming sinks
- new game runtimes
- presentation UI
- long-term compatibility with retired v1.3 gameplay shapes

## 3. Locked Core Decisions

- Core makes a clean recorder schema break to v2.0.
- Runtime code remains v2-only after the break.
- Historical records that must be reused should be converted once rather than supported permanently by runtime compatibility paths.
- `MatchSurfaceProjector` is built only after live/replay gameplay event parity is explicit.
- Markers stay out of raw `GameplayEventData`; they belong in projection or scoring layers with provenance.
- The current viewer bundle remains tied to the old record shape unless separately updated.

## 4. Canonical GameplayEventData v2

`SPEC-GAMEPLAY-EVENT-DATA.md` is the authoritative contract.

```text
GameplayEventData v2
  mechanic: string
  phase_index: integer
  player: string
  state_before: object
  state_after: object
  turn_context: object

  action:
    value: string | object
    reasoning: string | null
    metadata: object

  interaction:
    prompt_text: string | null
    prompt_blocks: array
    response_text: string | null
    usage_info: object | null
    renderer_output: object | null
    controller_format: string | null
    controller_metadata: object | null
```

Resolved design notes:

- Use `action.value`, not `action.action`.
- Do not serialize `action.raw_response`; raw model output belongs at `interaction.response_text`.
- Use only `phase_index`; remove the `turn_index` alias.
- Keep action data, interaction metadata, state snapshots, and projection markers in separate containers.

## 5. Specification Work

Specs added or updated:

1. `SPEC-GAMEPLAY-EVENT-DATA.md`
   - Defines canonical gameplay payloads.
   - Defines JSON-safe serialization rules.
   - Defines live/replay parity invariants.
   - Defines ownership for action, interaction, state, and context fields.
2. `SPEC-MATCH-SURFACE-PROJECTION.md`
   - Defines `MatchSurfaceProjector` as a read-only spectator.
   - Defines `MatchSurfaceSink`.
   - Defines `InMemorySink` and `JsonArtifactSink`.
3. Dependent specs:
   - `SPEC-OBSERVABILITY.md`
   - `SPEC-MATCH-RUNTIME.md`
   - `SPEC-RECORDER.md`
   - `SPEC-REPLAY.md`
   - `SPEC-SPECTATOR.md`
   - `SPEC-VIEWER.md`
   - `SPEC.md`

## 6. Implementation Work

Completed implementation steps:

1. Strengthened parity tests.
   - Compare `.play()`, `.replay(match=...)`, and `.replay(path=...)`.
   - Deep-compare gameplay payload structure rather than only event counts.
   - Include prompt/interaction, action, state, usage, phase index, and turn context.
2. Unified gameplay event construction.
   - `EventFactory.turn()` is the shared builder.
   - `MatchRuntime.record_turn()` delegates to the shared builder.
   - Duplicate inline payload construction was removed.
3. Bumped recorder schema to v2.0.
   - Recorder serializes canonical gameplay payloads verbatim.
   - Recorder does not flatten action.
   - Recorder does not move interaction fields while writing JSON.
4. Made `ReplayEngine` v2-only.
   - Replay re-emits canonical events without legacy-shape normalization.
   - Missing or unsupported recording schemas fail fast.
5. Removed dual-shape defensive code from current runtime paths.
6. Added one-shot record migration tooling.
   - Converts retired v1.3 gameplay payloads into v2 shape.
   - Validates semantic preservation for action, reasoning, states, prompts, usage, controller metadata, and turn context.
   - Keeps runtime code v2-only.
7. Implemented `MatchSurfaceProjector`.
   - Read-only spectator.
   - Consumes canonical gameplay and lifecycle events.
   - Produces the stable Match Surface protocol.
8. Implemented sinks.
   - `InMemorySink` for tests.
   - `JsonArtifactSink` for deterministic static JSON artifacts.

## 7. Validation

Required validation:

```bash
pytest tests/integration/test_lifecycle_parity.py
pytest tests/unit/test_event_factory.py tests/unit/test_match_runtime.py
pytest tests/unit/test_recorder_lifecycle.py tests/unit/test_replay_lifecycle.py
pytest tests/unit/test_match_surface.py tests/unit/test_spectator_contracts.py
pytest tests/
./scripts/ci.sh
```

Additional checks:

- Verify converted records are schema v2.0.
- Verify one-shot conversion preserves all semantic fields required by current analysis tooling.
- Verify no checked-in runtime path accepts retired gameplay shapes as compatibility input.
- Verify generated Match Surface JSON is deterministic for identical input records.
- Verify factual Match Surface output remains stable after dual-shape cleanup.

## 8. Static Artifact Completeness

Current Core slice:

```text
historical v1.3 records
  -> safe migration bridge
  -> Recorder v2.0 derived records
  -> ReplayEngine + MatchSurfaceProjector + JsonArtifactSink
  -> complete Match Surface JSON artifact
```

Core deliverables:

1. Propagate record provenance into `MatchSurfaceDocument.source.provenance`.
   - Derived records already carry `migration_provenance`.
   - Static export must preserve that relationship in the surface artifact.
2. Import optional external curation sidecars during static export.
   - `subtitle` and `synopsis` become surface curation metadata.
   - `highlights` become upstream markers with deterministic provenance.
   - `transcript` remains sidecar-only and is not embedded in the surface artifact.
3. Keep viewer work out of Core.
   - Core ends at complete Match Surface JSON artifacts.
   - External viewers consume the artifact through their own `SurfaceDocumentLoader`.
   - No product-specific naming or routing belongs in this repository.

Validation:

- Run historical records through migration and static export without mutating originals.
- Verify every exported artifact has frames, action, interaction, state deltas, source provenance, and curation markers when sidecars are provided.
- Verify missing adjacent sidecars remain optional, while an explicit sidecar directory fails fast if a matching sidecar is absent or invalid.

## 9. Deferred Core Work

- Streaming sinks.
- Browser or remote human input bridges.
- Seat/session abstractions.
- Mid-match branching or takeover.
- New game runtimes.
- Updating the current viewer bundle for recorder schema v2.0.

These should get separate specs if they become Core work.

## 10. Resolved Review Decisions

1. The LLM I/O container is named `interaction`.
2. `phase_index` is the only structural phase key.
3. One-shot migration tooling is committed under `scripts/` for auditability.
4. Runtime code remains v2-only.
5. `SPEC-GAMEPLAY-EVENT-DATA.md` remains standalone and is referenced by Observability, MatchRuntime, Recorder, Replay, and Spectator.

## 11. References

- `CONTRIBUTING.md` - spec-first workflow and testing requirements.
- `specs/SPEC.md` - Core design principles.
- `specs/SPEC-OBSERVABILITY.md` - EventBus and spectator event language.
- `specs/SPEC-MATCH-RUNTIME.md` - gameplay event emission path.
- `specs/SPEC-RECORDER.md` - recording schema.
- `specs/SPEC-REPLAY.md` - replay parity contract.
- `specs/SPEC-SPECTATOR.md` - read-only spectator contract.
- `specs/SPEC-VIEWER.md` - current viewer contract.
