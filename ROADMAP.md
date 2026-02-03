# AgentDeck Roadmap

Last updated: 2026-02-03T13:15:56Z

> Purpose: keep a lightweight, current map of active roadmap work and recent completions.

## Read First (Required Context)
- CONTRIBUTING.md
- specs/SPEC.md
- specs/SPEC-PLAYER.md
- specs/SPEC-PROMPT-BUILDER.md
- specs/SPEC-LLM.md
- specs/SPEC-OBSERVABILITY.md
- specs/SPEC-RECORDER.md

## Rules
- Record a timestamp for each phase start and conclusion (ISO 8601 UTC).

## Current Focus
- Replay Viewer MVP (reference viewer + FFVI skin)
- Game config export (spec-first drafts in progress)

## Active Work
Phase D: Replay Viewer MVP (Reference Viewer)
- Status: In Progress
- Start: 2026-01-21T02:39:25Z
- Deliverables (done):
  - `viewer/` split into loader/timeline/app/renderer registry.
  - FixedDamage FFVI renderer wired via registry.
  - Record loader ordering aligns with `turn_index`/`phase_index`.
  - Max health derived from recorded params with frame-based fallback.
  - `specs/SPEC-VIEWER.md` + viewer docs aligned to structure.
  - Shipped sample record renders out-of-the-box (`viewer/sample-match.json` is `FixedDamageGame`).
  - Added a lightweight viewer smoke-check (`scripts/viewer_smoke_check.js`).
  - Visual polish pass (reasoning panel stabilization, winner spoiler prevention, layout bounce fixes).
  - Test match script for generating matches with mixed controllers.
- Deliverables (in progress):
  - Restructure viewer to demonstrate game-bundled viewer pattern.
  - Update registry to support (game, skin) keys.
  - Add debug renderer as second viewer for FixedDamageGame.
  - Add skin selector UI.
- Implementation steps:
  1. Restructure: Move FFVI renderer to `src/agentdeck/games/fixed_damage/viewers/ffvi/`
  2. Registry: Update to support `register(game, skin, RendererClass)` + `getAll(game)`
  3. Debug renderer: Create minimal `viewers/debug/` with state-focused view
  4. UI: Add skin dropdown to controls
  5. Wiring: Update index.html paths and registration
  6. Tests: Update smoke check for new structure

Phase E: Game Config Export (Spec-First)
- Status: Drafting
- Start: 2026-01-21T02:39:25Z
- Deliverables (drafted):
  - `specs/drafts/SPEC-GAME-v0.8.0.md` (Game.describe + params).
  - `specs/drafts/SPEC-RECORDER-v1.4.0.md` (game_config.params).
- Deliverables (remaining):
  - Approvals and promotion to `specs/`.
  - Implement `Game.describe()` + `get_config_params()`.
  - Recorder wiring to store `game_config.params`.
  - Update example games + tests for metadata.

## Recent Work (Complete)
Phase A: Conclusion Defaults + Disabled Conclusion Templates (Spec Alignment)
- Status: Complete
- Start: 2026-01-20T23:58:19Z
- End: 2026-01-20T23:58:19Z
- Deliverables:
  - SPEC-PLAYER: default conclusion records metadata; describe reports None.
  - SPEC-PROMPT-BUILDER: explicit None disables conclusion composition; compose raises.
  - SPEC-LLM: None disables conclusion prompt composition, but records metadata.

Phase B: Implementation (PromptBuilder + Player/LLMPlayer)
- Status: Complete
- Start: 2026-01-20T23:58:19Z
- End: 2026-01-20T23:58:19Z
- Deliverables:
  - PromptBuilder sentinel for defaults; None disables conclusion template.
  - Base Player concludes with minimal prompt metadata; safe fallback.
  - LLMPlayer defers to base when conclusion template is disabled.

Phase C: Validation (Unit Tests)
- Status: Complete
- Start: 2026-01-20T23:58:19Z
- End: 2026-01-20T23:58:19Z
- Deliverables:
  - Ensure existing experiments conform to the spec with no drift.
  - Update templates if the spec tightens or clarifies fields.
- Acceptance:
  - Templates match the finalized spec.
  - `research/INDEX.md` output matches spec requirements.

Phase 4: Release Polish
- Status: Complete
- Start: 2026-01-20T01:05:29Z
- End: 2026-01-20T01:07:13Z
- Deliverables:
  - Update repo URLs from `agentdeck-preview` to `agentdeck`.
  - Reconcile spec statuses (Player, Recorder, ReplayEngine).
  - Mark research directory as reference examples.
- Acceptance:
  - No `agentdeck-preview` URLs remain in docs/config.
  - Spec statuses align with v0.1.0 release messaging.
  - research/README.md clarifies example status.

