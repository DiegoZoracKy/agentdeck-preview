# SPEC-AGENTDECK Audit Note

Spec: [SPEC-AGENTDECK.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-AGENTDECK.md)
Wave: 2
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Public facade contract for session construction, batch execution, replay, and researcher-facing helpers.
- Does not own match orchestration internals, recorder schema, or turn mechanics.

## Evidence Reviewed
- spec sections: full document, especially §§3-8
- implementation files: [agentdeck.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/agentdeck.py), [session.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/session.py), [types.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/types.py)
- tests: [test_agentdeck.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_agentdeck.py)
- docs/examples: in-spec examples and top-level exports in [__init__.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/__init__.py)

## Findings

### Blocker
- none

### High
- The spec still advertised unsupported public surface: `console=` injection in the constructor and explicit `close()` / `off()` helpers.
- The SessionConfig shape and examples had drifted from the current public API (`session=` instead of `config=`, real exported games instead of `CombatGame`).

### Medium
- The spec omitted public helper methods that now exist on the facade: `replay_batch()` and `get_session_stats()`.

### Low
- Seed/config wording was stale in a few places and implied constructor-level seed ownership that now lives in `AgentDeckConfig` and per-batch overrides.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 4
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Trim stale facade surface from the spec instead of adding new API just to satisfy old wording.
- Update the SessionConfig sketch and examples to the real public exports and constructor shape.
- Document the existing replay/session helper methods.

## Beta Relevance
- required before beta: yes, because this is the main user-facing library contract
- safe to defer: richer ergonomics beyond the currently shipped facade surface

## Final Verdict
- [SPEC-AGENTDECK.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-AGENTDECK.md) is compliant after the Wave 2 cleanup. The facade spec now matches the actual public API instead of older intended surface area.
