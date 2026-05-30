# ROADMAP: Match Surface Core Cleanup

> Status: Phase B/C complete on `match-surface-core-cleanup`
> Date: 2026-05-30
> Repository: AgentDeck Core
> Workflow: Follows `CONTRIBUTING.md` Phase A/B/C. This is a temporary planning note, not an authoritative spec.

## 1. Purpose

Prepare AgentDeck Core for agentdeck.tv by making live play, in-memory replay, disk recording, and disk replay speak one canonical gameplay event language.

The current Core has the right architecture (`play()` / `replay()` -> `EventBus` -> `Spectators`), but the gameplay event payload shape diverges between live events and disk replay. This roadmap fixes that at the source before building the public Match Surface projection layer.

## 2. Current Provenance Anchor

Completed:

- Created and pushed annotated tag `agentic-edge-research`.
- Tag target: `82c3dd3759918ccea114ca264f4675ef9d31e348`.
- Purpose: freeze the original Agentic Edge research state, including the v1.3 record/viewer shape.

Implication:

- Core can break cleanly to schema v2.0 with no permanent runtime compatibility for v1.3.
- The original Agentic Edge research remains inspectable by checking out the tag.
- Existing Agentic Edge records needed for agentdeck.tv should be converted once into the v2 shape, not supported forever by Core runtime code.

## 3. Locked Decisions

- No second replay engine in agentdeck.tv.
- AgentDeck Core owns `play()`, `replay()`, records, EventBus, spectators, canonical gameplay event data, and Match Surface projection.
- agentdeck.tv owns public pages, dossier/report framing, routing, shareability, publishing policy, and artifact consumption.
- Core makes a clean recorder schema break to v2.0.
- No permanent v1.3 replay/record compatibility in Core after the break.
- One-shot Agentic Edge record re-serialization is allowed as a migration step, but not as runtime compatibility.
- `MatchSurfaceProjector` is built after Core gameplay event parity is honest.
- Markers stay out of raw `GameplayEventData`; they belong in projection/scoring layers downstream.
- Live challenge features are deferred: seats, `ChallengeRecipe`, `HumanPlayer` web input, SSE/WebSocket sinks, and live sessions are not v0 Core work.

## 4. Canonical GameplayEventData v2 Draft

This is the Phase A-approved shape. `SPEC-GAMEPLAY-EVENT-DATA.md` is the authoritative contract.

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

- Use `action.value`, not `action.action`, to avoid stutter.
- Do not serialize `action.raw_response`; raw model output belongs at `interaction.response_text`.
- Use only `phase_index`; remove the `turn_index` alias unless a spec proves both are needed.
- `interaction` is the container name because it holds prompt, response, usage, renderer, and controller metadata.
- Keep raw decision data separate from presentation markers.

## 5. Phase A: Specification

Per `CONTRIBUTING.md`, implementation is blocked until specs are drafted, reviewed, and approved.

Draft specs / updates:

1. Place specs flat under `specs/` using each spec's `Status` field; do not introduce a new `specs/drafts/` directory.
2. Draft and approve `SPEC-GAMEPLAY-EVENT-DATA.md`.
   - Defines canonical gameplay event payload.
   - Defines JSON-safe serialization rules.
   - Defines live/replay parity invariants.
   - Defines field ownership: action vs interaction vs state vs context.
3. Draft and approve `SPEC-MATCH-SURFACE-PROJECTION.md`.
   - Defines `MatchSurfaceProjector` as a read-only spectator.
   - Defines sink interface.
   - Defines `InMemorySink` and `JsonArtifactSink` for v0.
   - Reserves SSE/WebSocket sinks for future work.
4. Update dependent specs after review:
   - `SPEC-OBSERVABILITY.md`
   - `SPEC-MATCH-RUNTIME.md`
   - `SPEC-RECORDER.md`
   - `SPEC-REPLAY.md`
   - `SPEC-SPECTATOR.md`
   - `SPEC-VIEWER.md`
   - `SPEC.md` if the architecture summary changes

Phase A exit criteria:

- Canonical event shape is approved.
- Recorder schema v2.0 break is explicit.
- Replay parity test obligations are written as invariants.
- Projector responsibilities are limited to projection, not game logic or research scoring.
- Out-of-scope live challenge pieces are documented as future work.

## 6. Phase B: Implementation

Implementation order after Phase A approval:

1. Write failing parity tests first.
   - Compare `.play()` live spectator events, `.replay(match=...)`, and `.replay(path=...)`.
   - Deep-compare gameplay payload structure, not only event counts or player names.
   - Include prompt/interaction, action, state, usage, phase index, and turn context.
   - Replace the current player-only gameplay assertion in `tests/integration/test_lifecycle_parity.py` with a deep structural comparison. This is the regression guard that previously failed to catch the drift.
