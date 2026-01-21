# AgentDeck Roadmap

Last updated: 2026-01-20T23:58:19Z

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
- None (ready for next task).

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
