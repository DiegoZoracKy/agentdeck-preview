# SPEC-MATCH-RUNTIME Audit Note

Spec: [SPEC-MATCH-RUNTIME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MATCH-RUNTIME.md)
Wave: 2
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Per-match runtime surface exposed to mechanics for events, state validation, RNG, parse failures, and prompt capture.
- Does not own recorder schema details or console lifecycle sequencing.

## Evidence Reviewed
- spec sections: full document
- implementation files: [match_runtime.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/match_runtime.py), [console.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/console.py)
- tests: indirect coverage through [test_turn_based_mechanic.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_turn_based_mechanic.py), [test_player_ordering.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_player_ordering.py)
- docs/examples: in-spec usage example and runtime docstrings

## Findings

### Blocker
- none

### High
- The public constructor and `record_turn(...)` signature had drifted significantly from the implementation.
- The spec still advertised a `context` property that does not exist and omitted shipped properties such as `previous_match_result`, `events`, and `initial_state`.

### Medium
- The parse-failure wording made it sound like runtime could never delegate to console internals, while the actual runtime intentionally wraps a console helper.

### Low
- Example snippets in the runtime docstring still used the old match-context and setup signatures.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 0
- doc/example drift: 1

## Required Remediation
- Rewrite the public API section to the actual flattened constructor and method signatures.
- Document the shipped runtime properties, especially `initial_state`.
- Align the examples and parse-failure wording with the actual wrapper behavior.

## Beta Relevance
- required before beta: yes, because mechanic authors depend on this exact surface
- safe to defer: stronger direct unit coverage for MatchRuntime-specific helpers

## Final Verdict
- [SPEC-MATCH-RUNTIME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MATCH-RUNTIME.md) is compliant after cleanup. The runtime spec now matches the shipped mechanic-facing surface.