Phase 5: Session-to-Research Packager
- Status: Complete
- Start: 2026-01-20T02:15:57Z
- End: 2026-01-20T02:34:30Z
- Deliverables:
  - Spec promoted to `specs/SPEC-RESEARCH-PACKAGER.md`.
  - Implement `src/agentdeck/research/packager.py` for core logic.
  - Add thin CLI wrapper `scripts/research_package.py`.
  - Update `research/README.md` with the new command.
  - Add tests covering manifest inference and error handling.
- Acceptance:
  - Spec approved and moved to `specs/SPEC-RESEARCH-PACKAGER.md`.
  - Running the script creates a valid experiment folder with results and index.
  - `scripts/research_validate.py` passes on generated packages.

Phase 6: Spec Compliance Review
- Status: Complete
- Start: 2026-01-21T00:00:00Z
- End: 2026-01-21T23:59:59Z
- Deliverables:
  - Phase A complete: All 20 specs reviewed for implementation compliance.
  - Drift issues identified and tracked through resolution.
- Acceptance:
  - All P0-P3 specs reviewed with clear resolution paths for drift.
  - No non-compliant items without action plan.
- Results:
  - 20 specs reviewed (~307 invariants)
  - 100% compliant: PROMPT-BUILDER, MONITOR, RESEARCH-PACKAGER
  - Critical drift identified: PRICING V0, CONTROLLER GB6/CP2, LLM PM1-PM3

Phase 7: Full Drift Resolution
- Status: Complete
- Start: 2026-01-22T00:00:00Z
- End: 2026-01-22T01:30:00Z
- Deliverables:
  - Resolve all action items identified during Phase 6 before Phase B.
  - Fix each spec in sequence, commit after each spec's fixes.
  - Specs to fix (in order):
    1. SPEC-AGENTDECK (3 items): elapsed_time property, finished_at exposure, replay type validation
    2. SPEC-CONTROLLER (2 items): GB6 unbound validation, CP2 return type alignment
    3. SPEC-GAME-MECHANIC-TURN-BASED (4 items): parse failure handling, player validation, match_id in exceptions, JSON-serializable events
    4. SPEC-LLM (7 items): ADC provider behavior, phase context, provider identifiers, estimated flags, history dedup, logging levels, metadata wiring
    5. SPEC-MATCH-RUNTIME (4 items): mechanic metadata, parse failure context, cleanup helpers, compatibility guards
    6. SPEC-OBSERVABILITY (2 items): PL3 event schema, PL4 prompt metadata
    7. SPEC-PARALLEL (3 items): fallback warning level, failure cancellation, benchmarking docs
    8. SPEC-PLAYER (2 items): DS2 metadata docs, CI3 clone audit
    9. SPEC-PRICING (2 items): V0 type check, C1 logger integration
    10. SPEC-RENDERER (2 items): format hint, field validation
    11. SPEC-RESEARCH (7 items): elapsed_time tracking, player_order_source, config snapshots, CI computation, install guidance, recording validation, schema versioning
    12. SPEC-RESEARCH-EXPERIMENT (4 items): README enforcement, provenance check, schema validation, recordings constraints
    13. SPEC-SPECTATOR (2 items): lifecycle handler stubs, handler documentation
- Acceptance:
  - All action items resolved or documented as deferred with rationale.
  - No silent failure paths remain.
- Results:
  - 12 specs received code fixes (10 commits)
  - Critical fixes: SPEC-PRICING V0, SPEC-CONTROLLER CP2, SPEC-LLM PM1-PM3
  - 26 items fixed, remaining items deferred with rationale

Phase 8: Spec → Tests (Phase B)
- Status: Complete
- Start: 2026-01-27T00:00:00Z
- End: 2026-01-27T00:00:00Z
- Deliverables:
  - Added tests for Phase 7 invariants (E3, R1, TL6, MO1).
  - Hardened tests with tmp_path isolation, removed timing dependencies.
  - Fixed TL5/FP1/RE2/RE8 drift per Codex review.
- Acceptance:
  - 341 tests passing, 75% coverage.
  - Critical invariants have automated tests.

## Decision Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-19 | v0.1.0 release tagged | Release readiness complete |
| 2026-01-20 | Added research experiment spec + validator | Formalize and enforce experiment contracts |
| 2026-01-20 | Reconciled spec statuses + repo links | Align public signals with v0.1.0 release |
| 2026-01-20 | Drafted session-to-research packager spec | Reduce boilerplate for experiment packaging |
| 2026-01-20 | Implemented session-to-research packager | Create packages from sessions with consistent exports |
| 2026-01-21 | Completed Phase A spec compliance review | Systematic audit of all 20 specs against implementation |
| 2026-01-21 | Created drift summary and action items | Aggregate findings for prioritized resolution |
| 2026-01-22 | Expanded Phase 7 to cover ALL action items | Complete drift resolution before Phase B testing |
| 2026-01-22 | Completed Phase 7 drift resolution | 26 items fixed; remaining deferred with rationale |
| 2026-01-27 | Completed Phase 8 tests + Codex review fixes | TL5/FP1/RE2/RE8 fixes, test hardening |
