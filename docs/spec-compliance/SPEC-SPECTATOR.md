# SPEC-SPECTATOR Audit Note

Spec: [SPEC-SPECTATOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-SPECTATOR.md)
Wave: 4
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Spectator observer contract, scope semantics, logger injection, and read-only handling expectations.
- Does not own event emission, recording schema, or replay scheduling.

## Evidence Reviewed
- spec sections: full document, especially §§4-7 and examples
- implementation files: [spectator.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/base/spectator.py), [event_bus.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/event_bus.py), [reporter.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/spectators/reporter.py), [stats.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/spectators/stats.py), [token_usage.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/spectators/token_usage.py)
- tests: [test_spectator_contracts.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_spectator_contracts.py), [test_spectator_logger_injection.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_spectator_logger_injection.py), [test_match_reporter.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_match_reporter.py), [test_auto_reporter.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_auto_reporter.py)
- docs/examples: in-spec examples and exported spectator docs

## Findings

### Blocker
- none

### High
- The public API section advertised the wrong session handler signatures (`deck` argument) and implied a stricter signature contract than the actual duck-typed lifecycle handlers.
- The spec blurred the difference between lifecycle helpers defined on the base `Spectator` class and optional event-specific handlers such as `on_player_handshake_complete`.

### Medium
- One example still implied `MatchReporter(mode=...)`, which is not part of the shipped constructor surface.
- Several references were pinned to older adjacent spec versions rather than the current contract.

### Low
- none

## Drift Classification Summary
- implementation drift: 0
- spec drift: 4
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Rewrite the public API section around the real base-class signatures and the actual duck-typed event routing model.
- Fix stale examples and genericize cross-spec references.

## Beta Relevance
- required before beta: yes, because spectators are the extension point most likely to be used in public research and replay workflows
- safe to defer: additional example expansion beyond the stable observer contract

## Final Verdict
- [SPEC-SPECTATOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-SPECTATOR.md) is compliant after Wave 4 cleanup. No code changes were required; the implementation was already stable and tested, while the spec needed to catch up to the real duck-typed surface.
