# SPEC-REPLAY Audit Note

Spec: [SPEC-REPLAY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-REPLAY.md)
Wave: 4
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- ReplayEngine artifact ingestion, lifecycle replay ordering, scheduler semantics, context hydration, and spectator isolation.
- Does not own recording, viewer UI, or live execution.

## Evidence Reviewed
- spec sections: full document, especially §§3-8 and references
- implementation files: [replay.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/replay.py), [replay_utils.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/replay_utils.py)
- tests: [test_replay_lifecycle.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_replay_lifecycle.py)
- docs/examples: replay/viewer adjacent docs

## Findings

### Blocker
- none

### High
- The spec overstated validation requirements: it claimed mandatory-section and prompt-payload validation that the shipped replay engine does not perform.
- It also described replay as refusing synthesis, while the real implementation intentionally backfills missing `PLAYER_HANDSHAKE_START` events to preserve live lifecycle order.
- The public constructor section used the wrong parameter name and implied stricter schema expectations than the real v1.x-compatible loader.

### Medium
- Timing/error semantics were too prescriptive in places (`NaN`, invalid speed type, mandatory phase metadata) compared with the actual implementation.
- Several references were pinned to older neighboring spec versions.

### Low
- none

## Drift Classification Summary
- implementation drift: 0
- spec drift: 6
- test drift: 0
- doc/example drift: 1

## Required Remediation
- Rewrite the replay contract around the actual v1.x artifact loader and tested handshake-start backfill behavior.
- Trim speculative validation requirements and align examples/references to the current implementation.

## Beta Relevance
- required before beta: yes, because replay is central to the public “inspectable and reproducible” product claim
- safe to defer: stronger future validation if replay later becomes a stricter artifact gate

## Final Verdict
- [SPEC-REPLAY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-REPLAY.md) is compliant after Wave 4 cleanup. The replay engine was already feature-complete; the spec needed to stop describing a stricter or different contract than the one that is actually implemented and tested.