2. Unify gameplay event construction.
   - Make one builder the source of truth, likely `EventFactory.turn()`.
   - Have `MatchRuntime.record_turn()` call the shared builder.
   - Remove duplicate inline payload construction.
3. Bump recorder schema to v2.0.
   - Serialize canonical gameplay payloads verbatim.
   - Do not flatten action.
   - Do not move interaction fields around at write time.
   - Preserve JSON safety only.
4. Make `ReplayEngine` re-emit canonical v2 events.
   - Rehydrate only unavoidable JSON-to-runtime types if the spec requires it.
   - Do not normalize multiple legacy shapes.
5. Delete dual-shape defensive code.
   - Remove support for flat action + separate reasoning + nested prompt where no longer reachable.
   - Clean affected spectators, reporters, token usage tracking, curator, viewer helpers, and research utilities.
   - Treat research/behavioral scoring changes as high-risk, not cosmetic cleanup.
6. One-shot re-serialize Agentic Edge records.
   - Use the frozen tag as the original research citation.
   - Convert only the records needed for v0 product artifacts.
   - Do not add permanent v1.3 runtime compatibility.
   - Commit the converter under `scripts/` for auditability, then keep runtime code v2-only.
   - Add a migration fidelity check: every semantic field used by the v0 evidence (`action`, `reasoning`, states, prompts, usage, controller metadata, and `turn_context`) must map into the v2 shape with no silent drops.
7. Implement `MatchSurfaceProjector`.
   - Read-only spectator.
   - Consumes canonical gameplay/lifecycle events.
   - Produces the stable Match Surface protocol for frontend consumption.
8. Implement v0 sinks.
   - `InMemorySink` for tests.
   - `JsonArtifactSink` for static agentdeck.tv artifacts.
   - Future live sinks are deferred.

Phase B exit criteria:

- All implementation matches approved specs exactly.
- `.play()`, `.replay(match=...)`, and `.replay(path=...)` expose equivalent canonical gameplay payloads to spectators.
- New recordings are schema v2.0.
- v1.3 compatibility logic is not present in runtime code.
- `MatchSurfaceProjector` works from both live and replayed events.

## 7. Phase C: Testing & Validation

Required validation:

```bash
pytest tests/integration/test_lifecycle_parity.py
pytest tests/unit/test_event_factory.py tests/unit/test_match_runtime.py
pytest tests/unit/test_recorder_lifecycle.py tests/unit/test_replay_lifecycle.py
pytest tests/unit/test_match_curator.py tests/unit/test_spectator_contracts.py
pytest tests/unit/test_behavioral_scoring.py tests/unit/test_variable_damage_behavioral_scoring.py tests/unit/test_research_*.py
pytest tests/
./scripts/ci.sh
```

Additional checks:

- Verify `agentic-edge-research` remains the public provenance anchor.
- Verify generated v2 Agentic Edge records/projector artifacts cite the source tag/commit.
- Verify one-shot Agentic Edge conversion preserves all semantic fields needed for the v0 dossier.
- Verify no checked-in code path accepts old gameplay event shapes as runtime compatibility.
- Verify generated Match Surface JSON is deterministic for identical input records and export policy.
- Verify behavioral/research scorer outputs still match their approved expectations after dual-shape cleanup.

Phase C exit criteria:

- Full test suite passes without warnings.
- Deep parity tests pass.
- New v2 records replay through the same spectator surface as live matches.
- First v0 Match Surface artifact can be generated from an Agentic Edge v2 record.

## 8. AgentDeck TV Handoff

Only after Core Phase C:

1. Update agentdeck.tv docs to stop describing projection as TV-owned.
2. Replace `tools/export_public_replays.py` as the long-term producer with Core `MatchSurfaceProjector + JsonArtifactSink`.
3. Keep agentdeck.tv validation and publishing policy.
4. Build the thin Match Surface UI over Core-produced artifacts.
5. Build the Agentic Edge dossier from v2 projector artifacts and report data.

## 9. Deferred Work

Do not build in this pass:

- WebSocket or SSE live sinks.
- Web `HumanPlayer` input bridge.
- Seat model.
- `ChallengeRecipe`.
- Live challenge session API.
- Mid-match branching / "take over from turn N".
- New CombatGame runtime.
- Keeping the current `viewer/` bundle compatible with recorder schema v2.0.

These should get their own specs after static Match Surface v0 works.

## 10. Resolved Review Decisions

1. The LLM I/O container is named `interaction`.
2. `phase_index` is the only structural phase key; `turn_index` is removed from the canonical payload.
3. The one-shot Agentic Edge converter is committed under `scripts/` for auditability, but runtime code remains v2-only.
4. Core provides redaction-capable sink mechanics; agentdeck.tv owns publishing policy.
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
- `agentic-edge-research` tag - frozen Agentic Edge research provenance.
