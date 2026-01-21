# AgentDeck Roadmap

Last updated: 2026-01-21T02:39:25Z

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
- Deliverables (remaining):
  - Visual polish pass (FFVI skin spacing, typography, animations).
  - Optional debug renderer (future).

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
  - PromptBuilder test for conclusion_template=None.
  - LLMPlayer describe test when conclusion is disabled.
