# Spec Compliance Closeout

Last updated: 2026-03-26
Status: Complete

## Scope

This closeout records the final pre-release spec-compliance sweep across the active AgentDeck contract surface.

Audited areas:
- Core facade and execution kernel
- Research workflow, experiment packaging, and behavioral scoring
- Game examples and runtime helpers
- Observability, replay, and viewer surface
- Provider integrations, pricing, prompt builder, and renderer

## Final Verdict

The active spec surface is release-clean for the pre-release branch:
- no active draft specs remain under `specs/`
- implemented specs now live in `specs/` rather than `specs/drafts/`
- active spec headers no longer advertise planned or pending implementations
- the audited code paths match the shipped spec contracts after targeted drift fixes
- spec invariants touched in the sweep are now guarded by targeted tests

## Key Fixes Applied

### Spec Surface Cleanup
- Promoted shipped research specs into `specs/`
- Finalized shipped game and behavioral specs
- Removed unshipped proposals from the release branch instead of keeping an archive surface
- Removed the last active draft spec from `specs/drafts/`
- Corrected stale status/version rows in `specs/SPEC.md`

### Research And Behavioral Contracts
- Added workflow/export invariants for matrix-aware package export
- Added deterministic and serialization checks for behavioral scoring
- Tightened packager/provider inference coverage

### Runtime And Game Contracts
- Added dedicated `MatchRuntime` contract tests
- Closed VariableDamage game edge-case gaps
- Corrected runtime/spec wording drift around event emission helpers

### Observability, Replay, And Viewer
- Fixed viewer invalid-JSON error behavior to match `SPEC-VIEWER`
- Added viewer contract tests covering record loading, timeline behavior, and renderer registry guarantees
- Updated `EventFactory` and observability docs to the actual canonical gameplay payload shape

### Facade, LLM, And Pricing
- Added `AgentDeck` validation and session-snapshot coverage
- Added provider constant coverage for shipped LLM players
- Added pricing structure and packaging coverage

## Validation Evidence

The final sweep completed with:

```bash
.venv/bin/pytest \
  tests/unit/test_research_export.py \
  tests/unit/test_behavioral_scoring.py \
  tests/unit/test_variable_damage_behavioral_scoring.py \
  tests/unit/test_research_packager.py \
  tests/unit/test_research_validate.py \
  tests/unit/test_research_posthoc.py \
  tests/unit/test_match_runtime.py \
  tests/unit/test_game.py \
  tests/unit/test_variable_damage_game.py \
  tests/unit/test_controller.py \
  tests/unit/test_game_hooks.py \
  tests/unit/test_turn_based_mechanic.py \
  tests/unit/test_player_ordering.py \
  tests/unit/test_event_factory.py \
  tests/unit/test_event_bus.py \
  tests/unit/test_replay_lifecycle.py \
  tests/unit/test_spectator_contracts.py \
  tests/unit/test_monitors.py \
  tests/unit/test_auto_narrator.py \
  tests/unit/test_viewer_contracts.py \
  tests/unit/test_agentdeck.py \
  tests/unit/test_pricing.py \
  tests/unit/test_llm_player.py \
  tests/unit/test_openai_player.py \
  tests/unit/test_google_player.py \
  tests/unit/test_parallel_execution.py \
  tests/unit/test_config_concurrency.py \
  tests/unit/test_match_artifact.py \
  tests/unit/test_prompt_builder.py \
  tests/unit/test_text_renderer.py \
  -q
```

Result:
- `402 passed`
- `2 skipped`
- overall coverage in this targeted sweep: `76%`

Additional validation:

```bash
python3 scripts/research_validate.py --research-dir research
node scripts/viewer_smoke_check.js
```

Result:
- research validation passed
- viewer smoke check passed

## Residual Notes

- This closeout covers the active release-facing contract surface.
- Future unshipped proposals should stay out of the active `specs/` surface until implemented.
